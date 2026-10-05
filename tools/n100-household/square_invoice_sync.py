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
                    square_created_at, square_updated_at, line_items, payment_requests, payload
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
                    last_synced_at = now()
                """,
                rows, page_size=100,
            )
            return len(rows)
    finally:
        conn.close()



def refresh_deposit_table():
    """Rebuild the internal interface table (D43). Apps read this, not the raw mirror."""
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("TRUNCATE public.invoices_with_deposit;")
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
            """)
            return cur.rowcount
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
        return 1
    try:
        invoices, pages = fetch_all_invoices()
        rows = []
        for inv in invoices:
            r = flatten(inv)
            rows.append(tuple(r[k] for k in (
                "square_invoice_id","invoice_number","square_order_id","location_id","status",
                "customer_id","customer_name","customer_email","customer_phone",
                "total_cents","amount_paid_cents","amount_due_cents","deposit_paid_cents",
                "has_deposit","is_fully_paid","due_date",
                "square_created_at","square_updated_at","line_items","payment_requests","payload")))
        upserted = upsert(rows)
        with_deposit = refresh_deposit_table()
        log.info("invoices_with_deposit refreshed: %d rows", with_deposit)
        deposit_unpaid = sum(1 for r in rows if r[13] and not r[14])
        log.info("seen=%d upserted=%d deposit_unpaid=%d pages=%d", len(rows), upserted, deposit_unpaid, pages)
        write_sync_log("ok", len(rows), upserted, deposit_unpaid, pages)
        return 0
    except Exception as exc:
        log.exception("sync failed")
        write_sync_log("failed", 0, 0, 0, 0, str(exc)[:500])
        return 1


if __name__ == "__main__":
    sys.exit(main())
