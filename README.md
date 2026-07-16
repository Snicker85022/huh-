# Taza OS

Catering operations system for **Taza Catering & Events** (Phoenix, AZ).
Runs on a single N100 mini-PC in the Taza kitchen/office (Ubuntu 22.04 LTS
Server, PostgreSQL, Python, systemd). This repository is the source of truth
for the database schema and the data-import pipelines; it is pulled onto the
N100 and deployed there.

## Layout

| Path | Purpose |
|------|---------|
| `db/schema/` | PostgreSQL DDL for the v1 tables (idempotent, ordered by dependency) |
| `db/migrations/` | Incremental schema changes applied after initial build |
| `pipelines/square_import/` | Square invoice/order import → PostgreSQL (Python + systemd timer) |
| `pipelines/wix_import/` | Wix platter-order import → PostgreSQL (Python + systemd timer) |
| `deploy/systemd/` | systemd service + timer units for the pipelines |
| `deploy/env/` | `.env` templates (no secrets committed) |
| `docs/` | Build notes, deployment runbook |

## Governing contract

All schema and automation behavior conforms to **Taza OS — Schema Contract v1**
(canonical, in Notion KB). Key rules carried into this codebase:

- **Idempotency:** every externally-sourced record carries `source_system`,
  `external_id`, `external_updated_at`, and an optional `external_payload_hash`.
  Automations **upsert by `(source_system, external_id)`** — never blind-insert.
- **Customer Event is the primary entity.** All operational records relate to
  exactly one Customer Event (`opportunities`), one Production Batch, or Intake.
- **Automations may not alter schema or invent statuses.** Ambiguous inbound
  data is quarantined for human review, never guessed.

## Deployment target

- Host: N100 mini-PC (`taza-server`), Ubuntu 22.04 LTS Server
- DB: PostgreSQL, schema `taza_ops`
- Network: Ethernet, ER605 DHCP reservation
- Scheduling: systemd timers (not cron)

## Build status (week of July 15–19, 2026)

- [x] **Wed 7/16** — PostgreSQL schema build (33 tables, validated on PG16)
- [x] **Wed 7/16** — Square invoice/order import pipeline (validated on real data)
- [x] **Wed 7/16** — Square catalog sync → menu_items (variation-keyed, weekly; validated)
- [ ] **Wed 7/16** — Wix order import pipeline
- [ ] Thu 7/17 — Nick structured interview (shopping app, workflows)
- [ ] Fri 7/18 — Sandra recipe/allergen deep interview
- [ ] Sat 7/19 — new mini-PC provisioning
