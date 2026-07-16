-- ============================================================================
-- Taza OS — Catalog & catalog intelligence
--   menu_items · equipment · procedures
--   item_components · item_packing_profiles · item_equipment · procedure_link
-- ----------------------------------------------------------------------------
-- menu_items is the sellable catalog, synced weekly from Square (source of
-- truth). The 12 "catalog intelligence" attributes live in Square as custom
-- attributes and are mirrored here as columns so the DB can reason about
-- portioning, hold times, and packing. The relational intelligence (bill of
-- materials, packing profiles, equipment needs, SOP links) lives in the four
-- join tables below — designed with full constraints in v1 even though the
-- Catalog Ops interview populates them later (Sandra, Friday).
--
-- PERISHABILITY HOOKS (shelf_life_days, buy_ahead_max_days) are Nick's
-- requirement and are NOT in the documented specs — columns exist, values TBD.
-- These are int PKs (BIGINT), matching the as-built menu_items DDL.
-- ============================================================================
SET search_path TO taza_ops, public;

CREATE TYPE taza_ops.service_mode  AS ENUM
    ('delivery', 'staffed_buffet', 'personal_chef', 'plated', 'passed');
CREATE TYPE taza_ops.pan_footprint AS ENUM ('full', 'half', 'third', 'sixth');

-- ---- MENU_ITEMS ------------------------------------------------------------
CREATE TABLE taza_ops.menu_items (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    square_id             TEXT UNIQUE,                 -- Square catalog object id
    name                  TEXT NOT NULL,
    category              TEXT,                        -- Catering / Restaurant / ...
    description           TEXT,
    price_cents           INTEGER,
    pricing_unit          TEXT,                        -- per_person / per_tray / each
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,

    -- Catalog intelligence (mirrored from Square custom attributes)
    serves_min            INTEGER,
    serves_max            INTEGER,
    dietary_flags         TEXT[],
    allergens             TEXT[],
    allergen_notes        TEXT,
    station_type          TEXT,
    hot_hold_max_min      INTEGER,
    cold_hold_max_min     INTEGER,
    prep_advance_max_hr   INTEGER,
    prep_time_min         INTEGER,
    quality_risk          TEXT,
    default_pan_footprint taza_ops.pan_footprint,

    -- Perishability hooks (Nick; undocumented; values from Sandra Friday)
    shelf_life_days       INTEGER,
    buy_ahead_max_days    INTEGER,                     -- "don't buy berries 4 days ahead"

    -- Idempotency (weekly Square sync upserts by square_id)
    source_system         taza_ops.source_system DEFAULT 'square',
    external_id           TEXT,                        -- = square_id
    external_updated_at    TIMESTAMPTZ,
    external_payload_hash  TEXT,
    last_synced_at        TIMESTAMPTZ DEFAULT now(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_menu_items_category ON taza_ops.menu_items (category);
CREATE INDEX idx_menu_items_active   ON taza_ops.menu_items (is_active);
CREATE TRIGGER trg_menu_items_updated_at BEFORE UPDATE ON taza_ops.menu_items
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- Back-fill the FK from invoice_line_items (declared in 40_financial.sql).
ALTER TABLE taza_ops.invoice_line_items
    ADD CONSTRAINT fk_line_items_menu
    FOREIGN KEY (menu_item_id) REFERENCES taza_ops.menu_items(id) ON DELETE SET NULL;

-- ---- EQUIPMENT (referenced by item_equipment; from Equipment & Capacity intv) --
CREATE TABLE taza_ops.equipment (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name               TEXT NOT NULL,
    equipment_type     TEXT,
    quantity_available INTEGER DEFAULT 1,
    capacity_notes     TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_equipment_updated_at BEFORE UPDATE ON taza_ops.equipment
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- PROCEDURES (atomic SOPs; referenced by procedure_link) -----------------
CREATE TABLE taza_ops.procedures (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT NOT NULL,
    procedure_type TEXT,
    content        TEXT,
    kb_ref         TEXT,                                -- Google Drive / Notion source ref
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_procedures_updated_at BEFORE UPDATE ON taza_ops.procedures
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- ITEM_COMPONENTS (bill of materials: Mezza Platter = Hummus + Baba + …) --
CREATE TABLE taza_ops.item_components (
    parent_item_id    BIGINT NOT NULL REFERENCES taza_ops.menu_items(id) ON DELETE CASCADE,
    component_item_id BIGINT NOT NULL REFERENCES taza_ops.menu_items(id) ON DELETE CASCADE,
    qty_per_parent    NUMERIC NOT NULL,
    notes             TEXT,                            -- substitution notes
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (parent_item_id, component_item_id),
    CHECK (parent_item_id <> component_item_id)
);

-- ---- ITEM_PACKING_PROFILES (per item × service mode) -----------------------
CREATE TABLE taza_ops.item_packing_profiles (
    item_id            BIGINT NOT NULL REFERENCES taza_ops.menu_items(id) ON DELETE CASCADE,
    service_mode       taza_ops.service_mode NOT NULL,
    pan_footprint      taza_ops.pan_footprint,
    pan_depth_in       NUMERIC CHECK (pan_depth_in IN (2, 4, 6)),
    fill_qty_per_pan   NUMERIC,
    container_override TEXT,
    notes              TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (item_id, service_mode)
);
CREATE TRIGGER trg_packing_updated_at BEFORE UPDATE ON taza_ops.item_packing_profiles
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- ITEM_EQUIPMENT (drives equipment-contention detection) ----------------
CREATE TABLE taza_ops.item_equipment (
    item_id       BIGINT NOT NULL REFERENCES taza_ops.menu_items(id) ON DELETE CASCADE,
    equipment_id  BIGINT NOT NULL REFERENCES taza_ops.equipment(id)  ON DELETE CASCADE,
    occupancy_min NUMERIC,                             -- minutes this item ties up the equipment
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (item_id, equipment_id)
);

-- ---- PROCEDURE_LINK (item × SOP × service mode) ----------------------------
-- Spec keys on (item_id, procedure_id, service_mode) with service_mode nullable
-- (null = applies to all modes). Because SQL PKs can't contain nulls, this uses
-- a surrogate PK + nullable service_mode; promotion logic enforces dedupe.
CREATE TABLE taza_ops.procedure_link (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id      BIGINT NOT NULL REFERENCES taza_ops.menu_items(id) ON DELETE CASCADE,
    procedure_id BIGINT NOT NULL REFERENCES taza_ops.procedures(id) ON DELETE CASCADE,
    service_mode taza_ops.service_mode,                -- NULL = all modes
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_procedure_link_item ON taza_ops.procedure_link (item_id, procedure_id);
