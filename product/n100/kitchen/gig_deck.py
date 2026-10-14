#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gig_deck.py -- feeder for Mom's Table kanban card game (taza-card-table.html).

WHY THIS EXISTS  (Nick 2026-10-14 ruling, recorded D107/D108)
  Gig data has exactly two consumers: (a) the checklist app, (b) Mom's Table kanban game on
  all three touchscreens -- as GRANULAR, INDIVIDUAL task cards that can be played.  This
  script is (b).  It replaces the retired ~/pm_web/gig_board.py, which wrongly wrote gig
  columns into Nick's PM/sprint kanban.

WHAT IT TOUCHES  (and what it refuses to touch)
  Exactly three regions of the live board file: the `cards` deck, the seeded `doneCards`
  scoreboard, and the seeded `streak=2` counter.  Every other byte is byte-identical -- the
  script proves this with a region-stripped md5 before it writes.  Look and feel,
  drag-to-play, fan reorder, PIN close, prep-photo capture, chime, burst, chain bonus and
  the 10/20/30 point table are untouched.  Only the TASKS ON THE CARDS change.

SPIRIT OF THE SPECS MET IN THIS BOOTSTRAP  (spec.taza_os_user_requirement_specifications)
  PROD-03 / SCREEN-01      cards carry real kitchen work; brand/game framing untouched
  URS-KANBAN-001           hand / table / done three-state flow -- the board's own, unchanged
  URS-KANBAN-002           who / where / urgency slots filled from the order; PIN close unchanged
  URS-KANBAN-003           urgency stripe + allergen slot + fixed slots -- real values, null when unknown
  URS-KIT-METHOD-001/004   "The Taza way" block carries VERBATIM locked KB rules quoted from the
                           checklist app (never paraphrased, never invented)
  CULT-010                 card text is terse craft language, no enterprise phrasing
  DEFERRED, FLAGGED, NOT FAKED:
    URS-KANBAN-004  Short Stop residual row   -- needs the task engine; no residual writer exists
    URS-KANBAN-005  commit-then-emit fan-out  -- needs the close writer + event bus
    URS-KIT-107     temp-reading bonus cards  -- close sheet has no temperature capture yet
    URS-KIT-103     blocking van-load card    -- no checklist gate in the close path yet
    URS-KIT-101     equipment-cleaning cards  -- no obligation source yet
    KIT-017/020/PROD-37 voice + camera close  -- not deployed
    DECK CAPACITY   the whole service day's work goes in the deck; the fan is wider than the
                    page on purpose and is dragged left/right to read cards off the edge
                    (Nick 2026-10-14).  --max 0 = every card; deck.json keeps the same list.

DATA SOURCE  (no LLM anywhere)
  tazaos.public.system_events topic='order.captured', the same bus and the same content_hash
  rule the checklist app consumes (DEBT-007).  The invoice mirror says WHICH gigs are live;
  the bus says WHAT they contain.  Every card carries a _trace naming the line item or note
  sentence on that bus row it came from (deck.json keeps it; the board does not need it).

USAGE
  gig_deck.py --list                      # what the bus offers (invoice / service date / items)
  gig_deck.py --dry-run                   # build + print the deck, write nothing
  gig_deck.py --apply                     # back up the board, splice the deck in
  gig_deck.py --apply --date 2026-10-24   # pin a service day
  gig_deck.py --apply --max 8 --per-gig 3 # override the hand capacity / per-job floor
  Default target day = the NEXT service date on the bus (today counts as next).
