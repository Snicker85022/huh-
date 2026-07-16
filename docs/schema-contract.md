# Taza OS — Schema Contract (physical, v1)

The physical realization of the Taza OS data model on PostgreSQL (schema
`taza_ops`), authored from the Notion KB (Schema Contract v1 semantics, Data
Schemas & Field Maps v0.5.0, System Architecture, Workflows Registry, Invoice
Form Field Spec) plus Nick's on-site field session (July 16, 2026).

Validated: applies cleanly on PostgreSQL 16 — **33 tables, 63 foreign keys**;
the `tasks` dependency-release trigger passes a live smoke test.

## Load order

Apply `db/schema/[0-9]*.sql` in ascending numeric order (or run
`db/schema/apply.sh` against a fresh database). `99_constraints.sql` adds the
cross-cutting FKs and must run last.

| File | Domain |
|------|--------|
| `00_init` | schema, conventions, `source_system` enum, `updated_at` fn |
| `10_tasks` | single task engine + dependency auto-release trigger |
| `20_crm` | contacts · accounts · leads · opportunities · touchpoints |
| `30_comms` | exceptions · voice_notes · customer_communications |
| `40_financial` | invoices · orders · invoice_line_items · payments |
| `50_catalog` | menu_items + catalog intelligence (BOM/packing/equipment/SOP) |
| `60_inventory_shopping` | inventory_items · stores · shopping lists · aisle memory |
| `70_production` | production_batches · allocations · task_completions · labels |
| `80_people_gamification` | crew · points_ledger · overrides |
| `90_audit` | audit_log (provenance + change history) |
| `99_constraints` | deferred cross-cutting foreign keys |

## Load-bearing decisions

1. **Hybrid primary keys (forced by the documented specs).** The CRM/comms/
   financial core uses **UUID** PKs — the documented `voice_notes` and
   `customer_communications` field maps declare UUID FKs to `accounts`,
   `opportunities`, `contacts`, so those tables must be UUID. The operational
   tables (`tasks`, `menu_items`, catalog, inventory, shopping, production,
   crew) use **BIGINT identity** PKs, matching their canonical/as-built DDL.
   Cross-links (e.g. `tasks.opportunity_id`) are typed to match their target.
2. **Payer ≠ inquirer.** `contacts` (a person) is separate from `accounts` (the
   paying entity, person or company). An `opportunity` points at both — the
   corporate case where the inquirer isn't the payer is first-class.
3. **Change history via `audit_log`.** Before/after JSONB on every consequential
   write reconstructs how an opportunity's dates / venue / **payer name** /
   guest count evolved. No per-table shadow versioning in v1.
4. **Idempotency.** Externally-sourced tables carry `source_system`,
   `external_id`, `external_updated_at`, `external_payload_hash` with
   `UNIQUE (source_system, external_id)`. Automations upsert by that pair.
5. **Two payment rails.** Square = catering invoices + deposits; Wix Payments =
   the online platter store.
6. **Deposit.** 50% default, locked as a fixed dollar amount at first publish;
   balance due default `service_date − 7`.
7. **One task engine.** Kanban cards render from `tasks`; close-out
   (`task_completions`) requires PIN + location + weight, optional label.

## Open items flagged during authoring

These are recorded here because SQL comments reference them. None block the
schema; each needs a ruling or later data.

### Contradictions with the documentation (need Nick's ruling)
- **Inference host.** Nick: the Aoostar runs sales inference (+ hot backup).
  Docs: the **N100** runs the nightly LLM (`qwen2.5:14b`, `llama.cpp`; Ollama
  deprecated), and the Aoostar's purchase note calls it a dev machine to cut API
  spend. The multi-round "anticipatory follow-up to Sandra's phone" is a **V1.x
  roadmap** item, not built. Schema is host-agnostic; pipelines are not.
- **Do Sandra's overrides capture "why"?** Nick wants exceptions to ask "why
  this way, not that?" Docs (HAI-001) make Sandra's routine overrides carry
  **no** justification ("PIN = auth, not justification"), reserving "why" for
  Nick's invoice deltas + the Socratic loop. `overrides` currently has **no**
  reasoning column (doc-faithful); `exceptions.resolution_reasoning` is optional.

### Wanted but undocumented (hooks built; values/logic TBD)
- **Date/time conflict detection** — columns + index exist; conflict *logic* is
  unwritten (advisory, always overridable — never a hard constraint).
- **Perishability buy-ahead** ("no berries 4 days out") — `menu_items.
  shelf_life_days` / `buy_ahead_max_days` hooks; values from Sandra (Friday).
- **Store best-VALUE ranking** — `stores.value_rank` hook. Contradicts the one
  written store rule (G-02, "cheapest available").
- **Invoice dual-email** to `tazabistro@gmail.com` — not in any doc; Nick's add.

### Deliberate deviations from source specs
- `procedure_link` uses a surrogate PK + nullable `service_mode` (spec's
  composite key can't hold the documented "null = all modes" in a SQL PK).
- Enum casing follows each source verbatim (`task_status` UPPERCASE from its
  canonical DDL; lead/opportunity statuses Title-case from Schema Contract §6).
