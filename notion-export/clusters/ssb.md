# Taza OS URS — SSB cluster
_Exported: 2026-09-19 21:35 | 7 rows_
_Source: Notion Master URS & Specification Registry_

---
## SSB-001 — TV dashboard event progress view
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV dashboard shows live event checklist — completed items muted w/ strikethrough + bin location, incomplete in full contrast, progress % prominent — updating automatically.

**Functional Requirement Specification:**  
TV dashboard event progress view: displays the active event checklist from real-time NocoDB state. Completed items remain visible with visual suppression (muted + strikethrough) and inline bin location; incomplete items shown in full contrast; progress % shown prominently. Updates automatically on state change, no human action required.

**Failure Behavior:**  
Fallback: paper checklist on clipboard.

**Acceptance Criteria:**  
NORMAL:
1. Dashboard reflects real-time NocoDB state: completed items muted+strikethrough with inline bin location, incomplete items full-contrast, progress % prominent — updates automatically with no human action.

EDGE:
2. A state change in NocoDB that happens while the dashboard is mid-render doesn't produce a torn/partial visual update (some items updated, others not, in an inconsistent frame).
3. Progress % calculation is correct at both extremes (0% and 100% complete), not just mid-range values.

NEGATIVE:
4. A NocoDB write that fails or is rejected does not appear on the dashboard as if it succeeded — dashboard reflects actual committed state only.

SILENT FAILURE:
5. Dashboard silently falling behind real state (delayed update, not a hard disconnect) is worse than an obvious disconnect — verify there's a staleness indicator if updates lag beyond an expected threshold, not just binary connected/disconnected.
6. This is the composite view that DISPLAY 9 (persistence) and DISPLAY 10 (bin location) both feed into — verify integration between all three, not just each individually.

**Verification Method:**  
1) Real-time sync test: make a NocoDB state change, measure and confirm dashboard update latency and correctness. 2) Boundary test: 0% and 100% progress states render correctly. 3) Integration test: confirm DISPLAY 9 (persistence) and DISPLAY 10 (bin location) behaviors both hold correctly within this composite view, not just in isolation. 4) Staleness test: introduce an artificial update delay, confirm a staleness indicator appears rather than the dashboard silently looking current. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/TV-dashboard-event-progress-view-3cfe152fc19981e8b52cc29d4fd9be8f_

---
## SSB-002 — TV dashboard glanceability standard
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV dashboard text legible at 15ft in bright, oblique-angle conditions — checklist ≥40pt, bin labels ≥32pt, progress ≥72pt.

**Functional Requirement Specification:**  
Glanceability standard: all TV dashboard text legible from 15 feet minimum — checklist text ≥40pt, bin labels ≥32pt, progress % ≥72pt. Completed vs incomplete must be distinguishable in high-ambient-light kitchen conditions at oblique viewing angles.

**Failure Behavior:**  
Fallback: increase font sizes if legibility fails.

**Acceptance Criteria:**  
NORMAL:
1. Checklist text ≥40pt, bin labels ≥32pt, progress % ≥72pt, all legible from 15 feet under normal kitchen lighting.
2. Completed vs incomplete is visually distinguishable at 15 feet.

EDGE:
3. Text at these sizes doesn't overflow/truncate/wrap awkwardly for the longest realistic item names and bin IDs actually in use, not just short test strings.
4. Distinguishability holds at oblique viewing angles (crew walking past, not standing square to the screen), not just head-on.

NEGATIVE:
5. High-ambient-light conditions (kitchen lighting, possible glare) do not wash out the completed/incomplete visual distinction — must be tested under actual kitchen lighting, not a dim office.

SILENT FAILURE:
6. A design that passes a controlled test (good lighting, straight-on, short strings) but fails in real kitchen conditions (glare, angle, long item names) is the exact risk this row exists to prevent — verify under real conditions, not idealized ones.
7. Font/size regressions introduced in a later UI change would silently violate this standard unless there's a repeatable check (e.g. a visual regression test or documented style guide enforcement), not just a one-time design review.

**Verification Method:**  
1) Measured test: physical tape-measure distance test in the actual kitchen, at 15 feet, at multiple oblique angles, under actual operating lighting. 2) Content-stress test: longest real item names and bin IDs from the actual catalog/bin master rendered to confirm no overflow/truncation. 3) Visual-regression check: establish a baseline screenshot/style-guide reference so future UI changes can be checked against this standard. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/TV-dashboard-glanceability-standard-3cfe152fc199812e89c2d8efa6feff29_

---
## SSB-003 — Completed item persistence on TV display
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: completed items stay visible (muted, not removed) on TV until event closes — preserves shared reference of what's done.

**Functional Requirement Specification:**  
Completed item persistence: completed checklist items never disappear from the TV display during an active event, only suppress visually, until the event is explicitly closed. Disappearing items would destroy the shared reference frame for the team.

**Acceptance Criteria:**  
NORMAL:
1. A checklist item marked complete remains visible on the TV (visually suppressed — muted/strikethrough), never removed from the display, until the event is explicitly closed.

EDGE:
2. An event with every single item completed still shows the full completed list (visually suppressed), not an empty/cleared board.
3. An item's completion is un-done (correction) — it correctly reverts to full-contrast incomplete display, not stuck showing as suppressed-complete.

