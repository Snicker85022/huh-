#!/usr/bin/env python3
"""
Taza OS — Wix platter-order import pipeline.

Pulls PAID orders from the Wix eCommerce store (+ their line items and
Wix Payments transactions) into PostgreSQL (schema taza_ops), idempotently.
Designed to run on the N100 under a systemd timer.

Why PAID-only: platter orders on the Wix store are deterministic — the customer
pays online, the order is auto-fired, and it can't be modified afterward. Today
that "PAID" email gets hand-copied onto a paper prep checklist. This pipeline
replaces that manual step: every paid order lands in taza_ops as an invoice +
order + line items + payment, ready for the day-of prep view.

Flow, per the Schema Contract (Wix Payments rail; <=10% of revenue):
    orders/search (filter paymentStatus=PAID)
      -> upsert accounts/contacts   (from buyerInfo + billingInfo.contactDetails)
      -> upsert invoices            (one per Wix order; status Paid)
      -> upsert orders              (order_source='wix')
      -> replace invoice_line_items (from order.lineItems)
    payments/list-by-ids (batch)
      -> upsert payments            (rail='wix'; refunds captured too)

Idempotency: every row upserts on (source_system='wix', external_id). An
external_payload_hash is stored; unchanged orders are skipped without touching
the DB. Because paid orders are immutable, a re-run is almost entirely skips.

Config (environment / .env — see .env.example):
    WIX_API_KEY              required   (Wix account API key)
    WIX_SITE_ID             required   (site the store belongs to)
    DATABASE_URL           required   e.g. postgres://taza@localhost/taza_ops
    WIX_API_BASE           default https://www.wixapis.com
    WIX_PAYMENT_STATUSES   default "PAID"  (comma-separated, e.g. "PAID,PARTIALLY_PAID")
    WIX_UPDATED_AFTER_DAYS optional   if set, only orders updated within N days
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

import psycopg2
import psycopg2.extras
import requests

log = logging.getLogger("wix_import")

WIX_API_BASE = os.environ.get("WIX_API_BASE", "https://www.wixapis.com")

# Wix order paymentStatus -> taza_ops.invoice_status enum value.
PAYMENT_STATUS_MAP = {
    "PAID": "Paid",
    "PARTIALLY_PAID": "PartiallyPaid",
    "FULLY_REFUNDED": "Refunded",
    "PARTIALLY_REFUNDED": "Refunded",
    "REFUNDED": "Refunded",
    "NOT_PAID": "Unpaid",
    "PENDING": "Unpaid",
}

# Wix transaction status -> taza_ops.payment_status enum value.
TXN_STATUS_MAP = {
    "APPROVED": "completed",
    "AUTHORIZED": "completed",
    "SETTLED": "completed",
    "PENDING": "pending",
    "PENDING_MERCHANT": "pending",
    "DECLINED": "failed",
    "CANCELED": "failed",
    "VOIDED": "failed",
    "REFUNDED": "refunded",
    "PARTIALLY_REFUNDED": "refunded",
}


# --------------------------------------------------------------------------- #
# Wix REST client                                                             #
# --------------------------------------------------------------------------- #
class Wix:
    """Thin client for the Wix eCommerce Orders + Order Transactions REST APIs.

    Auth: an account-level API key in the Authorization header, scoped to one
    site via the wix-site-id header (required for site-context eCom calls).
    """

    def __init__(self, api_key: str, site_id: str):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": api_key,
                "wix-site-id": site_id,
                "Content-Type": "application/json",
            }
        )

    def _post(self, path: str, body: dict) -> dict:
        r = self.session.post(f"{WIX_API_BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def iter_orders(
        self, payment_statuses: list[str], updated_after: datetime | None
    ) -> Iterable[dict]:
        """Search Orders (POST /ecom/v1/orders/search), paging via cursor.

        Search Orders never returns INITIALIZED orders and defaults to
        createdDate DESC — both fine for us. We filter to the paid statuses so
        only fireable orders come through.
        """
        filt: dict[str, Any] = {}
        if payment_statuses:
            filt["paymentStatus"] = (
                payment_statuses[0]
                if len(payment_statuses) == 1
                else {"$in": payment_statuses}
            )
        if updated_after:
            filt["updatedDate"] = {"$gte": updated_after.isoformat()}

        cursor: str | None = None
        while True:
            search: dict[str, Any] = {"cursorPaging": {"limit": 100}}
            if filt:
                search["filter"] = filt
            if cursor:
                # Once a cursor is in play, Wix ignores filter/sort — send cursor only.
                search = {"cursorPaging": {"cursor": cursor}}
            data = self._post("/ecom/v1/orders/search", {"search": search})
            for o in data.get("orders", []):
                yield o
            meta = data.get("metadata", {}) or {}
            cursor = (meta.get("cursors") or {}).get("next")
            if not meta.get("hasNext") or not cursor:
                return

    def transactions(self, order_ids: list[str]) -> dict[str, dict]:
        """List Transactions For Multiple Orders
        (POST /ecom/v1/payments/list-by-ids) -> {order_id: {payments, refunds}}."""
        out: dict[str, dict] = {}
        for i in range(0, len(order_ids), 100):
            chunk = order_ids[i : i + 100]
            data = self._post("/ecom/v1/payments/list-by-ids", {"orderIds": chunk})
            for ot in data.get("orderTransactions", []):
                oid = ot.get("orderId")
                if oid:
                    out[oid] = ot
        return out


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def payload_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def to_cents(price: Any) -> int | None:
    """Wix money is a decimal string in major units ("45.00"), often wrapped in
    a Price object {amount, formattedAmount}. Convert to integer cents."""
    if isinstance(price, dict):
        price = price.get("amount")
    if price is None or price == "":
        return None
    try:
        return int((Decimal(str(price)) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return None


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def order_number(order: dict) -> str | None:
    n = order.get("number")
    return None if n is None else str(n)


# --------------------------------------------------------------------------- #
# Upserts                                                                      #
# --------------------------------------------------------------------------- #
def upsert_account(cur, order: dict) -> str | None:
    """Upsert the buyer as an account + primary contact. Keyed by Wix contactId."""
    buyer = order.get("buyerInfo", {}) or {}
    details = (order.get("billingInfo", {}) or {}).get("contactDetails", {}) or {}
    contact_id = buyer.get("contactId")
    if not contact_id:
        return None
    email = buyer.get("email") or (order.get("billingInfo", {}) or {}).get("email")
    first, last = details.get("firstName"), details.get("lastName")
    name = " ".join(p for p in [first, last] if p) or email or contact_id
    phone = details.get("phone")

    cur.execute(
        """
        INSERT INTO taza_ops.accounts
            (display_name, primary_email, primary_phone,
             source_system, external_id, external_updated_at)
        VALUES (%s, %s, %s, 'wix', %s, now())
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            display_name  = EXCLUDED.display_name,
            primary_email = COALESCE(EXCLUDED.primary_email, taza_ops.accounts.primary_email),
            primary_phone = COALESCE(EXCLUDED.primary_phone, taza_ops.accounts.primary_phone),
            updated_at    = now()
        RETURNING id
        """,
        (name, email, phone, contact_id),
    )
    account_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO taza_ops.contacts
            (account_id, first_name, last_name, email, phone, is_primary,
             source_system, external_id, external_updated_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, 'wix', %s, now())
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            account_id = EXCLUDED.account_id,
            first_name = EXCLUDED.first_name,
            last_name  = EXCLUDED.last_name,
            email      = COALESCE(EXCLUDED.email, taza_ops.contacts.email),
            phone      = COALESCE(EXCLUDED.phone, taza_ops.contacts.phone),
            updated_at = now()
        """,
        (account_id, first, last, email, phone, contact_id),
    )
    return account_id


