#!/usr/bin/env python3
"""
order_ingest -- README-FIRST section 13, steps 2+3: look up the ORDER, pull ALL of it
word for word, and POST it to the intercom (PROD-20, D49).

WHY THIS EXISTS
  `square_invoices.line_items` has been empty since the mirror was built. The invoice
  search response returns order_id only, so the sync never had the line items -- and the
  line items are where the actual booking lives: venue, arrival time, guest count and the
  whole menu are sitting in the free-text `Details` note of the order. An app that needs
  to know what gig, when, with what food, where and what service type cannot get any of
  that from the invoice row. It has to come from the order.

WHAT IT DOES
  deposited invoice  ->  /v2/orders/{order_id}  ->  emit_event('order.captured', ...)
  The payload carries the order VERBATIM (sec.13: "not summarised, not interpreted, not
  field-mapped at capture time") alongside a clearly-separated `derived` block, because
  anything summarised at capture can never be un-summarised.

IDEMPOTENT
  content_hash covers the order contents. Re-running with no change emits nothing.

READS Square; WRITES only event bus rows via emit_event(). Never writes invoice tables.
"""
import hashlib, json, os, re, subprocess, sys, uuid, datetime
import urllib.request
import psycopg2

VERSION = "0.1.0"
SRC     = "order_ingest"
DSN     = os.environ.get("TAZAOS_PG_DSN", "dbname=tazaos user=taza host=/var/run/postgresql")
SECRETS = "/etc/taza/secrets"
CACHE   = "/home/taza/order-ingest/cache"
LOG     = "/home/taza/order-ingest/order_ingest.log"


def log(msg):
    line = "%s %s" % (datetime.datetime.now().strftime("%F %T"), msg)
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def conn():
    # 14.1 application_name on every connection; 14.2 nothing runs at timeout 0
    return psycopg2.connect(DSN, application_name=SRC,
                            options="-c statement_timeout=120s -c lock_timeout=10s")


def token():
    out = subprocess.run(["sudo", "grep", "^SQUARE_ACCESS_TOKEN=", SECRETS],
                         capture_output=True, text=True).stdout.strip()
    return out.split("=", 1)[1]


def fetch_order(oid, tok):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, oid + ".json")
    if not os.path.exists(p):
        req = urllib.request.Request("https://connect.squareup.com/v2/orders/" + oid,
                                     headers={"Authorization": "Bearer " + tok,
                                              "Square-Version": "2024-06-04"})
        with urllib.request.urlopen(req, timeout=25) as f:
            open(p, "w").write(f.read().decode())
    return json.load(open(p))["order"]


def derive(note_text, items):
    """Split the free text into the fields a checklist/shopping app needs.
    Every value here is DERIVED and is flagged as such in the payload - the verbatim
    text rides alongside it so a wrong parse can always be re-run."""
    b = note_text.lower()
    d = {}
    m = re.search(r"taza\s+(?:delivery|arrival|setup)\s*time\s*[:\-]\s*([0-9]{1,4}(?::[0-9]{2})?\s*[ap]m)", b)
    d["arrival_time"] = m.group(1).upper().replace(" ", "") if m else None
    m = re.search(r"event\s+(?:start\s*)?time\s*[:\-]\s*([0-9]{1,4}(?::[0-9]{2})?\s*[ap]m)", b)
    d["event_start_time"] = m.group(1).upper().replace(" ", "") if m else None
    for pat in (r"new total number of guests is\s*[:\-]?\s*([0-9]+)",
                r"number of guests\s*[:\-]?\s*([0-9]+)",
                r"for\s+([0-9]+)\s+guests"):
        m = re.search(pat, b)
        if m:
            d["guest_count"] = int(m.group(1)); break
    addrs = []
    for L in note_text.split("\n"):
        s = L.strip().rstrip(")")
        if re.match(r"^\d{3,5}\s+\w", s) and "," in s:
            addrs.append(s)
        elif re.search(r"(university|reservation|center|resort|hotel|club)", s, re.I) \
             and not s.lower().startswith(("address", "event")):
            addrs.append(s)
    d["venue_address"] = " / ".join(dict.fromkeys(addrs)) or None
    d["service_type"] = ("full_service"
                         if any("full service" in (i.get("name") or "").lower() for i in items)
                         else "drop_off")
    d["derived_from"] = "order line item notes (verbatim text preserved under note_text)"
    d["derived_by"] = SRC + " v" + VERSION
    return d


