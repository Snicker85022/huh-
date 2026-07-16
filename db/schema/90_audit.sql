-- ============================================================================
-- Taza OS — audit_log  (provenance + change history)
-- ----------------------------------------------------------------------------
-- Serves TWO jobs at once:
--   1. Provenance — every Claude/automation-initiated write is logged with the
--      actor and the prompt/rationale that produced it (decision D-019).
--   2. Change history — before/after JSONB lets us reconstruct how a volatile
--      record (opportunity dates, venue, PAYER NAME, guest count, ...) evolved
--      over time. This is how "track all the changes and the history of the
--      customer's details as they change" is satisfied without versioning every
--      table by hand.
--
-- Merged from the two designs found in the KB:
--   * revision-history guide (entity_type/id, change_type, change_summary,JSONB)
--   * architecture doc D-019 (actor_role, prompt_excerpt, before/after, soft-delete)
-- ============================================================================
SET search_path TO taza_ops, public;

CREATE TYPE taza_ops.audit_change_type AS ENUM (
    'INSERT', 'UPDATE', 'DELETE', 'STATUS_CHANGE', 'OVERRIDE'
);

CREATE TYPE taza_ops.audit_actor_role AS ENUM (
    'claude', 'automation', 'team_member', 'external_sync', 'system'
);

CREATE TABLE taza_ops.audit_log (
    event_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- What was touched
    entity_type        VARCHAR(60) NOT NULL,   -- table/entity name, e.g. 'opportunities'
    entity_id          TEXT,                   -- PK of the affected row (as text; heterogeneous)
    entity_label       VARCHAR(255),           -- human-friendly name for quick scanning

    change_type        taza_ops.audit_change_type NOT NULL,
    change_summary     TEXT,                   -- one-line human summary

    -- Change history payloads (null side = insert/delete)
    before_value       JSONB,
    after_value        JSONB,

    -- Provenance (D-019)
    actor_role         taza_ops.audit_actor_role NOT NULL DEFAULT 'system',
    actor_ref          VARCHAR(255),           -- crew PIN / automation id / model id
    prompt_excerpt     TEXT,                   -- the prompt/instruction that produced a Claude write
    source_system      taza_ops.source_system,

    -- Override & soft-delete flags (humans can always override; see conflict rules)
    is_override        BOOLEAN NOT NULL DEFAULT FALSE,
    is_breaking_change BOOLEAN NOT NULL DEFAULT FALSE,
    notes              TEXT
);

CREATE INDEX idx_audit_entity   ON taza_ops.audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_time     ON taza_ops.audit_log (occurred_at DESC);
CREATE INDEX idx_audit_actor    ON taza_ops.audit_log (actor_role, actor_ref);

COMMENT ON TABLE taza_ops.audit_log IS
    'Provenance + change history. Every consequential write lands here with before/after JSONB.';
COMMENT ON COLUMN taza_ops.audit_log.prompt_excerpt IS
    'For Claude-initiated writes: the instruction that produced the change (D-019).';
COMMENT ON COLUMN taza_ops.audit_log.is_override IS
    'TRUE when a human overrode a system recommendation/conflict flag.';
