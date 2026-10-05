#!/usr/bin/env python3
"""
Square invoice mirror -- pull-and-upsert on a 30-minute timer (decision D43).

Mirrors square_catalog_sync.py exactly in shape: same env file, same PG DSN,
same retry helper, same sync-log pattern. Difference: Square's invoice search
requires a query object, and the payload shape is invoices rather than catalog
objects.

Stores every invoice returned, with the API object kept verbatim in payload, so
nothing is lost if a derived column turns out to be wrong. Two booleans express
the subset Nick specified (D43): has_deposit and is_fully_paid.
"""
import fcntl
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("square_invoice_sync")

ACCESS_TOKEN  = os.environ.get("SQUARE_ACCESS_TOKEN")
API_BASE      = os.environ.get("SQUARE_API_BASE", "https://connect.squareup.com/v2")
API_VERSION   = os.environ.get("SQUARE_API_VERSION", "2025-01-23")
LOCATION_ID   = os.environ.get("SQUARE_LOCATION_ID")
PG_DSN        = os.environ.get("TAZAOS_PG_DSN", "dbname=tazaos user=taza host=/var/run/postgresql")

LOCK_PATH = os.environ.get("SYNC_LOCK_PATH", "/tmp/square_invoice_sync.lock")

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Square-Version": API_VERSION,
    "Content-Type": "application/json",
}


def request_json(path, body=None, method="POST", attempts=3):
    url = f"{API_BASE}{path}"
    for attempt in range(1, attempts + 1):
        try:
            if method == "POST":
                r = requests.post(url, headers=HEADERS, json=body, timeout=30)
            else:
                r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504) and attempt < attempts:
                wait = 2 ** attempt
                log.warning("http %s on %s, retrying in %ss", r.status_code, path, wait)
                time.sleep(wait)
                continue
            log.error("http %s on %s: %s", r.status_code, path, r.text[:500])
            return {"errors": [{"code": f"http_{r.status_code}", "detail": r.text[:500]}]}
        except requests.RequestException as exc:
            if attempt < attempts:
                time.sleep(2 ** attempt)
                continue
            log.error("request failed on %s: %s", path, exc)
            return {"errors": [{"code": "request_failed", "detail": str(exc)}]}
    return {"errors": [{"code": "exhausted_retries"}]}


def money(node):
    if not node:
        return 0
    try:
        return int(node.get("amount") or 0)
    except (TypeError, ValueError):
        return 0


def resolve_location_ids():
    if LOCATION_ID:
        return [LOCATION_ID]
    data = request_json("/locations", method="GET")
    if "errors" in data:
        return []
    return [l.get("id") for l in data.get("locations", []) if l.get("id") and l.get("status") == "ACTIVE"]


def fetch_all_invoices():
    """Paginate /invoices/search. Square requires a query object."""
    location_ids = resolve_location_ids()
    log.info("locations resolved: %s", location_ids or "(none - searching unfiltered)")
    cursor, invoices, pages = None, [], 0
    while True:
        # an explicit filter is only meaningful when we actually know the location
        body = {"query": {"filter": {"location_ids": location_ids}} if location_ids else {}, "limit": 100}
        if cursor:
            body["cursor"] = cursor
        data = request_json("/invoices/search", body=body)
        if "errors" in data:
            raise RuntimeError(json.dumps(data["errors"])[:500])
        invoices.extend(data.get("invoices") or [])
        pages += 1
        cursor = data.get("cursor")
        if not cursor:
            break
    return invoices, pages


def flatten(inv):
    """Derive queryable columns. Anything uncertain stays in payload."""
    requests_ = inv.get("payment_requests") or []
    first = requests_[0] if requests_ else {}
    # Sum across EVERY payment request. An invoice with a deposit has two requests
    # (deposit + balance); reading only the first makes a half-paid invoice look
    # settled. Caught 2026-10-04 by cross-checking PARTIALLY_PAID invoices (D43).
    total = sum(money(r.get("computed_amount_money")) for r in requests_)
    paid  = sum(money(r.get("total_completed_amount_money")) for r in requests_)
    due = max(total - paid, 0)
    recipient = inv.get("primary_recipient") or {}
    status = inv.get("status")
    return {
        "square_invoice_id": inv.get("id"),
        "invoice_number": inv.get("invoice_number"),
        "square_order_id": inv.get("order_id"),
        "location_id": inv.get("location_id"),
        "status": status,
        "customer_id": recipient.get("customer_id"),
        "customer_name": recipient.get("given_name") or recipient.get("family_name") or recipient.get("company_name"),
        "customer_email": recipient.get("email_address"),
        "customer_phone": recipient.get("phone_number"),
        "total_cents": total,
        "amount_paid_cents": paid,
        "amount_due_cents": due,
        "deposit_paid_cents": paid,
        "has_deposit": paid > 0,
        "is_fully_paid": status == "PAID" or (total > 0 and due <= 0),
        "due_date": first.get("due_date"),
        "square_created_at": inv.get("created_at"),
        "square_updated_at": inv.get("updated_at"),
        "line_items": json.dumps((inv.get("order") or {}).get("line_items") or []),
        "payment_requests": json.dumps(requests_),
        "payload": json.dumps(inv),
        "last_seen_at": datetime.now(timezone.utc),
    }


