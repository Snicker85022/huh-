SPEC LOAD — the record of what was written into the spec database, and from where.
=================================================================================

Each load is one dated .sql file, idempotent (guarded by NOT EXISTS on spec_id), so it can
be inspected, re-run, and version-controlled. The proposals it transcribes are the source;
this directory is the receipt.

2026-10-16  load-2026-10-16.sql
  URS-KANBAN-006  Kanban task lifecycle, canonical close contract, and bus publication
                  P0 / Atomic Requirement / Production Core / required_for_release=YES
                  from factory/team-log/SPEC-PROPOSAL-kanban-task-lifecycle.md
  HW-012          LG webOS TV OLED55B7A (kitchen checklist display)
                  P1 / Atomic Requirement / System Infrastructure / required_for_release=NO
                  from factory/team-log/SPEC-PROPOSAL-lg-tv-hw-012.md

  Status on both: 'Spec Drafted'. Loaded to stop them getting lost, NOT because they are
  final. Nick re-debates them once every app has a good spec, then the seams are reviewed.

  NOT loaded: the checklist-on-LG-TV feature row. Its proposed id (URS-TV-CHECKLIST-001)
  collides with the Android/TV namespace and was rejected during the build; it belongs
  under URS-DISP-007 and must be rewritten against the facts learned 2026-10-15
  (PROD-38, the kanban close contract, the proven SSAP control path).

  Lesson recorded here so it cannot bite again: set is_current = true EXPLICITLY on insert.
  Every pre-existing row is 't'. The spec-export mirror filters `where is_current`, and SQL
  excludes NULL from that — so a row inserted without it is invisible to the CSV. Both rows
  here needed a follow-up UPDATE on the first attempt.
