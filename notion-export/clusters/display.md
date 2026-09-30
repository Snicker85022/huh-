# Taza OS URS — DISPLAY cluster
_Exported: 2026-09-19 21:35 | 7 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-DISP-001 — Each display has one canonical primary role
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: every kitchen screen boots to its correct surface and stays there after a power event, with no manual setup.

**Atomic Requirement:**  
Each named display shall load its assigned primary surface after boot or supervised recovery.

**Functional Requirement Specification:**  
Each named display shall boot to and maintain its assigned primary surface: MT1 → kanban (KANBAN 2, East); MT2 → kanban (KANBAN 2, West); z33 → ops console (DISPLAY 5 + 4 tabs); TCL East 75" → situational (DISPLAY 2); TCL West 75" → prep (DISPLAY 3); Insignia Fire TV → van loadout (DISPLAY 4); 50" onboarding TV → onboarding panels (DISPLAY 6 / TV-009, once networked). After any boot or supervised recovery, every device resolves to its documented role and correct application endpoint.

**Inputs:**  
DHCP-reserved LAN IPs per device; the self-heal maintain scripts (ADB-based for MT1/MT2; TV-equivalent needed for the 3 TVs); the correct URL per role.

**Outputs:**  
Every named display serving its assigned primary surface after boot and after any self-heal recovery.

**Trigger:**  
Device boot; supervised self-heal recovery cycle.

**Invariants:**  
One primary role per named display; roles are fixed in the DHCP/maintain-script config, not per-session; the 50" onboarding TV role is fixed once networked.

**Failure Behavior:**  
Wrong-surface boot → self-heal maintain script redirects. Script itself fails → visible error, not a blank screen. Addresses: a display silently serving the wrong content after reboot, which crew trust without realising.

**Acceptance Criteria:**  
All six devices resolve to the documented role and correct application endpoint.

**Verification Method:**  
Device-by-device field inspection after reboot.

**Maintenance Requirements:**  
Update role map + maintain scripts whenever a TV is added or a role reassigned.

**Dependency Notes:**  
Roles realised by [[SPEC:SCREEN-01]]..05, DISPLAY 6. Boot/recovery depends on TV self-heal maintain scripts (mt1/mt2 confirmed; 3 TVs missing).

**External Dependencies:**  
Configured LAN addresses and browser launch/supervision.

**Open Questions:**  
Open items tracked on [[SPEC:URS-DISP-PKG]] (items 2, 3, 4 apply here).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Each-display-has-one-canonical-primary-role-569e9bf0a9b04ee4a8c02ff7d4e376db_

---
## URS-DISP-002 — Display mode is resolved deterministically from operating state
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: displays switch themselves between event / prep / overnight / dead-day views based on actual operating state.

**Atomic Requirement:**  
For any valid state input, the mode engine shall return exactly one documented display mode.

**Functional Requirement Specification:**  
The mode engine shall deterministically select exactly one of four modes from current time, active-event state, departure state, and pending-task state: EVENT (imminent/active event with open departure); PREP (pending prep, no imminent event); OVERNIGHT (22:00–06:00); DEAD DAY (no event, no pending prep, daytime). Priority: OVERNIGHT > EVENT > PREP > DEAD DAY. Any valid input returns exactly one mode; conflicts resolve by priority.

**Inputs:**  
Current time; active-event flag + event start/end times ([[SPEC:PROD-01]]); departure state; pending-task count ([[SPEC:PROD-01]]).

**Outputs:**  
One of: EVENT | PREP | DEAD DAY | OVERNIGHT — broadcast to all displays via the push fabric ([[SPEC:PROD-04]]).

**Trigger:**  
Any change to time window, active-event state, departure state, or pending-task count; also evaluated on each push cycle.

**Invariants:**  
Exactly one mode output per input set; priority order is fixed (OVERNIGHT > EVENT > PREP > DEAD DAY); no undefined or intermediate mode exists.

