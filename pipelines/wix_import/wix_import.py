#!/usr/bin/env python3
"""
Taza OS — Wix platter-store order/payment import pipeline.

Pulls Wix eCommerce orders (+ their payments and refunds) into PostgreSQL
(schema taza_ops), idempotently. Designed to run on the N100 under a systemd
timer. This is the second payment rail (Schema Contract §5): Square = catering
invoices; Wix Payments = the online platter store (≤10% of revenue).

Flow (per the Wix eCommerce REST APIs):
    orders/search (POST /ecom/v1/orders/search)          -> the platter orders
      -> upsert accounts/contacts (from buyerInfo + billingInfo.contactDetails)
      -> upsert orders               (UPSERT by source_system='wix' + order id)
    payments/list-by-ids (POST /ecom/v1/payments/list-by-ids, batched)
      -> upsert payments             (one row per Wix payment; refunds too)

A Wix platter sale is a store *order*, not a Square-style invoice, so it lands
in taza_ops.orders (order_source='wix') — not invoices. Line items ride along in
orders.raw_payload until a relational breakout is built.

Idempotency: every row upserts on (source_system='wix', external_id). Change
detection: an external_payload_hash is stored; unchanged orders are skipped
without touching the DB. Per-order failures route to the `exceptions` queue —
one bad order never aborts the run.

Money: Wix amounts are decimal strings in the order currency (e.g. "19.00");
they are converted to integer cents (banker's-safe, ROUND_HALF_UP) on write.

Config (environment / .env — see .env.example):
    WIX_API_KEY           required — Wix account API key
    WIX_SITE_ID           required — site id the platter store lives on
    DATABASE_URL          required — e.g. postgres://taza@localhost/taza_ops
    WIX_ORDERS_SINCE_DAYS optional — only import orders created within N days
    WIX_API_BASE          default https://www.wixapis.com
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

import psycopg2
import psycopg2.extras
import requests

log = logging.getLogger("wix_import")

WIX_API_BASE = os.environ.get("WIX_API_BASE", "https://www.wixapis.com")

# Wix regular-payment status -> taza_ops.payment_status enum value.
PAYMENT_STATUS_MAP = {
    "APPROVED": "completed",
    "PENDING": "pending",
    "DECLINED": "failed",
    "FAILED": "failed",
    "REFUNDED": "refunded",
    "PARTIALLY_REFUNDED": "refunded",
    "VOIDED": "failed",
    "CANCELED": "failed",
}


# --------------------------------------------------------------------------- #
# Wix REST client                                                             #
# --------------------------------------------------------------------------- #
class Wix:
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

    def iter_orders(self, since_days: int | None) -> Iterable[dict]:
        """Search Orders, newest first, following cursor paging.

        Search Orders excludes INITIALIZED (abandoned) orders by default, which
        is exactly what we want — only real placed orders."""
        cursor: str | None = None
        base_filter: dict[str, Any] = {}
        if since_days:
            since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
            base_filter = {"createdDate": {"$gte": since}}
        while True:
            search: dict[str, Any] = {"cursorPaging": {"limit": 100}}
            if cursor:
                # On a cursor page Wix ignores filter/sort; send cursor only.
                search["cursorPaging"]["cursor"] = cursor
            elif base_filter:
                search["filter"] = base_filter
            data = self._post("/ecom/v1/orders/search", {"search": search})
            for order in data.get("orders", []):
                yield order
            meta = data.get("metadata", {}) or {}
            cursor = (meta.get("cursors") or {}).get("next")
            if not meta.get("hasNext") or not cursor:
                return

    def batch_transactions(self, order_ids: list[str]) -> dict[str, dict]:
        """List Transactions For Multiple Orders -> {order_id: {payments, refunds}}."""
        out: dict[str, dict] = {}
        for i in range(0, len(order_ids), 100):  # batch cap, mirrors Square
            chunk = order_ids[i : i + 100]
            data = self._post("/ecom/v1/payments/list-by-ids", {"orderIds": chunk})
            for tx in data.get("orderTransactions", []):
                if tx.get("orderId"):
                    out[tx["orderId"]] = tx
        return out


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def payload_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def to_cents(money: Any) -> int | None:
    """Wix Money ({'amount': '19.00', ...}) or bare string/number -> integer cents."""
    if money is None:
        return None
    amt = money.get("amount") if isinstance(money, dict) else money
    if amt is None or amt == "":
        return None
    return int((Decimal(str(amt)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def buyer_name(order: dict) -> str | None:
    cd = (order.get("billingInfo") or {}).get("contactDetails") or {}
    name = " ".join(p for p in [cd.get("firstName"), cd.get("lastName")] if p)
    return name or None


def tip_cents(order: dict) -> int | None:
    """Tips arrive as an additionalFees entry named 'Tip' (included in total)."""
    total = 0
    found = False
    for fee in order.get("additionalFees") or []:
        if (fee.get("name") or "").strip().lower() == "tip":
            total += to_cents(fee.get("price")) or 0
            found = True
    return total if found else None


# --------------------------------------------------------------------------- #
# Upserts                                                                      #
# --------------------------------------------------------------------------- #
def upsert_account(cur, order: dict) -> str | None:
    """Upsert the paying account (+ its contact) from a Wix order's buyer.

    Keyed on the Wix contactId (stable across a customer's orders). Falls back
    to the buyer email, then the order id, so an account is always resolvable."""
    buyer = order.get("buyerInfo") or {}
    cd = (order.get("billingInfo") or {}).get("contactDetails") or {}
    email = buyer.get("email")
    external_id = buyer.get("contactId") or email or order["id"]
    company = cd.get("company")
    account_type = "company" if company else "individual"
    # accounts.display_name is the payer: the company when there is one, else
    # the person from billing contact details, else email.
    name = company or buyer_name(order) or email or external_id
    cur.execute(
        """
        INSERT INTO taza_ops.accounts
            (account_type, display_name, legal_name, primary_email, primary_phone,
             source_system, external_id, external_updated_at)
        VALUES (%s, %s, %s, %s, %s, 'wix', %s, now())
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            account_type  = EXCLUDED.account_type,
            display_name  = EXCLUDED.display_name,
            legal_name    = COALESCE(EXCLUDED.legal_name, taza_ops.accounts.legal_name),
            primary_email = COALESCE(EXCLUDED.primary_email, taza_ops.accounts.primary_email),
            primary_phone = COALESCE(EXCLUDED.primary_phone, taza_ops.accounts.primary_phone),
            updated_at    = now()
        RETURNING id
        """,
        (account_type, name, company, email, cd.get("phone"), external_id),
    )
    account_id = cur.fetchone()[0]
    # Keep a contact record for the person (the inquirer/decision-maker).
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
        (account_id, cd.get("firstName"), cd.get("lastName"),
         email, cd.get("phone"), external_id),
    )
    return account_id


def upsert_order(cur, order: dict, account_id: str | None) -> str:
    ps = order.get("priceSummary") or {}
    cur.execute(
        """
        INSERT INTO taza_ops.orders
            (account_id, order_source, status, provider_status,
             order_number, payment_status, fulfillment_status, currency,
             subtotal_cents, shipping_cents, discount_cents, total_tax_cents,
             total_tip_cents, net_amount_due_cents, total_cents, buyer_email,
             source_system, external_id, external_updated_at,
             external_payload_hash, raw_payload)
        VALUES (%s, 'wix', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'wix', %s, %s, %s, %s)
        ON CONFLICT (source_system, external_id) DO UPDATE SET
            account_id            = EXCLUDED.account_id,
            status                = EXCLUDED.status,
            provider_status       = EXCLUDED.provider_status,
            order_number          = EXCLUDED.order_number,
            payment_status        = EXCLUDED.payment_status,
            fulfillment_status    = EXCLUDED.fulfillment_status,
            currency              = EXCLUDED.currency,
            subtotal_cents        = EXCLUDED.subtotal_cents,
            shipping_cents        = EXCLUDED.shipping_cents,
            discount_cents        = EXCLUDED.discount_cents,
            total_tax_cents       = EXCLUDED.total_tax_cents,
            total_tip_cents       = EXCLUDED.total_tip_cents,
            net_amount_due_cents  = EXCLUDED.net_amount_due_cents,
            total_cents           = EXCLUDED.total_cents,
            buyer_email           = EXCLUDED.buyer_email,
            external_updated_at   = EXCLUDED.external_updated_at,
            external_payload_hash = EXCLUDED.external_payload_hash,
            raw_payload           = EXCLUDED.raw_payload,
            updated_at            = now()
        RETURNING id
        """,
        (
            account_id,
            order.get("status"),
            order.get("status"),
            str(order["number"]) if order.get("number") is not None else None,
            order.get("paymentStatus"),
            order.get("fulfillmentStatus"),
            order.get("currency"),
            to_cents(ps.get("subtotal")),
            to_cents(ps.get("shipping")),
            to_cents(ps.get("discount")),
            to_cents(ps.get("tax")),
            tip_cents(order),
            to_cents((order.get("balanceSummary") or {}).get("balance")),
            to_cents(ps.get("total")) or 0,
            (order.get("buyerInfo") or {}).get("email"),
            order["id"],
            parse_dt(order.get("updatedDate")),
            payload_hash(order),
            psycopg2.extras.Json(order),
        ),
    )
    return cur.fetchone()[0]


def _payment_method(p: dict) -> dict:
    """Extract method label, provider txn id, raw status, and card brand/last4
    for a Wix payment (regular / gift-card / membership)."""
    reg = p.get("regularPaymentDetails")
    if reg:
        card = reg.get("creditCardDetails") or {}
        return {
            "method": reg.get("paymentMethod"),
            "provider_txn": reg.get("providerTransactionId") or reg.get("gatewayTransactionId"),
            "status": reg.get("status"),
            "card_brand": card.get("brand"),
            "card_last4": card.get("lastFourDigits"),
        }
    if p.get("giftCardPaymentDetails"):
        return {"method": "gift_card", "status": None,
                "provider_txn": (p["giftCardPaymentDetails"] or {}).get("giftCardId"),
                "card_brand": None, "card_last4": None}
    if p.get("membershipPaymentDetails"):
        return {"method": "membership", "provider_txn": None, "status": None,
                "card_brand": None, "card_last4": None}
    return {"method": None, "provider_txn": None, "status": None,
            "card_brand": None, "card_last4": None}


def refund_amount_status(r: dict) -> tuple[int, str]:
    """Amount + status for a Wix refund. A refund carries per-payment
    transactions each with a refundStatus (SUCCEEDED / FAILED / PENDING); only
    SUCCEEDED transactions actually moved money, so a FAILED refund attempt must
    record $0 (not inflate the order's refunded total). Transactions with no
    explicit status are treated as succeeded (older/simple providers)."""
    txns = r.get("transactions") or []
    if not txns:
        return 0, "refunded"
    succeeded = sum(
        to_cents(t.get("amount")) or 0
        for t in txns
        if t.get("refundStatus") in (None, "SUCCEEDED")
    )
    if succeeded > 0:
        return succeeded, "refunded"
    if any(t.get("refundStatus") == "PENDING" for t in txns):
        return 0, "pending"
    return 0, "failed"


def upsert_payments(cur, tx: dict, order_id: str, account_id: str | None) -> int:
    """One payments row per Wix payment and per refund on the order."""
    n = 0
    for p in tx.get("payments", []) or []:
        pid = p.get("id")
        if not pid:
            continue
        pm = _payment_method(p)
        # regularPaymentDetails.status is authoritative; fall back to top-level.
        status = PAYMENT_STATUS_MAP.get(
            (pm["status"] or p.get("status") or "").upper(), "completed"
        )
        cur.execute(
            """
            INSERT INTO taza_ops.payments
                (order_id, account_id, payment_type, rail, amount_cents, status,
                 paid_at, payment_method, provider_transaction_id,
                 card_brand, card_last4,
                 source_system, external_id, external_updated_at, raw_payload)
            VALUES (%s, %s, 'full', 'wix', %s, %s, %s, %s, %s, %s, %s,
                    'wix', %s, %s, %s)
            ON CONFLICT (source_system, external_id) DO UPDATE SET
                amount_cents            = EXCLUDED.amount_cents,
                status                  = EXCLUDED.status,
                paid_at                 = EXCLUDED.paid_at,
                payment_method          = EXCLUDED.payment_method,
                provider_transaction_id = EXCLUDED.provider_transaction_id,
                card_brand              = EXCLUDED.card_brand,
                card_last4              = EXCLUDED.card_last4,
                raw_payload             = EXCLUDED.raw_payload,
                updated_at              = now()
            """,
            (
                order_id, account_id, to_cents(p.get("amount")) or 0, status,
                parse_dt(p.get("createdDate")), pm["method"], pm["provider_txn"],
                pm["card_brand"], pm["card_last4"],
                pid, parse_dt(p.get("updatedDate") or p.get("createdDate")),
                psycopg2.extras.Json(p),
            ),
        )
        n += 1

    for r in tx.get("refunds", []) or []:
        rid = r.get("id")
        if not rid:
            continue
        amt, status = refund_amount_status(r)
        reason = (r.get("details") or {}).get("reason") or r.get("reason")
        cur.execute(
            """
            INSERT INTO taza_ops.payments
                (order_id, account_id, payment_type, rail, amount_cents, status,
                 paid_at, payment_method, refund_reason,
                 source_system, external_id, external_updated_at, raw_payload)
            VALUES (%s, %s, 'refund', 'wix', %s, %s, %s, 'refund', %s,
                    'wix', %s, %s, %s)
            ON CONFLICT (source_system, external_id) DO UPDATE SET
                amount_cents  = EXCLUDED.amount_cents,
                status        = EXCLUDED.status,
                paid_at       = EXCLUDED.paid_at,
                refund_reason = EXCLUDED.refund_reason,
                raw_payload   = EXCLUDED.raw_payload,
                updated_at    = now()
            """,
            (
                order_id, account_id, amt, status, parse_dt(r.get("createdDate")),
                reason, rid, parse_dt(r.get("createdDate")), psycopg2.extras.Json(r),
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
def run(wix: Wix, conn, since_days: int | None) -> dict:
    stats = {"seen": 0, "written": 0, "skipped": 0, "errors": 0, "payments": 0}
    orders = list(wix.iter_orders(since_days))
    stats["seen"] = len(orders)
    order_ids = [o["id"] for o in orders if o.get("id")]
    txns = wix.batch_transactions(order_ids) if order_ids else {}

    for order in orders:
        oid = order["id"]
        try:
            with conn.cursor() as cur:
                # skip unchanged orders
                cur.execute(
                    "SELECT external_payload_hash FROM taza_ops.orders "
                    "WHERE source_system='wix' AND external_id=%s",
                    (oid,),
                )
                row = cur.fetchone()
                if row and row[0] == payload_hash(order):
                    stats["skipped"] += 1
                    continue

                account_id = upsert_account(cur, order)
                internal_order_id = upsert_order(cur, order, account_id)
                tx = txns.get(oid)
                if tx:
                    stats["payments"] += upsert_payments(
                        cur, tx, internal_order_id, account_id
                    )
            conn.commit()
            stats["written"] += 1
        except Exception as exc:  # noqa: BLE001 — gentle failure, mirror square_import
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

    since_days_raw = os.environ.get("WIX_ORDERS_SINCE_DAYS")
    since_days = int(since_days_raw) if since_days_raw else None

    wix = Wix(api_key, site_id)
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        stats = run(wix, conn, since_days)
        log.info("DONE totals: %s", stats)
    finally:
        conn.close()
    return 1 if stats["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
