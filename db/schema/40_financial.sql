-- ============================================================================
-- Taza OS — Financial layer
--   invoices · orders · invoice_line_items · payments
-- ----------------------------------------------------------------------------
-- Rail split (Nick): SQUARE = catering invoices + deposits; WIX PAYMENTS = the
-- online platter store. Square is the system of record for a published invoice;
-- our system owns the DRAFT lifecycle (W7 auto-draft -> Sandra review -> Nick
-- approve -> publish to Square -> deposit -> opportunity goes Booked via W3).
--
-- Deposit logic (Invoice Form Field Spec §6 + Build Brief): deposit_pct default
-- 50%, deposit_amount LOCKED as a fixed dollar amount at first publish (prevents
-- Square auto-nag on later revisions); balance due default service_date − 7 days;
-- tipping enabled by default.  All money stored as integer cents.
-- ============================================================================
SET search_path TO taza_ops, public;

CREATE TYPE taza_ops.invoice_status AS ENUM (
    'Draft',          -- W7 auto-generated
    'SandraReview',   -- pushed to Sandra: dropdowns / other-blank
    'NickReview',     -- pushed to Nick for final approval
    'Approved',       -- Nick approved; ready to publish
    'Published',      -- sent via Square (emails customer + tazabistro@gmail.com)
    'PartiallyPaid',  -- deposit received
    'Paid',           -- balance settled
    'Overdue',
    'Void'
);
CREATE TYPE taza_ops.order_source   AS ENUM ('square', 'wix');
CREATE TYPE taza_ops.line_type      AS ENUM
    ('food', 'service', 'delivery', 'surcharge', 'discount', 'info_block');  -- info_block = $0 customer-facing text
CREATE TYPE taza_ops.payment_type   AS ENUM ('deposit', 'balance', 'full', 'refund', 'tip');
CREATE TYPE taza_ops.payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
CREATE TYPE taza_ops.payment_rail   AS ENUM ('square', 'wix', 'check', 'ach', 'card', 'cash');

