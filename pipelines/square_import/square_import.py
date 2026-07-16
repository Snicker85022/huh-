#!/usr/bin/env python3
"""
Taza OS — Square invoice/order import pipeline.

Pulls Square invoices (+ their orders, line items, and payments) into
PostgreSQL (schema taza_ops), idempotently. Designed to run on the N100 under a
systemd timer.

Flow, per the Schema Contract:
    invoices.search (by location)
      -> upsert accounts/contacts (from primary_recipient)
      -> upsert invoices                     (UPSERT by source_system+external_id)
      -> orders.batch-retrieve (by order_id)
      -> upsert orders
      -> replace invoice_line_items (from order.line_items)
      -> upsert payments (from order.tenders)

Idempotency: every row is upserted on (source_system='square', external_id).
Change detection: an external_payload_hash is stored; unchanged invoices are
skipped without touching the DB.

Config (environment / .env — see .env.example):
    SQUARE_ACCESS_TOKEN   required
    DATABASE_URL          required, e.g. postgres://taza@localhost/taza_ops
    SQUARE_LOCATION_ID    optional; if unset, all active locations are imported
    SQUARE_API_BASE       default https://connect.squareup.com
    SQUARE_API_VERSION    default 2025-01-23
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import date, datetime
from typing import Any, Iterable

import psycopg2
import psycopg2.extras
import requests

log = logging.getLogger("square_import")

SQUARE_API_BASE = os.environ.get("SQUARE_API_BASE", "https://connect.squareup.com")
SQUARE_API_VERSION = os.environ.get("SQUARE_API_VERSION", "2025-01-23")

# Square invoice status (UPPER_SNAKE) -> taza_ops.invoice_status enum value.
INVOICE_STATUS_MAP = {
    "DRAFT": "Draft",
    "SCHEDULED": "Scheduled",
    "UNPAID": "Unpaid",
    "PARTIALLY_PAID": "PartiallyPaid",
    "PAID": "Paid",
    "REFUNDED": "Refunded",
    "CANCELED": "Canceled",
    "FAILED": "Failed",
}


# --------------------------------------------------------------------------- #
# Square REST client                                                          #
# --------------------------------------------------------------------------- #
class Square:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Square-Version": SQUARE_API_VERSION,
                "Content-Type": "application/json",
            }
        )

    def _post(self, path: str, body: dict) -> dict:
        r = self.session.post(f"{SQUARE_API_BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def _get(self, path: str) -> dict:
        r = self.session.get(f"{SQUARE_API_BASE}{path}", timeout=30)
        r.raise_for_status()
        return r.json()

    def active_location_ids(self) -> list[str]:
        locs = self._get("/v2/locations").get("locations", [])
        return [l["id"] for l in locs if l.get("status") == "ACTIVE"]

    def iter_invoices(self, location_id: str) -> Iterable[dict]:
        cursor = None
        while True:
            body: dict[str, Any] = {
                "query": {"filter": {"location_ids": [location_id]}},
                "limit": 100,
            }
            if cursor:
                body["cursor"] = cursor
            data = self._post("/v2/invoices/search", body)
            for inv in data.get("invoices", []):
                yield inv
            cursor = data.get("cursor")
            if not cursor:
                return

    def batch_orders(self, location_id: str, order_ids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for i in range(0, len(order_ids), 100):  # Square caps batch at 100
            chunk = order_ids[i : i + 100]
            data = self._post(
                "/v2/orders/batch-retrieve",
                {"location_id": location_id, "order_ids": chunk},
            )
            for o in data.get("orders", []):
                out[o["id"]] = o
        return out


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def payload_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def money(m: dict | None) -> int | None:
    return None if not m else m.get("amount")


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_date(s: str | None) -> date | None:
    return None if not s else date.fromisoformat(s[:10])


# --------------------------------------------------------------------------- #
# Upserts                                                                      #
# --------------------------------------------------------------------------- #
def upsert_account(cur, recipient: dict) -> str | None:
    """Upsert the paying account from an invoice primary_recipient; return id."""
    cid = recipient.get("customer_id")
    if not cid:
        return None
    name = " ".join(
        p for p in [recipient.get("given_name"), recipient.get("family_name")] if p
    ) or recipient.get("email_address") or cid
    cur.execute(
        """
        INSERT INTO taza_ops.accounts
            (display_name, primary_email, primary_phone,
             source_system, external_id, external_updated_at)
        VALUES (%s, %s, %s, 'square', %s, now())
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            display_name  = EXCLUDED.display_name,
            primary_email = COALESCE(EXCLUDED.primary_email, taza_ops.accounts.primary_email),
            primary_phone = COALESCE(EXCLUDED.primary_phone, taza_ops.accounts.primary_phone),
            updated_at    = now()
        RETURNING id
        """,
        (name, recipient.get("email_address"), recipient.get("phone_number"), cid),
    )
    account_id = cur.fetchone()[0]
    # Keep a contact record for the person too (the inquirer/decision-maker).
    cur.execute(
        """
        INSERT INTO taza_ops.contacts
            (account_id, first_name, last_name, email, phone, is_primary,
             source_system, external_id, external_updated_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, 'square', %s, now())
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            account_id = EXCLUDED.account_id,
            first_name = EXCLUDED.first_name,
            last_name  = EXCLUDED.last_name,
            email      = COALESCE(EXCLUDED.email, taza_ops.contacts.email),
            phone      = COALESCE(EXCLUDED.phone, taza_ops.contacts.phone),
            updated_at = now()
        """,
        (
            account_id,
            recipient.get("given_name"),
            recipient.get("family_name"),
            recipient.get("email_address"),
            recipient.get("phone_number"),
            cid,
        ),
    )
    return account_id


def deposit_fields(inv: dict) -> dict:
    """Extract deposit/balance figures from payment_requests."""
    out = {
        "deposit_pct": None,
        "deposit_amount_cents": None,
        "balance_due_cents": None,
        "date_balance_due": None,
    }
    for pr in inv.get("payment_requests", []):
        if pr.get("request_type") == "DEPOSIT":
            out["deposit_pct"] = (
                float(pr["percentage_requested"])
                if pr.get("percentage_requested")
                else None
            )
            out["deposit_amount_cents"] = money(pr.get("computed_amount_money"))
        elif pr.get("request_type") == "BALANCE":
            out["balance_due_cents"] = money(pr.get("computed_amount_money"))
            out["date_balance_due"] = parse_date(pr.get("due_date"))
    return out


def upsert_invoice(cur, inv: dict, order: dict | None, account_id: str | None) -> str:
    dep = deposit_fields(inv)
    status_raw = inv.get("status")
    status = INVOICE_STATUS_MAP.get(status_raw, "Draft")
    subtotal = None
    total = None
    if order:
        total = money(order.get("total_money"))
        net = order.get("net_amounts", {})
        subtotal = None if total is None else total - (money(net.get("tax_money")) or 0)
    # deposit basis = the initial-quote total (locked); we record the current
    # order total as the basis on first import — later scope changes never move
    # the deposit (Nick, 7/16).
    cur.execute(
        """
        INSERT INTO taza_ops.invoices
            (account_id, title, status, provider_status, invoice_number, public_url,
             sale_or_service_date, subtotal_cents, tax_cents, total_cents,
             deposit_pct, deposit_amount_cents, deposit_basis_cents, deposit_locked,
             balance_due_cents, date_balance_due, tipping_enabled, published_at,
             square_invoice_id, square_order_id,
             source_system, external_id, external_updated_at, external_payload_hash,
             raw_payload)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
             %s, %s, 'square', %s, %s, %s, %s)
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            account_id           = EXCLUDED.account_id,
            title                = EXCLUDED.title,
            status               = EXCLUDED.status,
            provider_status      = EXCLUDED.provider_status,
            invoice_number       = EXCLUDED.invoice_number,
            public_url           = EXCLUDED.public_url,
            sale_or_service_date = EXCLUDED.sale_or_service_date,
            subtotal_cents       = EXCLUDED.subtotal_cents,
            tax_cents            = EXCLUDED.tax_cents,
            total_cents          = EXCLUDED.total_cents,
            deposit_pct          = EXCLUDED.deposit_pct,
            deposit_amount_cents = EXCLUDED.deposit_amount_cents,
            -- basis is locked at first import; never overwritten on update
            balance_due_cents    = EXCLUDED.balance_due_cents,
            date_balance_due     = EXCLUDED.date_balance_due,
            square_order_id      = EXCLUDED.square_order_id,
            external_updated_at  = EXCLUDED.external_updated_at,
            external_payload_hash= EXCLUDED.external_payload_hash,
            raw_payload          = EXCLUDED.raw_payload,
            updated_at           = now()
        RETURNING id
        """,
        (
            account_id,
            inv.get("title"),
            status,
            status_raw,
            inv.get("invoice_number"),
            inv.get("public_url"),
            parse_date(inv.get("sale_or_service_date")),
            subtotal,
            money(order.get("total_tax_money")) if order else None,
            total,
            dep["deposit_pct"],
            dep["deposit_amount_cents"],
            total,  # deposit_basis_cents (locked on first insert)
            True,
            dep["balance_due_cents"],
            dep["date_balance_due"],
            any(pr.get("tipping_enabled") for pr in inv.get("payment_requests", [])),
            parse_dt(inv.get("created_at")),
            inv["id"],
            inv.get("order_id"),
            inv["id"],
            parse_dt(inv.get("updated_at")),
            payload_hash(inv),
            psycopg2.extras.Json(inv),
        ),
    )
    return cur.fetchone()[0]


def upsert_order(cur, order: dict, invoice_id: str, account_id: str | None) -> str:
    net = order.get("net_amounts", {})
    cur.execute(
        """
        INSERT INTO taza_ops.orders
            (invoice_id, account_id, order_source, status, provider_status,
             total_cents, total_tax_cents, total_tip_cents, net_amount_due_cents,
             source_system, external_id, external_updated_at, external_payload_hash,
             raw_payload)
        VALUES (%s, %s, 'square', %s, %s, %s, %s, %s, %s, 'square', %s, %s, %s, %s)
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            invoice_id           = EXCLUDED.invoice_id,
            account_id           = EXCLUDED.account_id,
            status               = EXCLUDED.status,
            provider_status      = EXCLUDED.provider_status,
            total_cents          = EXCLUDED.total_cents,
            total_tax_cents      = EXCLUDED.total_tax_cents,
            total_tip_cents      = EXCLUDED.total_tip_cents,
            net_amount_due_cents = EXCLUDED.net_amount_due_cents,
            external_updated_at  = EXCLUDED.external_updated_at,
            external_payload_hash= EXCLUDED.external_payload_hash,
            raw_payload          = EXCLUDED.raw_payload,
            updated_at           = now()
        RETURNING id
        """,
        (
            invoice_id,
            account_id,
            order.get("state"),
            order.get("state"),
            money(order.get("total_money")),
            money(order.get("total_tax_money")),
            money(order.get("total_tip_money")),
            money(order.get("net_amount_due_money")),
            order["id"],
            parse_dt(order.get("updated_at")),
            payload_hash(order),
            psycopg2.extras.Json(order),
        ),
    )
    return cur.fetchone()[0]


def replace_line_items(cur, invoice_id: str, order_id: str, order: dict) -> None:
    """Line items are re-derived from the order each sync (delete + reinsert)."""
    cur.execute("DELETE FROM taza_ops.invoice_line_items WHERE invoice_id = %s", (invoice_id,))
    for idx, li in enumerate(order.get("line_items", [])):
        cur.execute(
            """
            INSERT INTO taza_ops.invoice_line_items
                (invoice_id, order_id, line_type, menu_item_id, sku, description,
                 quantity, unit_price_cents, total_cents, tax_cents, note,
                 square_uid, catalog_object_id, sort_order)
            VALUES
                (%s, %s, 'food',
                 (SELECT id FROM taza_ops.menu_items WHERE square_id = %s),
                 %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_id,
                order_id,
                li.get("catalog_object_id"),
                li.get("catalog_object_id"),
                li.get("name"),
                float(li.get("quantity", "1")),
                money(li.get("base_price_money")),
                money(li.get("total_money")),
                money(li.get("total_tax_money")),
                li.get("note"),
                li.get("uid"),
                li.get("catalog_object_id"),
                idx,
            ),
        )


