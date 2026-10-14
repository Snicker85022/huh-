#!/usr/bin/env python3
"""
Taza Checklist App - BOOTSTRAP v0.2     (Nick, 2026-10-08: "bootstrap this checklist app")

Turns a deposited invoice whose performance date falls inside the next N days into a
per-EVENT-DAY production checklist, populated from:
  * tazaos.square_invoices        invoice facts (NB line_items is EMPTY - never fetched)
  * Square Orders API            /v2/orders/{order_id} - verbatim capture (README sec.13)
  * tazaos.rag_operations_content the Operations Content KB - the rules
and prints it to the HP DeskJet 3700 series.

Governed by the KB "Task System Governance Rules": do not invent, do not infer
quantities, FLAG when uncertain. Every derived line names the rule behind it.

READ-ONLY: writes nothing to the database. Writes .txt under out/ and prints.
"""
import json, os, re, shutil, subprocess, sys, datetime, textwrap, urllib.request
import sheet_pdf

VERSION = "0.2.0"
W       = 84
CRED    = "/home/taza/viewer_ro.cred"
SECRETS = "/etc/taza/secrets"
APP     = "/home/taza/checklist-app"
CACHE   = os.path.join(APP, "cache")
OUT     = os.path.join(APP, "out")
# PRINTER is the CUPS CLASS "Checklist" (created 2026-10-13, D84): member 1 TazaHP-USB
# (the ipp-usb endpoint on n100, localhost:60000), member 2 TazaHP (Wi-Fi fallback, dead
# until the printer's radio is back). Print to the class, never to a single queue or a
# cups-browsed queue - TazaHP is a Wi-Fi address now, and a browsed implicitclass queue
# loses its destination when the printer naps, killing every job with "No destination
# host name supplied by cups-browsed" (jobs 26 & 27).
PRINTER = os.environ.get("CHECKLIST_PRINTER", "Checklist")
SPOOL   = os.path.join(APP, "spool")
ORIGIN  = "85007"                                   # KB: shop, Central City / Capitol
DAYS    = int(os.environ.get("CHECKLIST_WINDOW_DAYS", "4"))

HOT = ("skewer", "slider", "date", "chicken", "steak", "salmon", "rib", "potato",
       "braise", "meatball", "lasagna", "moussaka", "couscous", "rice", "pasta")
SOFT = ("charcuterie", "grazing", "caprese", "salad", "canape", "canapé", "platter",
        "board", "hummus", "dip", "fruit")
PRES = ("charcuterie", "grazing", "caprese", "canape", "canapé", "platter", "board")
NONFOOD = re.compile(r"(delivery|setup|details|rental|station)", re.I)

# ------------------------------------------------------------------ db
def db(sql):
    env = dict(os.environ, PGPASSWORD=open(CRED).read().strip())
    r = subprocess.run(["psql", "-U", "viewer_ro", "-h", "127.0.0.1", "-d", "tazaos",
                        "-At", "-F", "\x1f", "-c", sql], capture_output=True, text=True, env=env)
    if r.returncode:
        sys.exit("psql failed: " + r.stderr)
    return [l.split("\x1f") for l in r.stdout.strip().split("\n") if l]

# ------------------------------------------------------------------ square
def token():
    out = subprocess.run(["sudo", "grep", "^SQUARE_ACCESS_TOKEN=", SECRETS],
                         capture_output=True, text=True).stdout.strip()
    return out.split("=", 1)[1]

def order(oid, tok):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, oid + ".json")
    if not os.path.exists(p):
        req = urllib.request.Request("https://connect.squareup.com/v2/orders/" + oid,
                                     headers={"Authorization": "Bearer " + tok,
                                              "Square-Version": "2024-06-04"})
        with urllib.request.urlopen(req, timeout=25) as f:
            open(p, "w").write(f.read().decode())
    return json.load(open(p))["order"]

# ------------------------------------------------------------------ dates from invoice_number
def parse_dates(inv):
    parts = re.split(r"[-_ ]+", inv or "")
    yr = next((int(p) for p in parts if p.isdigit() and len(p) == 4 and 2020 <= int(p) <= 2035), None)
    out = []
    for p in parts:
        if p.isdigit() and len(p) == 4 and not (2020 <= int(p) <= 2035):
            mm, dd = int(p[:2]), int(p[2:])
            if yr and 1 <= mm <= 12 and 1 <= dd <= 31:
                try: out.append(datetime.date(yr, mm, dd))
                except ValueError: pass
    return sorted(set(out))