**Failure Behavior:**  
Ambiguous or conflicting input must resolve to exactly one mode — never undefined, never left to the display to guess. Unrecognised state defaults to DEAD DAY (safest low-information mode), not a stale EVENT display. Addresses: displays stuck on event content with no event, and mode flicker on conflicting inputs.

**Acceptance Criteria:**  
Overnight 22:00–06:00 resolves OVERNIGHT; imminent/departed-open event resolves EVENT; pending prep resolves PREP; otherwise DEAD DAY.

**Verification Method:**  
Table-driven unit tests at boundaries and conflicting-state cases.

**Maintenance Requirements:**  
Keep mode boundary times configurable (e.g. OVERNIGHT window); run table-driven boundary tests after any mode-logic change.

**Dependency Notes:**  
Mode computed server-side on N100; pushed to displays (DISPLAY 1/DISPLAY 7). Inputs: time, active-event state ([[SPEC:PROD-19]]), departure state, pending-task state.

**Open Questions:**  
Blocked by [[SPEC:URS-DISP-PKG]] open item 1 (display-persistence.js not wired).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Display-mode-is-resolved-deterministically-from-operating-state-79de623e04ff4d9fbdead8eaa51a639f_

---
## URS-DISP-003 — TCL East presents situational awareness by mode
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: east wall screen always shows the current big picture — timeline, allergens, assignments, departure status, exceptions — switching automatically as the day progresses.

**Atomic Requirement:**  
For each documented mode, TCL East shall render the required situational sections and omit stale event-critical information.

**Functional Requirement Specification:**  
TCL East shall present the situational sections required for the current mode: EVENT — event timeline, allergens, crew assignments, notes, departure status, active health/exception flags; PREP — pending tasks, allergens, prep countdown; DEAD DAY — upcoming events preview, recent LKL summary; OVERNIGHT — minimal/sleep state. Stale event-critical information (especially allergens) shall be visibly marked, never silently displayed as current.

**Inputs:**  
/situational.json + /inventory.json from N100; current mode from [[SPEC:URS-DISP-002]]; push updates via SSE ([[SPEC:PROD-04]]).

**Outputs:**  
A rendered, mode-appropriate situational display on TCL East, updated within the <4s lag SLA.

**Trigger:**  
Mode change ([[SPEC:URS-DISP-002]]); push update on any content-source change ([[SPEC:PROD-04]]).

**Invariants:**  
Allergen flags never silently disappear; stale signals always carry a visible timestamp/degraded indicator; content set is mode-specific (no event-mode content in OVERNIGHT).

**Failure Behavior:**  
Stale/unavailable signals render visibly degraded with timestamp (fail-visible, per [[SPEC:URS-HEALTH-005]]). Allergen flags must never silently disappear — a stale signal keeps the flag visible with a staleness indicator. Addresses: the east wall becoming background noise, and stale allergen flags crew stop noticing.

**Acceptance Criteria:**  
Golden-screen tests validate the required section set for EVENT, PREP, DEAD DAY, and OVERNIGHT.

**Verification Method:**  
Visual regression and field demonstration.

**Maintenance Requirements:**  
Keep golden-screen fixtures current as the section set evolves; verify allergen-staleness behaviour after any signal-source change.

**Dependency Notes:**  
Sources: event record ([[SPEC:PROD-19]]), allergen flags (CLOSE 14/[[SPEC:CAT-002]]), crew assignments ([[SPEC:PROD-17]]), departure state ([[SPEC:PROD-02]]), health signals (HEALTH 1). Mode from DISPLAY 22. DISPLAY 2 fetches /situational.json + /inventory.json.

**External Dependencies:**  
TCL East 192.168.2.106; situational.json or equivalent API.

**Open Questions:**  
Awaiting repoint + mode-engine wiring (DISPLAY 27 items 1, 3).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/TCL-East-presents-situational-awareness-by-mode-d66c222900f84927bdc964797232461e_

---
## URS-DISP-004 — TCL West presents prep execution by mode
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: west wall screen shows live prep progress — done, blocked, next, and time to loadout — switching modes automatically.

**Atomic Requirement:**  
For each documented mode, TCL West shall render the required prep sections using current task and LKL data.

