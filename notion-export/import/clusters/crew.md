# Taza OS URS — CREW cluster
_Exported: 2026-09-19 21:35 | 4 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-CREW-001 — Crew display operates offline as a full-screen PWA
**Status:** Built (unverified live) | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: launch the tablet display from home screen and run the full event offline — no reliance on venue Wi-Fi.

**Atomic Requirement:**  
The crew service display shall launch from the device home screen, operate full-screen in Chrome, and continue its configured presentation without network access.

**Functional Requirement Specification:**  
The crew service display shall be a standalone HTML file installable via Chrome 'Add to Home Screen' (PWA), launch full-screen from the device home screen, and present its complete configured prompt cycle with no network calls after initial load. The Wake Lock API shall prevent device sleep during service. All event content is embedded at setup time.

**Inputs:**  
The configured event data entered at setup ([[SPEC:URS-CREW-002]]); no runtime network calls during service.

**Outputs:**  
A full-screen, offline-capable crew display running from the device home screen with Wake Lock active.

**Trigger:**  
Crew taps the home-screen icon before service; runs until crew manually exits.

**Invariants:**  
No network call required during active presentation; Wake Lock prevents sleep for the full event duration; the app installs and runs from the home screen like a native app.

**Failure Behavior:**  
Network loss after installation has no effect on presentation; the display continues its configured prompt cycle without error or blank screen. A network-dependent feature (V2 auto-populate) gracefully degrades to manual setup in V1.

**Failure Mode Addressed:**  
A crew display that goes blank or stalls mid-event because a venue has no Wi-Fi or the N100 is unreachable — depriving crew of the anchoring attention prompts at the worst possible moment.

**Acceptance Criteria:**  
After initial installation, airplane-mode launch and complete prompt cycle succeed without network calls.

**Verification Method:**  
Offline field test on a crew tablet. Status: Deployed (built and deployed; "unverified live" means not yet field-tested at a real event).

**Maintenance Requirements:**  
Verify offline operation after any change to the HTML file; confirm Wake Lock API still supported on the tablet's Chrome version after OS/browser updates.

**Dependency Notes:**  
Implemented by [[SPEC:SCREEN-08]] (taza-crew-display.html, standalone offline HTML/PWA). Deployed via Chrome 'Add to Home Screen' on the Galaxy Tab A8. No dependency on the N100 during an event. Parent [[SPEC:PROD-29]].

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Crew-display-operates-offline-as-a-full-screen-PWA-bfb17baa49824cbd99c39c24b5465515_

---
## URS-CREW-002 — Crew display accepts complete event setup
**Status:** Built (unverified live) | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: a setup form for event name, client story, guest count, event type, and hold/prompt durations — saved correctly so service always shows tonight's client, not last week's.

**Atomic Requirement:**  
Before service, the crew display shall accept event name, client story, guest count, event type, story hold duration, and prompt duration.

**Functional Requirement Specification:**  
Before service, the crew display shall present a setup form accepting: event name, client story (the narrative text crew will see first), guest count, event type, story hold duration (configurable seconds), and prompt duration (configurable seconds per prompt). All fields shall validate, persist for the active event session, and survive application restart on the same device.

**Intent / User Need:**  
Client story is the most important field — anchors the crew emotionally before service.

**Inputs:**  
Crew or Nick manually entering event name, client story, guest count, event type, story hold duration, prompt duration before service.

**Outputs:**  
A validated, persisted event configuration used by [[SPEC:URS-CREW-003]] and [[SPEC:URS-CREW-004]] for the active service session.

**Trigger:**  
Crew/Nick opens the setup screen before service begins.

**Invariants:**  
All required fields validate before the display can enter service mode; setup persists through app restart; a new-event setup clears the prior event's data (no carry-over contamination).

**Failure Behavior:**  
Missing or invalid required fields block the start of service presentation; partial or corrupt setup data does not carry over to a new event (prior event data is cleared on new setup).

**Failure Mode Addressed:**  
Starting service with the wrong client's story on screen, or a blank prompt deck because setup was skipped or saved incorrectly — both undermine the crew's emotional connection to the event.

**Acceptance Criteria:**  
All fields validate, persist for the active event, and survive application restart.

**Verification Method:**  
Form validation and persistence test.

**Maintenance Requirements:**  
Keep field definitions aligned with what the prompt-cycling and story-presentation logic consumes ([[SPEC:URS-CREW-003]]/004); update the field set when V2 auto-populate (URS-CREW-005) launches.

**Dependency Notes:**  
Setup data is used by [[SPEC:URS-CREW-003]] (story presentation) and [[SPEC:URS-CREW-004]] (prompt cycling). In V2, this step is replaced by auto-population from the canonical event record (URS-CREW-005). Until then, manual entry here is the only setup path. Parent [[SPEC:PROD-29]].

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Crew-display-accepts-complete-event-setup-13bc574d620d428cbb52fe5564a80849_

---
## URS-CREW-003 — Crew display presents client story before prompts
**Status:** Built (unverified live) | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: tablet shows the client's story with a slow reveal before prompts start, every time — crew pauses and reads it together before service.

**Atomic Requirement:**  
The crew display shall present the configured client story for the configured hold time before beginning hospitality prompts.