# ------------------------------------------------------------------ note scraping
def scrape(lines):
    blob = "\n".join(lines).lower()
    f = {}
    for pat in (r"new total number of guests is\s*[:\-]?\s*([0-9]+)",
                r"number of guests\s*[:\-]?\s*([0-9]+)",
                r"for\s+([0-9]+)\s+guests"):
        m = re.search(pat, blob)
        if m: f["guests"] = int(m.group(1)); break
    m = re.search(r"taza\s+(?:delivery|arrival|setup)\s*time\s*[:\-]\s*([0-9]{1,4}(?::[0-9]{2})?\s*[ap]m)", blob)
    f["arrival"] = norm_time(m.group(1)) if m else None
    m = re.search(r"event\s+(?:start\s*)?time\s*[:\-]\s*([0-9]{1,4}(?::[0-9]{2})?\s*[ap]m(?:\s*-\s*[0-9]{1,4}(?::[0-9]{2})?\s*[ap]m)?)", blob)
    f["start"] = norm_time(m.group(1)) if m else None
    addrs = []
    for L in lines:
        s = L.strip().rstrip(")")
        if re.match(r"^\d{3,5}\s+\w", s) and "," in s: addrs.append(s)
        elif re.search(r"(university|reservation|center)", s, re.I) and not s.lower().startswith(("address", "event")):
            addrs.append(s)
    f["address"] = " / ".join(dict.fromkeys(addrs)) if addrs else None
    return f

def split_item(name, raw, day):
    """Return [(date, lines)] - a line item can belong to more than one event day."""
    parts = re.split(r"(?=\bevent date\s*:)", raw, flags=re.I)
    if len(parts) > 1:
        pre = ""
        if not re.search(r"event date\s*:", parts[0], re.I):
            pre = parts[0].strip()          # "Number of Guests: 65" - applies to EVERY day
            parts = parts[1:]
        out = []
        for p in parts:
            if not p.strip(): continue
            m = re.search(r"event date\s*:[^\d]*(\d{1,2})/(\d{1,2})/(\d{4})", p, re.I)
            d = datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else day
            out.append((d, ([pre] if pre else []) + p.strip().split("\n")))
        return out
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?!\d)", name) or \
        re.search(r"(?:for|to)\s+(\d{1,2})/(\d{1,2})(?!\d)", raw, re.I)
    d = day
    if m:
        try: d = datetime.date(day.year, int(m.group(1)), int(m.group(2)))
        except ValueError: d = day
    return [(d, raw.split("\n"))]

def norm_time(t):
    """'1pm' / '2:30pm' / '430pm' -> '1:00 PM' / '2:30 PM' / '4:30 PM'. Ranges get both halves."""
    if not t: return None
    out = []
    for part in re.split(r"\s*-\s*", t.strip().upper().replace(" ", "")):
        m = re.match(r"^(\d{1,2}):(\d{2})(AM|PM)$", part)
        if m: out.append("%d:%s %s" % (int(m.group(1)), m.group(2), m.group(3))); continue
        m = re.match(r"^(\d{3,4})(AM|PM)$", part)
        if m:
            v = m.group(1); out.append("%d:%s %s" % (int(v[:-2]), v[-2:], m.group(2))); continue
        m = re.match(r"^(\d{1,2})(AM|PM)$", part)
        if m: out.append("%d:00 %s" % (int(m.group(1)), m.group(2))); continue
        out.append(part)
    return "-".join(out)

def scrape_wide(lines):
    """Event-wide guest count: prefer the plain statement over an add-on note."""
    blob = "\n".join(lines).lower()
    for pat in (r"number of guests\s*[:\-]?\s*([0-9]+)", r"for\s+([0-9]+)\s+guests",
                r"new total number of guests is\s*[:\-]?\s*([0-9]+)"):
        m = re.search(pat, blob)
        if m: return int(m.group(1))
    return None

def hhmm(t):
    if not t: return None
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)", t.strip().upper())
    if not m: return None
    h = int(m.group(1)) % 12
    if m.group(3) == "PM": h += 12
    return datetime.datetime(2000, 1, 1, h, int(m.group(2) or 0))

