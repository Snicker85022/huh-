-- ============================================================================
-- Migration 001 — Square import support
-- ----------------------------------------------------------------------------
-- Adds the columns the Square invoice/order import pipeline needs, discovered by
-- grounding against live Square data (2026-07-16):
--   * Square invoice statuses beyond the internal draft lifecycle
--     (UNPAID / SCHEDULED / REFUNDED / FAILED / CANCELED)
--   * invoice_number, public_url, sale_or_service_date on invoices
--   * deposit_basis_cents (deposit = 50% of the INITIAL quote; later changes
--     never require more deposit — Nick, 7/16)
--   * raw_payload JSONB on invoices/orders/payments for full fidelity
--   * order tax/tip/amount-due totals + provider state
--   * card brand/last4 on payments (from order tenders)
-- Idempotent: safe to re-run (IF NOT EXISTS everywhere).
-- Apply AFTER db/schema/*.sql. Run outside a txn block (ALTER TYPE ADD VALUE).
-- ============================================================================
SET search_path TO taza_ops, public;

-- Square invoice statuses (internal lifecycle values already exist).
ALTER TYPE taza_ops.invoice_status ADD VALUE IF NOT EXISTS 'Scheduled';
ALTER TYPE taza_ops.invoice_status ADD VALUE IF NOT EXISTS 'Unpaid';
ALTER TYPE taza_ops.invoice_status ADD VALUE IF NOT EXISTS 'Refunded';
ALTER TYPE taza_ops.invoice_status ADD VALUE IF NOT EXISTS 'Failed';
ALTER TYPE taza_ops.invoice_status ADD VALUE IF NOT EXISTS 'Canceled';

-- Invoices
ALTER TABLE taza_ops.invoices ADD COLUMN IF NOT EXISTS invoice_number       TEXT;
ALTER TABLE taza_ops.invoices ADD COLUMN IF NOT EXISTS public_url           TEXT;
ALTER TABLE taza_ops.invoices ADD COLUMN IF NOT EXISTS provider_status      TEXT;   -- raw Square status
ALTER TABLE taza_ops.invoices ADD COLUMN IF NOT EXISTS sale_or_service_date DATE;   -- event date
ALTER TABLE taza_ops.invoices ADD COLUMN IF NOT EXISTS deposit_basis_cents  INTEGER;-- initial-quote basis for the locked deposit
ALTER TABLE taza_ops.invoices ADD COLUMN IF NOT EXISTS raw_payload          JSONB;

-- Orders
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS provider_status      TEXT;   -- Square order state (OPEN/COMPLETED/CANCELED)
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS total_tax_cents      INTEGER;
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS total_tip_cents      INTEGER;
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS net_amount_due_cents INTEGER;
ALTER TABLE taza_ops.orders ADD COLUMN IF NOT EXISTS raw_payload          JSONB;

-- Invoice line items (sourced from the order's line_items)
ALTER TABLE taza_ops.invoice_line_items ADD COLUMN IF NOT EXISTS square_uid         TEXT;  -- order line_item uid
ALTER TABLE taza_ops.invoice_line_items ADD COLUMN IF NOT EXISTS catalog_object_id  TEXT;  -- may be NULL (ad-hoc item)
ALTER TABLE taza_ops.invoice_line_items ADD COLUMN IF NOT EXISTS tax_cents          INTEGER;
ALTER TABLE taza_ops.invoice_line_items ADD COLUMN IF NOT EXISTS note               TEXT;

-- Payments (sourced from order tenders)
ALTER TABLE taza_ops.payments ADD COLUMN IF NOT EXISTS card_brand  TEXT;
ALTER TABLE taza_ops.payments ADD COLUMN IF NOT EXISTS card_last4  TEXT;
ALTER TABLE taza_ops.payments ADD COLUMN IF NOT EXISTS raw_payload JSONB;

-- Helpful lookup indexes for the import's upserts
CREATE INDEX IF NOT EXISTS idx_invoices_number   ON taza_ops.invoices (invoice_number);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_square
    ON taza_ops.orders (external_id) WHERE source_system = 'square';