def upsert_payments(cur, order: dict, invoice_id: str, account_id: str | None,
                    deposit_cents: int | None) -> int:
    """One payment row per captured tender on the order."""
    n = 0
    for t in order.get("tenders", []):
        amount = money(t.get("amount_money"))
        card = (t.get("card_details") or {}).get("card", {})
        captured = (t.get("card_details") or {}).get("status") == "CAPTURED"
        is_deposit = deposit_cents is not None and amount == deposit_cents
        cur.execute(
            """
            INSERT INTO taza_ops.payments
                (invoice_id, account_id, payment_type, rail, amount_cents, status,
                 is_deposit, paid_at, card_brand, card_last4,
                 source_system, external_id, external_updated_at, raw_payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'square', %s, %s, %s)
            ON CONFLICT (source_system, external_id) DO UPDATE SET
                amount_cents = EXCLUDED.amount_cents,
                status       = EXCLUDED.status,
                is_deposit   = EXCLUDED.is_deposit,
                paid_at      = EXCLUDED.paid_at,
                raw_payload  = EXCLUDED.raw_payload,
                updated_at   = now()
            """,
            (
                invoice_id,
                account_id,
                "deposit" if is_deposit else "balance",
                "card" if t.get("type") == "CARD" else "square",
                amount,
                "completed" if captured else "pending",
                is_deposit,
                parse_dt(t.get("created_at")),
                card.get("card_brand"),
                card.get("last_4"),
                t.get("payment_id") or t.get("id"),
                parse_dt(t.get("created_at")),
                psycopg2.extras.Json(t),
            ),
        )
        n += 1
    return n


