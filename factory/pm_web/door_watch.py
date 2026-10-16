#!/usr/bin/env python3
"""
door_watch.py -- which DOORS are open? A door is a hostname someone can reach.

WHY (D146, 2026-10-16)
  On 2026-10-16 three exposures were found by asking the right question at the right
  moment, not by tooling:
    * fusion.tazacateringphoenix.com served an unauthenticated bash shell (ttyd -W, no
      credential, /token returned an empty token)
    * nocodb.tazacateringphoenix.com served a pgweb SQL console with a WRITE credential
      against the production tazaos database
    * the ER605 forwarded :80 and :443 from the WAN straight to gflip's nginx, bypassing
      Cloudflare entirely
  Nick asked for a standing check: "so this stops being found by luck."

WHAT A DOOR IS, AND THE TWO THINGS THAT MAKE ONE
  A hostname is reachable only when BOTH exist:
    (a) a public DNS record for it, AND
    (b) a route that answers -- a Cloudflare tunnel ingress stanza, or a real public
        address that is NOT in the tailnet range
  A name with no DNS is not a door. A DNS record pointing at a tailnet address
  (100.64.0.0/10) is a door with no outside handle: the name resolves, the address does
  not route. That is the private pattern from D143-D145, and it is EXPECTED here.

HOW IT DECIDES
  It reads the ALLOW-LIST below and compares reality against it. It does not guess.
  Anything not on the list is a FINDING -- either a door that should be closed, or a door
  Nick has decided to keep and should therefore be added to the list.

READ-ONLY. It changes nothing: no DNS edit, no tunnel reload, no service touched.
"""
import json, os, re, subprocess, sys, datetime, time

ZONE = "tazacateringphoenix.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "door_watch.json")
CFG = "/etc/cloudflared/config.yml"

# -- THE ALLOW-LIST. One line per hostname Nick has DECIDED about. --
#   private = expected to resolve into the tailnet (no outside handle)
#   public  = deliberately reachable from the internet
# Anything found that is not here is reported. Add a line only with a decision.
# ── THE ROUTER (D147) ────────────────────────────────────────────────────────
# A port-forward on the ER605 is a door too, and a worse one: it sends WAN traffic
# straight to a LAN host and is INVISIBLE to every Cloudflare policy. It never shows
# up in DNS or tunnel ingress, which is why door_watch did not see it.
#
# Read from the 5-minute ER605 snapshot pulled by er605_pull.sh. If that snapshot is
# older than MAX_SNAPSHOT_AGE_MIN the router check REFUSES TO JUDGE and says so,
# rather than reporting on stale data.
SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "arch", "er605_live.json")
MAX_SNAPSHOT_AGE_MIN = 30

# Forwards Nick has DECIDED to keep. Empty is the goal: nothing should be forwarded.
# Key is "<name>|<external port>". Adding a line here IS the decision.
ALLOW_FORWARDS = {
    # e.g. "SomeService|8080": "D999 justified because ...",
}

ALLOW = {
    "architecture": "private",   # D143 the live map
    "fusion":       "private",   # D144 the team terminal (was an open shell)
    "specs":        "private",   # D145 the URS viewer
    "nocodb":       "private",   # D145 the tazaos viewer
    "chat":         "public",    # LibreChat, has its own login
    "openwebui":    "public",    # the assistant UI
    "vision":       "public",
    "www":          "public",    # behind a Cloudflare Access gate (401)
    "decisions":    "public",    # Nick: the decisions db does not matter
}

# Hostnames that live in the tunnel config but have NO DNS. Not doors. Listed so the
# report can say so out loud instead of leaving them unexplained.
KNOWN_DEAD = {"pm", "rules", "pgadmin", "pgadmin-dev"}


