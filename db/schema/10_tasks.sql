-- ============================================================================
-- Taza OS — Tasks engine (single canonical task system)
-- ----------------------------------------------------------------------------
-- One tasks system for the whole operation (Nick confirmed). Kanban cards on
-- the kitchen displays RENDER FROM this table — they are a view of tasks, not a
-- separate store. Task generation is largely deterministic (driven by rules +
-- the detailed menu); some initial inference may run on the Aoostar.
--
-- v1 supports linear dependency chains via a self-referencing depends_on.
-- Multi-dependency fan-in (a junction table) is deferred to v2.
-- Source: 🏛️ System Architecture & Diagrams — "Tasks Table DDL (Canonical)".
-- ============================================================================
SET search_path TO taza_ops, public;

CREATE TYPE taza_ops.task_status AS ENUM (
    'LOCKED',            -- waiting on a predecessor
    'PENDING',           -- unlocked, ready to work
    'COMPLETED',
    'PARTIAL_COMPLETE',  -- added per D-026 / KIT-006; needs its own automation
    'FAILED'
);

-- High-level workflow phase a task belongs to, so cards can be grouped/filtered
-- on the displays: shopping, storage, prep, day-of, follow-up, admin.
CREATE TYPE taza_ops.task_phase AS ENUM (
    'shopping', 'storage', 'prep', 'day_of', 'follow_up', 'admin'
);

CREATE TABLE taza_ops.tasks (
    task_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    description      TEXT        NOT NULL,
    assigned_surface VARCHAR(50) NOT NULL,          -- which display/device shows this card
    phase            taza_ops.task_phase,
    status           taza_ops.task_status NOT NULL DEFAULT 'LOCKED',

    -- Linear dependency: this task unlocks when depends_on reaches COMPLETED.
    depends_on       BIGINT REFERENCES taza_ops.tasks(task_id) ON DELETE SET NULL,

    -- What this task is for: every task must trace to a Customer Event
    -- (opportunity, UUID PK) or a Production Batch (BIGINT PK) — Schema Contract
    -- v1 §5 binding rule. FKs added in 99_constraints.sql once those tables exist.
    opportunity_id   UUID,
    batch_id         BIGINT,

    -- Gamification: base points a crew member earns for closing this card.
    points_value     INTEGER NOT NULL DEFAULT 0,

    unlocked_at      TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast lookup of what a completed task should unlock.
CREATE INDEX idx_tasks_dependency ON taza_ops.tasks (depends_on) WHERE status = 'LOCKED';
CREATE INDEX idx_tasks_status     ON taza_ops.tasks (status);
CREATE INDEX idx_tasks_opportunity ON taza_ops.tasks (opportunity_id);

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON taza_ops.tasks
    FOR EACH ROW EXECUTE FUNCTION taza_ops.set_updated_at();

-- ----------------------------------------------------------------------------
-- Dependency release: when a task goes COMPLETED, flip its direct dependents
-- from LOCKED -> PENDING and stamp unlocked_at. (PARTIAL_COMPLETE deliberately
-- does NOT release dependents — that needs separate, explicit automation.)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION taza_ops.release_dependent_tasks()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status IS DISTINCT FROM 'COMPLETED' THEN
        UPDATE taza_ops.tasks
           SET status = 'PENDING', unlocked_at = now()
         WHERE depends_on = NEW.task_id
           AND status = 'LOCKED';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_task_completion
    AFTER UPDATE ON taza_ops.tasks
    FOR EACH ROW EXECUTE FUNCTION taza_ops.release_dependent_tasks();

COMMENT ON TABLE taza_ops.tasks IS
    'Single canonical task engine. Kanban cards on kitchen displays render from this table.';
COMMENT ON COLUMN taza_ops.tasks.depends_on IS
    'Self-reference for linear chains; COMPLETED release handled by trg_task_completion.';