-- ---- INVOICES --------------------------------------------------------------
CREATE TABLE taza_ops.invoices (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id        UUID REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    account_id            UUID REFERENCES taza_ops.accounts(id)      ON DELETE SET NULL,  -- payer
    contact_id            UUID REFERENCES taza_ops.contacts(id)      ON DELETE SET NULL,
    -- Auto-title: "{First} {Last} {TYPE}{adults}(extras) {MMDDYYYY}" (Invoice Form §7)
    title                 TEXT,
    status                taza_ops.invoice_status NOT NULL DEFAULT 'Draft',

    -- Review flow timestamps (Sandra -> Nick -> publish)
    drafted_at            TIMESTAMPTZ,
    reviewed_by_sandra_at TIMESTAMPTZ,
    approved_by_nick_at   TIMESTAMPTZ,
    published_at          TIMESTAMPTZ,

    -- Money (integer cents)
    subtotal_cents        INTEGER NOT NULL DEFAULT 0,
    tax_cents             INTEGER NOT NULL DEFAULT 0,
    delivery_cents        INTEGER NOT NULL DEFAULT 0,
    surcharge_cents       INTEGER NOT NULL DEFAULT 0,
    total_cents           INTEGER NOT NULL DEFAULT 0,

    -- Deposit: fixed-dollar, locked at first publish
    deposit_pct           NUMERIC NOT NULL DEFAULT 50,
    deposit_amount_cents  INTEGER,
    deposit_locked        BOOLEAN NOT NULL DEFAULT FALSE,
    balance_due_cents     INTEGER,
    date_balance_due      DATE,                          -- default service_date − 7
    tipping_enabled       BOOLEAN NOT NULL DEFAULT TRUE,

    generated_by_model    TEXT,                          -- W7 provenance (e.g. qwen2.5:7b)

    -- Square identity / idempotency
    square_invoice_id     TEXT,
    square_order_id       TEXT,
    source_system         taza_ops.source_system,
    external_id           TEXT,
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_invoices_opp     ON taza_ops.invoices (opportunity_id);
CREATE INDEX idx_invoices_account ON taza_ops.invoices (account_id);
CREATE INDEX idx_invoices_status  ON taza_ops.invoices (status);
CREATE UNIQUE INDEX idx_invoices_square ON taza_ops.invoices (square_invoice_id)
    WHERE square_invoice_id IS NOT NULL;
CREATE TRIGGER trg_invoices_updated_at BEFORE UPDATE ON taza_ops.invoices
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- Back-fill forward FK from customer_communications (declared in 30_comms.sql).
ALTER TABLE taza_ops.customer_communications
    ADD CONSTRAINT fk_cc_linked_invoice
    FOREIGN KEY (linked_invoice_id) REFERENCES taza_ops.invoices(id) ON DELETE SET NULL;

-- ---- ORDERS (Square order / Wix platter order) -----------------------------
CREATE TABLE taza_ops.orders (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id            UUID REFERENCES taza_ops.invoices(id)      ON DELETE SET NULL,
    account_id            UUID REFERENCES taza_ops.accounts(id)      ON DELETE SET NULL,
    opportunity_id        UUID REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    order_source          taza_ops.order_source NOT NULL,
    status                TEXT,                          -- provider order status
    total_cents           INTEGER NOT NULL DEFAULT 0,
    -- Square Order Custom Attributes: taza_setup_type / taza_tables_count /
    -- taza_linens_tier / taza_kitchen_departure (Invoice Form output spec)
    custom_attributes     JSONB,
    source_system         taza_ops.source_system,
    external_id           TEXT,                          -- Square/Wix order id
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_orders_invoice ON taza_ops.orders (invoice_id);
CREATE INDEX idx_orders_account ON taza_ops.orders (account_id);
CREATE TRIGGER trg_orders_updated_at BEFORE UPDATE ON taza_ops.orders
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- INVOICE_LINE_ITEMS ----------------------------------------------------
CREATE TABLE taza_ops.invoice_line_items (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id        UUID NOT NULL REFERENCES taza_ops.invoices(id) ON DELETE CASCADE,
    order_id          UUID REFERENCES taza_ops.orders(id) ON DELETE SET NULL,
    line_type         taza_ops.line_type NOT NULL DEFAULT 'food',
    -- menu_item_id references menu_items (BIGINT) — FK added in 50_catalog.sql.
    menu_item_id      BIGINT,
    sku               TEXT,                              -- Square catalog SKU
    description       TEXT NOT NULL,
    quantity          NUMERIC NOT NULL DEFAULT 1,
    unit_price_cents  INTEGER NOT NULL DEFAULT 0,
    total_cents       INTEGER NOT NULL DEFAULT 0,
    sort_order        INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_line_items_invoice ON taza_ops.invoice_line_items (invoice_id);
CREATE INDEX idx_line_items_menu    ON taza_ops.invoice_line_items (menu_item_id);
CREATE TRIGGER trg_line_items_updated_at BEFORE UPDATE ON taza_ops.invoice_line_items
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- PAYMENTS --------------------------------------------------------------
CREATE TABLE taza_ops.payments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id        UUID REFERENCES taza_ops.invoices(id) ON DELETE SET NULL,
    order_id          UUID REFERENCES taza_ops.orders(id)   ON DELETE SET NULL,
    account_id        UUID REFERENCES taza_ops.accounts(id) ON DELETE SET NULL,
    payment_type      taza_ops.payment_type NOT NULL,
    rail              taza_ops.payment_rail NOT NULL,
    amount_cents      INTEGER NOT NULL,
    status            taza_ops.payment_status NOT NULL DEFAULT 'completed',
    -- A completed deposit is the signal that flips the opportunity Open -> Booked (W3).
    is_deposit        BOOLEAN NOT NULL DEFAULT FALSE,
    paid_at           TIMESTAMPTZ,
    source_system     taza_ops.source_system,
    external_id       TEXT,                              -- Square/Wix payment id
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, external_id)
);
CREATE INDEX idx_payments_invoice ON taza_ops.payments (invoice_id);
CREATE INDEX idx_payments_account ON taza_ops.payments (account_id);
CREATE INDEX idx_payments_deposit ON taza_ops.payments (is_deposit) WHERE is_deposit;
CREATE TRIGGER trg_payments_updated_at BEFORE UPDATE ON taza_ops.payments
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();