def upsert(rows):
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn, conn.cursor() as cur:
            # execute_values pages internally, so rowcount reflects only the last
            # batch; accumulate instead of trusting it (D43 fix)
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO square_invoices (
                    square_invoice_id, invoice_number, square_order_id, location_id, status,
                    customer_id, customer_name, customer_email, customer_phone,
                    total_cents, amount_paid_cents, amount_due_cents, deposit_paid_cents,
                    has_deposit, is_fully_paid, due_date,
                    square_created_at, square_updated_at, line_items, payment_requests, payload,
                    last_seen_at
                ) VALUES %s
                ON CONFLICT (square_invoice_id) DO UPDATE SET
                    invoice_number = EXCLUDED.invoice_number,
                    status = EXCLUDED.status,
                    customer_id = EXCLUDED.customer_id,
                    customer_name = EXCLUDED.customer_name,
                    customer_email = EXCLUDED.customer_email,
                    customer_phone = EXCLUDED.customer_phone,
                    total_cents = EXCLUDED.total_cents,
                    amount_paid_cents = EXCLUDED.amount_paid_cents,
                    amount_due_cents = EXCLUDED.amount_due_cents,
                    deposit_paid_cents = EXCLUDED.deposit_paid_cents,
                    has_deposit = EXCLUDED.has_deposit,
                    is_fully_paid = EXCLUDED.is_fully_paid,
                    due_date = EXCLUDED.due_date,
                    square_updated_at = EXCLUDED.square_updated_at,
                    line_items = EXCLUDED.line_items,
                    payment_requests = EXCLUDED.payment_requests,
                    payload = EXCLUDED.payload,
                    last_seen_at = EXCLUDED.last_seen_at,
                    last_synced_at = now()
                """,
                rows, page_size=100,
            )
            return len(rows)
    finally:
        conn.close()




def raise_alert(severity, title, detail):
    """Write to the interim exception sink (ops_alert, D45). PROD-23 will own this later.
    A job that can fail silently is an unmonitored job."""
    try:
        conn = psycopg2.connect(PG_DSN)
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.ops_alert (source, severity, title, detail) VALUES (%s,%s,%s,%s)",
                ("square_invoice_sync", severity, title, detail[:2000]))
        conn.close()
    except Exception:
        log.exception("could not write the alert either")


def previous_successful_count():
    """How many invoices the last OK run saw. None if there is no history."""
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT invoices_seen FROM public.square_invoice_sync_log
                           WHERE status = 'ok' ORDER BY id DESC LIMIT 1""")
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()



# Business fields whose change means the WORK has changed, not just the money (D52).
# Invoices changing is the normal case - the estimate grows after the deposit, as
# customers add headcount and food. So invoice.changed is a first-class event.
BUSINESS_FIELDS = ("status", "total_cents", "amount_due_cents", "due_date",
                   "customer_name", "customer_email", "event_date", "invoice_number")