def run(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return "ERR:%s" % e


def resolve(name):
    """The A records the public internet sees. Empty = no door."""
    fqdn = "%s.%s" % (name, ZONE)
    out = run("getent ahostsv4 %s 2>/dev/null | awk '{print $1}' | sort -u" % fqdn)
    ips = [l.strip() for l in out.splitlines() if re.match(r"^\d+\.\d+\.\d+\.\d+$", l.strip())]
    if ips:
        return ips
    out = run("timeout 8 dig +short @1.1.1.1 %s 2>/dev/null" % fqdn)
    return [l.strip() for l in out.splitlines() if re.match(r"^\d+\.\d+\.\d+\.\d+$", l.strip())]


def is_tailnet(ip):
    try:
        a, b = int(ip.split(".")[0]), int(ip.split(".")[1])
    except Exception:
        return False
    return a == 100 and 64 <= b <= 127          # 100.64.0.0/10


def http_code(host, timeout=12):
    """Can it actually be reached from here? 000 = no answer."""
    out = run("timeout %d curl -s -o /dev/null -w '%%{http_code}' "
              "https://%s.%s/ 2>/dev/null" % (timeout, host, ZONE), timeout=timeout + 5)
    return out.strip()[-3:] if out.strip() else "000"


def tunnel_ingress():
    """Hostnames the local cloudflared config would route, if DNS pointed at them."""
    names = set()
    try:
        txt = open(CFG).read()
    except Exception:
        return names
    for m in re.finditer(r"^\s*-\s*hostname:\s*(\S+)", txt, re.M):
        h = m.group(1).strip()
        if h.endswith("." + ZONE):
            names.add(h[: -(len(ZONE) + 1)])
    return names


def check_router():
    """Port-forwards are doors that never touch DNS. Read the ER605 snapshot.

    Returns (findings, rows_ok, note). Refuses to judge on a stale snapshot.
    """
    findings, ok = [], []
    try:
        d = json.load(open(SNAPSHOT))
    except Exception as e:
        return [], [], "router snapshot unreadable (%s) -- router NOT checked" % e

    if not d.get("ok") or not d.get("logged_in"):
        return [], [], "router snapshot was not a successful logged-in read -- NOT checked"

    # Staleness guard: a watch built on an old snapshot is worse than no watch.
    #
    # USE THE EPOCH FIELD, NOT THE "iso" STRING. er605_live.py writes `iso` in the
    # ROUTER'S local time (US/Mountain) while this script runs on gflip, which is UTC.
    # Comparing the two produced a phantom 422-minute gap and the check refused to run.
    # `ts` is a plain Unix timestamp and is timezone-independent - that is the one to use.
    age_min = None
    try:
        ts = d.get("ts")
        if ts:
            age_min = abs(time.time() - float(ts)) / 60.0
        else:
            when = datetime.datetime.strptime(d.get("iso") or "", "%Y-%m-%d %H:%M:%S")
            age_min = abs((datetime.datetime.now() - when).total_seconds()) / 60.0
    except Exception:
        age_min = None   # cannot tell: fall through, judge the rows, note the weakness
    if age_min is not None and age_min > MAX_SNAPSHOT_AGE_MIN:
        return [], [], ("router snapshot is %.0f min old (max %d) -- NOT checked"
                        % (age_min, MAX_SNAPSHOT_AGE_MIN))

    rows = (d.get("tables") or {}).get("port_forward") or []
    # first row is the header; the rest are forwards
    for r in rows[1:]:
        if len(r) < 10:
            continue
        _blank, rid, name, iface, wanip, ext, internal, host, proto, status = r[:10]
        if (status or "").strip().lower() != "enabled":
            continue
        key = "%s|%s" % (name, ext)
        entry = {"id": rid, "name": name, "external": ext, "internal": internal,
                 "host": host, "proto": proto, "status": status, "iface": iface}
        if key in ALLOW_FORWARDS:
            ok.append(dict(entry, allowed=ALLOW_FORWARDS[key]))
        else:
            findings.append(entry)
    return findings, ok, ""


def main():
    now = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
    findings, ok, dead = [], [], []

    candidates = sorted(set(ALLOW) | tunnel_ingress() | KNOWN_DEAD)
    for name in candidates:
        ips = resolve(name)
        tn = [i for i in ips if is_tailnet(i)]
        pub = [i for i in ips if not is_tailnet(i)]
        want = ALLOW.get(name)

        if not ips:
            dead.append({"host": name, "why": "no DNS -- not a door",
                         "note": "in the tunnel config" if name in tunnel_ingress() else ""})
            if want == "public":
                findings.append({
                    "host": name, "severity": "high",
                    "what": "allow-listed as PUBLIC but has NO DNS -- broken, not closed",
                    "do": "re-add its DNS record, or remove it from the allow-list"})
            continue

        if want is None:
            findings.append({
                "host": name, "severity": "high",
                "what": "an UNDECIDED door: it has DNS but is not on the allow-list",
                "ips": ips,
                "do": "decide: make it private (tailnet A record + nginx + DNS-01 cert), "
                      "or add it to ALLOW as public"})
            continue

        if want == "private":
            if pub:
                findings.append({
                    "host": name, "severity": "critical",
                    "what": "marked PRIVATE but resolves to a PUBLIC address %s" % pub,
                    "ips": ips,
                    "do": "point the record at the tailnet IP (see D143-D145)"})
            else:
                ok.append({"host": name, "state": "private", "ips": tn, "https": http_code(name)})
        else:
            ok.append({"host": name, "state": "public", "ips": ips, "https": http_code(name)})

    # ── the router: port-forwards are doors too, and invisible to DNS ──
    rfind, rok, rnote = check_router()
    for fw in rfind:
        findings.append({
            "host": "ER605 port-forward",
            "severity": "critical",
            "what": ("the router forwards WAN :%s straight to %s (rule %r). A port-forward "
                     "bypasses Cloudflare entirely -- DNS, Access and the tunnel are all "
                     "irrelevant to it." % (fw["external"], fw["host"], fw["name"])),
            "ips": [],
            "do": "disable it in the router UI (Transmission > NAT > Virtual Servers), "
                  "or add it to ALLOW_FORWARDS in door_watch.py with a decision",
            "rule": fw,
        })

    payload = {
        "ts": now,
        "router": {
            "checked": not rnote,
            "note": rnote,
            "forwards_enabled": rfind + rok,
            "allowed": rok,
        },
        "what": "A door is a hostname someone can reach from the internet.",
        "allow_list": ALLOW,
        "private_ok": [o for o in ok if o["state"] == "private"],
        "public_ok": [o for o in ok if o["state"] == "public"],
        "not_doors": dead,
        "findings": findings,
        "counts": {"private": len([o for o in ok if o["state"] == "private"]),
                   "public": len([o for o in ok if o["state"] == "public"]),
                   "not_doors": len(dead), "findings": len(findings),
                   "router_checked": (1 if not rnote else 0),
                   "router_forwards": len(rfind + rok)},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp, OUT)

    print(json.dumps(payload["counts"]))
    if rnote:
        print("  NOTICE: %s" % rnote)
    for f in findings:
        print("  FINDING [%s] %s -- %s" % (f["severity"], f["host"], f["what"]))
    if not findings:
        print("  every door is as decided: %d private, %d public, %d names that are not doors"
              % (payload["counts"]["private"], payload["counts"]["public"],
                 payload["counts"]["not_doors"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
