SPEC PROPOSAL: URS-DISP-007 — LG webOS TV presents live checklist
================================================================================

Proposed: 2026-10-15 / deep (ARCHITECT — spec_id, dependencies, integration)
Supersedes: the earlier draft in this file (flash). The content, failure and
out-of-scope sections were largely sound; the spec_id, the invented status
topic, and the non-house AC format are corrected here.
Purpose:  PROPOSE ONLY. Nothing written to any database.

================================================================================
SPEC-ID DECISION
================================================================================

spec_id: URS-DISP-007

Why (evidence, all verified against the LIVE spec table):
  - URS-DISP is the established per-display series. URS-DISP-003 "TCL East
    presents situational awareness by mode", URS-DISP-004 "TCL West presents
    prep execution by mode", URS-DISP-005 "Van Scoreboard exposes loadout
    readiness by mode". This LG TV is a new display in that same fleet, and
    URS-DISP-001 "Each display has one canonical primary role" is its parent.
  - URS-DISP-006 is the highest DISP id; 007 is free (verified: no row exists).
  - There is NO `URS-TV-*` area in the live table (areas are CALL, CREW, CRM,
    DISP, EVENT, HEALTH, INV, KANBAN, KIT, LABEL, LKL, MOB, PLAN). "TV-xxx"
    (TV-005/007/011/012) is a legacy mURS namespace, not the URS-{AREA}-{SEQ}
    pattern new atomic requirements use.
  - URS-TV-CHECKLIST-001 invents a new area AND a non-atomic suffix; it would
    sit outside the fleet architecture (URS-DISP-PKG) this display belongs to.

================================================================================
FULL ROW
================================================================================

spec_id:              URS-DISP-007
name:                 LG webOS TV presents live checklist

record_type:          Atomic Requirement
domain:               Event Execution
determinism_class:    D
required_for_release: NO          (additive; paper + kanban stay the safety net)
priority:             P1          (see Q1)
release:              V1.0
status:               Spec Drafted

----------------------------------------------------------------------
user_requirement:
Need: the same checklist that prints on paper is also shown on the LG webOS TV
in the kitchen, updating live as item statuses change (within 2.5s), so the
crew can read the current gig's tasks at a glance without touching anything.

----------------------------------------------------------------------
functional_requirement:
The LG webOS TV (OLED55B7A, wired 192.168.2.127 primary / wifi .137 fallback)
runs com.webos.app.browser in locked kiosk pointed at a checklist page served
by n100. The page renders the current checklist(s) from the intercom
(order.captured, the same topic checklist_app.py consumes — product/n100/
checklist-app/checklist_app.py:48-49). Task lines show VERB + ITEM (e.g.
"PACK — chafers"), never a bare count, matching the paper task block's
"%-8s %s" verb+item rendering (checklist_app.py:143). The set covers all gigs
in [today, today+4d] (CHECKLIST_WINDOW_DAYS=4, checklist_app.py:25,160). With
2+ active gigs the page cycles every 15s. n100 PUSHES status changes to the
page (WebSocket per [[SPEC:INFRA-009]]); 2.5s polling is the fallback only.
The page shows "last updated <time>" at all times; when stale it shows a banner
naming the cause, and that banner pulses red/pink only when stale >=12min AND
it is the day of service AND at least one item has been marked started. A
cancelled invoice (intercom invoice.canceled) ntfy's Nick asking whether to
cancel — never auto-cancel. A fully-completed checklist is archived and not
shown the next day. Alerts go to ntfy "taza-ops", http://192.168.2.102:9000,
and the TV. Re-launching com.webos.app.browser is the heal; turnOnScreen is NOT
a dependency (returns 401). Paper + kanban remain the safety net. OCR/vision
attaches later at a named seam and must not break this view.

----------------------------------------------------------------------
failure_behavior:
- TV/browser off or crashed: watchdog detects via getForegroundAppInfo and
  re-launches com.webos.app.browser to the checklist URL (proven heal). No
  turnOnScreen call.
- Push/bus stalled: the page shows "last updated <time>" and the stale banner
  naming the cause; the pulse fires only on the day of service after an item
  is started and data is >=12min stale.
- Ethernet down -> wifi: the page keeps updating and an alert fires (ntfy +
  health page + TV), because wifi is fallback-only.
- Everything fails: paper checklist + Mom's kanban remain authoritative. The TV
  is additive, never the only path.

----------------------------------------------------------------------
dependency_notes:
- Content source: [[SPEC:PROD-20]] topic `order.captured` (LIVE — 34 events in
  system_events; consumed by product/n100/checklist-app/checklist_app.py:48-49
  `where topic='order.captured' and payload ? 'content_hash'`).
