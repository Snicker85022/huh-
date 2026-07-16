-- ============================================================================
-- Taza OS — Schema foundation
-- Target: PostgreSQL on the N100 (schema `taza_ops`), fronted by NocoDB.
-- ----------------------------------------------------------------------------
-- Conventions used throughout db/schema/*.sql:
--   * All objects live in schema `taza_ops`.
--   * Primary keys:  <table_singular>_id  BIGINT GENERATED ALWAYS AS IDENTITY.
--   * Timestamps:    TIMESTAMPTZ, default now(); every table carries
--                    created_at + updated_at (updated_at maintained by trigger).
--   * Enums:         Postgres ENUM types for stable status sets — these map
--                    cleanly to NocoDB single-select fields.
--   * Idempotency:   any table populated by an external system (Square, Wix,
--                    Gmail, Make) carries the four contract fields via the
--                    external_identity mixin columns and a UNIQUE
--                    (source_system, external_id).  Automations UPSERT by that
--                    pair — never blind-insert.  (Schema Contract v1 §4.)
--   * Change history: mutations of consequence are written to audit_log with
--                    before/after JSONB, so an opportunity's shifting dates /
--                    venue / payer are fully reconstructable. (see 90_audit.sql)
-- Files are numbered by dependency order; apply in ascending order.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS taza_ops;
SET search_path TO taza_ops, public;

-- gen_random_uuid(), digest() for payload hashes
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ----------------------------------------------------------------------------
-- Shared: updated_at maintenance
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION taza_ops.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION taza_ops.set_updated_at() IS
    'BEFORE UPDATE trigger fn: stamps updated_at = now() on every row change.';

-- ----------------------------------------------------------------------------
-- Source-system enum (external identity / idempotency)
-- ----------------------------------------------------------------------------
CREATE TYPE taza_ops.source_system AS ENUM (
    'square', 'wix', 'gmail', 'make', 'manual', 'internal'
);
COMMENT ON TYPE taza_ops.source_system IS
    'Owning external system for a record. Used with external_id for idempotent upserts.';
