# Taza OS Build Plan — Updated July 16, 2026

**From:** Claude Code (field session, Jackson Kitchens)
**To:** Nick Lockard
**Supersedes:** taza-build-plan-july15.md (progress + revised forward plan)

---

## ✅ Completed Wednesday July 16 (CC builds)

All delivered to GitHub `Snicker85022/huh-`, branch
`claude/taza-build-plan-review-f8uxxv`, and validated against a live
PostgreSQL 16 and real Square data.

1. **PostgreSQL schema (v1)** — 33 tables, 63 FKs, `taza_ops` schema. Applies
   cleanly; the `tasks` dependency-release trigger passes a live smoke test.
   Domains: CRM pipeline · communications (`voice_notes` + `customer_communications`
   built 1:1 from Data Schemas v0.5.0) · financial · catalog intelligence ·
   inventory + shopping · production · people + gamification · audit/change-history.
2. **Square invoice/order import pipeline** — invoices → orders (batch) → line
   items → payments, idempotent on `(source_system, external_id)`, payload-hash
   skip, per-invoice failures routed to `exceptions`. Validated end-to-end on
   real invoices (idempotent across repeat runs). systemd timer, 30-min cadence.
   (migration 001)
3. **Square catalog sync** — full catalog cached into `menu_items`, one row per
   `ITEM_VARIATION` **keyed by variation id** (the id order line items
   reference — this is what makes invoice linking work), weekly systemd timer,
   auto-deactivates items removed from the catalog, full `raw_payload` kept.
   Validated. (migration 002)
4. **Hybrid invoice ingestion (decided + built)** — structured line items
   (priced, → `menu_items`) + Order Custom Attributes (typed event facts →
   `orders.custom_attributes`) + catalog attributes + open-item/voice escape
   hatch (~5%) + `raw_payload` safety net on every record.

**Also established:** the GitHub delivery pipeline (write CC → push → N100
`git pull`), after enabling the Claude GitHub App on the repo.

---

## 🔜 Remaining from Wednesday

- **Wix platter-order import pipeline** (step 3) — pull Wix orders/payments →
  PostgreSQL, idempotent, systemd timer. Wix Payments rail (≤10% of revenue).

---

## 📌 Follow-up: per-item intelligence attributes  *(NEW — added 7/16)*

The catalog sync currently preserves every per-item "intelligence" custom
attribute inside `menu_items.raw_payload`, but does **not** yet map them into the
dedicated typed columns. Next job: map the Square **catalog custom-attribute
definitions** into these `menu_items` columns —

| menu_items column | Square catalog custom attribute |
|---|---|
| `serves_min`, `serves_max` | serves min/max |
| `pricing_unit` | pricing unit (per-person / per-tray / each) |
| `dietary_flags` | dietary flags |
| `allergens`, `allergen_notes` | allergen notes |
| `station_type` | station type |
| `hot_hold_max_min`, `cold_hold_max_min` | hot/cold hold maximum minutes |
| `prep_advance_max_hr` | prep-advance maximum hours |
| `quality_risk` | quality risk |
| `default_pan_footprint` | default pan footprint |

**Blocker:** need the exact custom-attribute **definition keys** from the Square
account (7 visible + 5 hidden per Catalog Operations Intelligence). Once
confirmed, this is a small mapping addition to `catalog_sync.py` + a migration.
These deterministic fields are what let the brain pre-draft tightly-structured,
menu-driven invoices (open items → ~5%).

---

## Key decisions / findings locked this session

- **Aoostar = inference host** (supersedes the docs' N100 assumption). N100
  stays orchestrator + DB + NocoDB and is the **hot/live-backup target**.
  Anticipatory sales follow-up to Sandra's phone **promoted to V1.0**.
- **Payer ≠ inquirer** modeled first-class (contacts vs accounts).
- **Change history** via `audit_log` before/after JSONB (no per-table shadowing).
- **Deposit** = 50% of the **initial** quote, locked; later scope changes never
  require more deposit (`deposit_basis_cents`).
- **Two payment rails:** Square (catering invoices) + Wix Payments (platter store).
- **"Why" capture** = optional + deferrable (Socratic loop now or re-asked later).

---

## Pending schema work (migration 003+ / to build)

Round-2 field-session additions, captured, not yet built:
- `learning_prompts` (deferred Socratic "why?" queue → RAG signal)
- Crew (1099 contractors) **skill tags** + **flow-to-work** assignment model +
  **vehicles/vans** resource, for calendar-conflict smart questions
- Safety stock / par levels + critical-shortage alerts
- Van-restock dry-good inventory capture
- Shelf-life learning; store best-VALUE ranking; date/time conflict logic
- Day-of / BOE web page + emergency power-outage QR printouts

---

## Forward schedule

- **Thu 7/17** — Nick structured interview (shopping app, workflows, touchpoints)
- **Fri 7/18** — Sandra deep interview (recipes, allergens, portioning, equipment)
- **Sat 7/18** — Aoostar arrives → provision (Linux, network, `llama-bench`,
  strongest model it supports); begin hot-backup + inference role
- **Next week** — build sprints: Wix import, lead capture/scoring, pre-call
  brief, invoice draft (RAG), + the per-item intelligence mapping and the
  round-2 schema migrations
