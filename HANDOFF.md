# HANDOFF — Cortex (DeepSeek) → next session

**Date:** 2026-10-01 (session ran 2026-09-25 through 10-01)

## TL;DR
Master URS review (mURS) for Taza OS. Pass 0 and 0.5 DONE. Pass 1 (per-cluster
prose audit) DONE — findings committed. Next: review findings in batches + apply
real fixes, then Pass 2 (seam audit).

## Files that matter (all in ~/repo on gflip)
- **`master-urs.md`** — THE single source of truth. 287 specs, one file.
  Legacy cluster labels are carried per-spec as `Legacy ID (ID.2)`.
  Cross-references are `[[SPEC:ID]]` pointers. Decisions D1–D25 at top.
- `docs/postgres-spec.md` — living DB spec (D1–D23 decisions, object model,
  MIGRATION-001). Companion to master-urs.md, not merged.
- `urs/pass1-findings.md` — Pass 1 audit output: 35 clusters, 49 real defects,
  220 determinism-class lines.
- `urs/alias-map.tsv` — legacy-label → Spec ID (from Notion ID.2), 283 rows.
- `urs/refs.py` — `check` (dangling pointers) and `render <ID>` (pretty view).
- `notion-export/import/` — archived Notion originals (CSV + cluster markdown).
  Do not edit; provenance only.

## Decisions locked (D1–D25)
Full text at top of master-urs.md. Highlights:
- D4/D5: single store = tazaos PostgreSQL; NocoDB is UI skin only.
- D18: 11 Square catalog attrs (6 visible + 5 hidden), not 12.
- D19: deposit = fixed dollar (deposit_basis_cents).
- D20/D24: spec IDs frozen; rename project CANCELLED.
- D21: W11 folded into PROD-22; changelog = alert queue; audit_log = history.
- D22/D23: AC/VM standard; [AUTO]/[NICK]/[NICK+AUTO] verification tags.
- D25: bonus-card cadence 1–4/high-cadence week, ~1/low-cadence 2-week.

## Just-completed sweeps (this session)
1. NocoDB-as-storage → PostgreSQL across master-urs.md (D4/D5 compliance).
2. W10 → W2 where "lead scoring" was misreferenced; W11 dropped from
   extraction lists (it's a read-only view now, per D21).

## Fusion team
- Runs in ttyd at :7684 (fusion.tazacateringphoenix.com), stack `cheap5`
  (deepseek-v4-pro architect, deepseek-v4-flash Main, glm/cohere/poolside debaters).
- Main slot (v4-flash) gets context-exhausted on large batches. Keep audits to
  ~1 cluster per session, or use the small-group approach.
- Restart: Ctrl+C the TUI process and re-run `just fh-stack ...cheap5.yaml`
  via run-tui.sh. Fresh context per restart.

## Next steps (priority order)
1. Review `urs/pass1-findings.md` with Nick in small batches; apply real fixes.
2. Pass 2: seam audit (two agents map cross-cluster deps independently, diff).
3. Pass 3: interrogation (questions for Nick). Pass 4: debates. Pass 5: synthesis.
4. Pass 6: red team. Pass 7: Nick's human review (defect list first, then URS).

## Backups (verified 2026-10-01)
- gflip `~/repo` → GitHub `Snicker85022/huh-` nightly 08:00 UTC (systemd timer
  `taza-git-push.timer`).
- n100 `taza-git-sync.timer` nightly 02:00 MST mirrors GitHub → USB (`/mnt/taza-git`).
- Chain: gflip → GitHub → USB. PostgreSQL dump refreshed 2026-09-30.

## Gotchas
- `refs.py check` must report 0 dangling pointers after ANY edit to master-urs.md.
- Archived IDs (not dangling): KIT-002/003/004/006/009/011/018/019/021, MT-003,
  TV-008/009/010, URS-CREW-005, URS-LABEL-002, META-001/002, SW-020, INT-002,
  PROD-30..33, PROD-35.
- Notion is FROZEN. Never export back. master-urs.md is the registry.
- GitHub token rotation pending (Nick is handling).
