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

### Contradictions — RESOLVED at the 7/16 field session (round 2)
- **Inference host → the AOOSTAR** (Nick, superseding the docs). The N100 is too
  weak for same-day inference; the Aoostar (→ 64GB RAM planned) is now the
  inference host, dev box, and Nick's personal AI-memory partner. The N100 stays
  the orchestrator + DB + NocoDB, and is the **hot-backup target**. The
  "anticipatory follow-up to Sandra's phone" is **promoted to V1.0**. Schema is
  host-agnostic; only the pipelines/timers target a host.
- **"Why" capture → optional + deferrable.** A real-time Socratic "why?" is
  ideal but never required; if the crew is busy, the system re-asks later ("for
  that event you did X — why?") to learn. `overrides` stays justification-free
  (HAI-001) for the real-time tap; the deferred teaching loop needs a new
  `learning_prompts` queue (see round-2 additions).

### Round-2 additions (implement as `db/migrations/001_*`)
Captured from the 7/16 field session; not yet in the base DDL:
- **`learning_prompts`** — deferred Socratic queue: a pending "why did you do X?"
  question tied to any record, answered later, answer stored as a RAG signal.
- **Crew + resources for conflict inference** — crew attributes (on-call,
  speed-dial, FOH-experienced, role) and a **vehicles/vans** resource with
  commitment tracking, so the AI can watch the `hello@` Google Calendar and ask
  smart questions ("both vans committed — delivery fallback?"; "who runs FOH on
  the small event?") then record answers for learning.
- **Safety stock / par levels** — per-item target the system aligns to and
  alerts on (critical-shortage prompts); values set by asking the crew.
- **Van restock capture** — the "clean & restock vans" kanban card prompts for
  dry-good inventory, stored for later Last-Known-Location lookups.
- **Shelf-life learning** — `menu_items.shelf_life_days`/`buy_ahead_max_days`
  become learned, not just static.
- **Deposit basis** — deposit = 50% of the INITIAL quoted amount, locked; later
  headcount/scope changes do NOT require additional deposit. Add
  `invoices.deposit_basis_cents` to make the basis explicit.
- **Output surfaces** — day-of / BOE web page and emergency power-outage QR
  printouts render from existing opportunity/task data (no new core tables).

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