- Cancellation source: [[SPEC:PROD-20]] topic `invoice.canceled` (LIVE — 1 event;
  emitted by product/n100/square-sync/square_invoice_sync.py:312
  `emit("invoice.canceled", iid, p_status, "CANCELED",`).
- Status feed = PLACEHOLDER. No live topic carries item started/completed.
  system_events topics verified: event.created, invoice.canceled/changed/
  created/deposit_received/paid, ops.printer_state, order.captured, test.ping.
  Item status goes live only when [[SPEC:URS-KANBAN-005]] -> [[SPEC:PROD-38]]
  (Canonical Task Close Contract, Spec Drafted) -> [[SPEC:PROD-20]] emit. Do NOT
  name a status topic; attach to PROD-38's TaskCloseEvent emit when it lands.
- Push: [[SPEC:INFRA-009]] (Shared push/pull hybrid client library, Spec
  Drafted) WebSocket + polling watchdog. NOTE: its watchdog is 10s, this spec
  needs 2.5s — see Q3.
- Alerts: [[SPEC:PROD-25]] (Unified Notifier -> ntfy "taza-ops",
  product/n100/notifications/notify.py:10 `NTFY_TOPIC=taza-ops`), health page
  http://192.168.2.102:9000 (taza-dashboard.service), [[SPEC:PROD-28]].
- Staleness pattern: [[SPEC:URS-HEALTH-005]] ("Stale or missing health data
  fails visibly", In Development) — the same check SSB-001 names.
- Content semantics reused: [[SPEC:SSB-001]] (progress view), [[SPEC:SSB-002]]
  (glanceability >=40pt), [[SPEC:SSB-003]] (completed persistence),
  [[SPEC:SSB-005]] (partial completion) — written for the TCL/Android dashboards;
  this spec is their webOS delivery.
- Fleet slot: [[SPEC:URS-DISP-001]] (canonical role = live checklist),
  [[SPEC:URS-DISP-PKG]] (fleet architecture).
- Control path (given, probe 2026-10-15): SSAP over WebSocket :3000,
  com.webos.app.browser, paired client-key /home/taza/repo/secrets/lg_tv.json.
  No ADB / Dev Mode / CDP. turnOnScreen returns 401 — excluded.
- OCR placeholder: [[SPEC:PROD-37]] (voice/camera close) — MT1/MT2. Attach at
  the push/render seam; the bootstrap must not require it.

----------------------------------------------------------------------
consumes:
  [[SPEC:PROD-20]] `order.captured` (content) and `invoice.canceled`
  (cancellation); [[SPEC:PROD-38]] TaskCloseEvent (PLACEHOLDER — item status);
  SSAP control (launch + foreground heal) on the LG TV.

consumed_by:
  None — leaf display. Alerts fan out via [[SPEC:PROD-25]] (ntfy) and
  [[SPEC:PROD-28]] (health page).

----------------------------------------------------------------------
open_questions:
Q1. Priority: I propose P1 / required_for_release=NO (the TV is additive;
    paper + kanban are the safety net). flash proposed P2. URS-DISP house is P1.
    Confirm P1 vs P2.
Q2. Status feed is the hard blocker. No live topic carries started/completed
    ([[SPEC:PROD-38]] + [[SPEC:URS-KANBAN-005]] are Spec Drafted). Ship the
    checklist view now with all items "pending" until that path emits, or hold
    this spec until the task-close emit is built? This decides whether the TV is
    shippable in isolation.
Q3. 2.5s vs INFRA-009: INFRA-009's polling watchdog is 10s, the decided budget
    is 2.5s. Tighten the watchdog to 2.5s, or accept 2.5s only while push is
    healthy (polling fallback may lag)?
Q4. Content form: I specify a static n100-served HTML page rendered in
    com.webos.app.browser, pushed over WebSocket with 2.5s polling fallback —
    not a PWA ([[SPEC:TV-012]]), which the webOS browser may not kiosk. Confirm.
Q5. The 12-min pulse needs "an item marked started", but item status has no live
    source yet (Q2). Until the status feed lands, the day-of-service pulse can
    never fire. Accept pulse deferred to the status feed, or tie the pulse to
    service_date only?
Q6. Cycle semantics with 2+ gigs: 15s per gig, or 15s total split evenly?
Q7. Serving: which port/process serves the TV page on n100, and who owns it
    (new process vs existing dashboard.py / server_kanban.py)? flash proposed
    9004 — unverified, needs Nick.

================================================================================
AC
================================================================================

ac_normal:
1. TV shows the same checklist content as paper: task lines VERB + ITEM
   (e.g. "PACK — chafers"), never a bare count.
2. A status change published on the intercom is reflected on the TV within
   2.5s, with no human action.
3. "last updated <time>" is visible and updates on every push.
4. With 2+ active gigs, the page cycles between them every 15s, covering every
   gig in [today, today+4d].

ac_edge:
5. A multi-day order / two gigs on one day: the set covers every service day in
   the 0–4 day window (same window as checklist_app.py DAYS=4), and the cycle
   includes each day.
6. A status change arriving mid-render does not produce a torn/partial frame.
7. Ethernet down -> wifi up: the page keeps updating and an alert fires on all
   three surfaces (ntfy + health page + TV).
8. 0% and 100% progress extremes render correctly.

ac_negative:
9. invoice.canceled never auto-cancels: it ntfy's Nick asking whether to cancel,
   and the checklist stays until Nick decides.
10. A completed checklist does not appear the next day; it is archived for
    troubleshooting.
11. A failed/rejected event does not render as if committed — the display shows
    committed state only.

ac_silent_failure:
-> detected by: [[SPEC:URS-HEALTH-005]] (Stale or missing health data fails
   visibly) plus the page's own stale banner.
12. Push stalled but the page still renders a plausible stale checklist: the
    stale banner names the cause, and the pulse fires only when stale >=12min
    AND day-of-service AND an item is started.
13. Browser running but on the wrong/old URL (crashed to home): the watchdog
    detects via getForegroundAppInfo and re-launches to the checklist URL —
    no turnOnScreen.
14. Wifi fallback active silently: the network-source alert actually fires on
    all three surfaces (not merely configured).

ac_challenge: (empty)
ac_block:    (empty)

================================================================================
VM
================================================================================

verification_methods:
1) [AUTO] Latency test: publish a status change, confirm TV reflect <=2.5s. ;
2) [AUTO] Cycle test: seed 2+ active gigs, confirm the 15s cycle covers each
   over a 30s observation window. ;
