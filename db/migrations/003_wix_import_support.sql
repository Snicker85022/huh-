-- ============================================================================
-- Migration 003 — Wix platter-order import support
-- ----------------------------------------------------------------------------
-- The second payment rail (Schema Contract §5): SQUARE = catering invoices;
-- WIX PAYMENTS = the online platter store (≤10% of revenue). A Wix platter sale
-- is a store *order*, not a Square-style invoice, so the import lands in
-- taza_ops.orders (order_source='wix') + payments + accounts/contacts. The
-- order's line items are preserved in orders.raw_payload for v1; a relational
-- line-item breakout is a later follow-up.
--
-- This adds the Wix-specific columns the import needs, grounded against the
-- eCommerce Orders API (POST /ecom/v1/orders/search) and Order Transactions API
-- (POST /ecom/v1/payments/list-by-ids). Wix money is a decimal string in the
-- order currency; the pipeline converts to integer cents before writing.
--
-- Idempotent: safe to re-run (IF NOT EXISTS everywhere).
-- Apply AFTER db/schema/*.sql and migrations 001–002.
-- ============================================================================
SET search_path TO taza_ops, public;

-- ---- ORDERS: Wix store-order facts -----------------------------------------
-- (order_source / status / total_cents / total_tax_cents / custom_attributes /
--  raw_payload already exist from 40_financial.sql + migration 001.)
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS order_number       TEXT;    -- human order # (order.number)
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS payment_status     TEXT;    -- PAID / NOT_PAID / PARTIALLY_PAID / *REFUNDED
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS fulfillment_status TEXT;    -- FULFILLED / NOT_FULFILLED / PARTIALLY_FULFILLED
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS currency           TEXT;    -- ISO-4217 (order currency)
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS subtotal_cents     INTEGER; -- priceSummary.subtotal
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS shipping_cents     INTEGER; -- priceSummary.shipping
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS discount_cents     INTEGER; -- priceSummary.discount
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS buyer_email        TEXT;    -- buyerInfo.email (denormalized for quick lookup)

CREATE INDEX IF NOT EXISTS idx_orders_number ON taza_ops.orders (order_number);
-- One idempotency lane per rail (mirrors idx_orders_square from migration 001).
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_wix
    ON taza_ops.orders (external_id) WHERE source_system = 'wix';

-- ---- PAYMENTS: Wix transaction provenance ----------------------------------
-- (card_brand / card_last4 / raw_payload already exist from migration 001.)
ALTER TABLE taza_ops.payments ADD COLUMN IF NOT EXISTS payment_method          TEXT; -- CreditCard / PayPal / gift_card / membership …
ALTER TABLE taza_ops.payments ADD COLUMN IF NOT EXISTS provider_transaction_id TEXT; -- gateway/provider txn id (reconciliation)
ALTER TABLE taza_ops.payments ADD COLUMN IF NOT EXISTS refund_reason           TEXT; -- populated on payment_type='refund'

COMMENT ON COLUMN taza_ops.orders.raw_payload IS
    'Full provider order object (Square order or Wix order). For Wix, preserves line items until a relational breakout lands.';