# ------------------------------------------------------------------ rules
def apply_rules(ev):
    txt = " ".join(ev["food_names"]).lower() + " " + ev["notes"].lower()
    equip, tasks, used = [], [], set()
    if ev["hot_service"]:
        equip += ["Chafers: 4 standard + 1 spare, chrome roll-top + black skirts  [KB Equipment]",
                  "Rolling cart (carries the 4 chafers permanently, big van)     [KB Equipment]",
                  "Hot box + rubber bladders 4-6L near-boiling water (95C)       [KB G-09]"]
        used |= {"G-09"}
    if "skewer" in txt:
        equip.append("6-inch bamboo skewers (chicken + steak skewers)               [KB Equipment]")
    if "wrapped date" in txt or ("date" in txt and "bacon" in txt):
        equip.append("Multi-color toothpicks - BWD house standard                   [KB Equipment]")
    if any(t in txt for t in SOFT):
        equip += ["Soft bag / pizza carrier - presentation items do not fit pan slots [KB Carrier Types]",
                  "Insulating blankets (large boards only: below + above, kraft-taped) [KB Carrier Types]"]
    if any(t in txt for t in PRES):
        tasks += [("PACK", "pan carrier load (cold/hot pans)"),
                  ("PACK", "soft carrier load - presentation items, LOAD LAST (zone 3)"),
                  ("STAGE", "unwrap + place presentation items on site")]
        used.add("Presentation-Ready Items")
    if ev["hot_service"]:
        tasks.append(("FLAG", "all transport pans must be FULL-WIDTH; sixth pans prohibited (decant rule)"))
        used |= {"Pan Geometry - Kitchen vs Transport", "Decant Rule"}
    used |= {"Three-Zone Vehicle Load Pattern", "Arrival Timing Matrix (all service types)",
             "Task Verb Library & Naming Conventions", "G-06", "G-08", "G-10",
             "RULE: Hot-hold above 140F", "RULE: Cook->chill within 2h"}
    tasks.append(("CONFIRM", "allergen / dietary check BEFORE procurement (nuts, shellfish, dairy, gluten)"))
    if any(t in txt for t in ("charcuterie", "grazing")):
        tasks.append(("CONFIRM", "nut-allergy check before buying charcuterie  [KB G-10]"))
    return equip, tasks, sorted(used)

# ------------------------------------------------------------------ render
def rule(c="="): return c * W
def money(c): return "$%s" % format(c / 100.0, ",.2f")

def ev_flags(ev):
    """The FLAGS block, condensed into footer lines under the grid."""
    out = ["FLAGS   (KB Task System Governance: when uncertain, FLAG - never guess)"]
    for f in ev.get("flags", []):
        out.append("   - " + f)
    out.append("RULES APPLIED:  " + ", ".join(ev.get("rules", [])))
    out.append("Automated from the Square order + the Operations Content KB (locked procedures only). "
               "Generated by checklist_bootstrap.py.")
    return out