def upsert_invoice(cur, order: dict, account_id: str | None) -> str:
    """One invoice per Wix order (the platter purchase the customer paid for)."""
    ps = order.get("priceSummary", {}) or {}
    status = PAYMENT_STATUS_MAP.get(order.get("paymentStatus"), "Paid")
    total = to_cents(ps.get("total"))
    cur.execute(
        """
        INSERT INTO taza_ops.invoices
            (account_id, title, status, provider_status, invoice_number,
             subtotal_cents, tax_cents, delivery_cents, total_cents,
             deposit_pct, deposit_locked, balance_due_cents, tipping_enabled,
             published_at, source_system, external_id, external_updated_at,
             external_payload_hash, raw_payload)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, FALSE, 0, FALSE,
             %s, 'wix', %s, %s, %s, %s)
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            account_id            = EXCLUDED.account_id,
            title                 = EXCLUDED.title,
            status                = EXCLUDED.status,
            provider_status       = EXCLUDED.provider_status,
            subtotal_cents        = EXCLUDED.subtotal_cents,
            tax_cents             = EXCLUDED.tax_cents,
            delivery_cents        = EXCLUDED.delivery_cents,
            total_cents           = EXCLUDED.total_cents,
            external_updated_at   = EXCLUDED.external_updated_at,
            external_payload_hash = EXCLUDED.external_payload_hash,
            raw_payload           = EXCLUDED.raw_payload,
            updated_at            = now()
        RETURNING id
        """,
        (
            account_id,
            f"Wix Platter Order #{order_number(order) or order['id'][:8]}",
            status,
            order.get("paymentStatus"),
            order_number(order),
            to_cents(ps.get("subtotal")),
            to_cents(ps.get("tax")),
            to_cents(ps.get("shipping")),
            total,
            parse_dt(order.get("createdDate")),
            order["id"],
            parse_dt(order.get("updatedDate")),
            payload_hash(order),
            psycopg2.extras.Json(order),
        ),
    )
    return cur.fetchone()[0]


