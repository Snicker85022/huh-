# RAG Operations Content — Notion → PostgreSQL transfer

**Date:** 2026-09-30 | **Operator:** Cortex | **Source:** Notion DB "📖 RAG — Operations Content" (202 records)
**Target:** tazaos.rag_operations_content on n100.

## Decision: dedicated table

The advisory said "prefer existing schema if it fits, else a dedicated table is fine."
Existing KB-shaped tables in tazaos were checked first:
- `cooking_rules` (9 cols: rule_type, title, description, applies_to, priority,
  is_active, timestamps) — 0 rows. Shape is too narrow: no Content/Metadata/status/type.
- The game-design `kb_*` schema (kb_rules, kb_perishability_rules, kb_dishes,
  kb_task_templates, kb_batching_rules) exists only in `08-backend-schema.sql` on
  disk — NOT in the live DB. It is a downstream consumer design, not a landing zone.

None fit. The Notion records carry 18 fields (title, type, status, domains, content,
page-body text, metadata JSON, embedding text, relationships, tags, locked-by,
SOP comic link, parent/child relations, timestamps, URL). A lossless transfer needs
a table that mirrors the source 1:1. Created `rag_operations_content` (public schema).

This is a LANDING table — faithful, lossless, traceable. Downstream fan-out (into
kb_* game-design tables, cooking_rules, BOM tables) is a later deterministic step,
not part of this transfer.

## Coverage

- Fetched 201 records (202 minus the junk `ZZZ_DELETE_ME_TEST`).
- Content property text: 190 records. Page-body-only text: 11 records (e.g. Ribeye
  Steak Seared Then Sliced, Sea Bass Butter Lemon Caper, Bechamel GF, the two RULE
  records, F-24). Both fetched, so 0 records with no text at all.
- Status preserved: locked / draft / pending_approval / superseded.
- Every row carries notion_page_id (traceable) + notion_url.
- Metadata kept both as raw text AND best-effort jsonb (parse failures stored under
  `{"_raw": "..."}`).

## Breakdown

- Types: recipe 98, procedure 42, flag 24, rule 23, logistic 8, staffing_model 4, equipment 2.
- Status: locked 117, pending_approval 41, draft 39, superseded 4.
- Locked by: Nick 112, Sandra 56, Claude 1, none 32.

## Sandra's backlog (the "ask her" list)

The 24 flag records ARE the interview agenda — see table for full list. Highlights:
- F-23: locked recipe conflicts vs Sandra's recipe doc (HIGH)
- F-19: all sauce/dressing/base ratios (HIGH — blocks locking many drafts)
- F-03 short ribs braise, F-01 CLMC garlic, F-09 chicken skewer cut/marinade, F-13 buffet staffing, F-21 commissary address (all HIGH)
- F-22: ~28 draft menu items need method/temp/portion specs

Also: 39 draft + 41 pending_approval records still need Sandra/Nick sign-off before
downstream use can trust them as much as locked records.

## Overlap with existing knowledge

- `game-design/02-taza-rules.md` + `08-backend-schema.sql` seed 3 dishes (salmon,
  short ribs, greek salad) and ~11 technique rules. The Notion transfer covers far
  more (98 recipes) — the game-design seed is a subset. No conflict; the Notion data
  is the superset and is now the source of truth for retrieval.
- Portion notes Nick sent recently (hummus 2.2oz, rice 2c=5pp, etc.) are all
  present in the transfer (Chicken Skewers 1.3oz, Meat Kofta, Rice, Hummus, NY Steak
  skewers, Passed Apps, Aioli, TazaCo, Greek Salad, Pear Chop, Broccoli/Asparagus,
  Yogurt Parfait, Medi Grill platter, Prime Rib temping). All 15 covered.

## Open items for Nick

1. **Embeddings**: pgvector is NOT installed. Landing clean text was per the advisory.
   If retrieval-quality embeddings are wanted, install `vector` + add an embedding
   column as a separate step.
2. **Status gating**: recommend downstream consumers trust `locked` only until
   Sandra clears the 41 pending_approval + 39 draft.
3. **F-23 + F-19 first**: resolve before BOM/shopping use, since they gate ratios.
