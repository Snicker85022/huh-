-- ============================================================================
-- Taza OS — Production
--   production_batches · batch_allocations · task_completions · labels
-- ----------------------------------------------------------------------------
-- Shared prep is produced ONCE in a Production Batch and allocated to the
-- Customer Events it serves (Schema Contract v1 §5) — no double-counting.
--
-- task_completions is the kitchen close-out touchpoint: to close a kanban card
-- a crew member MUST supply PIN + where they put the item (Last Known Location)
-- + the item's weight; a label print is optional (earns bonus points).
-- ============================================================================
SET search_path TO taza_ops, public;

-- ---- PRODUCTION_BATCHES ----------------------------------------------------
CREATE TABLE taza_ops.production_batches (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          TEXT NOT NULL,
    batch_type    TEXT,                               -- sauce / dessert / shopping run / ...
    status        taza_ops.task_status NOT NULL DEFAULT 'PENDING',
    scheduled_for TIMESTAMPTZ,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_batches_updated_at BEFORE UPDATE ON taza_ops.production_batches
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- BATCH_ALLOCATIONS (batch <-> opportunity, many-to-many) ----------------
CREATE TABLE taza_ops.batch_allocations (
    batch_id       BIGINT NOT NULL REFERENCES taza_ops.production_batches(id) ON DELETE CASCADE,
    opportunity_id UUID   NOT NULL REFERENCES taza_ops.opportunities(id)      ON DELETE CASCADE,
    quantity       NUMERIC,                           -- portions/units from batch to this event
    unit           TEXT,
    notes          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (batch_id, opportunity_id)
);

-- ---- TASK_COMPLETIONS (the close-out: PIN + location + weight [+ label]) -----
CREATE TABLE taza_ops.task_completions (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id           BIGINT NOT NULL REFERENCES taza_ops.tasks(task_id) ON DELETE CASCADE,
    crew_id           BIGINT,                          -- FK -> crew in 99_constraints.sql
    crew_pin          TEXT NOT NULL,                   -- PIN entered at close-out (auth)
    inventory_item_id BIGINT REFERENCES taza_ops.inventory_items(id) ON DELETE SET NULL,
    location          TEXT NOT NULL,                   -- where the item was put (required)
    weight_value      NUMERIC NOT NULL,                -- item weight (required)
    weight_unit       TEXT NOT NULL DEFAULT 'lb',
    label_printed     BOOLEAN NOT NULL DEFAULT FALSE,  -- optional; bonus points
    points_awarded    INTEGER NOT NULL DEFAULT 0,
    completed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes             TEXT
);
CREATE INDEX idx_completions_task ON taza_ops.task_completions (task_id);
CREATE INDEX idx_completions_crew ON taza_ops.task_completions (crew_id);

-- ---- LABELS (print events) -------------------------------------------------
CREATE TABLE taza_ops.labels (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_completion_id BIGINT REFERENCES taza_ops.task_completions(id) ON DELETE SET NULL,
    inventory_item_id  BIGINT REFERENCES taza_ops.inventory_items(id)  ON DELETE SET NULL,
    label_type         TEXT,
    content            JSONB,                          -- what was printed
    printed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    printed_by         TEXT                            -- crew PIN
);
CREATE INDEX idx_labels_completion ON taza_ops.labels (task_completion_id);