NEGATIVE:
4. No code path (bug, refresh, reconnect) causes a completed item to disappear entirely from the display before explicit event close — this is the specific failure this row exists to prevent.

SILENT FAILURE:
5. A display reconnect/resync after a dropped connection (see DISPLAY 20) must not silently drop completed items that existed before the disconnect — verify resync preserves full history, not just current-state deltas.
6. Event close itself must be an explicit, auditable action — verify items don't get cleared by an ambiguous or accidental trigger (e.g. end-of-day TV routine) that isn't actually 'event closed.'

**Verification Method:**  
1) Unit tests: item completion suppresses visually without removal, un-completion reverts correctly, full-completion state still shows all items. 2) Reconnect/resync test: disconnect and reconnect a display mid-event, confirm all previously-completed items are still present, not dropped. 3) Explicit-close test: confirm only the documented explicit close action clears the board, not any other trigger (e.g. TV sleep/wake routine). 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Completed-item-persistence-on-TV-display-3cfe152fc199818fbadcecd767156888_

---
## SSB-004 — Bin location shown inline on TV display
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: each completed TV checklist item shows its bin location inline (e.g. "Charcuterie cups ✔ WIC-1-4") — locate prepped items by glancing at the wall.

**Functional Requirement Specification:**  
Bin location on TV display: every completed checklist item shows its bin ID inline (e.g. "Charcuterie cups ✔ WIC-1-4") so any team member can locate a completed item by glancing at the shared display without querying LKL or interrupting someone.

**Acceptance Criteria:**  
NORMAL:
1. Every completed checklist item on the TV shows its bin ID inline (e.g. "Charcuterie cups ✔ WIC-1-4"), legible at glance distance.

EDGE:
2. An item completed without a location-changing close (bin ID not applicable) shows a defined, sensible display state — not a blank/broken-looking gap where the bin ID would be.
3. An item's bin location changes after initial completion (correction/move) — the TV display updates to the new bin ID, not left showing the original.

NEGATIVE:
4. A bin ID that doesn't resolve to a real bin master entry (data integrity issue) does not display as a raw broken reference — shows a clear fallback state instead.

SILENT FAILURE:
5. Bin ID displayed on the TV silently going stale relative to the actual LKL record (display not resyncing on a later location change) would actively mislead a crew member searching for the item — verify the inline bin ID always reflects current LKL state, not a cached value from completion time.

**Verification Method:**  
1) Unit tests: bin ID renders correctly on completion, no-bin-applicable case handled gracefully, invalid bin reference doesn't render broken. 2) Live-sync test: change an item's bin location after display, confirm the TV updates to the new value rather than showing stale data. 3) Legibility check: confirm inline bin ID meets the glanceability standard (DISPLAY 8) at 15 feet. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Bin-location-shown-inline-on-TV-display-3cfe152fc199819cb89ee9454e146fb8_

---
## SSB-005 — Partial completion visual indicator
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: partial completion shows progress inline (e.g. "◑ 19/24") with a visual treatment distinct from both done and not-started.

**Functional Requirement Specification:**  
Partial completion visual indicator: PARTIAL_COMPLETE items show partial progress inline (e.g. "Charcuterie cups ◑ 19/24 — WIC-1-4") with a distinct visual treatment from both complete and incomplete states.

**Failure Behavior:**  
Fallback: show as incomplete until fully done (loses partial visibility).

**Acceptance Criteria:**  
Partial items shown with distinct visual treatment; qty_completed/qty_target shown inline; distinguishable from complete and incomplete at 15ft

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Partial-completion-visual-indicator-3cfe152fc1998142b02cfeaaa9049c3e_

---
## SSB-006 — Team member active task indicator
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV shows who is working each in-progress task (e.g. "Plating salmon — Sandra ▶"), updating within 10s of PIN pickup.

**Functional Requirement Specification:**  
Team member active task indicator: TV dashboard shows which team member is currently executing each in-progress task (e.g. "Plating salmon — Sandra ▶"), pulled from task assignment + PIN log, updating within 10s of PIN entry on pickup.

**Failure Behavior:**  
Fallback: task assignment visible on touchscreen only (requires approach).

**Acceptance Criteria:**  
Active task shows assigned staff name; name updates within 10s of PIN entry; no task shows two names at once; visible at 15ft

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Team-member-active-task-indicator-3cfe152fc19981ab9067c2fc8f62daea_

---
## SSB-007 — Event cadence indicator
**Status:**  | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV top bar shows elapsed time, time remaining to service, and current phase (Prep/Staging/Service/Breakdown).

**Functional Requirement Specification:**  
Event cadence indicator: TV dashboard top bar shows overall timeline position — time elapsed, time remaining to service start, and current phase (Prep/Staging/Service/Breakdown) — computed from the NocoDB event timeline.

**Failure Behavior:**  
Fallback: Sandra announces phase transitions verbally.

**Acceptance Criteria:**  
Timeline position shown in top bar; phase label updates automatically at transition times; time remaining counts down live; visible at 15ft

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Event-cadence-indicator-3cfe152fc19981818bd6fd0d4f3020c7_