**Functional Requirement Specification:**  
On service start, the crew display shall present the configured client story text with animated line-by-line reveal in large gold typography for the configured hold duration, before transitioning to the hospitality prompt cycle ([[SPEC:URS-CREW-004]]). A crew member who arrives late can tap 'Replay' to restart the story from the beginning without interrupting others. After the hold duration, the transition to prompts is automatic.

**Inputs:**  
Client story text and hold duration from [[SPEC:URS-CREW-002]] setup; crew 'Replay' tap.

**Outputs:**  
A full-screen animated client-story display for the configured hold duration, then automatic transition to prompts.

**Trigger:**  
Service starts (after setup completes); 'Replay' tap from a late-arriving crew member.

**Invariants:**  
Story always precedes prompts; hold duration is exactly as configured; Replay returns to the story start without resetting the hold timer globally.

**Failure Behavior:**  
If story text is empty or setup was skipped, the display skips to prompts immediately rather than showing a blank story screen.

**Failure Mode Addressed:**  
Crew beginning service without the shared emotional anchor of the client's story — the ritual that activates empathy before the first plate is touched. Without this sequencing, the story is just text nobody reads.

**Acceptance Criteria:**  
Story appears first for the configured duration and prompt rotation begins only afterward.

**Verification Method:**  
Timed UI test.

**Maintenance Requirements:**  
Keep the story animation and typography (gold/large) consistent with the Taza brand language established in the Mom's Table design; verify the Replay tap behaviour after any UI change.

**Dependency Notes:**  
Uses the client story and hold duration from setup ([[SPEC:URS-CREW-002]]). After the hold duration expires, control passes to the prompt cycle ([[SPEC:URS-CREW-004]]). The late-crew 'Replay' tap re-shows the story from the start. Parent [[SPEC:PROD-29]].

**Rationale:**  
The gold animated line-by-line reveal is a first-class brand/psychological requirement, not a cosmetic detail.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Crew-display-presents-client-story-before-prompts-413f4f9c7a9441418c5bb44b1c45d5d0_

---
## URS-CREW-004 — Crew display cycles hospitality prompts and stays awake
**Status:** Built (unverified live) | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
As the crew on site, I need the tablet to stay on and keep cycling through the service prompts for the whole event — big enough to read across the room, calm enough not to stress anyone out — so there's always something reminding me what I should be doing right now without anyone having to say it.

**Atomic Requirement:**  
During service, the display shall remain awake and cycle the approved hospitality-scanning prompts at the configured duration.

**Functional Requirement Specification:**  
During service, the crew display shall remain fully awake via Wake Lock API and cycle through the approved hospitality-scanning prompts — 14 prompts following the natural event arc (core scanning questions, bus pass, utensil scan, client check-in, trash pass, social-drift interruption, wind-down) — at the configured duration per prompt. Each prompt shall display in large, readable white text on a dark background. A progress bar shall indicate position in the cycle.

**Intent / User Need:**  
Silent mentor, not surveillance — the display points, crew act.

**Inputs:**  
Prompt set (14 approved prompts, hardcoded in V1); prompt duration from [[SPEC:URS-CREW-002]] setup; Wake Lock API.

**Outputs:**  
A continuous, Wake-Lock-guaranteed full-screen prompt cycle on the crew tablet throughout service.

**Trigger:**  
Story hold expires ([[SPEC:URS-CREW-003]]); continues until crew manually exits or service ends.

**Invariants:**  
Wake Lock is active for the full service duration; every prompt appears in the configured order; the cycle does not reset on a late arrival (Replay is story-only); prompts are aspirational in tone, never corrective.

**Failure Behavior:**  
Device sleep would break the cycle — prevented by Wake Lock ([[SPEC:URS-CREW-001]]). If Wake Lock API is unavailable on the device, display a visible warning at setup rather than silently failing mid-event.

**Failure Mode Addressed:**  
Crew attention drifting during low-urgency or slow periods of an event — the screen going dark removes the external anchor that keeps crew scanning and serving proactively instead of clustering.

**Acceptance Criteria:**  
No device sleep occurs during a two-hour test and each configured prompt appears in the expected cycle.

**Verification Method:**  
Extended-duration device test.

**Maintenance Requirements:**  
Prompt set is curated by Nick/Sandra and versioned; update the hardcoded set in the HTML file and re-deploy ([[SPEC:SCREEN-08]]) when prompts change; verify Wake Lock on every new browser/OS version on the tablet.

**Dependency Notes:**  
Begins after the story hold expires ([[SPEC:URS-CREW-003]]). Uses prompt duration from setup ([[SPEC:URS-CREW-002]]). Prompt set follows the Taza Scanning Method arc: bus pass, utensil scan, client check-in, social-drift interruption, wind-down. Wake Lock ([[SPEC:URS-CREW-001]]) must be active for the full cycle. Parent [[SPEC:PROD-29]].

**Rationale:**  
Prompt set is curated Taza Scanning Method content — not LLM-generated, not user-editable at runtime (aspirational tone is a brand requirement).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Crew-display-cycles-hospitality-prompts-and-stays-awake-57d3c802d4b04cc69711cc941e6d90c1_