def build(ev):
    L = []; A = L.append
    A(rule()); A(" TAZA CATERING & EVENTS   EVENT CHECKLIST            bootstrap v" + VERSION)
    A(" generated %s MST by checklist_bootstrap.py   [READ-ONLY: nothing written to the DB]"
      % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    A(rule())
    A(" EVENT    %s" % ev["title"])
    A(" CUSTOMER %-30s INVOICE  %s" % (ev["customer"], ev["invoices"][0]))
    for i in ev["invoices"][1:]:
        A(" %-9s%-30s          %s" % ("", "", i))
    A(" PHONE    %-34s DATE  %s" % (ev["phone"], ev["date_label"]))
    A(" EMAIL    %s" % ev["email"])
    A(" GUESTS   %s" % (ev["guests_txt"]))
    A(" SERVICE  %s" % ev["service"])
    A(" ARRIVAL  %s" % ev["arrival_txt"])
    A(" START    %s" % (ev["f"].get("start") or "FLAG - not in order note"))
    A(textwrap.fill(" ADDRESS  %s" % (ev["f"].get("address") or "FLAG - no address in DB or order note"),
                    W, subsequent_indent="          "))
    A(" DRIVE    _____ min      LEAVE AT  _____      [FLAG: PhoenixValley drive-time xlsx not on n100]")
    A(" MONEY    %s" % ev["money"])
    A(rule("-"))
    A(" FOOD  (verbatim from the Square order - README sec.13 'capture word for word')")
    A("       NOTE: tazaos.square_invoices.line_items is EMPTY. Fetched live from the Orders API.")
    for it in ev["items"]:
        A("   [ ] %s  x%s  %s%s" % (it["name"], it["qty"], money(it["amt"]),
                                    "" if it["food"] else "   [service/fee]"))
        for n in it["lines"]:
            if n.strip(): A(textwrap.fill(n.strip(), W, initial_indent="       ", subsequent_indent="       "))
        if it["food"]:
            A("       purch[ ]  pre[ ]  full-pre[ ]  par[ ]  cook[ ]  trans[%s]  temp[____]"
              % ("pan" if it["hot"] else "soft"))
    A("")
    A(rule("-"))
    A(" EQUIPMENT   [ ] on the van   [ ] on site        (KB Equipment / Carrier Types / G-09)")
    for e in ev["equip"] or ["(nothing triggered by the captured text - REVIEW MANUALLY)"]:
        A("   [ ] " + e)
    A("")
    A(" SERVING / DISPOSABLE / LINEN  (verbatim from the order)")
    for s in ev["serving"] or ["   - none stated in the order note"]:
        A(textwrap.fill(s, W, initial_indent="   [ ] ", subsequent_indent="       "))
    A("")
    A(" SIGNS    [ ] __PRINTED__" + " " * 22 + "[ ] loaded")
    A(rule("-"))
    A(" SAFETY & TEMP   (locked KB rules - not optional)")
    A("   [ ] first-cook poultry 165F IT at 3-4 spots; reheats + fish 145F        [G-08]")
    A("   [ ] flash-chill make-ahead proteins: ice bath ~30 min, NO tight cover >45F [G-06]")
    A("   [ ] cook->chill <= 2h    [ ] hot-hold > 140F    [ ] salmon target 125F")
    A("   [ ] hot-box bladders 4-6L @ 95C; electric heater if the delay > 1h      [G-09]")
    A("   [ ] date & initial the poly   [ ] no butter in savoury dishes, olive oil [G-01]")
    A("   [ ] allergen check BEFORE procurement                                   [G-10]")
    A(rule("-"))
    A(" TASKS   (KB Task Verb Library prefixes; status default Not Started)")
    for verb, what in ev["tasks"]:
        A(textwrap.fill("%-8s %s" % (verb, what), W, initial_indent="   [ ] ",
                        subsequent_indent="       "))
    A(rule("-"))
    A(" FLAGS   (KB Task System Governance: when uncertain, FLAG - never guess)")
    for f in ev["flags"]:
        A(textwrap.fill("- FLAG: " + f, W, initial_indent=" ", subsequent_indent="         "))
    A(rule("-"))
    A(" RULES APPLIED   (Operations Content KB - tazaos.rag_operations_content)")
    A(textwrap.fill(", ".join(ev["rules"]), W, initial_indent="  ", subsequent_indent="  "))
    A(rule("="))
    return "\n".join(L)

# ------------------------------------------------------------------ main
SQL = """
select invoice_number, customer_name, coalesce(customer_phone,''), coalesce(customer_email,''),
       status, coalesce(amount_paid_cents,0), coalesce(event_date_derived::text,''),
       coalesce(payload->>'order_id',''), coalesce(payload->>'title',''), coalesce(total_cents,0)
from square_invoices where coalesce(amount_paid_cents,0) > 0 order by invoice_number
"""

def main():
    dry  = "--dry-run" in sys.argv
    sheet = "--format=long" not in sys.argv   # sheet = Nick's spreadsheet layout (default)
    nop  = "--no-print" in sys.argv
    today = datetime.date.today()
    end   = today + datetime.timedelta(days=DAYS)

    invs = []
    for r in db(SQL):
        ds = parse_dates(r[0]) or ([datetime.date.fromisoformat(r[6])] if r[6] else [])
        ds = [d for d in ds if today <= d <= end]
        if ds:
            invs.append({"inv": r[0], "cust": r[1], "phone": r[2], "email": r[3], "status": r[4],
                         "paid": int(r[5]), "derived": r[6], "oid": r[7], "title": r[8],
                         "total": int(r[9]), "dates": ds})
    if not invs:
        print("No deposited invoice has a performance date in %s..%s." % (today, end)); return

    tok = token()
    days = {}                                            # (cust, date) -> bucket
    for iv in invs:
        for d in iv["dates"]:
            b = days.setdefault((iv["cust"], d), {"invs": [], "items": [], "all_lines": []})
            if iv not in b["invs"]: b["invs"].append(iv)
            if not iv["oid"]: continue
            try:
                o = order(iv["oid"], tok)
            except Exception as ex:
                b.setdefault("err", []).append("%s: %s" % (iv["oid"], ex)); continue
            for li in o.get("line_items", []):
                nm = li.get("name", "") or ""
                raw = (li.get("note") or "").strip()
                for td, lines in split_item(nm, raw, d):
                    if td != d: continue
                    txt = (nm + " " + raw).lower()
                    b["items"].append({"name": nm, "qty": li.get("quantity", "1"),
                                       "amt": li.get("total_money", {}).get("amount", 0),
                                       "lines": lines, "order": iv["oid"],
                                       "food": not NONFOOD.search(nm),
                                       "hot": any(t in txt for t in HOT)})
                    b["all_lines"] += lines

    made, seen = [], {}
    for (cust, d), b in sorted(days.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        same = sorted({k[1] for k in days if k[0] == cust})
        label = d.strftime("%A %Y-%m-%d") + ("   (day %d of %d)" % (same.index(d) + 1, len(same)) if len(same) > 1 else "")
        f = scrape(b["all_lines"])
        wg = scrape_wide([l for k in days if k[0] == cust for l in days[k]["all_lines"]])
        ev_wide = None
        if not f.get("guests") and wg:
            ev_wide = wg; f["guests"] = wg
        food_names = [i["name"] for i in b["items"] if i["food"]]
        full = any("full service" in i["name"].lower() for i in b["items"])
        ev = {"title": (b["invs"][0]["title"] or cust).split("1008")[0].split(" & ")[0].strip(),
              "customer": cust, "phone": b["invs"][0]["phone"], "email": b["invs"][0]["email"],
              "date_label": label, "f": f, "items": b["items"], "food_names": food_names,
              "notes": " ".join(b["all_lines"]),
              "hot_service": any(t in " ".join(b["all_lines"]).lower() for t in HOT) or full,
              "service": ("Full service - passed hors d'oeuvres"
                          if full else "Drop-off / delivery + setup")
                         + "   [FLAG: invoice service_code meaning is not defined in the KB]",
              "invoices": [i["inv"] for i in b["invs"]],
              "money": ", ".join("%s %s (paid %s)" % (i["inv"], i["status"], money(i["paid"])) for i in b["invs"])}
        ev["date"] = d
        ev["printed"] = datetime.datetime.now().strftime("%a %d %b %Y %H:%M")

        # arrival: order note value, cross-checked against the Arrival Timing Matrix
        arr = ev["f"].get("arrival"); st = hhmm(ev["f"].get("start") or "")
        if arr:
            a_txt = "%s  (from the order note)" % arr
            h = hhmm(arr)
            if st and h:
                if full:
                    a_txt += "   matrix rows that could apply: HD+passing 50 min / Stations 1.75-2.0h"
                else:
                    d0 = (st - datetime.timedelta(minutes=35)).strftime("%-I:%M %p")
                    a_txt += "   matrix says %s (event start %s - 35 min drop-off: 30 setup + 5 parking)" % (d0, st.strftime("%-I:%M %p"))
                    if abs((st - h).total_seconds() - 35 * 60) > 20 * 60:
                        a_txt += "  <<< MISMATCH - CONFIRM"
        else:
            a_txt = ("FLAG - not in the order note; matrix (%s): drop-off = start - 35 min, "
                     "plated 2.5h, buffet 2.0/1.75/1.25h by guest band, HD+passing 50 min"
                     % ev["service"].split("   ")[0])
        ev["arrival_txt"] = a_txt
        ev["guests_txt"] = ("%s%s" % (ev["f"]["guests"],
                                      "   (event-wide; not re-stated for this day)" if ev_wide else "")
                            if ev["f"].get("guests") else "FLAG - not stated in the order")

        ev["equip"], ev["tasks"], ev["rules"] = apply_rules(ev)
        ev["serving"] = []
        for it in b["items"]:
            for n in it["lines"]:
                if re.search(r"\b(plates?|napkins?|plasticware|cutlery|forks?|cups?|linen|silverware)\b", n, re.I):
                    ev["serving"].append(n.strip())
        ev["serving"] = list(dict.fromkeys(ev["serving"]))

        act, info, sysn = [], [], []

        # Short plain sentences, one idea each (KB 10.4: readable in a kitchen by a cook
        # on a phone). Nothing here is a run-on, and nothing here is jargon.
        if any(i["derived"] == "" for i in b["invs"]):
            sysn.append("The date was worked out from the invoice number, not from a calendar "
                        "field. Check the date and time above before you rely on them.")
        sysn.append("This job is not linked to an event record yet, so the kitchen board and "
                    "the event displays will not show it.")
        act.append("Drive time and leave-at are blank because the drive-time table is not "
                   "loaded on the server. Fill them in by hand before the van leaves.")
        act.append("Crew numbers for this service type are not set yet. Confirm the roster "
                   "before the van leaves.")
        act.append("Sauce, dressing and base ratios are not fixed yet. Do not improvise "
                   "quantities - ask Nick or Sandra.")
        if any("linen" in x.lower() for x in ev["serving"]):
            act.append("Linen and table come from the host. Confirm them when you arrive.")
        info.append("The food list was copied word for word from the Square order. Nothing was "
                    "added and nothing was assumed - if it is not on this sheet, it was not ordered.")
        info.append("Foods are read live from the Square order because the invoice mirror does "
                    "not store order lines yet.")
        recs = db("select title, status from rag_operations_content where type='recipe' and (%s)" %
                  " or ".join("title ilike '%%%s%%'" % n.replace("Catering ", "").replace("'", "''")
                              for n in food_names)) if food_names else []
        for t, st in recs:
            if st != "locked":
                act.append("Recipe still in draft: %s. Read the method before you cook it." % t)
        if b.get("err"):
            sysn.append("The order could not be fetched for this job, so this sheet may be short.")

        fl = act + info + sysn
        grp = [("BEFORE YOU COOK", act), ("GOOD TO KNOW", info), ("NOT YOUR PROBLEM TODAY", sysn)]
        ev["flags"] = list(dict.fromkeys(fl))
        ev["flag_groups"] = [(t, list(dict.fromkeys(x))) for t, x in grp if x]

        txt = build(ev)
        made.append(((cust, d), txt, ev))

    os.makedirs(OUT, exist_ok=True)
    for (cust, d), txt, ev in made:
        p = os.path.join(OUT, "checklist_%s_%s.txt" % (d, re.sub(r"\W+", "", cust)))
        open(p, "w").write(txt + "\n")
        if not nop: print("\n" + txt + "\n>>> saved %s" % p)
        if dry or nop: continue
        if sheet:                                     # GRID layout <- Nick's sheet
            pdf = p[:-4] + ".pdf"
            data = sheet_pdf.render(ev, ev_flags(ev))     # render first: never truncate on error
            with open(pdf, "wb") as fh:
                fh.write(data)
            r = subprocess.run(["lp", "-d", PRINTER, "-o", "media=na_letter_8.5x11in",
                                "-o", "print-color-mode=monochrome", "-t",
                                "CHECKLIST %s %s" % (d, cust), pdf],
                               capture_output=True, text=True)
            print(">>> PRINT rc=%s %s [sheet]" % (r.returncode, (r.stdout or r.stderr).strip()))
            continue
        # CUPS cannot type-detect a bare .txt on this driverless queue ("Can't detect file type",
        # job 23, 2026-10-08), so render to PDF first and send the PDF.
        pdf = p[:-4] + ".pdf"
        try:
            with open(pdf, "wb") as fh:
                subprocess.run(["cupsfilter", "-m", "application/pdf", p], stdout=fh,
                               stderr=subprocess.DEVNULL, check=True)
        except Exception as ex:
            print(">>> PDF render failed for %s: %s" % (p, ex)); continue
        r = subprocess.run(["lp", "-d", PRINTER, "-o", "media=na_letter_8.5x11in",
                            "-o", "print-color-mode=monochrome", "-t",
                            "CHECKLIST %s %s" % (d, cust), pdf], capture_output=True, text=True)
        if r.returncode:
            # Either the queue is gone or the backend refused. Spool it; the
            # checklist-printer.timer self-heal will push it through when the
            # printer is back on the LAN.
            os.makedirs(SPOOL, exist_ok=True)
            shutil.copy(pdf, SPOOL)
            subprocess.run(["/home/taza/checklist-app/printer-selfheal.sh"])
            print(">>> PRINT rc=%s %s -> SPOOLED %s (self-heal will retry)"
                  % (r.returncode, (r.stdout or r.stderr).strip(), pdf))
        else:
            print(">>> PRINT rc=0 %s" % (r.stdout or "").strip())
    print("\n%d checklist(s) generated; printer queue '%s'." % (len(made), PRINTER))

if __name__ == "__main__":
    main()