**Functional Requirement Specification:**  
TCL West shall present the prep-execution sections required for the current mode: EVENT — station progress, crew assignments, blockers, departure countdown, active LKL summary; PREP — full prep task list with completion state, blockers, countdown; DEAD DAY — upcoming event preview, pending prep; OVERNIGHT — minimal/sleep state. No data shall exceed the documented refresh window without a visible staleness indicator.

**Inputs:**  
/situational.json from N100 (station progress, task state, LKL summary, blockers); current mode from [[SPEC:URS-DISP-002]]; push updates via SSE ([[SPEC:PROD-04]]).

**Outputs:**  
A rendered, mode-appropriate prep-execution display on TCL West, updated within the <4s lag SLA.

**Trigger:**  
Mode change; push update on any task/LKL/blocker change ([[SPEC:PROD-04]]).

**Invariants:**  
Blocked stations are always visibly distinct from in-progress; content is mode-specific; data is never silently stale.

**Failure Behavior:**  
Stale task/LKL data renders with a visible staleness indicator; a blocked station is never silently shown in-progress. Refresh exceeding the documented window flags the display as potentially stale. Addresses: the west wall going static and irrelevant, breaking the shared operational picture.

**Acceptance Criteria:**  
Golden-screen tests validate EVENT, PREP, DEAD DAY, and OVERNIGHT content; no data is older than the documented refresh window.

**Verification Method:**  
Visual regression and field demonstration.

**Maintenance Requirements:**  
Keep golden-screen fixtures current; verify blocked/in-progress visual distinction after any card-state or colour change.

**Dependency Notes:**  
Sources: task records + station assignments ([[SPEC:PROD-19]]), LKL data ([[SPEC:PROD-02]]/URS-LKL), departure countdown ([[SPEC:PROD-02]]), upcoming events ([[SPEC:PROD-19]]). Mode from DISPLAY 22. DISPLAY 3 fetches /situational.json.

**External Dependencies:**  
TCL West 192.168.2.101; task/LKL APIs.

**Open Questions:**  
Awaiting mode-engine wiring (DISPLAY 27 item 1).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/TCL-West-presents-prep-execution-by-mode-edbd7619f9a94a52b75163340b2a55dc_

---
## URS-DISP-005 — Van Scoreboard exposes loadout readiness by mode
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: one screen showing whether the van is packed, who's driving, destination, and time to departure — with unloaded items clearly flagged.

**Atomic Requirement:**  
For LOADOUT ACTIVE, PREP, and DEAD DAY states, the van scoreboard shall render the documented state-specific content from current packing and assignment data.

**Functional Requirement Specification:**  
The van scoreboard shall render state-specific content from current packing and assignment data: LOADOUT ACTIVE — packing completion %, item-by-item checklist, driver, travel time, destination, departure countdown; PREP — upcoming departure preview (time + estimated packing state); DEAD DAY — next event + estimated departure window. Unchecked items shall be visibly flagged at all times before departure. The ~6% right-edge dead zone on the Insignia panel is handled via a CSS variable in van-loadout.html.

**Inputs:**  
/van-loadout.json from N100 (packing state, driver, destination, drive-time, departure time); current mode/state from [[SPEC:URS-DISP-002]].

**Outputs:**  
A rendered, state-appropriate van readiness scoreboard on the Insignia Fire TV.

**Trigger:**  
Mode/state change; packing-state push update ([[SPEC:PROD-04]]).

**Invariants:**  
Unchecked items never appear as complete; departure countdown is always accurate to the drive-time matrix; CSS dead-zone compensation is always applied on this specific screen.

**Failure Behavior:**  
Unchecked items are always visibly flagged before departure — never shown complete until they are. Stale packing records show a staleness indicator, not false confidence. Countdown reaching zero without full packing shows a visible alert, not a blank countdown. Addresses: departing with an incomplete load because the board showed green.

**Acceptance Criteria:**  
Each state renders its required fields; unchecked items are visibly flagged before departure.

