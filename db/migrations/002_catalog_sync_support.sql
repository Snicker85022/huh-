-- ============================================================================
-- Migration 002 — Catalog sync support
-- ----------------------------------------------------------------------------
-- The catalog sync caches the FULL Square catalog into menu_items, one row per
-- sellable ITEM_VARIATION, keyed by the variation id (square_id) — because that
-- is the id order line items reference. This is the fix that makes invoice
-- line-item linking work.
--
-- Adds catalog provenance/pricing columns + raw_payload (so nothing is lost;
-- the per-item "intelligence" custom attributes are preserved in raw_payload
-- and mapped to the dedicated columns as their definition keys are confirmed).
-- Idempotent; run after db/schema/*.sql and migration 001.
-- ============================================================================
SET search_path TO taza_ops, public;

ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS square_item_id          TEXT;   -- parent ITEM id
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS catalog_version         BIGINT; -- variation version (change detection)
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS kitchen_name            TEXT;   -- prep/build-sheet name
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS pricing_type            TEXT;   -- FIXED_PRICING / VARIABLE_PRICING
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS default_unit_cost_cents INTEGER;-- vendor cost, for margin
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS reporting_category_id   TEXT;
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS ecom_available          BOOLEAN;
ALTER TABLE taza_ops.menu_items ADD COLUMN IF NOT EXISTS raw_payload             JSONB;

CREATE INDEX IF NOT EXISTS idx_menu_items_item ON taza_ops.menu_items (square_item_id);

COMMENT ON COLUMN taza_ops.menu_items.square_id IS
    'Square ITEM_VARIATION id — the id order line items reference. The join key.';
COMMENT ON COLUMN taza_ops.menu_items.raw_payload IS
    'Full catalog object; preserves per-item intelligence custom attributes until mapped.';
