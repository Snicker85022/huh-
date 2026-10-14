#!/usr/bin/env python3
"""
checklist_app -- CONSUMES the intercom. Does not read invoices, does not call Square.

    order.captured  (PROD-20, published by order_ingest)
          |
          v
    this app pulls what it needs and does its thing

Everything it prints comes off the bus: gig, service date, venue, arrival time, guest
count, service type and the full verbatim menu. If the bus says nothing, this app prints
nothing -- which is the point. It has no privileged path to the data.
"""
import json, os, re, shutil, subprocess, sys, datetime, textwrap

VERSION = "0.3.0"
W       = 84
APP     = "/home/taza/checklist-app"
OUT     = os.path.join(APP, "out")
SPOOL   = os.path.join(APP, "spool")
CRED    = "/home/taza/viewer_ro.cred"
PRINTER = os.environ.get("CHECKLIST_PRINTER", "TazaHP")
DAYS    = int(os.environ.get("CHECKLIST_WINDOW_DAYS", "4"))
CONSUMER = "checklist_app"          # 14.1 application_name

HOT  = ("skewer","slider","date","chicken","steak","salmon","rib","potato","braise",
        "meatball","lasagna","moussaka","couscous","rice","pasta")
SOFT = ("charcuterie","grazing","caprese","salad","canape","canapé","platter","board",
        "hummus","dip","fruit")
PRES = ("charcuterie","grazing","caprese","canape","canapé","platter","board")
NONFOOD = re.compile(r"(delivery|setup|details|rental|station|coffee|beverage)", re.I)


