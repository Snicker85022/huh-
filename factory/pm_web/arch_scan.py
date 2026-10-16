#!/usr/bin/env python3
"""arch_scan.py -- build the LIVE architecture page from the live machines.

Runs on gflip. Reads gflip directly and n100 over ssh, both through arch_collect.sh,
then writes exactly three files of its own:

  architecture.json           what /architecture renders (arch.py's schema)
  data/arch_live.json         every fact + the decision list, machine readable (/architecture.json)
  data/arch_repo_state.json   the repo inventory from the previous run (drives "NEW FORK")

It is read-only with respect to the system it describes: it starts nothing, stops
nothing, fetches nothing, and never edits a repository.

A repository is flagged only when a human has to choose something:
  * commits that were never pushed        -> commit it or archive the folder
  * the same project in two places        -> pick the owner
  * the same file in two trees            -> pick the owner
  * a repo with no remote at all          -> nothing is backed up
  * a repo that was not here last hour    -> NEW, and only a human can say if it may stay

Flags are rendered red on the page and pushed to ntfy when the set changes.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(HERE, "architecture.json")
LIVE = os.path.join(HERE, "data", "arch_live.json")
STATE = os.path.join(HERE, "data", "arch_repo_state.json")
COLLECT = os.path.join(HERE, "arch_collect.sh")
N100 = "taza@192.168.2.102"
NTFY = "https://ntfy.sh/taza-ops"
NTFY_FALLBACK = "http://192.168.2.102:2586/taza-llama-alerts"
CANON = "/home/taza/repo"
SYSDIRS = ("/usr/lib/systemd/system", "/lib/systemd/system", "/run/systemd", "/usr/lib/systemd/systemd")
HINTS = ("taza", "pm-os", "vision", "print", "ollama", "ornith", "mcp_shell", "fusion", "llama",
         "ntfy", "kanban", "librechat", "open-webui", "mediamtx", "cups", "ttyd", "dashboard",
         "emergency", "square", "adb", "metrics", "inference", "ipp-usb", "postgres", "dnsmasq",
         "tailscale", "apcupsd", "cloudflared", "nginx", "docker", "cron", "ssh")

# ---- the ledger: the red items Nick has ALREADY ruled on --------------------
# Rulings live in the decisions database. This file only says which ruling covers
# which item; the scan re-checks every cited ruling still exists, and a ruling
# that has gone puts its item straight back into the red list.
LEDGER_PATH = "/home/taza/repo/factory/arch/ledger.json"
DB_DECISIONS = set()     # branch_ids the collector could actually read this scan
RULED_ISSUES = []        # red items moved out of the list, with their ruling


def load_ledger():
    try:
        with open(LEDGER_PATH) as fh:
            return (json.load(fh).get("entries") or [])
    except Exception as e:                                  # noqa: BLE001
        return [dict(match="\x00never\x00", decision=None, error=str(e))]


def ledger_hit(entries, key, hay):
    """Exact scan key first, then the longest substring match. Nothing fuzzy."""
    for e in entries:
        if e.get("key") and e["key"] == key:
            return e
    best = None
    for e in entries:
        m = str(e.get("match") or "")
        if m and m in hay and (best is None or len(m) > len(str(best.get("match") or ""))):
            best = e
    return best


# --------------------------------------------------------------------------- io
def run(cmd, timeout=150):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout or "", p.stderr or "", p.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1
    except Exception as e:                                     # noqa: BLE001
        return "", str(e), 1


def run_bytes(cmd, data, timeout=150):
    """Same as run(), but feeds bytes on stdin - so the collector has exactly one copy."""
    try:
        p = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout)
        return (p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), p.returncode)
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1
    except Exception as e:                                     # noqa: BLE001
        return "", str(e), 1


def mask(s):
    """Never let a token reach a page, a log or a repo. Keeps the shape, drops the secret."""
    return re.sub(r"//[^@/\s]*@", "//***@", str(s or ""))


def trim(s, n=300):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n - 1] + "\u2026"


# ------------------------------------------------------------------------- parse
# ---------------------------------------------------------------- listeners
# Every TCP port an agent may find listening on the two boxes, with the thing
# that owns it. The scan compares this list against the live sockets; ANY
# listener that is NOT here becomes a RED "unknown listener" card. This is how
# noVNC sat on n100:6080 unseen -- a socket with no name in the inventory.
# Add a line ONLY when the port has a name and an owner. A port that is real but
# still unanswered stays OUT, on purpose, so the page keeps asking.
KNOWN_LISTENERS = {
    "taza-server": {
        "22": "sshd", "53": "dnsmasq (LAN / loopback / tailnet DNS)",
        "631": "cupsd (loopback)", "2586": "ntfy",
        "3551": "apcupsd (loopback)", "5037": "adb server (loopback)",
        "5432": "postgres", "7682": "ttyd.service", "7683": "ttyd-cc.service",
        "8080": "pgweb (docker) -> tazaos", "8081": "pgweb-dev-pipeline (docker) -> dev_pipeline",
        # Read-only factory viewers (D139/D140, 2026-10-16). Each URL names the database
        # it serves. Both connect as viewer_ro: SELECT only, no write path.
        "8082": "pgweb-spec (docker, read-only) -> spec  [specs.tazacateringphoenix.com]",
        "8083": "pgweb-decisions (docker, read-only) -> decisions  [decisions.tazacateringphoenix.com]",
        "9000": "taza-dashboard.service", "9001": "taza-emergency.service",
        "9003": "taza-kanban.service", "20241": "cloudflared metrics (loopback)",
        "41712": "tailscaled", "51874": "tailscaled",
        "60000": "ipp-usb (HP printer, loopback)",
    },
    "taza-gflip": {
        "22": "sshd", "53": "systemd-resolved (loopback)",
        "80": "nginx (redirects to https)", "443": "nginx (chat., architecture.)", "631": "cupsd (loopback)",
        "1935": "mediamtx rtmp", "3000": "admin-panel (docker)",
        "3001": "open-webui (docker)", "3080": "LibreChat (docker)",
        "4444": "mcp-shell (user@1000 unit)", "7684": "fusion-tui.service",
        "8002": "notion-mcp-proxy (docker)", "8090": "vision-app.service",
        "8095": "pm-os.service", "8096": "print-app.service",
        "8099": "rules-door.service", "8182": "mcp_shell.service",
        "8183": "mcp_shell_owui.service", "8554": "mediamtx rtsp",
        "8888": "mediamtx", "8889": "mediamtx", "8892": "mediamtx",
        "9997": "mediamtx", "11434": "ollama",
        "20241": "cloudflared metrics (loopback)",
    },
}


def parse(text):
    d = dict(host={}, svc=[], dead=[], ports=[], timers=[], cron=[], repos=[], sqlite=[],
             pgdb=[], pgrow=[], pgver="", docker=[], ls=[], files=[], shadow=[], dirs=[], tailnet=[], ts={},
             clock={})
    for line in text.splitlines():
        f = line.split("\t")
        t = f[0]
        try:
            if t == "HOST" and len(f) >= 8:
                d["host"] = dict(name=f[1], ip=f[2], kernel=f[3], uptime=f[4], mem=f[5],
                                 disk=f[6], cpu=f[7], cpuinfo=(f[8] if len(f) > 8 else ""))
            elif t in ("SVC", "USVC") and len(f) >= 5:
                d["svc"].append(dict(unit=f[1], argv=f[2], file=f[3], wd=f[4]))
            elif t == "SVCDEAD" and len(f) >= 4:
                d["dead"].append(dict(unit=f[1], state=f[2], file=f[3]))
            elif t == "PORT" and len(f) >= 6:
                d["ports"].append(dict(proto=f[1], addr=f[2], proc=f[3], pid=f[4], unit=f[5]))
            elif t == "TIMER" and len(f) >= 5:
                d["timers"].append(dict(unit=f[1], next=f[2], last=f[3], activates=f[4]))
            elif t == "CRON" and len(f) >= 2:
                d["cron"].append(f[1])
            elif t == "REPO" and len(f) >= 12:
                d["repos"].append(dict(path=f[1], branch=f[2], head=f[3], ahead=f[4], behind=f[5],
                                       dirty=f[6], bare=f[7], remotes=mask(f[8]), tracked=f[9],
                                       last=f[10], root=f[11],
                                       raw_remotes=[u for u in f[8].split(",") if u]))
            elif t == "SQLITE" and len(f) >= 3:
                d["sqlite"].append(dict(path=f[1], bytes=int(f[2] or 0)))
            elif t == "PGDB" and len(f) >= 3:
                d["pgdb"].append(dict(name=f[1], size=f[2]))
            elif t == "PGROW" and len(f) >= 4:
                d["pgrow"].append(dict(db=f[1], table=f[2], rows=f[3]))
            elif t == "PGVER" and len(f) >= 2:
                d["pgver"] = f[1]
            elif t == "LEDGER" and len(f) >= 2:
                DB_DECISIONS.update(x.strip() for x in f[1].split(",") if x.strip())
            elif t == "DOCKER" and len(f) >= 5:
                d["docker"].append(dict(name=f[1], image=f[2], status=f[3], ports=f[4]))
            elif t == "LS" and len(f) >= 5:
                d["ls"].append(dict(path=f[1], count=f[2], size=f[3], names=f[4].split()))
            elif t == "DIR" and len(f) >= 4:
                d["dirs"].append(dict(path=f[1], count=f[2], size=f[3]))
            elif t == "FILE" and len(f) >= 4:
                d["files"].append(dict(path=f[1], bytes=f[2], mtime=f[3]))
            elif t == "TSSTATE" and len(f) >= 4:
                d["ts"] = dict(state=f[1], version=f[2], self=f[3])
            elif t == "TS" and len(f) >= 6:
                d["tailnet"].append(dict(host=f[1], ip=f[2], os=f[3], state=f[4], kind=f[5]))
            elif t == "CLOCK" and len(f) >= 6:
                # D148: the INSTANT this box believes, plus where it came from.
                # Epoch only -- a formatted stamp is what caused two bugs on 2026-10-16.
                d["clock"] = dict(epoch=f[1], tz=f[2], server=f[3], synced=f[4],
                                  offset=f[5], root_distance=(f[6] if len(f) > 6 else ""))
            elif t == "SHADOW" and len(f) >= 4:
                d["shadow"].append(dict(name=f[1], path=f[2], bytes=int(f[3] or 0)))
        except (IndexError, ValueError):
            continue
    return d


def in_scope(r):
    urls = r["remotes"]
    if "Snicker85022" in urls or "tazaos" in urls or "/mnt/taza-git" in urls:
        return True
    if not urls.strip():
        return True
    return r["path"].startswith("/opt/taza")


def third_party(r):
    return "github.com" in r["remotes"] and "Snicker85022" not in r["remotes"]


def app_service(svc):
    u, f = svc["unit"], svc["file"]
    if any(f.startswith(s) for s in SYSDIRS):
        return any(h in u.lower() for h in HINTS) and "snap" not in u
    return not u.startswith("snap.")


def app_port(p):
    if p["proto"] != "tcp":
        return False
    a = p["addr"]
    if a.startswith("127.0.0.5") or a.startswith("[fe80") or a.startswith("[fd") or a.startswith("100."):
        return False
    try:
        port = int(a.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        return False
    if port == 53 or port >= 32768:
        return False
    return True


# ------------------------------------------------------------------------- cards

# ---------------------------------------------------------------- role of thing
# Every card and every red item carries one role, so product and factory are
# readable at a glance. Rules live in roles.json, first match wins. A thing that
# matches no rule is NOT guessed at: it is flagged "WHAT IS THIS?" for Nick.
ROLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roles.json")
try:
    _ROLES = json.load(open(ROLES_FILE))
except Exception:                                            # noqa: BLE001
    _ROLES = {"roles": {}, "rules": []}
ROLE_DEFS = _ROLES.get("roles", {})
ROLE_ORDER = _ROLES.get("order", ["product", "factory", "frozen", "third-party",
                                  "host", "repo", "unlabelled"])
ROLE_RULES = [r for r in _ROLES.get("rules", []) if r.get("re")]


def role_of(*bits):
    """First matching rule wins. No match => unlabelled (a human must say)."""
    blob = " ".join(str(b) for b in bits if b)
    for r in ROLE_RULES:
        try:
            if re.search(r["re"], blob):
                return r["role"]
        except re.error:
            continue
    return "unlabelled"


# ---- which units are versioned in the one repo ---------------------------
# A unit the machines run but the repo does not hold is drift: that is exactly
# how fusion-tui.service and pm-os.service went missing. Derived, not hand-listed.
REPO_UNITS = set()


def load_repo_units(canon):
    global REPO_UNITS
    out, _, rc = run(["git", "-C", canon, "ls-files"])
    if rc != 0:
        return
    REPO_UNITS = {os.path.basename(l.strip()) for l in out.splitlines()
                  if l.strip().endswith((".service", ".timer"))}


def role_of_unit(unit, *bits):
    if unit in REPO_UNITS or (unit.split("@")[0] + ".service") in REPO_UNITS:
        return "product"
    return role_of(unit, *bits)


def card(name, status="done", desc="", note="", deps="", needed=None, tip=""):
    c = {"name": trim(name, 90), "status": status, "desc": trim(desc, 240),
         "note": trim(note, 160), "deps": trim(deps, 120)}
    if tip:
        c["tip"] = tip
    if needed:
        c["needed"] = [trim(x, 150) for x in needed][:8]
    return c


def chunkcards(prefix, items, per=8):
    out = []
    items = list(items)
    n = max(1, (len(items) + per - 1) // per)
    for i in range(0, len(items), per):
        part = items[i:i + per]
        pfx = prefix if n == 1 else "%s (%d/%d)" % (prefix, i // per + 1, n)
        out.append((pfx, part))
    return out


# --------------------------------------------------------------------- decisions
def find_decisions(hosts, prev):
    """Return the list of things a human must choose. Facts only, no opinions."""
    issues = []
    seen = {}

    def add(key, host, title, why, action, ev, sev=2):
        issues.append(dict(key=key, host=host, title=title, why=why, action=action, ev=ev, sev=sev,
                           role=role_of(title, why, action, " ".join(str(x) for x in ev))))

    repos = [(h["host"]["name"], r) for h in hosts for r in h["repos"]]

    by_root = {}
    for hn, r in repos:
        if r["bare"] == "true" or not in_scope(r) or not r["root"]:
            continue
        by_root.setdefault(r["root"], []).append((hn, r))
    for root, group in sorted(by_root.items()):
        if len(group) > 1:
            paths = ["%s:%s (%s @ %s)" % (hn, r["path"], r["branch"], r["head"]) for hn, r in group]
            add("duproot:" + root, ", ".join(sorted({hn for hn, _ in group})),
                "SAME PROJECT IN %d PLACES" % len(group),
                "These %d checkouts share one root commit (%s), so they are copies of the same "
                "project, not separate projects. Only one of them can be the owner." % (len(group), root[:8]),
                "Pick the owner, then archive the others. Nothing is deleted without Nick.",
                paths, sev=1)

    covered = set()
    for grp in by_root.values():
        if len(grp) > 1:
            covered |= {"%s:%s" % (hn, r["path"]) for hn, r in grp}
    by_url = {}
    for hn, r in repos:
        for u in r["raw_remotes"]:
            if "Snicker85022" in u:
                by_url.setdefault(mask(u), []).append((hn, r))
    for url, group in sorted(by_url.items()):
        if len(group) > 1 and not {"%s:%s" % (hn, r["path"]) for hn, r in group} <= covered:
            add("dupurl:" + url, ", ".join(sorted({hn for hn, _ in group})),
                "%d PUSHERS FOR ONE GITHUB REMOTE" % len(group),
                "More than one checkout on disk pushes to the same GitHub repository. That is how "
                "the same file ends up with three owners.",
                "Keep one pusher; archive the rest.", 
                ["%s:%s @ %s" % (hn, r["path"], r["head"]) for hn, r in group], sev=1)

    for hn, r in repos:
        key = "%s:%s" % (hn, r["path"])
        seen[key] = dict(root=r["root"], head=r["head"], path=r["path"], host=hn,
                         seen=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        if r["bare"] == "true" or not in_scope(r):
            continue
        if r["path"] == CANON and hn == "taza-gflip":
            if r["dirty"] not in ("0", ""):
                add("dirty:" + key, hn, "CANONICAL REPO HAS %s UNCOMMITTED FILES" % r["dirty"],
                    "The one repo is dirty. Anything uncommitted there is not in any snapshot.",
                    "Commit or discard, by hand.", ["%s @ %s, %s dirty" % (r["path"], r["head"], r["dirty"])], sev=3)
            continue
        if r["ahead"] not in ("0", "-", ""):
            add("ahead:" + key, hn, "FORK: %s COMMIT(S) NEVER PUSHED -- %s" % (r["ahead"], r["path"]),
                "%s/%s is %s commit(s) ahead of %s. Work exists there and nowhere else."
                % (hn, r["path"], r["ahead"], r["branch"] + "@" + r["head"]),
                "Commit and push it into the one repo, or archive the folder. Decide before Phase 5.",
                ["head %s on %s" % (r["head"], r["branch"]),
                 "ahead of upstream: %s" % r["ahead"],
                 "uncommitted files: %s" % r["dirty"],
                 "remotes: %s" % (r["remotes"] or "(none)")], sev=1)
        elif r["ahead"] == "0" and r["dirty"] not in ("0", "") and r["path"].startswith("/opt/taza"):
            add("optdirty:" + key, hn, "UNCOMMITTED WORK IN A LEGACY TREE: %s FILES -- %s" % (r["dirty"], r["path"]),
                "%s holds live files but its working tree is dirty." % r["path"],
                "Commit it or archive it.", ["%s" % r["path"]], sev=2)
        if not r["remotes"].strip():
            add("noremote:" + key, hn, "NO REMOTE: " + r["path"],
                "%s is a git repo with %s tracked files and no remote at all."
                % (r["path"], r["tracked"]),
                "Point it at the one repo, or archive it.", ["%s, %s dirty" % (r["path"], r["dirty"])], sev=2)
        if key not in (prev.get("repos") or {}):
            add("new:" + key, hn, "NEW REPO ON %s: %s" % (hn, r["path"]),
                "%s appeared on %s since the last scan." % (r["path"], hn),
                "Say if it may stay.", ["head %s on %s" % (r["head"], r["branch"])], sev=1)

    # ---- who owns the files: a repo tree, or a bare running copy -------
    repo_paths = {}
    for h in hosts:
        hn = h["host"].get("name", "?")
        repo_paths[hn] = sorted([r["path"] for r in h["repos"]
                                 if r["bare"] != "true" and r["root"]], key=len, reverse=True)

    def owner(hn, path):
        for rp in repo_paths.get(hn, []):
            if path == rp or path.startswith(rp + "/"):
                return rp
        return ""

    # 1. a service that is started out of some tree that is not the one repo
    for h in hosts:
        hn = h["host"].get("name", "?")
        for svc in h["svc"]:
            exe = ""
            for tok in (svc["argv"] or "").split():
                if tok.startswith("/") and not tok.startswith("--"):
                    exe = tok
            rp = owner(hn, exe) if exe else ""
            if rp and rp != CANON:
                add("runsfrom:%s:%s" % (hn, svc["unit"]), hn,
                    "SERVICE RUNS FROM A NON-CANONICAL TREE",
                    "%s is started from %s, inside %s. A live service is load-bearing on a tree "
                    "that is not the one repo." % (svc["unit"], exe, rp),
                    "Move the file and repoint the unit, then archive %s." % rp,
                    [exe, "unit " + svc["unit"], "tree " + rp], sev=2)

    # 2. the same filename living in two different checkouts on one machine
    files = {}
    for h in hosts:
        hn = h["host"].get("name", "?")
        for sh in h["shadow"]:
            if role_of(sh["path"]) == "frozen":
                continue            # an archive is not a loose copy, it is a kept one
            files.setdefault(hn + "|" + sh["name"], []).append((sh["path"], sh["bytes"]))
    for key, entries in sorted(files.items()):
        hn, name = key.split("|", 1)
        paths = [x for x, _ in entries]
        sizes = sorted({n for _, n in entries})
        repos_hit = sorted({o for o in (owner(hn, x) for x in paths) if o})
        live = [x for x in paths if not owner(hn, x)]
        differs = len(sizes) > 1
        if not differs and len(repos_hit) < 2 and len(live) < 2:
            continue
        if differs:
            title = "SAME NAME, DIFFERENT BYTES: %s" % name
            why = ("%d copies and they do not match (%s). Which copy a process loads decides "
                   "what actually runs." % (len(paths), " vs ".join("{:,}".format(n) for n in sizes)))
        elif len(repos_hit) >= 2:
            title = "ONE FILE, %d TREES: %s" % (len(repos_hit), name)
            why = ("Tracked by %d different checkouts on %s (%s). Which tree the process loads "
                   "decides what runs." % (len(repos_hit), hn, ", ".join(repos_hit)))
        else:
            title = "ONE FILE, %d LOOSE COPIES: %s" % (len(live), name)
            why = "The same filename exists %d times on %s outside any repo." % (len(live), hn)
        add("shadow:%s:%s" % (hn, name), hn, title, why, "Name the owner, then archive the rest.",
            ["%s  (%s bytes)" % (x, "{:,}".format(n)) for x, n in sorted(entries)], sev=1)

    order = {1: 0, 2: 1, 3: 2}
    issues.sort(key=lambda i: (order.get(i["sev"], 3), i["title"]))

    # ---- everything Nick has already ruled on leaves the red list -----------
    global RULED_ISSUES
    RULED_ISSUES = []
    entries = load_ledger()
    openq = []
    for i in issues:
        hay = " ".join([str(i.get("key") or ""), i["title"], i["why"], i["action"],
                        " ".join(str(x) for x in i["ev"])])
        e = ledger_hit(entries, str(i.get("key") or ""), hay)
        if e:
            did = e.get("decision")
            if did and DB_DECISIONS and did not in DB_DECISIONS:
                i["why"] += ("  [the ledger cites %s, which the decisions database no longer "
                             "holds -- so this is back to red]" % did)
            else:
                i["decided_by"], i["decided_on"] = did, e.get("date", "")
                i["ruling"], i["outstanding"] = e.get("ruling", ""), e.get("action", "")
                i["decider"] = e.get("decider", "nick")
                RULED_ISSUES.append(i)
                continue
        openq.append(i)
    issues = openq
    return issues, seen


# ----------------------------------------------------------------------- render
DIR_NOTE = {
    "/home/taza/venv-webos": "the webOS/LG control toolbox -- the one python env on the estate with a webOS driver in it (aiowebostv + websockets, built 2026-10-14 for the LG in D136). Nothing imports it yet. Nick 2026-10-15: intended product, keep for later.",
    "/home/taza/z33side": "ARCHIVED 2026-10-15. Nick's failed attempts to get the IP Webcam working on the z33 tablet -- the install payload, not code and not app data. Tarballed to ~/archive/retired-2026-10-15/z33side.tar.gz (44 MB); the folder is kept, never deleted.",
}


DB_NOTE = {
    "spec": "the SPEC database -- schema spec; the URS is spec.taza_os_user_requirement_specifications. Build records live here and nowhere else.",
    "decisions": "the DECISIONS database -- the change-management decision log, plus the change records (which URS lines moved, and the diffs).",
    "dev_pipeline": "transitional -- being split into spec + decisions; retires once nothing points at it",
    "tazaos": "older application database",
}


# ── DOORS (D146) ────────────────────────────────────────────────────────────
def _run_door_watch():
    """Which hostnames can the internet reach? Run the watch as part of the hourly
    scan so the map reports the doors it just measured and the two cannot drift.

    READ-ONLY and failure-tolerant: if door_watch cannot run, the scan still runs.
    A broken watch must never take down the map.
    """
    try:
        import subprocess as _sp
        _sp.run([sys.executable, os.path.join(HERE, "door_watch.py")],
                capture_output=True, text=True, timeout=240)
        with open(os.path.join(HERE, "data", "door_watch.json")) as fh:
            return json.load(fh)
    except Exception:
        return None


def _doors_section():
    """A door is a hostname someone can reach from the internet."""
    d = _run_door_watch()
    if not d:
        return None
    cards = []
    for f in d.get("findings", []):
        cards.append(card("DOOR -- %s" % f["host"], "fork",
                          desc=f.get("what", ""),
                          note="%s" % f.get("do", ""),
                          deps="severity: %s" % f.get("severity", "?"),
                          needed=["resolves to: %s" % ", ".join(f.get("ips", []))]))
    c = d.get("counts", {})
    if not cards and c.get("findings", 0) == 0:
        cards = [card("(none) -- every door is as decided", "done",
                      desc="%d private (tailnet only, no outside handle), %d public by "
                           "decision, %d names that are not doors"
                           % (c.get("private", 0), c.get("public", 0), c.get("not_doors", 0)),
                      note="this list must stay empty", deps="", needed=[])]
    return dict(id="doors", name="Doors  (%d)" % len(d.get("findings", [])),
                tagline="Every hostname the internet can reach. A name resolving to a "
                        "tailnet address (100.64.0.0/10) is a door with no outside handle. "
                        "Compared against the allow-list in door_watch.py (D146).",
                components=cards)


# ── CLOCKS (D148) ───────────────────────────────────────────────────────────
def _clocks_section(hosts):
    """Do the boxes agree on the time, and from where? Compare EPOCHS, not stamps.

    gflip is UTC and n100 is America/Phoenix, so a formatted string is meaningless
    across them -- that mismatch caused two bugs on 2026-10-16. The epoch is the
    instant and is timezone-independent, so that is what is compared here.
    """
    rows, missing = [], []
    for h in hosts:
        c = h.get("clock") or {}
        name = h["host"].get("name", "?")
        if not c.get("epoch"):
            missing.append(name)
            continue
        rows.append(dict(host=name, epoch=int(c["epoch"]), tz=c.get("tz", "?"),
                         server=c.get("server") or "?", synced=c.get("synced") or "?",
                         offset=c.get("offset") or "?", dist=c.get("root_distance") or "?"))
    cards = []
    if len(rows) >= 2:
        srv = {r["server"] for r in rows}
        # DO NOT compare the two epochs against each other.
        # They are sampled SEQUENTIALLY (the collector runs on gflip, then is piped to
        # n100 over ssh), so any gap between them is mostly ATTRIBUTABLE TO WHEN EACH
        # WAS POLLED, not to clock drift. A first version flagged "6s skew" on two boxes
        # that were provably within the same second - a false alarm, and a watch that
        # cries wolf is worse than no watch.
        #
        # What CAN be judged from a single sample is: is each box synchronised at all,
        # and are they using the SAME source. Genuine drift between boxes needs an
        # external reference (a third clock), which is out of scope here.
        if len(srv) > 1:
            cards.append(card("CLOCKS -- different NTP sources", "fork",
                              desc="the boxes sync to different servers: %s" % ", ".join(sorted(srv)),
                              note="pin both to the same source (D148) so they cannot diverge",
                              deps="", needed=["set NTP= in /etc/systemd/timesyncd.conf.d/ on both",
                                               "then: sudo systemctl restart systemd-timesyncd"]))
        elif len(srv) == 1 and rows:
            src = next(iter(srv))
            if "nist" not in src.lower():
                cards.append(card("CLOCKS -- shared source is not NIST", "fork",
                                  desc="both boxes use %s" % src,
                                  note="they agree with each other, but not with an authoritative clock",
                                  deps="", needed=[]))
        bad = [r for r in rows if r["synced"] != "yes"]
        if bad:
            cards.append(card("CLOCK -- not synchronised", "fork",
                              desc="%s reports NTPSynchronized != yes"
                                   % ", ".join(r["host"] for r in bad),
                              note="time may be wrong on that box",
                              deps="", needed=[]))
    if missing:
        cards.append(card("CLOCK -- no clock facts from %s" % ", ".join(missing), "fork",
                          desc="the collector did not report CLOCK for that box",
                          note="arch_collect.sh needs a CLOCK line there",
                          deps="", needed=[]))
    if not cards and rows:
        cards = [card("(in sync) -- both boxes on the same source", "done",
                      desc="; ".join("%s %s via %s (offset %s)" % (r["host"], r["tz"], r["server"], r["offset"])
                                     for r in rows),
                      note="epochs agree; the timezones are meant to differ",
                      deps="D148", needed=[])]
    return dict(id="clocks", name="Clocks  (%d)" % len([c for c in cards if c.get("status") == "fork"]),
                tagline="Do the boxes agree on the time, and from where? Compared by EPOCH, "
                        "never by formatted stamp -- gflip is UTC and n100 is America/Phoenix, "
                        "and that mismatch caused two bugs on 2026-10-16.",
                components=cards)


def build(hosts, issues, prev, errors):
    g = next((h for h in hosts if h["host"].get("name") == "taza-gflip"), {})
    n = next((h for h in hosts if h["host"].get("name") == "taza-server"), {})
    sections = []

    cards = []
    for i in issues:
        cards.append(card(i["title"], "fork", desc=i["why"],
                          note="decide: " + i["action"], deps="host: " + i["host"],
                          needed=[str(x) for x in i["ev"]]))
    if not cards:
        cards.append(card("Nothing is waiting on your decision", "done",
                          desc="Every red item the scan has found has already been ruled on, and "
                               "has moved to 'Already decided' below with the action that closes it.",
                          note="the scan never re-asks a question Nick has already answered",
                          deps="%d ruled item(s) tracked" % len(RULED_ISSUES),
                          needed=["every cited ruling was verified this scan: %d decision id(s) read "
                                  "from the decisions database" % len(DB_DECISIONS),
                                  "every hour the scan re-reads the decisions database",
                                  "if a cited ruling has gone, that item goes straight back to red"]))
    sections.append(dict(id="decide", name="Needs a decision from Nick  (%d)" % len(issues),
                         tagline="ONLY what is genuinely still open is in here. Anything Nick has "
                                 "already ruled on has left this list and sits under 'Already "
                                 "decided'. Nothing is moved or deleted automatically.",
                         components=cards))

    # ---- already decided: what is left is an action, not a question --------
    if RULED_ISSUES:
        cards = []
        for i in RULED_ISSUES:
            who = ("no decision needed" if i.get("decider") == "agent"
                   else "decided %s" % (i.get("decided_on") or ""))
            cards.append(card(i["title"], "decided",
                              desc="%s -- %s" % (who, i.get("ruling", "")),
                              note="still to do: " + (i.get("outstanding") or i["action"]),
                              deps=("decision " + i["decided_by"]) if i.get("decided_by")
                                   else "the agent's own open work",
                              needed=[str(x) for x in i["ev"]]))
        sections.append(dict(id="decided", name="Already decided -- the action is still "
                             "outstanding  (%d)" % len(cards),
                             tagline="Nothing in here needs Nick. Each item already has a ruling in "
                                     "the decisions database (or is the agent's own uncommitted "
                                     "work), and the card says what closes it. Every cited ruling was "
                                     "re-checked this scan: %d decision id(s) read from the database."
                                     % len(DB_DECISIONS),
                             components=cards))

    # ---- the rules -------------------------------------------------------
    sections.append(dict(id="rules", name="The rules", tagline="Three rules hold the whole estate "
                         "together -- they are why this page can stay simple.", components=[
        card("ONE markdown in the factory", "done",
             desc="In the development / FACTORY stack there is exactly ONE .md file: README-FIRST.md. "
                  "The PRODUCT stack may hold any file type, markdown included.",
             note="factory = what builds and operates it; product = what actually runs",
             deps="the only .md allowed: README-FIRST.md",
             needed=["factory: README-FIRST.md is the ONLY .md allowed",
                     "product: any file type allowed -- markdown is fine",
                     "long factory docs live in HTML (factory/docs/doctrine.html)"]),
        card("TWO development databases, on n100", "done",
             desc="spec = the SPEC database (schema spec; the URS is spec.taza_os_user_requirement_specifications) "
                  "and the build records. decisions = the DECISIONS database: the decision log, plus the change "
                  "records (which URS lines moved, and the diffs). Each record goes in exactly one of them.",
             note="spec  +  decisions;  dev_pipeline is transitional",
             deps="n100 192.168.2.102:5432",
             needed=["spec -- the specs, and the build records",
                     "decisions -- the decision log, and the change records",
                     "dev_pipeline -- transitional, retires once nothing points at it"]),
        card("one repo, one way in", "done",
             desc="The one repo (huh-) holds product/ and factory/. The factory rules are readable over plain "
                  "HTTP: the rules door -- whitelist only, read-only, one unit in the repo.",
             note="LAN http://192.168.2.107:8099/   |   tailnet http://100.65.71.49:8099/  (the public name was deleted 2026-10-15, D137)",
             deps="factory/rules-door/serve_rules.py",
             needed=["/README-FIRST.md   /roles.json   /architecture.json", "404 for everything else"]),
    ]))

    # ---- canonical -------------------------------------------------------
    canon_repo = next((r for r in g.get("repos", []) if r["path"] == CANON), {})
    cards = [
        card("The one repo: huh-", "done",
             desc="%s on gflip. Branch %s at %s, %s tracked files. origin: github.com/Snicker85022/huh-"
                  % (CANON, canon_repo.get("branch", "?"), canon_repo.get("head", "?"), canon_repo.get("tracked", "?")),
             note="single source of truth (D95)",
             deps="git remote origin", needed=["dirty files right now: %s" % canon_repo.get("dirty", "?"),
                                               "last commit: %s" % canon_repo.get("last", "?")]),
        card("huh-/product", "done", desc="running kitchen code: kanban, dashboard, emergency, "
             "checklist-app, order-ingest, vision-stack, print-app, systemd units",
             note="what the machines actually run", deps="product/",
             needed=["product/n100/kitchen", "product/n100/scripts", "product/n100/services"]),
        card("huh-/factory", "not_started", desc="pipeline tooling: fusion-harness, job_runner, "
             "pm_web (this page), scripts, specs",
             note="planned, does not exist yet", deps="factory/ (absent)",
             needed=["pm_web -- this portal", "fusion-harness", "job_runner", "scripts", "specs"]),
        card("Toshiba mirror", "done", desc="/mnt/taza-git/git/tazaos.git on n100, a bare mirror of GitHub",
             note="backup, not an owner", deps="taza-git-sync.timer", needed=["http mirror of huh-"]),
    ]
    sections.append(dict(id="canonical", name="Canonical map", tagline="One repo, two folders. "
                         "Everything else on disk is a mirror, a backup, a clone of somebody else's "
                         "code, or a fork that owes a decision.", components=cards))

    # ---- machines --------------------------------------------------------
    cards = []
    for h in hosts:
        hh = h["host"]
        if not hh:
            continue
        role = {"taza-gflip": "build + local inference + the portals (:8088 :8090 :8095 :8096 :3080)",
                "taza-server": "always-on: postgres, kanban screens, printers, cameras, dashboards"}.get(
            hh["name"], "")
        cards.append(card("%s  %s" % (hh["name"], hh["ip"]), "done",
                          desc="%s, %s cores, %s" % (hh.get("cpuinfo") or hh.get("cpu", ""), hh.get("cpu", ""), hh.get("kernel", "")),
                          note=role, deps=hh.get("uptime", ""),
                          needed=["memory %s" % hh.get("mem", ""), "disk %s" % hh.get("disk", ""),
                                  "%d services running" % len(h["svc"]),
                                  "%d git checkouts" % len(h["repos"]),
                                  "%d databases" % (len(h["pgdb"]) + len(h["sqlite"]))]))
    sections.append(dict(id="machines", name="Machines", tagline="Two boxes. gflip builds, "
                         "n100 serves. Ports below are the contract between them.",
                         components=cards))

    # ---- services --------------------------------------------------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        p_by_unit = {}
        for p in h["ports"]:
            if p["unit"]:
                p_by_unit.setdefault(p["unit"], []).append(p["addr"])
        for s in h["svc"]:
            if not app_service(s):
                continue
            argv = s["argv"] or ""
            exe = ""
            for tok in argv.split():
                if tok.startswith("/") and not tok.startswith("--"):
                    exe = tok
            cards.append(card("%s" % s["unit"], "done" if s["file"] else "unknown",
                              desc="%s :: %s" % (hn, exe or argv),
                              note=("listening " + ", ".join(sorted(set(p_by_unit.get(s["unit"], [])))))
                                   if p_by_unit.get(s["unit"]) else "",
                              deps=s["file"] or "unit file not on disk",
                              needed=["$ " + trim(argv, 200)] + (["working dir " + s["wd"]] if s["wd"] else [])))
        for s in h["dead"]:
            if not app_service(dict(unit=s["unit"], file=s["file"])):
                # a disabled unit that is OURS still belongs on the map: retirement
                # is a fact about the estate, not something to hide.
                if role_of_unit(s["unit"], s["file"] or "") in ("third-party",
                                                                "unlabelled"):
                    continue
            if s["state"] == "inactive" and not s["file"]:
                continue
            cards.append(card(s["unit"], "fork" if s["state"] == "failed" else "unknown",
                              desc="%s :: not running (%s)" % (hn, s["state"]),
                              note="retired, or never started" if s["state"] != "failed"
                                   else "FAILED -- look at it",
                              deps=s["file"], needed=["systemctl status " + s["unit"],
                                                      "journalctl -u " + s["unit"] + " -n 20"]))
    sections.append(dict(id="services", name="Services", tagline="What is actually running, the "
                         "exact file that starts it, and the port it owns. Failed units are red.",
                         components=cards))

    # ---- ports -----------------------------------------------------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        items = []
        for p in sorted([p for p in h["ports"] if app_port(p)], key=lambda p: int(p["addr"].rsplit(":", 1)[1])):
            port = p["addr"].rsplit(":", 1)[1]
            who = p["unit"] or p["proc"] or "?"
            if port == "631":
                who = who + " (cups)"
            items.append("%s  %s  %s" % (p["addr"], who, ("pid " + p["pid"]) if p["pid"] and not p["unit"] else ""))
        for pfx, part in chunkcards(hn + " -- listening (tcp)", items):
            cards.append(card(pfx, "done", desc="%d socket(s), loopback and LAN" % len(part),
                              note="", deps="", needed=part))
    sections.append(dict(id="ports", name="Ports", tagline="Every TCP socket that answers, and the "
                         "unit that owns it.", components=cards))

    # ---- unknown listeners: any live TCP socket the inventory does not name --
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        known = KNOWN_LISTENERS.get(hn, {})
        seen = {}
        for p in h["ports"]:
            if p["proto"] != "tcp":
                continue
            try:
                port = p["addr"].rsplit(":", 1)[1]
            except (ValueError, IndexError):
                continue
            seen.setdefault(port, p)
        for port in sorted(seen, key=lambda x: int(x) if x.isdigit() else 0):
            if port in known:
                continue
            p = seen[port]
            who = p["unit"] or p["proc"] or "no owner"
            cards.append(card("UNKNOWN LISTENER -- %s :%s" % (hn, port), "fork",
                              desc="a socket is listening on %s that no inventory line names" % p["addr"],
                              note="UNOWNED -- name it, or shut it",
                              deps="owner: %s" % who,
                              needed=["$ sudo ss -lntp | grep :%s" % port,
                                      "pid %s, process %s" % (p["pid"] or "?", p["proc"] or "?"),
                                      "then add it to KNOWN_LISTENERS or close it"]))
    if not cards:
        cards = [card("(none) -- every listener is named", "done",
                      desc="the inventory accounts for every listening TCP socket on both boxes",
                      note="this list must stay empty", deps="", needed=[])]
    sections.append(dict(id="listeners", name="Unknown listeners", tagline="Every TCP socket on the "
                         "estate that the inventory does NOT name. A port with no name is how noVNC hid "
                         "on n100:6080 for months. This list must be empty.", components=cards))
    # ---- doors (D146): every hostname the internet can reach ------------
    _ds = _doors_section()
    if _ds:
        sections.append(_ds)

    # ---- clocks (D148): do the boxes agree, and from where --------------
    sections.append(_clocks_section(hosts))

    # ---- databases -------------------------------------------------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        if h["pgver"]:
            for db in h["pgdb"]:
                rows = [f"{r['table']}: {r['rows']} rows" for r in h["pgrow"] if r["db"] == db["name"]]
                cards.append(card("postgres: %s" % db["name"], "done",
                                  desc="%s on %s, %s" % (db["size"], hn, trim(h["pgver"], 60)),
                                  note=DB_NOTE.get(db["name"], ""),
                                  deps="psql -d %s" % db["name"], needed=rows or ["no counts wanted"]))
        for s in h["sqlite"]:
            mb = s["bytes"] / 1048576.0
            cards.append(card("sqlite: %s" % os.path.basename(s["path"]), "done",
                              desc="%s on %s (%s)" % (s["path"], hn, ("%.1f MB" % mb) if mb >= 1 else ("%d KB" % (s["bytes"] // 1024))),
                              note="file database", deps="sqlite3 " + s["path"],
                              needed=["tables: sqlite3 %s .tables" % s["path"]]))
    for h in hosts:
        for d in h["docker"]:
            if "pg" in d["name"].lower() or "vector" in d["image"].lower() or "mongo" in d["image"].lower():
                cards.append(card("container db: %s" % d["name"], "done",
                                  desc="%s on %s -- %s" % (d["image"], h["host"].get("name", "?"), d["status"]),
                                  note="data lives inside the container volume", deps="docker exec",
                                  needed=["image " + d["image"], "ports " + mask(d["ports"])]))
    sections.append(dict(id="databases", name="Databases", tagline="Every store, where it lives, and "
                         "how many rows it holds. TWO development databases: spec (the SPEC database -- schema spec, the URS is spec.taza_os_user_requirement_specifications) and "
                         "decisions (the change-management decision log).",
                         components=cards))

    # ---- repositories ----------------------------------------------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        for r in sorted(h["repos"], key=lambda r: r["path"]):
            if r["bare"] == "true":
                st, tag = "resolved", "bare mirror"
            elif r["path"] == CANON and hn == "taza-gflip":
                st, tag = "done", "the one repo"
            elif third_party(r):
                st, tag = "not_started", "third-party clone, not ours"
            elif in_scope(r):
                st, tag = ("fork" if r["ahead"] not in ("0", "-", "") else "unknown"), "our lineage"
            else:
                st, tag = "unknown", "unclassified"
            cards.append(card(r["path"], st,
                              desc="%s @ %s -- %s files tracked, %s dirty" % (r["branch"], r["head"], r["tracked"], r["dirty"]),
                              note="%s | %s" % (hn, tag),
                              deps=trim(r["remotes"] or "(no remote)", 118),
                              needed=["branch %s, head %s" % (r["branch"], r["head"]),
                                      "ahead %s / behind %s of %s" % (r["ahead"], r["behind"], r["branch"]),
                                      "uncommitted: %s" % r["dirty"],
                                      "last commit: %s" % r["last"],
                                      "root commit: %s" % r["root"][:12]]))
    sections.append(dict(id="repositories", name="Repositories", tagline="Every git checkout on both "
                         "boxes. 'our lineage' means it pushes to huh- or the Toshiba mirror.",
                         components=cards))

    # ---- automation ------------------------------------------------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        if h["cron"]:
            for pfx, part in chunkcards(hn + " -- cron", h["cron"]):
                cards.append(card(pfx, "done", desc="user crontab", note="", deps="", needed=part))
        live = ["%s  ->  next %s" % (t["unit"], t["next"] or "not scheduled")
                for t in h["timers"] if t["activates"] and any(x in t["unit"] for x in HINTS)]
        for pfx, part in chunkcards(hn + " -- timers", live):
            cards.append(card(pfx, "done", desc="systemd timers that touch our services",
                              note="", deps="", needed=part))
    cards.append(card("the collector -- arch_collect.sh + arch_scan.py", "done",
                      desc="read-only facts from both boxes -> this page, hourly at :05",
                      note="the map is machine-written, never hand-drawn",
                      deps="cron: 5 * * * * /usr/bin/python3 /home/taza/repo/factory/pm_web/arch_scan.py",
                      needed=["arch_collect.sh runs on each box: units, ports, cron, git, postgres, docker, trees",
                              "arch_scan.py merges both boxes into architecture.json, which renders this page",
                              "it only reads - it never writes, restarts, fetches or installs anything"]))
    sections.append(dict(id="automation", name="Automation", tagline="What runs by itself: cron and "
                         "timers. This scan is one of them.", components=cards))

    # ---- files -----------------------------------------------------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        for d in h["ls"]:
            for i, (pfx, part) in enumerate(chunkcards("%s" % d["path"], d["names"])):
                cards.append(card(pfx if len(d["names"]) <= 8 else "%s (%d)" % (d["path"], i + 1), "done",
                                  desc="%s entries, %s, on %s" % (d["count"], d["size"], hn),
                                  note="", deps="ls " + d["path"], needed=part))
        for f in h["files"]:
            cards.append(card(f["path"], "done", desc="%s bytes, modified %s" % (f["bytes"], f["mtime"]),
                              note="", deps="", needed=[]))
    sections.append(dict(id="files", name="Files", tagline="The directories that matter, by name. "
                         "This is the list a fresh agent should read before it touches anything.",
                         components=cards))

    # ---- trees: every top-level folder, one card each, coloured by role ---
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        for dd in sorted(h["dirs"], key=lambda x: -int(x["count"] or 0)):
            p = dd["path"].rstrip("/")
            cards.append(card(p, "done",
                              desc="on %s -- %s files, %s" % (hn, dd["count"], dd["size"]),
                              note=DIR_NOTE.get(p, "top-level tree"), deps="", needed=["ls -la " + p]))
    sections.append(dict(id="trees", name="Trees  (%d folders)" % len(cards),
                         tagline="Every top-level folder on both boxes, biggest first, coloured by what "
                                 "it IS. Read this to see which is product and which is factory.",
                         components=cards))

    # ---- tailnet: tailscale, the way in from outside the LAN ---------------
    cards = []
    for h in hosts:
        hn = h["host"].get("name", "?")
        if not h.get("ts") and not h.get("tailnet"):
            cards.append(card("%s -- no tailscale" % hn, "unknown",
                              desc="tailscale is not installed on %s, so the tailnet reaches this "
                                   "box only by way of n100" % hn,
                              note="nothing to do unless we want this box reachable from outside",
                              deps="tailscaled not installed",
                              needed=["no tailscale binary on %s" % hn,
                                      "the tailnet is not a VLAN -- it is a separate, encrypted path"]))
            continue
        t = h.get("ts") or {}
        if t:
            cards.append(card("tailscaled on %s" % hn, "done" if t.get("state") == "Running" else "unknown",
                              desc="backend %s, tailscale %s, node %s" % (t.get("state", "?"),
                                                                          t.get("version", "?"),
                                                                          t.get("self", "?")),
                              note="the machine we reach from outside the LAN",
                              deps="tailscaled.service  (enabled at boot)",
                              needed=["backend state: %s" % t.get("state", "?"),
                                      "this node: %s" % t.get("self", "?"),
                                      "always-on, outbound-initiated: no port forward, no open WAN port"]))
        for n in h.get("tailnet", []):
            self_ = (n["kind"] == "self")
            cards.append(card("%s  %s" % (n["host"], n["ip"]),
                              "done" if n["state"] == "online" else "unknown",
                              desc="on the tailnet: %s, %s (seen from %s)" % (n["os"], n["state"], hn),
                              note="this box" if self_ else "tailnet peer",
                              deps="tailscale control plane",
                              needed=["ip %s" % n["ip"], "os %s" % n["os"], "state %s" % n["state"],
                                      "reached from outside without opening a port on the ER605"]))
    sections.append(dict(id="tailnet", name="Tailnet",
                         tagline="Tailscale: the private, encrypted path in from OUTSIDE the LAN. "
                                 "It needs no port forward and no open WAN port -- every node dials "
                                 "out. Separate from the VLAN plan, and it does not replace the "
                                 "port forwards.", components=cards))

    # ---- role on every card, then the list nobody has labelled ------------
    for sec in sections:
        for c in sec["components"]:
            nm = str(c.get("name") or "")
            if sec["id"] == "rules":
                c["role"] = "factory"       # the rules ARE factory rules
                continue
            if sec["id"] == "tailnet":
                c["role"] = "host"          # every tailnet card is a node or the client on one
                continue
            if sec["id"] in ("decide", "decided"):
                _r = role_of(c.get("name"), c.get("desc"), c.get("note"))
                c["role"] = "factory" if _r == "unlabelled" else _r
                continue
            if nm.endswith((".service", ".timer")):
                c["role"] = role_of_unit(nm, c.get("desc"), c.get("note"), c.get("deps"))
            else:
                c["role"] = role_of(c.get("name"), c.get("desc"), c.get("note"), c.get("deps"),
                                    " ".join(c.get("needed") or []))

    unknown = []
    for i in issues:
        if i.get("role") == "unlabelled":
            unknown.append(dict(kind="a red item", what=i["title"], host=i["host"],
                                facts=i.get("why", ""), hint=i.get("action", "")))
    for h in hosts:
        hn = h["host"].get("name", "?")
        for r in h["repos"]:
            if role_of(r["path"], r["root"], r["branch"]) == "unlabelled":
                unknown.append(dict(kind="a git checkout", what=r["path"], host=hn,
                                    facts="%s files tracked, %s dirty, %s @ %s, root %s, remotes %s"
                                          % (r["tracked"], r["dirty"], r["branch"], r["head"],
                                             r["root"][:10], trim(r["remotes"] or "(none)", 46)),
                                    hint="product, factory, or archive?"))
        for s in h["svc"]:
            if role_of_unit(s["unit"], s["file"], s["wd"], s["argv"]) == "unlabelled":
                unknown.append(dict(kind="a running service", what=s["unit"], host=hn,
                                    facts=trim(s["argv"], 130), hint="product, factory, or dead?"))
        for d in h["ls"]:
            if role_of(d["path"], " ".join(d["names"])) == "unlabelled":
                unknown.append(dict(kind="a directory", what=d["path"], host=hn,
                                    facts="%s entries, %s" % (d["count"], d["size"]),
                                    hint="product, factory, or archive?"))
        for dd in h["dirs"]:
            if role_of(dd["path"]) == "unlabelled":
                unknown.append(dict(kind="a top-level tree", what=dd["path"].rstrip("/"), host=hn,
                                    facts="%s files, %s" % (dd["count"], dd["size"]),
                                    hint="product, factory, or archive?"))
    if unknown:
        ucards = [card(u["what"], "fork", desc="%s on %s" % (u["kind"], u["host"]),
                       note="what is this?  " + u["hint"], deps="",
                       needed=[u["facts"], "answer: product / factory / dead / archive"])
                  for u in unknown]
        sections.insert(1, dict(id="label", name="Say what these are  (%d)" % len(unknown),
                                tagline="These cannot be classified from the machines alone, so "
                                        "they are not guessed at. Nick names each one once and it "
                                        "gets a colour; say archive and it leaves this list.",
                                components=ucards))

    pos = 2 if unknown else 1
    for i, sec in enumerate(sections):
        if sec["id"] == "trees":
            if i != pos:
                sections.insert(pos, sections.pop(i))
            break
    ti = next((i for i, s2 in enumerate(sections) if s2["id"] == "tailnet"), None)
    mi = next((i for i, s2 in enumerate(sections) if s2["id"] == "machines"), None)
    if ti is not None and mi is not None and ti != mi + 1:
        sections.insert(mi + 1, sections.pop(ti))

    for sec in sections:
        if sec["id"] in ("machines", "ports", "automation", "tailnet"):
            for c in sec["components"]:
                if c.get("role") == "unlabelled":
                    c["role"] = "host"

    role_counts = {}
    for sec in sections:
        for c in sec["components"]:
            k = c.get("role", "unlabelled")
            role_counts[k] = role_counts.get(k, 0) + 1

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    nxt = datetime.fromtimestamp(time.time() + (3600 - time.time() % 3600)).strftime("%H:%M")
    tail = ("%d item(s) need YOUR decision; %d already decided, action outstanding"
            % (len(issues), len(RULED_ISSUES))) if (issues or RULED_ISSUES) \
        else "No forks, no duplicate clones, no shadowed files"
    # ---- cluster every section by role, so like sits with like --------------
    def _rk(c):
        r = c.get("role", "unlabelled")
        return ROLE_ORDER.index(r) if r in ROLE_ORDER else len(ROLE_ORDER)
    for sec in sections:
        sec["components"].sort(key=_rk)
        for c in sec["components"]:
            c["group"] = c.get("role", "unlabelled")

    arch = dict(title="Live System Architecture",
                subtitle="Read off the machines at %s by arch_scan.py, hourly. %s. "
                         "Red cards need a decision. Nothing here is hand-written." %
                         (stamp, tail),
                sections=sections,
                roles=dict(defs=ROLE_DEFS, rules=ROLE_RULES, counts=role_counts,
                           order=ROLE_ORDER))
    live = dict(generated_at=stamp, next_run="%s (hourly cron)" % nxt,
                scan_seconds=round(time.time() - started, 1),
                errors=errors, decisions=issues, canonical=CANON,
                hosts=[{k: v for k, v in h.items() if k in ("host", "svc", "dead", "ports", "timers",
                                                            "cron", "sqlite", "pgdb", "pgrow", "pgver",
                                                            "clock")}
                       for h in hosts],
                repositories=[dict(host=h["host"].get("name"), **r) for h in hosts for r in h["repos"]],
                shadow={s["name"]: s["path"] for h in hosts for s in h["shadow"]},
                containers=[dict(host=h["host"].get("name"), **d) for h in hosts for d in h["docker"]],
                directories=[dict(host=h["host"].get("name"), **d) for h in hosts for d in h["ls"]],
                 trees=[dict(host=h["host"].get("name"), **dd) for h in hosts for dd in h["dirs"]],
                roles=dict(defs=ROLE_DEFS, rules=ROLE_RULES, counts=role_counts),
                unlabelled=[dict(kind=u["kind"], what=u["what"], host=u["host"]) for u in unknown])
    return arch, live


# ---------------------------------------------------------------------- notify
def notify(issues, prev_issues, errors):
    keys = sorted(i["key"] for i in issues)
    if keys == sorted(prev_issues):
        return None
    new = [i for i in issues if i["key"] not in prev_issues]
    gone = [k for k in prev_issues if k not in keys]
    if not keys and not gone:
        return None
    head = "ARCHITECTURE: %d item(s) need a decision" % len(issues)
    body = "\n".join("- " + i["title"] + " :: " + i["action"] for i in (new or issues)[:6])
    if gone:
        body += "\n(cleared: %d)" % len(gone)
    msg = head + "\n" + body + "\nhttp://192.168.2.107:8095/architecture"
    out = []
    for url in (NTFY, NTFY_FALLBACK):
        o, e, rc = run(["curl", "-s", "--max-time", "8", "-d", msg, url], timeout=12)
        out.append("%s rc=%s %s" % (url, rc, trim(e, 60)))
    return out


# ------------------------------------------------------------------------ main
started = time.time()
quiet = "--quiet" in sys.argv
errors = []
gout, gerr, grc = run(["bash", COLLECT], timeout=120)
if grc != 0:
    errors.append("local collect rc=%s %s" % (grc, trim(gerr, 200)))
with open(COLLECT, "rb") as _fh:
    _collector = _fh.read()                  # ONE collector: pipe it to n100 instead of keeping a second copy
nout, nerr, nrc = run_bytes(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", N100,
                            "bash -s"], _collector, timeout=150)
if nrc != 0:
    errors.append("n100 collect rc=%s %s" % (nrc, trim(nerr, 200)))

hosts = [parse(gout), parse(nout)]
prev = {}
first_run = not os.path.exists(STATE)
if os.path.exists(STATE):
    try:
        prev = json.load(open(STATE))
    except Exception:                                          # noqa: BLE001
        prev = {}
load_repo_units(CANON)
issues, seen = find_decisions(hosts, prev)
arch, live = build(hosts, issues, prev, errors)

os.makedirs(os.path.dirname(LIVE), exist_ok=True)
if os.path.exists(ARCH):
    try:
        os.replace(ARCH, ARCH + ".prev")
    except OSError:
        pass
tmp = ARCH + ".tmp"
with open(tmp, "w") as fh:
    json.dump(arch, fh, indent=1)
os.replace(tmp, ARCH)
tmp = LIVE + ".tmp"
with open(tmp, "w") as fh:
    json.dump(live, fh, indent=1)
os.replace(tmp, LIVE)
json.dump(dict(checked_at=live["generated_at"], issues=[i["key"] for i in issues], repos=seen),
          open(STATE + ".tmp", "w"), indent=1)
os.replace(STATE + ".tmp", STATE)

nt = None
if "--no-notify" not in sys.argv and not first_run:
    nt = notify(issues, prev.get("issues") or [], errors)

if not quiet:
    print("%s  %d hosts, %d sections, %d decision(s), %.1fs"
          % (live["generated_at"], len(hosts), len(arch["sections"]), len(issues), time.time() - started))
    for i in issues:
        print("  [%d] %s -- %s" % (i["sev"], i["title"], i["action"]))
    for e in errors:
        print("  ERROR " + e)
    if nt:
        print("  notified: " + "; ".join(nt))