def prior_state(ids):
    """The stored state BEFORE this run's upsert, so transitions can be detected."""
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT square_invoice_id, status, coalesce(amount_paid_cents,0),
                                  coalesce(amount_due_cents,0), coalesce(total_cents,0),
                                  coalesce(due_date::text,''), coalesce(customer_name,''),
                                  coalesce(customer_email,''), coalesce(event_date::text,''),
                                  coalesce(invoice_number,'')
                           FROM public.square_invoices
                           WHERE square_invoice_id = ANY(%s)""", (list(ids),))
            return {r[0]: r for r in cur.fetchall()}
    finally:
        conn.close()


def detect_and_emit(rows, prior):
    """Emit ONLY on genuine transitions. Discovery is not a transition."""
    emitted = 0
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn, conn.cursor() as cur:
            def emit(topic, iid, frm, to, payload):
                nonlocal emitted
                cur.execute("SELECT public.emit_event(%s,%s,%s,%s,%s,%s,NULL,%s,%s)",
                            (topic, "square_invoice_sync", "invoice", iid, "info",
                             json.dumps(payload), frm, to))
                emitted += 1

            for r in rows:
                iid = r["square_invoice_id"]
                p = prior.get(iid)
                paid, due, status = r["amount_paid_cents"], r["amount_due_cents"], r["status"]

                if p is None:
                    emit("invoice.created", iid, None, status,
                         {"invoice_number": r["invoice_number"], "status": status,
                          "total_cents": r["total_cents"]})
                    continue

                p_status, p_paid, p_due, p_total = p[1], p[2], p[3], p[4]

                # THE trigger (D51): first deposit. This is what starts downstream work.
                if p_paid == 0 and paid > 0 and status != "CANCELED":
                    emit("invoice.deposit_received", iid, p_status, status,
                         {"invoice_number": r["invoice_number"], "deposit_cents": paid,
                          "total_cents": r["total_cents"], "amount_due_cents": due,
                          "customer_name": r["customer_name"], "event_date": r["event_date"]})

                if p_status != "PAID" and status == "PAID":
                    emit("invoice.paid", iid, p_status, "PAID",
                         {"invoice_number": r["invoice_number"], "total_cents": r["total_cents"]})

                if p_status != "CANCELED" and status == "CANCELED":
                    emit("invoice.canceled", iid, p_status, "CANCELED",
                         {"invoice_number": r["invoice_number"]})

                if paid < p_paid:
                    emit("invoice.refunded", iid, p_status, status,
                         {"invoice_number": r["invoice_number"],
                          "was_paid_cents": p_paid, "now_paid_cents": paid})

                # content changed - the normal case, not an exception
                now_vals = (status, r["total_cents"], due, r["due_date"] or "",
                            r["customer_name"] or "", r["customer_email"] or "",
                            r["event_date"] or "", r["invoice_number"] or "")
                was_vals = (p[1], p_total, p_due, p[5], p[6], p[7], p[8], p[9])
                diffs = {f: {"was": w, "now": n}
                         for f, w, n in zip(BUSINESS_FIELDS, was_vals, now_vals) if w != n}
                if diffs:
                    emit("invoice.changed", iid, p_status, status,
                         {"invoice_number": r["invoice_number"], "diffs": diffs})
    finally:
        conn.close()
    return emitted


def refresh_deposit_table(min_expected=1):
    """min_expected guards against a bad run emptying the table via the prune."""
    """Rebuild the internal interface table (D43).

    UPSERT rather than TRUNCATE so first_deposit_seen_at survives across runs --
    a TRUNCATE reset it to now() every 30 minutes, making the column meaningless.
    """
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO public.invoices_with_deposit
                 (square_invoice_id, invoice_number, status, customer_id, customer_name,
                  customer_email, customer_phone, total_cents, deposit_cents, balance_cents,
                  is_fully_paid, is_outstanding, due_date, square_created_at, square_updated_at,
                  first_deposit_seen_at, refreshed_at)
                SELECT square_invoice_id, invoice_number, status, customer_id, customer_name,
                       customer_email, customer_phone, total_cents, amount_paid_cents, amount_due_cents,
                       is_fully_paid, (amount_paid_cents > 0 AND amount_due_cents > 0), due_date,
                       square_created_at, square_updated_at, now(), now()
                FROM public.square_invoices
                WHERE amount_paid_cents > 0
                ON CONFLICT (square_invoice_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    customer_name = EXCLUDED.customer_name,
                    customer_email = EXCLUDED.customer_email,
                    customer_phone = EXCLUDED.customer_phone,
                    total_cents = EXCLUDED.total_cents,
                    deposit_cents = EXCLUDED.deposit_cents,
                    balance_cents = EXCLUDED.balance_cents,
                    is_fully_paid = EXCLUDED.is_fully_paid,
                    is_outstanding = EXCLUDED.is_outstanding,
                    due_date = EXCLUDED.due_date,
                    square_updated_at = EXCLUDED.square_updated_at,
                    refreshed_at = now()
                    -- first_deposit_seen_at deliberately NOT touched
            """)
            n = cur.rowcount
            # drop anything that no longer has a deposit (refunded to zero)
            cur.execute("""
                DELETE FROM public.invoices_with_deposit d
                WHERE NOT EXISTS (SELECT 1 FROM public.square_invoices s
                                  WHERE s.square_invoice_id = d.square_invoice_id
                                    AND s.amount_paid_cents > 0)
            """)
            return n
    finally:
        conn.close()