**Verification Method:**  
State-fixture UI tests and field demonstration.

**Maintenance Requirements:**  
Keep /van-loadout.json schema aligned with checklist + assignment sources; re-test dead-zone CSS var if van-loadout.html is restructured; keep drive-time matrix current ([[SPEC:PROD-16]]/[[SPEC:W15]]).

**Dependency Notes:**  
Sources: packing completion (PACK 1/[[SPEC:URS-KIT-103]]), item + driver assignments, drive-time matrix (PACK 1/[[SPEC:W15]]). Mode from DISPLAY 22. DISPLAY 4 fetches /van-loadout.json.

**External Dependencies:**  
Insignia/Alexa 192.168.2.109; packing manifest; drive-time cache.

**Open Questions:**  
Insignia also carries ALC/Alexa role — two functional roles on one TV, reconcile in debate. Awaiting mode-engine wiring (DISPLAY 27 item 1).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Van-Scoreboard-exposes-loadout-readiness-by-mode-70097187f6b5420e90e6e3fdef36a5b9_

---
## URS-DISP-006 — Critical display state cannot be displaced by voice
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: an allergen warning or urgent alert can never be knocked off a screen by a voice query — voice answers come through the speakers, not over the safety-critical display.

**Atomic Requirement:**  
Voice interaction shall preserve RED/AMBER visual state and automatically restore GREEN visual state after the allowed temporary override.

**Functional Requirement Specification:**  
When a display is in RED or AMBER visual state, voice responses and all other transient content shall be delivered audio-only and shall never replace or overlay the critical visual state. In GREEN state, a voice response or transient content may occupy the display for a maximum of ten seconds before automatically reverting to the operational state with no user action. Gating is enforced at the display-persistence layer (display-persistence.js) and is not bypassable by push or voice.

**Inputs:**  
Current display visual state (RED/AMBER/GREEN from display-persistence.js); voice/transient content payload; automatic 10s revert timer.

**Outputs:**  
Audio-only voice response on RED/AMBER displays; a temporary (≤10s auto-reverting) visual override on GREEN displays.

**Trigger:**  
Any voice interaction or transient push content arriving while a display has an active visual state.

**Invariants:**  
RED state: no visual displacement, ever; AMBER state: no visual displacement, ever; GREEN state: displacement ≤10s, auto-reverts unconditionally; enforcement lives in display-persistence.js, not in individual content sources.

**Failure Behavior:**  
Any attempt to displace RED/AMBER visual state (voice, push, or manual) is silently dropped on the visual layer; audio still plays. A GREEN override that fails to revert within 10s is treated as a hang and self-reverts immediately. Addresses: a voice query or push wiping a critical allergen/exception state mid-event.

**Acceptance Criteria:**  
NORMAL:
1. Display in RED or AMBER state receiving a voice response or transient content delivers it audio-only — visual state is never replaced or overlaid.
2. Display in GREEN state receiving transient content shows it for a maximum of 10 seconds, then automatically reverts with no user action.

EDGE:
3. Display transitions from GREEN to AMBER/RED WHILE transient content is being shown — the transient content is immediately cut short and critical state takes over, not left running its full 10s.
4. Rapid repeated transient-content triggers in GREEN state don't stack/queue into a longer effective takeover than 10s at a time.

NEGATIVE:
5. A voice command or push explicitly attempting to force visual content onto a RED/AMBER display is rejected/blocked at the gating layer — not just 'discouraged by convention.'

SILENT FAILURE:
6. This is explicitly called out as 'not bypassable by push or voice' — verify this is enforced in code at display-persistence.js, not just true in the currently-tested paths; any new push/voice integration added later must inherit this gate automatically, not require each new integration to remember to check it.
7. The 10-second auto-revert in GREEN state failing to fire (stuck showing transient content indefinitely) must be caught — this would silently degrade the operational display into a stale non-operational one.