3) [AUTO] Staleness test: stall push, confirm "last updated <time>" + banner
   naming the cause; set day-of-service + item started + age >=12min -> pulse;
   before service start -> no pulse. ;
4) [AUTO] Cancellation test: publish invoice.canceled, confirm ntfy fired and
   the checklist was NOT auto-cancelled. ;
5) [AUTO] Network test: drop Ethernet to force wifi, confirm the alert fires on
   ntfy + health page + TV. ;
6) [AUTO] Archive test: complete a checklist, advance one day, confirm it is
   absent from the TV and present in the archive. ;
7) [NICK] Nick observes the LG TV during a real service day: checklist readable,
   reflects kanban status changes within 2.5s, no touch/remote needed.

vm_count:       7
vm_auto_count:  6
vm_nick_count:  1

================================================================================
DEPENDENCY DAG (build order — ARCHITECT)
================================================================================

Level 0 (start now, fully parallel):
  T1  Serve the checklist page on n100: render VERB+ITEM lines from
      order.captured (same model as checklist_app.py build()).
  T2  SSAP launcher + watchdog: launch com.webos.app.browser, heal via
      getForegroundAppInfo. Depends on nothing new.

Level 1:
  T3  Push fabric (INFRA-009 WebSocket + 2.5s polling fallback). Needs T1.
  T5a Stale banner (timestamp + cause) + network alert (ntfy/health/TV). Needs
      T3 heartbeat; ntfy + health endpoints already live.

Level 2 (BLOCKED on spec decisions, not code):
  T4  Item-status feed. Needs [[SPEC:PROD-38]] + [[SPEC:URS-KANBAN-005]] to
      emit a TaskCloseEvent on [[SPEC:PROD-20]]. Until then, statuses are a
      placeholder; the TV shows "pending".

Level 3:
  T5b Pulse (day-of-service AND >=12min AND item started). Needs T4.
  T6  Archive-on-complete + next-day suppression. Needs T4.

Nothing serialises behind T4 except T5b and T6. T1 and T2 must not wait.

================================================================================
RULES
================================================================================

rules:
  RULE-TV-REFLECT-2.5S: status_change_display_lag_s <= 2.5
  RULE-TV-STALE-12M:    stale_pulse_trigger_min = 12
  RULE-TV-CYCLE-15S:    gig_cycle_interval_s = 15
  RULE-TV-RELAUNCH:     browser relaunch is the heal; no turnOnScreen call
rule_count: 4

================================================================================
END OF PROPOSAL