"""
import argparse, hashlib, json, os, re, subprocess, sys, time

BOARD     = "/opt/taza/repo/kitchen/taza-card-table.html"   # the file all three displays load
BAK_DIR   = "/home/taza/archive/board-bak"                  # outside the served git checkout
DECK_JSON = "/home/taza/kitchen/deck.json"                  # artifact: full deck + traceability
DB        = "tazaos"

# locked KB rules, VERBATIM from the checklist app (checklist_app.py lines 126-131).
# The Taza-way block teaches locked KB text or nothing at all (URS-KIT-METHOD-001/004).
KB = {
    "cook_temp":   "first-cook poultry 165F IT; reheats + fish 145F   [G-08]",
    "flash_chill": "flash-chill make-ahead proteins, no tight cover >45F   [G-06]",
    "hot_box":     "hot-box bladders 4-6L @ 95C   [G-09]",
    "poly":        "date & initial the poly; olive oil not butter   [G-01]",
    "allergen":    "allergen check BEFORE procurement   [G-10]",
}
# The board has no crew-login concept yet (see its own comment at the handOrder block), so the
# slot is filled honestly with the crew role instead of inventing a person (URS-KANBAN-002 gap).
WHO = "Crew"

SQL_LIST = """
with latest as (
  select distinct on (payload->>'invoice_number') payload as p
  from public.system_events
  where topic='order.captured' and payload ? 'content_hash'
  order by payload->>'invoice_number', id desc)