def order_custom_attributes(order: dict) -> dict:
    """Operational facts the paper checklist needs, captured as queryable JSONB:
    fulfillment/pickup details, statuses, channel, and the buyer note."""
    return {
        "wix_number": order.get("number"),
        "payment_status": order.get("paymentStatus"),
        "fulfillment_status": order.get("fulfillmentStatus"),
        "order_status": order.get("status"),
        "channel": (order.get("channelInfo", {}) or {}).get("type"),
        "shipping": order.get("shippingInfo"),
        "buyer_note": order.get("buyerNote"),
    }


def upsert_order(cur, order: dict, invoice_id: str, account_id: str | None) -> str:
    ps = order.get("priceSummary", {}) or {}
    cur.execute(
        """
        INSERT INTO taza_ops.orders
            (invoice_id, account_id, order_source, status, provider_status,
             total_cents, total_tax_cents, net_amount_due_cents,
             custom_attributes, source_system, external_id, external_updated_at,
             external_payload_hash, raw_payload)
        VALUES (%s, %s, 'wix', %s, %s, %s, %s, 0, %s, 'wix', %s, %s, %s, %s)
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            invoice_id            = EXCLUDED.invoice_id,
            account_id            = EXCLUDED.account_id,
            status                = EXCLUDED.status,
            provider_status       = EXCLUDED.provider_status,
            total_cents           = EXCLUDED.total_cents,
            total_tax_cents       = EXCLUDED.total_tax_cents,
            custom_attributes     = EXCLUDED.custom_attributes,
            external_updated_at   = EXCLUDED.external_updated_at,
            external_payload_hash = EXCLUDED.external_payload_hash,
            raw_payload           = EXCLUDED.raw_payload,
            updated_at            = now()
        RETURNING id
        """,
        (
            invoice_id,
            account_id,
            order.get("status"),
            order.get("paymentStatus"),
            to_cents(ps.get("total")),
            to_cents(ps.get("tax")),
            psycopg2.extras.Json(order_custom_attributes(order)),
            order["id"],
            parse_dt(order.get("updatedDate")),
            payload_hash(order),
            psycopg2.extras.Json(order),
        ),
    )
    return cur.fetchone()[0]