def db(sql):
    env = dict(os.environ, PGPASSWORD=open(CRED).read().strip())
    r = subprocess.run(["psql","-U","viewer_ro","-h","127.0.0.1","-d","tazaos","-At","-c",sql],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        sys.exit("psql failed: " + r.stderr)
    return r.stdout


def pull_orders(today, horizon):
    """The only data source: the bus. Latest order.captured per invoice, content_hash
    present (DEBT-007: a placeholder row without a hash must never be acted on)."""
    sql = ("select payload::text from system_events where topic='order.captured' "
           "and payload ? 'content_hash' "
           "order by id")
    rows = [json.loads(l) for l in db(sql).split("\n") if l.strip()]
    latest = {}
    for p in rows:                                   # latest wins per invoice
        latest[p["invoice_number"]] = p
    out = []
    for p in latest.values():
        try:
            d = datetime.date.fromisoformat(p["service_date"])
        except Exception:
            continue
        if today <= d <= horizon:
            out.append(p)
    return out


def money(c): return "$%s" % format(int(c or 0)/100.0, ",.2f")
def rule(ch="="): return ch * W
def wrap(s, ind=0):
    return textwrap.fill(s, W, initial_indent=" "*ind, subsequent_indent=" "*ind)


def build(p, day_label):
    items = p["line_items"]
    txt   = " ".join((i["name"] or "") + " " + (i["note"] or "") for i in items).lower()
    d     = p.get("derived", {})
    notes = {i["name"]: i["note"] for i in items if i.get("note")}
    L=[]; A=L.append
    A(rule()); A(" TAZA CATERING & EVENTS   EVENT CHECKLIST            consumer v" + VERSION)
    A(" built from the intercom: topic order.captured, correlation %s" % (p.get("correlation_id") or "-")[:8])
    A(rule())
    A(" EVENT    %s" % p.get("title",""))
    A(" CUSTOMER %-28s INVOICE  %s" % (p.get("customer_name",""), p.get("invoice_number","")))
    A(" PHONE    %-28s DATE  %s" % (p.get("customer_phone","") or "-", day_label))
    A(" EMAIL    %s" % (p.get("customer_email","") or "-"))
    A(" GUESTS   %s" % (d.get("guest_count") or "FLAG - not stated in the order"))
    A(" SERVICE  %s   [FLAG: meaning of the invoice service_code is not defined in the KB]"
      % (d.get("service_type","").replace("_"," ")))
    A(wrap(" VENUE    %s" % (d.get("venue_address") or "FLAG - no address in the order"), 0))
    A(" ARRIVAL  %s      START %s      (both derived from the order note)"
      % (d.get("arrival_time") or "FLAG", d.get("event_start_time") or "FLAG"))
    A(" DRIVE    _____ min   LEAVE AT _____   [FLAG: drive-time matrix not on n100 - DEBT-011]")
    A(" MONEY    deposit %s   balance due %s" % (money(p.get("deposit_cents")), money(p.get("amount_due_cents"))))
    A(rule("-"))
    A(" FOOD  (verbatim from the order - README sec.13: capture word for word)")
    for i in items:
        A("   [ ] %s  x%s  %s%s" % (i["name"], i["quantity"], money(i["amount_cents"]),
                                    "" if not NONFOOD.search(i["name"] or "") else "   [service/fee]"))
        for n in (i.get("note") or "").split("\n"):
            if n.strip(): A(wrap(n.strip(), 7))
        if not NONFOOD.search(i["name"] or ""):
            A("       purch[ ] pre[ ] full-pre[ ] par[ ] cook[ ] trans[%s] temp[____]"
              % ("pan" if any(t in txt for t in HOT) else "soft"))
    A("")
    A(rule("-"))
    A(" EQUIPMENT   [ ] on the van   [ ] on site     (KB Equipment / Carrier Types / G-09)")
    if any(t in txt for t in HOT):
        for e in ("Chafers 4 + 1 spare, chrome roll-top + black skirts",
                  "Rolling cart (carries the 4 chafers permanently)",
                  "Hot box + rubber bladders 4-6L near-boiling water (95C)  [G-09]"):
            A("   [ ] " + e)
    if "skewer" in txt:  A("   [ ] 6-inch bamboo skewers")
    if "date" in txt and "bacon" in txt: A("   [ ] Multi-color toothpicks (BWD house standard)")
    if any(t in txt for t in SOFT):
        A("   [ ] Soft bag / pizza carrier - presentation items do not fit pan slots")
        A("   [ ] Insulating blanket (large boards: below + above, kraft-taped)")
    A("")
    A(" SERVING / DISPOSABLE / LINEN  (verbatim from the order)")
    got = [n for n in notes.values()
           if re.search(r"\b(plates?|napkins?|plasticware|cutlery|forks?|cups?|linen|silverware)\b", n, re.I)]
    for s in dict.fromkeys(got) or ["- none stated in the order note"]:
        A(wrap(s, 7, ) if False else textwrap.fill(s, W, initial_indent="   [ ] ", subsequent_indent="       "))
    A("")
    A(" SIGNS    [ ] __PRINTED__                      [ ] loaded")
    A(rule("-"))
    A(" SAFETY & TEMP   (locked KB rules - not optional)")
    A("   [ ] first-cook poultry 165F IT; reheats + fish 145F          [G-08]")
    A("   [ ] flash-chill make-ahead proteins, no tight cover >45F     [G-06]")
    A("   [ ] cook->chill <= 2h   [ ] hot-hold > 140F   [ ] salmon 125F")
    A("   [ ] hot-box bladders 4-6L @ 95C                              [G-09]")
    A("   [ ] date & initial the poly   [ ] olive oil not butter       [G-01]")
    A("   [ ] allergen check BEFORE procurement                        [G-10]")
    A(rule("-"))
    A(" TASKS   (KB Task Verb Library prefixes)")
    ts = []
    if any(t in txt for t in PRES):
        ts += [("PACK","pan carrier load (cold/hot pans)"),
               ("PACK","soft carrier load - presentation items, LOAD LAST (zone 3)"),
               ("STAGE","unwrap + place presentation items on site")]
    ts += [("FLAG","transport pans must be FULL-WIDTH; sixth pans prohibited (decant rule)"),
           ("CONFIRM","allergen / dietary check BEFORE procurement"),
           ("DELIVER","arrive %s at %s" % (d.get("arrival_time") or "TBC", d.get("venue_address") or "the venue"))]
    for v,w in ts:
        A(textwrap.fill("%-8s %s" % (v,w), W, initial_indent="   [ ] ", subsequent_indent="       "))
    A(rule("-"))
    A(" PROVENANCE")
    A("   source        intercom topic order.captured, published by order_ingest")
    A("   order_id      %s" % p.get("order_id"))
    A("   content_hash  %s" % p.get("content_hash"))
    A("   correlation   %s" % p.get("correlation_id"))
    A("   verbatim      payload.note_text and payload.line_items are unmodified")
    A("   derived       venue / arrival / start / guests came from the note text, not a human")
    A(rule("="))
    return "\n".join(L)


def main():
    dry = "--dry-run" in sys.argv
    nop = "--no-print" in sys.argv
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=DAYS)
    orders = pull_orders(today, horizon)
    if not orders:
        print("The bus carries no order.captured in %s..%s - nothing to print." % (today, horizon))
        return

    # group by (customer, service_date): one checklist per event-day, same invoice may
    # cover several days
    days = {}
    for p in orders:
        # a multi-day order (Peggy 10/8+10/9) is ONE order but TWO service days, and the
        # crew needs one sheet per day
        for sd in (p.get("service_dates") or [p["service_date"]]):
            try:
                if not (today <= datetime.date.fromisoformat(sd) <= horizon):
                    continue
            except Exception:
                continue
            days.setdefault((p.get("customer_name",""), sd), []).append(p)

    os.makedirs(OUT, exist_ok=True)
    made = []
    for (cust, sd), ps in sorted(days.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        d = datetime.date.fromisoformat(sd)
        same = sorted({k[1] for k in days if k[0] == cust})
        label = d.strftime("%A %Y-%m-%d") + (
            "   (day %d of %d)" % (same.index(sd)+1, len(same)) if len(same) > 1 else "")
        p = dict(ps[0])
        p["line_items"] = [i for q in ps for i in q["line_items"]]
        txt = build(p, label)
        path = os.path.join(OUT, "checklist_%s_%s.txt" % (sd, re.sub(r"\W+","",cust)))
        open(path, "w").write(txt + "\n")
        made.append((cust, sd, path, txt))
        if not nop: print("\n" + txt)

    if dry or nop:
        print("\n%d checklist(s) rendered from the bus." % len(made)); return

    os.makedirs(SPOOL, exist_ok=True)
    for cust, sd, path, _ in made:
        pdf = path[:-4] + ".pdf"
        try:
            with open(pdf, "wb") as fh:
                subprocess.run(["cupsfilter","-m","application/pdf",path], stdout=fh,
                               stderr=subprocess.DEVNULL, check=True)
        except Exception as ex:
            print(">>> PDF render failed for %s: %s" % (path, ex)); continue
        r = subprocess.run(["lp","-d",PRINTER,"-o","media=na_letter_8.5x11in",
                            "-o","print-color-mode=monochrome",
                            "-t","CHECKLIST %s %s" % (sd,cust), pdf],
                           capture_output=True, text=True)
        if r.returncode:
            shutil.copy(pdf, SPOOL)
            subprocess.run(["/home/taza/checklist-app/printer-selfheal.sh"])
            print(">>> print rc=%s -> SPOOLED, self-heal will retry (%s)" % (r.returncode, pdf))
        else:
            print(">>> queued %s" % (r.stdout or "").strip())
    print("\n%d checklist(s) built from order.captured." % len(made))


if __name__ == "__main__":
    main()
