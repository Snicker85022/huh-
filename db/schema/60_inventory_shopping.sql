-- ============================================================================
-- Taza OS — Inventory & shopping
--   inventory_items · stores · store_item_locations
--   shopping_lists · shopping_list_items
-- ----------------------------------------------------------------------------
-- inventory_items are PHYSICAL things (distinct from sellable menu_items). They
-- move through a lifecycle (raw -> work-in-process -> finished) and can be
-- REUSED: cooked meat becomes a stew base, so derived_from_id records lineage.
-- Every kitchen close-out stamps last_known_location + weight (see 70).
--
-- Two Last-Known-Location systems:
--   * kitchen:  inventory_items.last_known_location (set on task close-out)
--   * store:    store_item_locations.aisle (set when a shopper buys an item)
--
-- STORE VALUE ranking (stores.value_rank) is Nick's "best VALUE not cost"
-- requirement — undocumented, and it contradicts the one written store rule
-- (G-02 "cheapest available"). Column exists; ranking logic TBD.
-- ============================================================================
SET search_path TO taza_ops, public;

CREATE TYPE taza_ops.inventory_state AS ENUM ('raw', 'wip', 'finished');
CREATE TYPE taza_ops.shopping_status AS ENUM ('draft', 'active', 'shopping', 'complete');

-- ---- INVENTORY_ITEMS -------------------------------------------------------
CREATE TABLE taza_ops.inventory_items (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                 TEXT NOT NULL,
    menu_item_id         BIGINT REFERENCES taza_ops.menu_items(id) ON DELETE SET NULL,
    lifecycle_state      taza_ops.inventory_state NOT NULL DEFAULT 'raw',
    -- Reuse lineage: this item was derived from another (cooked meat -> stew base)
    derived_from_id      BIGINT REFERENCES taza_ops.inventory_items(id) ON DELETE SET NULL,
    quantity             NUMERIC,
    unit                 TEXT,
    weight_value         NUMERIC,                     -- captured at close-out
    weight_unit          TEXT DEFAULT 'lb',
    -- Kitchen Last Known Location (required on task close-out)
    last_known_location  TEXT,
    location_updated_at  TIMESTAMPTZ,
    location_updated_by  TEXT,                        -- crew PIN
    is_frozen            BOOLEAN NOT NULL DEFAULT FALSE,
    frozen_at            TIMESTAMPTZ,
    best_by              DATE,
    opportunity_id       UUID REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    batch_id             BIGINT,                      -- FK -> production_batches in 99_constraints.sql
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_inv_state    ON taza_ops.inventory_items (lifecycle_state);
CREATE INDEX idx_inv_menu     ON taza_ops.inventory_items (menu_item_id);
CREATE INDEX idx_inv_opp      ON taza_ops.inventory_items (opportunity_id);
CREATE INDEX idx_inv_derived  ON taza_ops.inventory_items (derived_from_id);
CREATE TRIGGER trg_inventory_updated_at BEFORE UPDATE ON taza_ops.inventory_items
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- STORES ----------------------------------------------------------------
CREATE TABLE taza_ops.stores (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    store_type  TEXT,                                 -- restaurant_depot / costco / grocery / ...
    address     TEXT,
    value_rank  INTEGER,                              -- best-VALUE ranking hook (Nick; TBD)
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_stores_updated_at BEFORE UPDATE ON taza_ops.stores
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- STORE_ITEM_LOCATIONS (Last Known Store Location: aisle memory) ---------
CREATE TABLE taza_ops.store_item_locations (
    store_id          BIGINT NOT NULL REFERENCES taza_ops.stores(id)          ON DELETE CASCADE,
    inventory_item_id BIGINT NOT NULL REFERENCES taza_ops.inventory_items(id) ON DELETE CASCADE,
    aisle             TEXT,                           -- recorded by the shopper
    last_seen_at      TIMESTAMPTZ,
    last_seen_by      TEXT,                           -- crew PIN
    notes             TEXT,
    PRIMARY KEY (store_id, inventory_item_id)
);

-- ---- SHOPPING_LISTS (vendor-grouped, consolidated across overlapping events) --
CREATE TABLE taza_ops.shopping_lists (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title          TEXT,
    store_id       BIGINT REFERENCES taza_ops.stores(id)        ON DELETE SET NULL,
    opportunity_id UUID   REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL,
    batch_id       BIGINT,                            -- FK -> production_batches in 99_constraints.sql
    status         taza_ops.shopping_status NOT NULL DEFAULT 'draft',
    generated_at   TIMESTAMPTZ DEFAULT now(),
    completed_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_shoplist_status ON taza_ops.shopping_lists (status);
CREATE TRIGGER trg_shoplist_updated_at BEFORE UPDATE ON taza_ops.shopping_lists
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- SHOPPING_LIST_ITEMS ---------------------------------------------------
CREATE TABLE taza_ops.shopping_list_items (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shopping_list_id  BIGINT NOT NULL REFERENCES taza_ops.shopping_lists(id) ON DELETE CASCADE,
    inventory_item_id BIGINT REFERENCES taza_ops.inventory_items(id) ON DELETE SET NULL,
    menu_item_id      BIGINT REFERENCES taza_ops.menu_items(id)      ON DELETE SET NULL,
    description       TEXT NOT NULL,
    quantity          NUMERIC,
    unit              TEXT,
    is_critical       BOOLEAN NOT NULL DEFAULT FALSE, -- never-forget critical item
    is_purchased      BOOLEAN NOT NULL DEFAULT FALSE,
    purchased_at      TIMESTAMPTZ,
    purchased_by      TEXT,                           -- crew PIN
    aisle_found       TEXT,                           -- shopper records -> store_item_locations
    store_id          BIGINT REFERENCES taza_ops.stores(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_shopitem_list     ON taza_ops.shopping_list_items (shopping_list_id);
CREATE INDEX idx_shopitem_critical ON taza_ops.shopping_list_items (is_critical) WHERE is_critical;
CREATE TRIGGER trg_shopitem_updated_at BEFORE UPDATE ON taza_ops.shopping_list_items
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();
