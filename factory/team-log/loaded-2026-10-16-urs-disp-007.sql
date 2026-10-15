-- ══════════════════════════════════════════════════════════════════════════════
-- HISTORICAL RECORD — this is a RECEIPT, not a tool.
--
-- *** DO NOT RUN THIS FILE. ***
-- The row below is ALREADY in the database. This file records what was written
-- on 2026-10-16, and from which proposal.
--
-- The spec database is the SOLE SOURCE OF TRUTH:
--     n100:5432  database `spec`  schema `spec`
--     spec.taza_os_user_requirement_specifications
-- To learn what a spec says, QUERY THE DATABASE. Never read a .sql file for spec
-- content: it is a copy of a moment and it is already stale.
--
-- The row this recorded:
--   URS-DISP-007    LG webOS TV presents live checklist
--                   P1 / Atomic Requirement / Event Execution / required_for_release=NO
--                   source: SPEC-PROPOSAL-checklist-on-lg-tv.md (aligned 2026-10-16)
--
-- Sits in the URS-DISP per-display fleet: URS-DISP-001 is its parent ("each display
-- has one canonical primary role"), and URS-DISP-003/004/005 are its siblings
-- ("TCL East presents situational awareness by mode", etc.).
--
-- Consumes HW-012 (the device, loaded 2026-10-16) and URS-KANBAN-006 (item completion).
-- This row did NOT exist before today; the earlier draft named URS-TV-CHECKLIST-001,
-- which was rejected because TV-* is the legacy Android/ADB namespace.
--
-- status = 'Spec Drafted': loaded so it could not get lost, NOT because it is final.
-- Nick re-debates it once each app has a good spec, then reviews the seams.
--
-- is_current is set EXPLICITLY to true: every other row is 't' and the spec-export
-- mirror filters `where is_current`, which SQL excludes NULL from.
-- ══════════════════════════════════════════════════════════════════════════════

BEGIN;

INSERT INTO spec.taza_os_user_requirement_specifications (
  spec_id, name, status, priority, release, record_type, domain,
  determinism_class, required_for_release, is_current,
  user_requirement, functional_requirement,
  ac_normal, ac_edge, ac_negative, ac_silent_failure, ac_challenge, ac_block,
  verification_methods, vm_count, vm_auto_count, vm_nick_count,
  failure_behavior, dependency_notes, open_questions,
  consumes, consumed_by,
  atomic_requirement, intent_user_need, inputs, outputs,
  trigger_condition, invariants, out_of_scope, maintenance_requirements,
  external_dependencies, rationale, failure_mode_addressed, source
)
SELECT
  'URS-DISP-007',
  'LG webOS TV presents live checklist',
  'Spec Drafted', 'P1', 'V1.0', 'Atomic Requirement', 'Event Execution',
  'D', 'NO', true,

  'Need: the same checklist that prints on paper is also shown on the LG webOS TV in the kitchen, updating live as item statuses change (within 2.5s), so the crew can read the current gig''s tasks at a glance without touching anything.',

  E'The LG webOS TV (see [[SPEC:HW-012]] for the device and its proven control surface: SSAP over WebSocket :3000, com.webos.app.browser, paired client-key on n100) runs that browser in a locked kiosk pointed at a checklist page served by n100. The page renders the current checklist(s) from the intercom (order.captured, the same topic checklist_app.py consumes - product/n100/checklist-app/checklist_app.py:48-49). Task lines show VERB + ITEM (e.g. "PACK - chafers"), never a bare count, matching the paper task block''s "%-8s %s" verb+item rendering (checklist_app.py:143). The set covers all gigs in [today, today+4d] (CHECKLIST_WINDOW_DAYS=4, checklist_app.py:25,160). With 2+ active gigs the page cycles every 15s PER GIG. n100 PUSHES status changes to the page (WebSocket per [[SPEC:INFRA-009]]); 2.5s polling is the fallback only, and the 10s watchdog of INFRA-009 is accepted on degradation. The page shows "last updated <time>" at all times; when stale it shows a banner naming the cause. The red/pink pulse is DEFERRED: it needs a started signal which has no source anywhere today (hand->table is client-side only), so it cannot fire until that exists. A cancelled invoice (intercom invoice.canceled) ntfy''s Nick asking whether to cancel - never auto-cancel. A fully-completed checklist is archived and not shown the next day. Alerts go to ntfy "taza-ops", http://192.168.2.102:9000, and the TV. Re-launching com.webos.app.browser is the heal; turnOnScreen is NOT a dependency (returns 401). Paper + kanban remain the safety net. OCR/vision attaches later at a named seam and must not break this view.',

  E'1. TV shows the same checklist content as paper: task lines VERB + ITEM (e.g. "PACK - chafers"), never a bare count.\n2. A status change published on the intercom is reflected on the TV within 2.5s, with no human action.\n3. "last updated <time>" is visible and updates on every push.\n4. With 2+ active gigs, the page cycles between them every 15s, covering every gig in [today, today+4d].',

  E'5. A multi-day order / two gigs on one day: the set covers every service day in the 0-4 day window (same window as checklist_app.py DAYS=4), and the cycle includes each day.\n6. A status change arriving mid-render does not produce a torn/partial frame.\n7. Ethernet down -> wifi up: the page keeps updating and an alert fires on all three surfaces (ntfy + health page + TV).\n8. 0% and 100% progress extremes render correctly.',

  E'9. invoice.canceled never auto-cancels: it ntfy''s Nick asking whether to cancel, and the checklist stays until Nick decides.\n10. A completed checklist does not appear the next day; it is archived for troubleshooting.\n11. A failed/rejected event does not render as if committed - the display shows committed state only.',

  E'Detected by [[SPEC:URS-HEALTH-005]] (Stale or missing health data fails visibly) plus the page''s own stale banner.\n12. Push stalled but the page still renders a plausible stale checklist: the stale banner names the cause. (The pulse cannot fire yet - see the deferred-pulse note.)\n13. Browser running but on the wrong/old URL (crashed to home): the watchdog detects via getForegroundAppInfo and re-launches to the checklist URL - no turnOnScreen.\n14. Wifi fallback active silently: the network-source alert actually fires on all three surfaces (not merely configured).',

  '',

  '',

  E'1) [AUTO] Latency test: publish a status change, confirm TV reflects <=2.5s.\n2) [AUTO] Cycle test: seed 2+ active gigs, confirm the 15s-per-gig cycle covers each over a 30s observation window.\n3) [AUTO] Staleness test: stall push, confirm "last updated <time>" + banner naming the cause; the pulse is deferred so no pulse is expected yet.\n4) [AUTO] Cancellation test: publish invoice.canceled, confirm ntfy fired and the checklist was NOT auto-cancelled.\n5) [AUTO] Network test: drop Ethernet to force wifi, confirm the alert fires on ntfy + health page + TV.\n6) [AUTO] Archive test: complete a checklist, advance one day, confirm it is absent from the TV and present in the archive.\n7) [NICK] Nick observes the LG TV during a real service day: checklist readable, reflects kanban status changes within 2.5s, no touch/remote needed.',

  7, 6, 1,

  E'- TV/browser off or crashed: watchdog detects via getForegroundAppInfo and re-launches com.webos.app.browser to the checklist URL (proven heal). No turnOnScreen call.\n- Push/bus stalled: the page shows "last updated <time>" and the stale banner naming the cause. The pulse is deferred (no started signal exists).\n- Ethernet down -> wifi: the page keeps updating and an alert fires (ntfy + health page + TV), because wifi is fallback-only.\n- Everything fails: paper checklist + Mom''s kanban remain authoritative. The TV is additive, never the only path.',

  E'- Device and control surface: [[SPEC:HW-012]] (loaded 2026-10-16). This row consumes it and does not re-describe the hardware.\n- Content source: [[SPEC:PROD-20]] topic `order.captured` (LIVE - 34 events in system_events; consumed by product/n100/checklist-app/checklist_app.py:48-49).\n- Cancellation source: [[SPEC:PROD-20]] topic `invoice.canceled` (LIVE - 1 event).\n- Status feed: [[SPEC:URS-KANBAN-006]] (Kanban task lifecycle, canonical close contract, and bus publication; Spec Drafted 2026-10-16) implements PROD-38''s TaskCloseEvent and proposes the topic `task.closed`. Item COMPLETION therefore has a source; it is not live yet because URS-KANBAN-006 is written but not built. Still absent everywhere: a `started` signal (hand->table is client-side only).\n- Push: [[SPEC:INFRA-009]] (Shared push/pull hybrid client library). Its watchdog is 10s; this spec needs 2.5s while push is healthy and accepts 10s on degradation - do not loosen the fleet watchdog for this one screen.\n- Alerts: [[SPEC:PROD-25]] (Unified Notifier -> ntfy "taza-ops"), health page http://192.168.2.102:9000.\n- Staleness pattern: [[SPEC:URS-HEALTH-005]] - the same check SSB-001 names.\n- Content semantics reused: [[SPEC:SSB-001]] (progress view), [[SPEC:SSB-002]] (glanceability), [[SPEC:SSB-003]] (completed persistence), [[SPEC:SSB-005]] (partial completion) - written for the TCL/Android dashboards; this spec is their webOS delivery.\n- Fleet slot: [[SPEC:URS-DISP-001]] (canonical role = live checklist), [[SPEC:URS-DISP-PKG]] (fleet architecture).\n- OCR placeholder: [[SPEC:PROD-37]] (voice/camera close) - MT1/MT2. Attach at the push/render seam; the bootstrap must not require it.',

  E'DECIDED by Nick 2026-10-15/16:\n  Q1. Priority = P1, required_for_release = NO. The TV is additive; paper and kanban remain the safety net.\n  Q2. SHIP NOW. Build the view against what exists; items render as not-yet-complete until URS-KANBAN-006 is built and emitting. Do not hold this spec.\n  Q3. 2.5s while push is healthy; accept the 10s polling fallback on degradation.\n  Q5. Pulse DEFERRED. It needs a `started` signal, which has no source anywhere. Show the "last updated" timestamp only.\n  Q6. 15 seconds PER GIG (two gigs take 30s to cycle fully), and only for gigs currently active. service_date is present in the order.captured payload, so the window [today, today+4d] is computable.\n  Q7. PORT 9004, and a DEDICATED process for this page (verified free 2026-10-15: 9000/9001/9003 are in use). Not an endpoint bolted onto dashboard.py.\n\nSTILL OPEN:\n  Q4. Content form is a static n100-served page in com.webos.app.browser (proven to launch), not a PWA [[SPEC:TV-012]]. Confirm this reading.\n  Q8. Who owns the page process on n100, and does it join the display fleet deploy pattern? Also: does the "gig is complete" computation (all cards done) live here or belong to URS-KANBAN-006? URS-KANBAN-006 DEF-9 records it as currently unowned.\n  Q9. "Started" has no source. Add a hand->table emit to URS-KANBAN-006 as its own gap so the pulse can eventually be implemented?',

  '[[SPEC:HW-012]] the device and its proven control surface (SSAP :3000 launch + foreground heal); [[SPEC:PROD-20]] `order.captured` (content) and `invoice.canceled` (cancellation); [[SPEC:URS-KANBAN-006]] for item completion (not yet built, so completion is not yet live); [[SPEC:URS-KANBAN-005]] and [[SPEC:PROD-38]] for the close contract it depends on.',
  'None - leaf display. Alerts fan out via [[SPEC:PROD-25]] (ntfy) and the health page.',

  'The LG webOS TV in the kitchen presents the current production checklist, rendered from intercom data, reflecting any status change within 2.5 seconds, with a visible "last updated" time and a cause-naming stale banner, and never showing a completed checklist on the following day.',
  'The crew needs to read the current gig''s tasks at a glance, without walking to the printer or touching a device.',
  'Intercom events: order.captured (content), invoice.canceled (cancellation), and item completion from URS-KANBAN-006 once built.',
  'A rendered HTML page on the LG TV (port 9004 on n100), pushed over WebSocket with a 2.5s polling fallback; alerts to ntfy, the health page, and the TV.',
  'The page is served on n100 and launched on the TV via SSAP; it re-renders on each pushed change.',
  'Ethernet is primary and a wifi fallback is always visible; the TV is additive and never the only path; no crew touch or remote input is required; the OCR/vision seam must not break the view if absent.',
  'Other TVs in the fleet (each has its own purpose); vision/OCR camera input; touch or remote input; game points; auto-cancelling on invoice.canceled.',
  'The page process on n100 must survive the TV and n100 restarting; the SSAP launcher and watchdog heal a dead or displaced browser.',
  'The SSAP service on the TV (see HW-012); n100 reachability to the TV; the intercom topics it consumes; the push fabric [[SPEC:INFRA-009]].',
  'The paper checklist is the single point of truth but exists only on paper. A dedicated, live display lets the same information be read at a glance without crew effort, and it is the first display off the Android/ADB fleet path.',
  'A crew member acting on a stale or wrong checklist because the screen looked authoritative; and a screen that silently stops updating.',
  'Nick 2026-10-16 (from the fusion team proposal SPEC-PROPOSAL-checklist-on-lg-tv.md)'
WHERE NOT EXISTS (
  SELECT 1 FROM spec.taza_os_user_requirement_specifications WHERE spec_id = 'URS-DISP-007'
);

COMMIT;