def replace_line_items(cur, invoice_id: str, order_id: str, order: dict) -> None:
    """Line items are re-derived from the order each sync (delete + reinsert).

    Wix platter SKUs are a different catalog than Square's, so menu_item_id is
    left NULL; catalog_object_id holds the Wix catalogItemId for later linking.
    """
    cur.execute("DELETE FROM taza_ops.invoice_line_items WHERE invoice_id = %s", (invoice_id,))
    for idx, li in enumerate(order.get("lineItems", [])):
        name = (li.get("productName", {}) or {}).get("original") or "Item"
        sku = (li.get("physicalProperties", {}) or {}).get("sku")
        catalog_item_id = (li.get("catalogReference", {}) or {}).get("catalogItemId")
        total = to_cents(li.get("totalPriceAfterTax"))
        if total is None:
            unit = to_cents(li.get("price")) or 0
            total = unit * int(li.get("quantity", 1))
        cur.execute(
            """
            INSERT INTO taza_ops.invoice_line_items
                (invoice_id, order_id, line_type, sku, description,
                 quantity, unit_price_cents, total_cents,
                 square_uid, catalog_object_id, sort_order)
            VALUES (%s, %s, 'food', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_id,
                order_id,
                sku,
                name,
                int(li.get("quantity", 1)),
                to_cents(li.get("price")) or 0,
                total,
                li.get("id"),
                catalog_item_id,
                idx,
            ),
        )


def upsert_payments(cur, invoice_id: str, account_id: str | None, txn: dict | None) -> int:
    """One payment row per Wix transaction (payments + refunds)."""
    if not txn:
        return 0
    n = 0
    for p in txn.get("payments", []):
        rpd = p.get("regularPaymentDetails", {}) or {}
        gpd = p.get("giftCardPaymentDetails", {}) or {}
        status = TXN_STATUS_MAP.get(rpd.get("status"), "completed")
        cur.execute(
            """
            INSERT INTO taza_ops.payments
                (invoice_id, account_id, payment_type, rail, amount_cents, status,
                 is_deposit, paid_at, source_system, external_id,
                 external_updated_at, raw_payload)
            VALUES (%s, %s, 'full', 'wix', %s, %s, FALSE, %s, 'wix', %s, %s, %s)
            ON CONFLICT (source_system, external_id) DO UPDATE SET
                amount_cents = EXCLUDED.amount_cents,
                status       = EXCLUDED.status,
                paid_at      = EXCLUDED.paid_at,
                raw_payload  = EXCLUDED.raw_payload,
                updated_at   = now()
            """,
            (
                invoice_id,
                account_id,
                to_cents(p.get("amount")) or 0,
                status,
                parse_dt(p.get("createdDate")),
                p.get("id"),
                parse_dt(p.get("updatedDate") or p.get("createdDate")),
                psycopg2.extras.Json(p),
            ),
        )
        n += 1
    for r in txn.get("refunds", []):
        amount = sum(
            to_cents(t.get("amount")) or 0 for t in r.get("transactions", [])
        )
        cur.execute(
            """
            INSERT INTO taza_ops.payments
                (invoice_id, account_id, payment_type, rail, amount_cents, status,
                 is_deposit, paid_at, source_system, external_id,
                 external_updated_at, raw_payload)
            VALUES (%s, %s, 'refund', 'wix', %s, 'refunded', FALSE, %s, 'wix', %s, %s, %s)
            ON CONFLICT (source_system, external_id) DO UPDATE SET
                amount_cents = EXCLUDED.amount_cents,
                status       = EXCLUDED.status,
                paid_at      = EXCLUDED.paid_at,
                raw_payload  = EXCLUDED.raw_payload,
                updated_at   = now()
            """,
            (
                invoice_id,
                account_id,
                amount,
                parse_dt(r.get("createdDate")),
                f"refund:{r.get('id')}",
                parse_dt(r.get("createdDate")),
                psycopg2.extras.Json(r),
            ),
        )
        n += 1
    return n


def record_exception(conn, order_id: str, exc: Exception) -> None:
    """Route a per-order failure to the exceptions queue (never crash the run)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO taza_ops.exceptions
                    (source_workflow, entity_type, entity_id, exception_type, message)
                VALUES ('wix_import', 'orders', %s, %s, %s)
                """,
                (order_id, type(exc).__name__, str(exc)[:2000]),
            )
        conn.commit()
    except Exception:  # exceptions table best-effort
        conn.rollback()


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #
def run(wix: Wix, conn, payment_statuses: list[str], updated_after: datetime | None) -> dict:
    stats = {"seen": 0, "written": 0, "skipped": 0, "errors": 0, "payments": 0}
    orders = list(wix.iter_orders(payment_statuses, updated_after))
    stats["seen"] = len(orders)
    txns = wix.transactions([o["id"] for o in orders]) if orders else {}

    for order in orders:
        oid = order["id"]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT external_payload_hash FROM taza_ops.invoices "
                    "WHERE source_system='wix' AND external_id=%s",
                    (oid,),
                )
                row = cur.fetchone()
                if row and row[0] == payload_hash(order):
                    stats["skipped"] += 1
                    continue

                account_id = upsert_account(cur, order)
                invoice_id = upsert_invoice(cur, order, account_id)
                internal_order_id = upsert_order(cur, order, invoice_id, account_id)
                replace_line_items(cur, invoice_id, internal_order_id, order)
                stats["payments"] += upsert_payments(
                    cur, invoice_id, account_id, txns.get(oid)
                )
            conn.commit()
            stats["written"] += 1
        except Exception as exc:  # noqa: BLE001 — gentle failure per D-006
            conn.rollback()
            log.exception("order %s failed", oid)
            record_exception(conn, oid, exc)
            stats["errors"] += 1
    return stats


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    api_key = os.environ.get("WIX_API_KEY")
    site_id = os.environ.get("WIX_SITE_ID")
    dsn = os.environ.get("DATABASE_URL")
    if not api_key or not site_id or not dsn:
        log.error("WIX_API_KEY, WIX_SITE_ID and DATABASE_URL are required")
        return 2

    payment_statuses = [
        s.strip()
        for s in os.environ.get("WIX_PAYMENT_STATUSES", "PAID").split(",")
        if s.strip()
    ]
    updated_after = None
    days = os.environ.get("WIX_UPDATED_AFTER_DAYS")
    if days:
        updated_after = datetime.now(timezone.utc) - timedelta(days=int(days))

    wix = Wix(api_key, site_id)
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        stats = run(wix, conn, payment_statuses, updated_after)
    finally:
        conn.close()
    log.info("DONE totals: %s", stats)
    return 1 if stats["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