SQL_WINDOW = """
select square_invoice_id, invoice_number, coalesce(customer_name,''), coalesce(customer_email,''),
       coalesce(customer_phone,''), coalesce(status,''), coalesce(total_cents,0),
       coalesce(amount_paid_cents,0), coalesce(amount_due_cents,0), coalesce(due_date::text,''),
       coalesce(payload->>'order_id',''), coalesce(payload->>'title',''),
       coalesce(event_date_derived::text,'')
from square_invoices
where coalesce(amount_paid_cents,0) > 0
  and coalesce(payload->>'order_id','') <> ''
"""


def main():
    days = int(os.environ.get("ORDER_WINDOW_DAYS", "30"))
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=days)
    tok = token()
    run_corr = str(uuid.uuid4())
    emitted = skipped = failed = 0

    with conn() as c, c.cursor() as cur:
        cur.execute(SQL_WINDOW)
        rows = cur.fetchall()

    for (sid, invno, cname, cemail, cphone, status, total, paid, due,
         due_date, oid, title, derived_date) in rows:
        # date window: prefer the invoice-encoded date, fall back to the derived column
        ds = []
        parts = re.split(r"[-_ ]+", invno or "")
        yr = next((int(p) for p in parts if p.isdigit() and len(p) == 4 and 2020 <= int(p) <= 2035), None)
        for p in parts:
            if p.isdigit() and len(p) == 4 and not (2020 <= int(p) <= 2035) and yr:
                mm, dd = int(p[:2]), int(p[2:])
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    try: ds.append(datetime.date(yr, mm, dd))
                    except ValueError: pass
        if not ds and derived_date:
            try: ds.append(datetime.date.fromisoformat(derived_date))
            except ValueError: pass
        ds = [d for d in ds if today <= d <= horizon]
        if not ds:
            continue
        service_date = min(ds)

        try:
            o = fetch_order(oid, tok)
        except Exception as ex:
            failed += 1
            log("ORDER FETCH FAILED %s (%s): %s" % (invno, oid, ex))
            continue

        items = [{"uid": li.get("uid"), "name": li.get("name"),
                  "quantity": li.get("quantity"),
                  "amount_cents": li.get("total_money", {}).get("amount"),
                  "note": li.get("note") or ""} for li in o.get("line_items", [])]
        note_text = "\n".join(i["note"] for i in items if i["note"])

        payload = {
            # ---- verbatim (sec.13: capture word for word) ----
            "invoice_number": invno, "order_id": oid, "title": title,
            "customer_name": cname, "customer_email": cemail, "customer_phone": cphone,
            "deposit_cents": paid, "amount_due_cents": due, "total_cents": total,
            "invoice_status": status, "invoice_due_date": due_date,
            "service_date": service_date.isoformat(),
            # a multi-day event is real (Peggy 10/8 + 10/9 is one order, two service days)
            "service_dates": [x.isoformat() for x in ds],
            "sale_or_service_date": o.get("sale_or_service_date"),
            "order_state": o.get("state"),
            "line_items": items,
            "note_text": note_text,
            "raw_order": o,
            # ---- derived (clearly separated, never a substitute for the verbatim) ----
            "derived": derive(note_text, items),
            "correlation_id": run_corr,
        }
        h = hashlib.sha256(json.dumps(
            {"items": items, "title": title, "paid": paid, "due": due, "status": status,
             "dates": [x.isoformat() for x in ds]},
            sort_keys=True).encode()).hexdigest()[:16]
        payload["content_hash"] = h

        # idempotent: skip if the bus already carries this exact content
        with conn() as c, c.cursor() as cur:
            cur.execute("""select 1 from system_events
                           where topic='order.captured' and entity_id=%s
                             and payload->>'content_hash'=%s limit 1""", (sid, h))
            if cur.fetchone():
                skipped += 1
                continue
            cur.callproc("emit_event", (
                "order.captured", SRC, "invoice", sid, "info",
                json.dumps(payload), run_corr, None, None, datetime.datetime.now(datetime.timezone.utc)))
            c.commit()
        emitted += 1
        log("POSTED order.captured %s  order=%s  service=%s  items=%d  guests=%s"
            % (invno, oid[:12], service_date, len(items),
               payload["derived"].get("guest_count")))

    log("run complete: emitted=%d skipped_unchanged=%d failed=%d correlation_id=%s"
        % (emitted, skipped, failed, run_corr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
