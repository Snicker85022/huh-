<!--
PASTE-READY NOTION REPORT
Suggested Notion page title:  Build Log — July 16, 2026 (Schema + Square Import + Catalog Sync)
Suggested icon: 🛠️   |   Suggested parent: Taza Catering & Events — Operating System (Canonical)
Copy everything BELOW this comment block into the Notion page body.
-->

_CC field session at Jackson Kitchens. All code delivered to GitHub `Snicker85022/huh-`, branch `claude/taza-build-plan-review-f8uxxv`; validated on live PostgreSQL 16 + real Square data. Full plan: `taza-build-plan-july16.md` (Google Drive) + `docs/build-plan-2026-07-16.md` (repo)._

## ✅ Shipped Wednesday July 16

1. **PostgreSQL schema v1** — 33 tables, 63 FKs, `taza_ops`. Applies cleanly on PG16; the `tasks` dependency-release trigger passes a live smoke test. `voice_notes` + `customer_communications` built 1:1 from Data Schemas v0.5.0.
2. **Square invoice/order import pipeline** — invoices → orders (batch) → line items → payments; idempotent on `(source_system, external_id)`; payload-hash skip; per-invoice failures → `exceptions`. Validated end-to-end on real invoices, idempotent across repeat runs. systemd timer (30 min). *(migration 001)*
3. **Square catalog sync** — full catalog → `menu_items`, one row per `ITEM_VARIATION` **keyed by variation id** (the id order line items reference — this makes invoice linking work). Weekly timer; auto-deactivates removed items; `raw_payload` kept. Validated. *(migration 002)*
4. **Hybrid invoice ingestion** — structured line items (priced → `menu_items`) + Order Custom Attributes (typed event facts → `orders.custom_attributes`) + catalog attributes + open-item/voice escape hatch (~5%) + `raw_payload` safety net.

Also: GitHub delivery pipeline established (write CC → push → N100 `git pull`) after enabling the Claude GitHub App on the repo.

## 📌 NEW follow-up — per-item intelligence attributes

The catalog sync preserves per-item intelligence custom attributes in `menu_items.raw_payload` but does **not** yet map them to dedicated typed columns. Next job: map the Square catalog custom-attribute definitions →

| menu_items column | source attribute |
| --- | --- |
| `serves_min`, `serves_max` | serves min/max |
| `pricing_unit` | pricing unit (per-person / per-tray / each) |
| `dietary_flags` | dietary flags |
| `allergens`, `allergen_notes` | allergen notes |
| `station_type` | station type |
| `hot_hold_max_min`, `cold_hold_max_min` | hot/cold hold max minutes |
| `prep_advance_max_hr` | prep-advance max hours |
| `quality_risk` | quality risk |
| `default_pan_footprint` | default pan footprint |

**Blocker:** need the exact custom-attribute **definition keys** from Square (7 visible + 5 hidden per Catalog Operations Intelligence). Then it's a small `catalog_sync.py` mapping + migration. These deterministic fields are what let the brain pre-draft tightly-structured, menu-driven invoices (open items → ~5%).

## Decisions locked this session

- **Aoostar = inference host** (supersedes docs). N100 stays orchestrator + DB + NocoDB and is the **hot/live-backup target**. Anticipatory sales follow-up to Sandra's phone **promoted to V1.0**.
- **Payer ≠ inquirer** modeled first-class (`contacts` vs `accounts`).
- **Change history** via `audit_log` before/after JSONB.
- **Deposit** = 50% of the **initial** quote, locked (`deposit_basis_cents`); later changes never require more deposit.
- **Two payment rails:** Square (catering invoices) + Wix Payments (platter store, ≤10%).
- **"Why" capture** = optional + deferrable (Socratic loop now or re-asked later).

## Remaining / next

- **Wix platter-order import pipeline** (last Wednesday dispatch).
- **Round-2 schema** (migration 003+): `learning_prompts`; crew skill-tags + flow-to-work + vehicles/vans for calendar-conflict questions; safety stock + shortage alerts; van-restock capture; shelf-life learning; store best-VALUE ranking; date/time conflict logic; day-of/BOE page + power-outage QR printouts.
- **Thu** Nick interview · **Fri** Sandra deep-dive · **Sat** Aoostar provisioning.
