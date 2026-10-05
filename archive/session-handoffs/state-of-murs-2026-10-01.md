# State of the mURS + NocoDB — 2026-10-01

One page. The relational database is now the source of truth; markdown is on its
way to being a rendered view.

## Where the data lives (PostgreSQL, `tazaos`, schema `public`)

| table | rows | what it is |
|---|---|---|
| `murs_specs` | **291** | ONE row per fully-defined spec. The stack. |
| `decisions_log` | **37** | append-only branch/decision log (D1–D28 + D29 + D30). |
| `master_urs` | 290 | the old markdown-derived registry (still the linked view). |
| `seam_stamps` | 337 | seam edges (consumes/consumed_by source). |

Two-way: NocoDB's Taza OS base reads/writes `public.*` directly — edits in NocoDB
land in Postgres; nothing needs syncing.

## What's in `murs_specs` (one row per spec)

- Identity: `spec_id, name, legacy_id, status, priority, release, record_type, domain, determinism_class, required_for_release`
- Prose: `user_requirement, functional_requirement, failure_behavior, dependency_notes, open_questions`
- AC as columns: `ac_normal, ac_edge, ac_negative, ac_silent_failure, ac_challenge`
- VM: `verification_methods, vm_count, vm_auto_count, vm_nick_count`
- Seams: `consumes, consumed_by, seam_count`
- Rules: `rules, rule_count`
- Versioning: `branch_id, version_id, is_current`
- Formal mirrors (blank, to fill): `ac_formal, vm_formal, functional_formal, failure_formal`
- Hardware (blank for non-HW): `hw_make, hw_model, hw_mpn, hw_cost_cents, hw_camera_mp, hw_ram_gb, hw_storage_gb, hw_chipset, hw_connectivity, hw_purchase_date, hw_purchase_source`

## Versioning model (deterministic, not hand-editable)

- `branch_id` = formulaic from the decision log (`D29.A`).
- `version_id` = `sha256(spec content + branch_id)[:16]` — a content hash; hand-editing
  a cell breaks the hash and the linter flags it.
- `is_current` = the filter that gives "one row per spec" while keeping history.
- `target_release` lives on branches; a spec's `release` derives from its branch
  once every spec is tagged.

## Decisions recorded

- D1–D28 from the old registry (D20 is missing in the source).
- **D29 — Off-premises internet failover** (S7/O1/D1, RPN 7): active = Moto G Pure 4G
  on ER605 WAN2; deferred = pre-caching/hardening (V1.x), proper secondary ISP (V2.0).
- **D30 — Moto G camera line observation + local AI** (deferred, V1.x, parent D29.A):
  13MP camera, 3GB RAM stripped, 4000K prep lighting → golden exemplars, bad-item
  examples, technique GIFs, time-and-motion studies.
- New spec **HW-011** (the phone) born directly in the DB — first spec not in markdown.

## NocoDB status

- `master_urs` view: current (290 specs, markdown-derived).
- `murs_specs` + `decisions_log`: **loaded in Postgres but not yet added to the base.**
  Claude in Chrome can't see them until they're added.

## To make them appear in NocoDB (one-time, 2 clicks)

Taza OS base → **Add New Table** → pick **`murs_specs`** and **`decisions_log`**
(optionally `seam_stamps`). After that they are live and two-way.

## Pending work

1. Tag every spec with its `branch_id` (unlocks release derivation + version history).
2. Fill the formal-mirror columns (`ac_formal`, `vm_formal`, `functional_formal`, `failure_formal`).
3. Backfill hardware columns for HW-001..010.
4. Resolve D20 (missing decision number).
5. Parallel AI team: Worker A specs, B branches, C rules, D FSMs, E seam edges
   (see `docs/murs-formalization-standard.md`).
