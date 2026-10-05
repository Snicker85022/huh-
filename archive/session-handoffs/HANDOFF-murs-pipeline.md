# HANDOFF — finish the mURS table (2026-10-02)

Source of truth is a RELATIONAL DATABASE. Not markdown. Not prose. The database.

## 1. Where everything lives

- **Server:** n100 = 192.168.2.102 (ssh `taza@192.168.2.102`)
- **Database:** PostgreSQL `tazaos`, schema `public`, user `taza`
- **UI:** pgweb — `https://nocodb.tazacateringphoenix.com` (zero-login, port 8080, container `pgweb`)
- **NocoDB:** STOPPED. Do not use. Do not resurrect.
- **Legacy input:** `master-urs.md` (markdown). It is READ-ONLY source for extraction. The DB is the store. Edits go to the DB, never back to markdown.
- **Working copies:** `urs/tables/*.tsv` + `export/*.csv`

## 2. Tables (exact columns)

### public.murs_specs — ONE row per spec (291 rows)
```
spec_id | name | legacy_id | status | priority | release | record_type | domain
| determinism_class | required_for_release | notion_url
| user_requirement | functional_requirement | failure_behavior | dependency_notes | open_questions
| ac_normal | ac_edge | ac_negative | ac_silent_failure | ac_challenge | ac_block
| verification_methods | vm_count | vm_auto_count | vm_nick_count
| consumes | consumed_by | seam_count | rules | rule_count | source
| branch_id | version_id | is_current
| ac_formal | vm_formal | functional_formal | failure_formal
| hw_make | hw_model | hw_mpn | hw_cost_cents | hw_camera_mp | hw_ram_gb | hw_storage_gb
| hw_chipset | hw_connectivity | hw_purchase_date | hw_purchase_source
| decision_ids | updated_at
```

### public.decisions_log — ONE row per branch/decision (37 rows)
```
decision_id | branch_id | branch_title | branch_status | severity | occurrence | detection | rpn
| target_release | dev_hours_initial_est | elapsed_focus_hours | elapsed_wallclock_hours
| elapsed_hours | dev_hours_remaining | maintenance_hours_month | recovery_rebuild_hours
| capex_cents | opex_cents_month | trigger_predicate | pivot_penalty_hours
| formal_logic_spec | rationale_prose | rationale_formal | parent_branch_id
| milestone_reached | milestone_reached_at | source | created_at | updated_at
```

## 3. Blank columns — the work to finish

| column | state |
|---|---|
| `determinism_class` | 291/291 blank |
| `ac_formal` `vm_formal` `functional_formal` `failure_formal` | 291/291 blank |
| `branch_id` / `decision_ids` | 26/291 tagged |
| hardware columns | HW-011 only; HW-001..010 blank |
| `release` | hand-typed; to become DERIVED from branch `target_release` |

## 4. Hard rules (Nick's, non-negotiable)

1. One row = one spec. Never one row per AC/VM/seam.
2. Prose column + formal mirror column in the same row. Prose is authoritative; formal is AI-proposed, Nick-approved.
3. Numeric, never ordinal (no low/med/high). Unmeasurable → boolean or free-text note.
4. Append-only. `version_id = sha256(spec_id + branch_id + canonical formal fields)[:16]`. A hand-edit breaks the hash and the linter flags it.
5. IDs are formulaic, machine-generated, never hand-typed: `branch_id = <decision_id>.<alt>` (D29.A); spec IDs frozen (D24).
6. Never invent a table or column. Un-groundable → `NEEDS-SCHEMA: <exactly what's missing>`.
7. Every output row carries `source`.
8. Merge key = `spec_id`. No overwrites. Conflict → `urs/tables/conflicts.tsv`.
9. Formal logic references ONLY real fields: `docs/schema-stub.md` columns, `domain_rules` entities, or the spec's own named columns. Nothing else.

## 5. The pipeline — one role-selected AI per stage

Each stage is a SEPARATE agent with a fixed I/O contract. Output is TSV keyed by spec_id. No stage edits another stage's columns.

| # | Stage | Input | Output column(s) | Model tier |
|---|---|---|---|---|
| 0 | Extract | master-urs.md | all prose columns | deterministic script (`tools/murs-specs.py`) |
| 1 | Determinism class | functional_requirement + ac_* | `determinism_class` ∈ {D,KG,EXT,EXT-EMAIL,HUM,INF} | cheap |
| 2 | Branch tag | decision bodies in decisions.tsv | `decision_ids`, `branch_id` | deterministic script |
| 3 | AC formalize | ac_normal..challenge + schema-stub | `ac_formal` (FOL predicates) | frontier |
| 4 | VM formalize | verification_methods + schema-stub | `vm_formal` (test/query/assert per VM) | frontier |
| 5 | Functional formalize | functional_requirement | `functional_formal` (contract/state-machine/invariants) | frontier |
| 6 | Failure formalize | failure_behavior + SILENT-FAILURE | `failure_formal` (guard + monitor) | frontier |
| 7 | Hardware backfill | HW-001..010 prose | hw_* columns | cheap |
| 8 | Validate | all tables | refs=0, version_id match, no blank determinism | deterministic script |
| 9 | Render (optional) | DB | markdown view generated FROM DB | deterministic script |

### Stage contracts (exact)

- **Stage 1 output:** `determinism.tsv` → `spec_id | determinism_class`. Rules:
  - D = AC asserts exact outputs for given inputs (arithmetic, counts, thresholds)
  - KG = graph/entity resolution
  - EXT = external dependency + fallback
  - HUM = human decision gate
  - INF = AI inference (no-fabrication)
- **Stage 2 output:** `branch-tags.tsv` → `spec_id | decision_ids | branch_id`. branch_id = highest-numbered decision mentioning the spec. Derive decision→spec mapping from decision bodies.
- **Stages 3-6 output:** `formal-*.tsv` → `spec_id | <col>`. One predicate per AC class. Ground in schema-stub columns; else NEEDS-SCHEMA.
- **Stage 8 validation commands:**
  - `python3 urs/refs.py check` → 0 problems
  - recompute version_id for every spec; fail on mismatch
  - `SELECT count(*) FROM murs_specs WHERE determinism_class = ''` → 0 after stage 1
  - `SELECT count(*) FROM murs_specs WHERE branch_id = ''` → 0 after stage 2

## 6. Model routing

- **cheap** = mechanical extraction / rule-based: stages 1, 2, 7.
- **frontier** = judgment + formal logic: stages 3, 4, 5, 6.
- Nick is the only estimator (hours/cents) and the only approver of formal mirrors.

## 7. Open items

- D20 missing from the decision list.
- 265 specs untagged.
- `release` derivation from branch `target_release` not yet wired.
- NocoDB was the failure surface; it is stopped. pgweb is the UI.

## 8. Tools (deterministic, re-runnable)

- `tools/murs-specs.py` — builds murs_specs.tsv + decisions_log.tsv
- `tools/murs-to-tables.py` — markdown → per-entity tables
- `tools/seam-graph.py` — seam edges + linter
- `tools/type-evidence.py` — evidence typing
- `tools/nocodb-register-table.py` — re-register a public table in NocoDB (legacy; NocoDB stopped)
- `urs/refs.py` — spec reference resolver (check must be 0)