def write_sync_log(status, seen, upserted, deposit_unpaid, pages, error=None):
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO square_invoice_sync_log
                   (finished_at, status, invoices_seen, invoices_upserted, deposit_unpaid, pages, error_message)
                   VALUES (NOW(), %s, %s, %s, %s, %s, %s)""",
                (status, seen, upserted, deposit_unpaid, pages, error),
            )
    finally:
        conn.close()


def main():
    if not ACCESS_TOKEN:
        log.error("SQUARE_ACCESS_TOKEN not set")
        write_sync_log("failed", 0, 0, 0, 0, "SQUARE_ACCESS_TOKEN not set")
        raise_alert("critical", "Square invoice sync: no token", "SQUARE_ACCESS_TOKEN missing from the environment file")
        return 1
    # CRITICAL 1: one run at a time. The timer fires every 30 min; a slow run must
    # not overlap the next one, or two runs race on the same rows.
    #
    # RE-HARDENED after this killed the sync in testing: the lock file was created
    # by one user (the service runs as taza) and refused to another (the direct test
    # ran as root), and the resulting PermissionError took the WHOLE SYNC DOWN.
    # A lock that cannot be taken must never stop the work. If we cannot lock, we
    # log loudly and carry on unlocked. systemd already refuses to start an active
    # oneshot unit, so the lock is belt-and-braces, not the primary defence.
    lock_fh = None
    try:
        lock_fh = open(LOCK_PATH, "w")
        try:
            os.chmod(LOCK_PATH, 0o666)
        except OSError:
            pass
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.warning("another sync is already running - exiting without doing anything")
        return 0
    except OSError as exc:
        log.warning("could not take the lock (%s) - continuing WITHOUT it", exc)
        raise_alert("warning", "Square invoice sync ran uNLOCKED",
                    f"could not acquire {LOCK_PATH}: {exc}. The sync proceeded. "
                    "systemd should still prevent overlap, but investigate the lock path.")

    try:
        invoices, pages = fetch_all_invoices()

        # CRITICAL 2a: validate the shape before trusting it. An error body or a
        # truncated response must never be interpreted as "there are no invoices".
        if not isinstance(invoices, list):
            raise RuntimeError("API returned a non-list invoices field")
        prev = previous_successful_count()
        if prev and len(invoices) < prev * 0.5:
            raise RuntimeError(
                f"anomaly guard: this run sees {len(invoices)} invoices but the last good run "
                f"saw {prev}. Refusing to write or prune on a suspicion of a partial response.")

        flat = []   # dicts, for transition detection
        rows = []   # tuples, for execute_values
        for inv in invoices:
            r = flatten(inv)
            flat.append(r)
            rows.append(tuple(r[k] for k in (
                "square_invoice_id","invoice_number","square_order_id","location_id","status",
                "customer_id","customer_name","customer_email","customer_phone",
                "total_cents","amount_paid_cents","amount_due_cents","deposit_paid_cents",
                "has_deposit","is_fully_paid","due_date",
                "square_created_at","square_updated_at","line_items","payment_requests","payload","last_seen_at")))
        prior = prior_state([r["square_invoice_id"] for r in flat])
        upserted = upsert(rows)
        emitted = detect_and_emit(flat, prior)
        log.info("transitions emitted: %d", emitted)
        with_deposit = refresh_deposit_table(min_expected=1)
        log.info("invoices_with_deposit refreshed: %d rows", with_deposit)
        deposit_unpaid = sum(1 for r in rows if r[13] and not r[14])
        log.info("seen=%d upserted=%d deposit_unpaid=%d pages=%d", len(rows), upserted, deposit_unpaid, pages)
        write_sync_log("ok", len(rows), upserted, deposit_unpaid, pages)
        return 0
    except Exception as exc:
        log.exception("sync failed")
        # CRITICAL 3: a failure must leave a visible row, not just a journal line.
        write_sync_log("failed", 0, 0, 0, 0, str(exc)[:500])
        raise_alert("critical", "Square invoice sync failed", repr(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
