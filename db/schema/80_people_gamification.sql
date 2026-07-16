-- ============================================================================
-- Taza OS — People & gamification
--   crew · points_ledger · overrides
-- ----------------------------------------------------------------------------
-- The system should feel like a game everyone is winning — and let Nick/Sandra
-- issue BONUSES and DEMERITS. points_ledger entries are signed (positive bonus,
-- negative demerit) with the issuer recorded.
--
-- overrides is Sandra's routine override log, kept faithful to HAI-001:
-- "PIN = auth, not justification. Zero explanation field." No reasoning column.
-- (If Nick rules that overrides should capture "why," add reasoning here — see
-- the flagged contradiction in docs/schema-contract.md.)
-- ============================================================================
SET search_path TO taza_ops, public;

CREATE TYPE taza_ops.points_reason AS ENUM
    ('task_completion', 'label_print', 'location_record', 'bonus', 'demerit');

-- ---- CREW ------------------------------------------------------------------
CREATE TABLE taza_ops.crew (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT NOT NULL,
    pin_hash       TEXT NOT NULL,                     -- store a hash, never the raw PIN
    role           TEXT,
    phone          TEXT,
    points_balance INTEGER NOT NULL DEFAULT 0,        -- denormalized running total
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_crew_updated_at BEFORE UPDATE ON taza_ops.crew
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ---- POINTS_LEDGER (signed: + bonus / - demerit) ---------------------------
CREATE TABLE taza_ops.points_ledger (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crew_id     BIGINT NOT NULL REFERENCES taza_ops.crew(id) ON DELETE CASCADE,
    points      INTEGER NOT NULL,                     -- negative for demerits
    reason      taza_ops.points_reason NOT NULL,
    issued_by   TEXT,                                 -- 'Nick' / 'Sandra' for manual bonus/demerit
    task_id     BIGINT REFERENCES taza_ops.tasks(task_id) ON DELETE SET NULL,
    note        TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_points_crew ON taza_ops.points_ledger (crew_id);

-- ---- OVERRIDES (Sandra override log — HAI-001, no justification field) -------
CREATE TABLE taza_ops.overrides (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workflow_id         TEXT,
    crew_pin            TEXT NOT NULL,                 -- auth only
    recommendation_text TEXT,
    action_taken        TEXT,
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_overrides_workflow ON taza_ops.overrides (workflow_id);