select p->>'invoice_number', p->>'service_date', coalesce(p->>'title',''), p::text
from latest order by 2, 1;"""

def psql(sql):
    r = subprocess.run(["psql", "-d", DB, "-At", "-F", "\x1f", "-c", sql],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        sys.exit("FATAL: bus read failed: " + r.stderr.strip())
    return [l.split("\x1f") for l in r.stdout.splitlines() if l]

def orders(day=None, invoice=None):
    out = []
    for inv, sd, title, pjson in psql(SQL_LIST):
        if invoice and inv != invoice: continue
        if day and sd != day:          continue
        out.append({"invoice": inv, "service_date": sd, "title": title, "p": json.loads(pjson)})
    return out

def today():
    return subprocess.run(["date", "+%F"], capture_output=True, text=True).stdout.strip()

def next_day(os_):
    days = sorted({o["service_date"] for o in os_ if o["service_date"]})
    t = today()
    for d in days:
        if d >= t: return d
    return days[-1] if days else None

# ---------------------------------------------------------------- classification (deterministic)
SERVICE_ONLY = re.compile(r"delivery|set[- ]?up|details|rental|tasting|water service|"
                          r"plates and plasticware|timeline|disposable|linen|staffing", re.I)
LEX = [  # (regex, label, cat, protein)   -- checked in order; first hit per label wins
 (r"mediterranean grill|grill platter|grill station", "grill platter",  "hot",     True),
 (r"greek chicken|grilled chicken|chicken",           "chicken",        "hot",     True),
 (r"ny steak|steak",                                  "steak",          "hot",     True),
 (r"short rib",                                       "short ribs",     "hot",     True),
 (r"meatball",                                        "meatballs",      "hot",     True),
 (r"salmon",                                          "salmon",         "hot",     True),
 (r"cucumber canap|canape|canap\u00e9",               "canapes",        "cold",    False),
 (r"charcuterie|grazing",                             "grazing spread", "cold",    False),
 (r"hors d'oeuvre|horts d'oeuvre",                    "hors d'oeuvre",  "cold",    False),
 (r"baby potato|potato",                              "potatoes",       "hot",     False),
 (r"couscous",                                        "couscous",       "hot",     False),
 (r"\brice\b",                                        "rice",           "hot",     False),
 (r"veggie|vegetable",                                "veg",            "hot",     False),
 (r"pear brie|brie|arugula",                          "pear brie stack","cold",    False),
 (r"green salad|\bsalad\b",                           "salad",          "cold",    False),
 (r"baklava",                                         "baklava",        "dessert", False),
 (r"cheesecake",                                      "cheesecake",     "dessert", False),
 (r"bonbon",                                          "bonbons",        "dessert", False),
 (r"\bcake\b|\btarts?\b|\bpie\b|cookies?|brownies?",    "dessert",        "dessert", False),
]
QTY = re.compile(r"(\d{1,4})\s*(?:portions?|pieces?|pcs\.?|count|servings?|plates?)", re.I)
# a platter/spread name is a category, not a dish: it never leads a card title
GENERIC = {"grill platter", "grazing spread", "hors d'oeuvre", "dessert"}
def order_labels(lst):
    return sorted(lst, key=lambda i: (i["label"] in GENERIC, lst.index(i)))

def clean_name(n):
    return re.sub(r"\s+", " ", re.sub(r"^catering\s+", "", n or "", flags=re.I)).strip()

def classify(order):
    """-> (labels, service flags, all note text) for one gig. Pure function of the bus row."""
    labels, svc, notes = [], set(), []
    for it in order["p"].get("line_items") or []:
        name = clean_name(it.get("name"))
        note = it.get("note") or ""
        notes.append(note)
        blob = name + " " + note
        if re.search(r"delivery|delivery address|venue address", blob, re.I): svc.add("deliver")
        if re.search(r"set[- ]?up|station|full service", blob, re.I):          svc.add("stage")
        if re.search(r"timeline to come|to come|TBD", note, re.I):             svc.add("open_note")
        foodish = any(re.search(rgx, blob, re.I) for rgx, _, _, _ in LEX)
        if SERVICE_ONLY.search(name) and not foodish: continue
        q = QTY.search(note)
        qty = q.group(1) if q else None
        for rgx, lab, cat, prot in LEX:
            if re.search(rgx, blob, re.I) and lab not in [h[0] for h in labels]:
                labels.append((lab, cat, prot, qty, name))
        if not foodish:
            lab = " ".join(clean_name(name).lower().split()[:2])[:16]
            if lab: labels.append((lab, "cold", False, qty, name))
    seen, out = set(), []
    for lab, cat, prot, qty, srcname in labels:
        if lab in seen: continue
        seen.add(lab)
        out.append({"label": lab, "cat": cat, "protein": prot, "qty": qty, "item": srcname})
    return out, svc, " ".join(notes)

def guests_of(order):
    """Only from data the order actually states: a Guests: line, or a per-person package line."""
    note = order["p"].get("note_text") or ""
    m = re.search(r"guests?\s*:?\s*([0-9]{1,3}(?:\s*[-\u2013]\s*[0-9]{1,3})?)", note, re.I)
    if m: return m.group(1).replace(" ", "")
    for it in order["p"].get("line_items") or []:
        nm = clean_name(it.get("name"))
        if re.search(r"full service|per person|per-person|buffet|reception|plated", nm, re.I):
            q = it.get("quantity")
            try: q = int(q)
            except (TypeError, ValueError): continue
            if 10 <= q <= 400: return str(q)
    return None

def city_of(order):
    """Town the food goes to, as the order writes it ("... Mesa, AZ")."""
    blob = order["p"].get("note_text") or ""
    m = re.search(r"([A-Z][A-Za-z'\. ]{2,24}?),?\s+(?:AZ|Arizona)\b", blob)
    return re.sub(r"\s+", " ", m.group(1)).strip().rstrip(",") if m else None

def venue_of(order):
    """Named venue, if the order names one -- it makes a better 'where' chip than a town."""
    blob = order["p"].get("note_text") or ""
    m = re.search(r"([A-Z][\w'&\. ]{3,28}?(?:Ranch|Barn|Hall|Farm|Estate|Gardens?|Club|Lodge|Resort|Center))\b", blob)
    return m.group(1).strip() if m else None

def time_of(order):
    """(prefix, clock) from the order's own words. A delivery WINDOW is shown as a window;
    an event start time is shown as a deadline ('by') -- never as a fabricated arrival time."""
    blob = order["p"].get("note_text") or ""
    m = re.search(r"(?:event\s+)?delivery\s+time\D{0,10}(\d{1,2})(?::(\d{2}))?\s*(am|pm)"
                  r"\s*[-to]{1,3}\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)", blob, re.I)
    if m:
        return "", "%d:%s %s\u2013%d:%s %s" % (int(m.group(1)), m.group(2) or "00", m.group(3).upper(),
                                              int(m.group(4)), m.group(5) or "00", m.group(6).upper())
    m = re.search(r"(?:event\s+)?delivery\s+time\D{0,10}(\d{1,2})(?::(\d{2}))?\s*(am|pm)", blob, re.I)
    if m: return "", "%d:%s %s" % (int(m.group(1)), m.group(2) or "00", m.group(3).upper())
    m = re.search(r"(?:event\s+)?start\s+time\D{0,10}(\d{1,2})(?::(\d{2}))?\s*(am|pm)", blob, re.I)
    if m: return "by ", "%d:%s %s" % (int(m.group(1)), m.group(2) or "00", m.group(3).upper())
    return None, None

def tag_of(order):
    """Short, human name for the job. Deterministic; keeps the card title inside its box."""
    t = re.sub(r"\b\d{3,}\b", " ", order["title"] or order["invoice"] or "")
    drop = {"catering","delivery","set","setup","full","service","reception","wedding","meal",
            "event","drop","off","school","reunion","anniversary","year","the","of","and","day","party"}
    toks = [w for w in re.split(r"[\s,]+", t)
            if w and re.search(r"[A-Za-z]", w) and w.lower() not in drop]
    if not toks: return (order["invoice"] or "GIG").split("-")[0]
    return toks[-1] if len(toks[-1]) <= 10 else toks[0]

def title(verb, items, tag, qty_prefix=False, extra=None):
    """Terse craft language (CULT-010). <=36 chars so the card keeps its designed shape."""
    if extra:   core = "%s %s" % (verb, extra)
    elif qty_prefix and items and items[0]["qty"]:
        core = "%s %s %s" % (verb, items[0]["qty"], items[0]["label"])
        if len(items) > 1: core += " +%d" % (len(items) - 1)
    else:
        joined = " & ".join(i["label"] for i in items[:2])
        if joined.lower().startswith(verb.lower()):
            core = joined[:1].upper() + joined[1:]      # "Grill platter", never "Grill grill platter"
        else:
            core = "%s %s" % (verb, joined)
        if len(items) > 2: core += " +%d" % (len(items) - 2)
    core = re.sub(r"\s+", " ", core).strip()
    t = "%s \u00b7 %s" % (core, tag)
    if len(t) <= 36: return t
    # the job tag matters more than the dish list: shorten the list, never drop the job
    if items and len(items) > 1 and not extra:
        head = items[0]["qty"] + " " + items[0]["label"] if (qty_prefix and items[0]["qty"]) else items[0]["label"]
        head = head if qty_prefix else head[:1].upper() + head[1:]
        short = "%s %s +%d" % (verb, head, len(items) - 1) if not head.lower().startswith(verb.lower()) \
                else "%s +%d" % (head, len(items) - 1)
        t2 = "%s \u00b7 %s" % (short.strip(), tag)
        if len(t2) <= 36: return t2
    return core if len(core) <= 36 else core[:35] + "\u2026"

def urgency(kind, days_out):
    """Lead time drives the stripe (rush=A/30, soon=K/20, normal=Q/10). The critical path --
    allergen confirm and cooking -- never drops below 'soon'."""
    crit = kind in ("confirm", "cook")
    if days_out <= 1: return "rush" if (crit or kind in ("pack", "deliver")) else "soon"
    if days_out <= 4: return "soon" if crit else "normal"
    return "soon" if kind == "confirm" else "normal"

ICON = {"confirm":"\u2705","prep":"\U0001f52a","cook":"\U0001f373","portion":"\U0001f370",
        "pack":"\U0001f4e6","stage":"\U0001f374","deliver":"\U0001f69a","flag":"\U0001f6a9"}
CAT  = {"confirm":"prep","prep":"prep","cook":"plate","portion":"plate","pack":"move",
        "stage":"move","deliver":"move","flag":"reset"}

def cards_for_gig(o, days_out):
    """Granular task cards for one gig, each traceable to one line item or one note sentence."""
    cards = []
    items, svc, blob = classify(o)
    tag, g = tag_of(o), guests_of(o)
    def add(kind, t, lkl, taza, trace):
        cards.append({"kind": kind, "title": t, "lkl": lkl, "taza": taza, "trace": trace})
    if items:
        add("confirm", title("Confirm", [], tag, extra=("allergen & %s" % g) if g else "allergen & counts"),
            "office", [KB["allergen"]],
            {"invoice": o["invoice"], "rule": "allergen gate before procurement [G-10]",
             "guests": g, "items": [i["item"] for i in items]})
    cold  = order_labels([i for i in items if i["cat"] == "cold"])
    hot   = order_labels([i for i in items if i["cat"] == "hot"])
    sweet = order_labels([i for i in items if i["cat"] == "dessert"])
    if cold:
        add("prep", title("Prep", cold, tag, qty_prefix=True), "cold line", [KB["poly"]],
            {"invoice": o["invoice"], "items": [i["item"] for i in cold]})
    grill = [i for i in hot if re.search(r"grill|steak|skewer|chicken", i["label"])]
    oven  = [i for i in hot if i not in grill]
    if "grill platter" in [i["label"] for i in grill]:
        grill = order_labels(grill)
    if grill:
        add("cook", title("Grill", grill, tag, qty_prefix=True), "grill",
            [KB["cook_temp"]] if any(i["protein"] for i in grill) else [],
            {"invoice": o["invoice"], "items": [i["item"] for i in grill]})
    if oven:
        add("cook", title("Cook", oven, tag, qty_prefix=True), "hot line",
            [KB["cook_temp"]] if any(i["protein"] for i in oven) else [],
            {"invoice": o["invoice"], "items": [i["item"] for i in oven]})
    if sweet:
        add("portion", title("Portion", sweet, tag, qty_prefix=True), "pastry",
            [KB["flash_chill"]] if any(i["protein"] for i in sweet) else [],
            {"invoice": o["invoice"], "items": [i["item"] for i in sweet]})
    if hot:
        add("pack", title("Pack hot pans", [], tag), "pack-out", [KB["hot_box"]],
            {"invoice": o["invoice"], "rule": "hot box [G-09]"})
    if cold or sweet:
        add("pack", title("Pack soft carrier", [], tag), "pack-out", [KB["poly"]],
            {"invoice": o["invoice"], "rule": "poly/date [G-01]"})
    if "stage" in svc:
        add("stage", title("Stage the buffet", [], tag), "on-site", [],
            {"invoice": o["invoice"], "rule": "order states setup/stations/full service"})
    if "deliver" in svc:
        pre, tm = time_of(o)
        dest = city_of(o) or venue_of(o)
        add("deliver", title("Deliver", [], tag, extra=((pre or "") + tm) if tm else (dest or "on time")),
            venue_of(o) or dest or "van", [],
            {"invoice": o["invoice"], "rule": "order states a delivery/venue address",
             "time": (pre or "") + (tm or ""), "city": city_of(o), "venue": venue_of(o)})
    flags = []
    if re.search(r"take out the bones|shred", blob, re.I):
        flags.append(("shred the ribs for yield", "note: take out the bones and shred so it serves more people"))
    if re.search(r"timeline to come|to come|TBD", blob, re.I):
        flags.append(("timeline still to come", "note: Timeline to come"))
    for txt, quote in flags[:2]:
        add("flag", title("Flag", [], tag, extra=txt), "office", [],
            {"invoice": o["invoice"], "quote": quote})
    out = []
    for c in cards:
        out.append({"title": c["title"], "icon": ICON[c["kind"]], "cat": CAT[c["kind"]],
                    "urg": urgency(c["kind"], days_out), "lkl": c["lkl"], "who": WHO,
                    "steps": [0, 1], "taza": c["taza"] or None, "trace": c["trace"],
                    "_kind": c["kind"], "_gig": tag})
    return out

PRIO = {"confirm": 0, "cook": 1, "prep": 2, "portion": 3, "pack": 4, "stage": 5, "deliver": 6, "flag": 7}

def build(day, os_, max_cards, per_gig):
    t = today()
    days_out = max(0, (time.mktime(time.strptime(day, "%Y-%m-%d")) -
                       time.mktime(time.strptime(t, "%Y-%m-%d"))) // 86400)
    allc = []
    for gi, o in enumerate(os_):
        for c in cards_for_gig(o, days_out):
            c["_gi"] = gi
            allc.append(c)
    # every job gets its critical path floor (per_gig), then the whole day's critical path
    pick = []
    for gi in range(len(os_)):
        g = sorted([c for c in allc if c["_gi"] == gi], key=lambda c: PRIO[c["_kind"]])
        pick += g[:per_gig]
    for c in sorted(allc, key=lambda c: (PRIO[c["_kind"]], c["_gi"])):
        if max_cards and len(pick) >= max_cards: break
        if c not in pick: pick.append(c)
    if max_cards: pick = pick[:max_cards]
    pick.sort(key=lambda c: (c["_gi"], PRIO[c["_kind"]]))
    shown, deferred = [], []
    for n, c in enumerate(pick, 1):
        c2 = dict(c); c2.pop("_gi", None)
        c2["id"] = 100 + n          # ids clear of any hand-order left in a kiosk's localStorage
        shown.append(c2)
    for c in allc:
        if c not in pick:
            d = dict(c); d.pop("_gi", None); deferred.append(d)
    return shown, deferred, days_out

def js_deck(cards):
    L = []
    for c in cards:
        f = ["id:%d" % c["id"], 'title:%s' % json.dumps(c["title"], ensure_ascii=False),
             'icon:%s' % json.dumps(c["icon"], ensure_ascii=False), 'cat:"%s"' % c["cat"],
             'urg:"%s"' % c["urg"], 'lkl:%s' % json.dumps(c["lkl"], ensure_ascii=False),
             'who:%s' % json.dumps(c["who"], ensure_ascii=False), "steps:[0,1]"]
        if c["taza"]: f.append("taza:[%s]" % ",".join(json.dumps(x, ensure_ascii=False) for x in c["taza"]))
        f.append('zone:"hand"')
        L.append("  {" + ", ".join(f) + "},")
    return "let cards=[\n" + "\n".join(L).rstrip(",") + "\n];"

REG      = re.compile(r"let cards=\[.*?\n\];", re.S)
REG_DONE = re.compile(r"let doneCards=\[.*?\n\];", re.S)
REG_STK  = re.compile(r"let score=0, streak=\d+,")

def splice(html, deck_js, stamp):
    html = REG_MARKS.sub("", html)          # idempotent: drop my own marks, then re-add them
    for rx, nm in ((REG, "cards"), (REG_DONE, "doneCards"), (REG_STK, "score/streak")):
        if len(rx.findall(html)) != 1:
            sys.exit("FATAL: marker %s not found exactly once -- refusing to guess." % nm)
    prov = ("/* DECK SOURCE: built by /home/taza/kitchen/gig_deck.py from system_events\n"
            "   topic=order.captured (same bus the checklist app reads; no LLM). %s\n"
            "   Full deck + per-card traceability: /home/taza/kitchen/deck.json */\n" % stamp)
    html = REG.sub(lambda m: prov + deck_js, html, count=1)
    html = REG_DONE.sub("/* bootstrap: the scoreboard opens EMPTY -- the score is what THIS crew\n"
                        "   really lays down today, not a seeded demo. */\nlet doneCards=[\n];", html, count=1)
    html = REG_STK.sub("let score=0, streak=0,", html, count=1)
    return html

REG_MARKS = re.compile(r"/\* DECK SOURCE:.*?\*/\n|/\* bootstrap: the scoreboard opens EMPTY.*?\*/\n", re.S)

def stripped(html):
    """Everything the splice is allowed to touch, normalised away. If a byte outside the three
    deck regions and my own two provenance comments differs, --apply refuses to write."""
    return REG_STK.sub("streak", REG_DONE.sub("done", REG.sub("cards", REG_MARKS.sub("", html))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--date"); ap.add_argument("--invoice")
    ap.add_argument("--board", default=BOARD)
    ap.add_argument("--max", type=int, default=0,  dest="max_cards",
                    help="0 = every card for the service day (the fan pans; Nick 2026-10-14). "
                         "Set a number only to trim the day.")
    ap.add_argument("--per-gig", type=int, default=2, help="cards every job gets before the day's global pick")
    a = ap.parse_args()
    os_all = orders(a.date, a.invoice)
    if a.list or not (a.dry_run or a.apply):
        for o in os_all:
            print("%-22s %s  %2d item(s)  %s" % (o["invoice"], o["service_date"],
                  len(o["p"].get("line_items") or []), o["title"][:48]))
        print("(%d gig(s) on the bus)" % len(os_all))
        return
    day = a.date or next_day(os_all)
    os_ = [o for o in os_all if o["service_date"] == day]
    if not os_: sys.exit("FATAL: no orders on the bus for %s" % day)
    shown, deferred, days_out = build(day, os_, a.max_cards, a.per_gig)
    stamp = "service day %s (in %d day(s)) \u00b7 %d gig(s) \u00b7 built %s MST" % (
        day, days_out, len(os_), time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()))
    print("service day %s  \u00b7  %d gig(s) on the bus  \u00b7  %d day(s) out  \u00b7  %d card(s) built, %d shown, %d deferred"
          % (day, len(os_), days_out, len(shown) + len(deferred), len(shown), len(deferred)))
    for c in shown:
        print("  %-2d [%-6s/%-4s] %-36s (%s)" % (c["id"], c["urg"], c["cat"], c["title"], c["lkl"]))
    for c in deferred:
        print("  -- [%-6s/%-4s] %-36s (%s)" % (c["urg"], c["cat"], c["title"], c["lkl"]))
    if a.dry_run and not a.apply: return
    html = open(a.board, encoding="utf-8").read()
    before_md5, before = hashlib.md5(html.encode()).hexdigest(), stripped(html)
    new = splice(html, js_deck(shown), stamp)
    after = stripped(new)
    if after != before:
        sys.exit("FATAL: something outside the three deck regions changed -- refusing to write.")
    sd = hashlib.md5(after.encode()).hexdigest()
    os.makedirs(BAK_DIR, exist_ok=True)
    bak = os.path.join(BAK_DIR, os.path.basename(a.board) + ".bak." + time.strftime("%Y%m%d_%H%M%S"))
    open(bak, "w", encoding="utf-8").write(html)
    open(a.board, "w", encoding="utf-8").write(new)
    open(DECK_JSON, "w", encoding="utf-8").write(json.dumps(
        {"built": stamp, "service_day": day, "days_out": days_out, "gigs": [o["invoice"] for o in os_],
         "shown": shown, "deferred": deferred, "outside_deck_md5": sd},
        indent=1, ensure_ascii=False))
    print("backup  : %s" % bak)
    print("board   : %s  %d -> %d bytes" % (a.board, len(html), len(new)))
    print("md5     : %s -> %s" % (before_md5, hashlib.md5(new.encode()).hexdigest()))
    print("outside-deck digest (unchanged on purpose): %s" % sd)
    print("deck.json: %s" % DECK_JSON)

if __name__ == "__main__":
    main()