**Verification Method:**  
1) Unit tests: RED/AMBER blocks all visual overlay, GREEN allows transient content capped at 10s. 2) State-transition test: trigger a GREEN→AMBER/RED transition mid-transient-display, confirm immediate cutover. 3) Bypass-attempt test: attempt to force visual content onto a RED/AMBER display via both push and voice paths, confirm both are blocked at the gating layer. 4) Architecture test: confirm the gate lives centrally in display-persistence.js such that any new content-source integration is gated by default, not opt-in per integration. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Test RED/AMBER preservation after any frontend change; verify auto-revert timer after any JS dependency update.

**Dependency Notes:**  
display-persistence.js implements RED/AMBER/GREEN locking. RED = critical/exception; AMBER = important/transitional; GREEN = normal. Gates both Hey Google and Alexa voice paths.

**Open Questions:**  
P0 — highest-priority row in cluster. BLOCKED by [[SPEC:URS-DISP-PKG]] item 1: display-persistence.js built+tested but not wired to any live TV frontend.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Critical-display-state-cannot-be-displaced-by-voice-8bf16473d5a34f5c8d388ac23cde6830_

---
## URS-DISP-PKG — Display Fleet Content & Mode Architecture
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: each wall display fixed in its role, auto-switching mode as the day evolves, canonically sourced, never hiding a safety alert behind a voice query.

**Atomic Requirement:**  
The display fleet shall present correct, mode-driven, role-assigned content on every surface at all times, and shall never let transient interactions displace safety-critical visual state.

**Functional Requirement Specification:**  
Display-fleet architecture shall: (1) assign one primary role per display, enforced after boot/recovery (DISPLAY 21); (2) resolve exactly one mode from operating state (DISPLAY 22); (3) render mode-appropriate content on TCL East (DISPLAY 23), TCL West (DISPLAY 24), van scoreboard (DISPLAY 25); (4) protect RED/AMBER visual state from voice/transient displacement (DISPLAY 26). All content canonically sourced; stale data visibly marked.

**Failure Behavior:**  
Addresses: wall displays becoming unreliable — wrong content, wrong mode, stale data, or a critical alert wiped by a voice query — causing crew to stop trusting and stop looking at them.

**Out of Scope:**  
[[SPEC:SCREEN-01]]..08 (built artifacts); [[SPEC:PROD-04]]/SSB (push fabric); [[SPEC:ALC-001]]..006 (Alexa — Insignia hosts both roles, separate concern). This package = display-fleet architecture only.

**Acceptance Criteria:**  
Every named display boots to its assigned primary surface ([[SPEC:URS-DISP-001]]); the mode engine returns exactly one mode for any input state ([[SPEC:URS-DISP-002]]); TCL East, TCL West, and the van scoreboard render their mode-correct content sets ([[SPEC:URS-DISP-003]]/004/005); RED/AMBER visual states are never displaced by voice or transient content ([[SPEC:URS-DISP-006]]).

**Verification Method:**  
Device-by-device reboot test ([[SPEC:URS-DISP-001]]); table-driven mode-engine unit tests ([[SPEC:URS-DISP-002]]); golden-screen tests per mode per display ([[SPEC:URS-DISP-003]]/004/005); RED/AMBER displacement test with voice integration ([[SPEC:URS-DISP-006]]).

**External Dependencies:**  
MT1 192.168.2.104; MT2 192.168.2.108; z33 192.168.2.105; TCL East 192.168.2.106; TCL West 192.168.2.101; Insignia/Alexa 192.168.2.109.

**Open Questions:**  
CANONICAL OPEN ITEMS for this cluster (do not duplicate on child rows): 1. display-persistence.js built+tested, NOT wired to any live TV frontend — blocks DISPLAY 22 and DISPLAY 26 (P0). 2. TV self-heal maintain scripts/timers missing for 3 TVs (per 08-22 gap) — blocks DISPLAY 21 boot-recovery. 3. TV→content repoint pass needed before launch; role split confirmed correct per Nick, actuals to be verified by debate-team gflip/N100 recon. 4. 50" onboarding TV not yet networked (DISPLAY 6).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Display-Fleet-Content-Mode-Architecture-67f47d1d42db43b186bdacb96a9d7b56_
