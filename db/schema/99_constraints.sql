-- ============================================================================
-- Taza OS — Deferred cross-cutting foreign keys
-- ----------------------------------------------------------------------------
-- These FKs reference tables that are created LATER than the referencing table
-- in load order, so they are added here after every table exists. Apply this
-- file LAST.
-- ============================================================================
SET search_path TO taza_ops, public;

-- tasks (10) -> opportunities (20) / production_batches (70)
ALTER TABLE taza_ops.tasks
    ADD CONSTRAINT fk_tasks_opportunity
    FOREIGN KEY (opportunity_id) REFERENCES taza_ops.opportunities(id) ON DELETE SET NULL;
ALTER TABLE taza_ops.tasks
    ADD CONSTRAINT fk_tasks_batch
    FOREIGN KEY (batch_id) REFERENCES taza_ops.production_batches(id) ON DELETE SET NULL;

-- inventory_items (60) / shopping_lists (60) -> production_batches (70)
ALTER TABLE taza_ops.inventory_items
    ADD CONSTRAINT fk_inventory_batch
    FOREIGN KEY (batch_id) REFERENCES taza_ops.production_batches(id) ON DELETE SET NULL;
ALTER TABLE taza_ops.shopping_lists
    ADD CONSTRAINT fk_shoplist_batch
    FOREIGN KEY (batch_id) REFERENCES taza_ops.production_batches(id) ON DELETE SET NULL;

-- task_completions (70) -> crew (80)
ALTER TABLE taza_ops.task_completions
    ADD CONSTRAINT fk_completions_crew
    FOREIGN KEY (crew_id) REFERENCES taza_ops.crew(id) ON DELETE SET NULL;