def record_exception(conn, inv_id: str, exc: Exception) -> None:
    """Route a per-invoice failure to the exceptions queue (never crash the run)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO taza_ops.exceptions
                    (source_workflow, entity_type, entity_id, exception_type, message)
                VALUES ('square_import', 'invoices', %s, %s, %s)
                """,
                (inv_id, type(exc).__name__, str(exc)[:2000]),
            )
        conn.commit()
    except Exception:  # exceptions table best-effort
        conn.rollback()


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #
def import_location(sq: Square, conn, location_id: str) -> dict:
    stats = {"seen": 0, "written": 0, "skipped": 0, "errors": 0, "payments": 0}
    invoices = list(sq.iter_invoices(location_id))
    stats["seen"] = len(invoices)
    order_ids = [i["order_id"] for i in invoices if i.get("order_id")]
    orders = sq.batch_orders(location_id, order_ids) if order_ids else {}

    for inv in invoices:
        inv_id = inv["id"]
        try:
            with conn.cursor() as cur:
                # skip unchanged invoices
                cur.execute(
                    "SELECT external_payload_hash FROM taza_ops.invoices "
                    "WHERE source_system='square' AND external_id=%s",
                    (inv_id,),
                )
                row = cur.fetchone()
                if row and row[0] == payload_hash(inv):
                    stats["skipped"] += 1
                    continue

                order = orders.get(inv.get("order_id"))
                account_id = upsert_account(cur, inv.get("primary_recipient", {}))
                invoice_id = upsert_invoice(cur, inv, order, account_id)
                if order:
                    internal_order_id = upsert_order(cur, order, invoice_id, account_id)
                    replace_line_items(cur, invoice_id, internal_order_id, order)
                    dep = deposit_fields(inv)["deposit_amount_cents"]
                    stats["payments"] += upsert_payments(
                        cur, order, invoice_id, account_id, dep
                    )
            conn.commit()
            stats["written"] += 1
        except Exception as exc:  # noqa: BLE001 — gentle failure per D-006
            conn.rollback()
            log.exception("invoice %s failed", inv_id)
            record_exception(conn, inv_id, exc)
            stats["errors"] += 1
    return stats


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    token = os.environ.get("SQUARE_ACCESS_TOKEN")
    dsn = os.environ.get("DATABASE_URL")
    if not token or not dsn:
        log.error("SQUARE_ACCESS_TOKEN and DATABASE_URL are required")
        return 2

    sq = Square(token)
    location_ids = (
        [os.environ["SQUARE_LOCATION_ID"]]
        if os.environ.get("SQUARE_LOCATION_ID")
        else sq.active_location_ids()
    )
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    total = {"seen": 0, "written": 0, "skipped": 0, "errors": 0, "payments": 0}
    try:
        for loc in location_ids:
            s = import_location(sq, conn, loc)
            log.info("location %s: %s", loc, s)
            for k in total:
                total[k] += s[k]
    finally:
        conn.close()
    log.info("DONE totals: %s", total)
    return 1 if total["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
