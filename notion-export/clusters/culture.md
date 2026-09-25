# Taza OS URS — CULTURE cluster
_Exported: 2026-09-19 21:35 | 12 rows_
_Source: Notion Master URS & Specification Registry_

---
## CULT-001 — Taza Lexicon
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: maintained Lexicon of Taza-specific terms (The Scan, Bus Pass, 90-Second Rule, etc.) all system-facing text draws from consistently.

**Functional Requirement Specification:**  
Taza Lexicon: maintained NocoDB table of Taza-specific terms with fields: term, definition, usage_contexts, associated_panel_id (FK, nullable). Initial terms defined by Nick and Sandra. All system-facing text must use Lexicon terms where applicable. System language is the culture. Initial Lexicon: The Scan, Bus Pass, 90-Second Rule, Zone Ownership, The Taza Way, Anticipatory Service, Key Customer Vibe, Close Strong, We Sequence.

**Failure Behavior:**  
Fallback: informal vocabulary, no system enforcement (culture drift risk).

**Acceptance Criteria:**  
Lexicon table populated with ≥9 terms; every tablet prompt uses Lexicon terms; every task card confirmation uses Lexicon phrasing; TV header rotation pulls from Lexicon; zero generic industry phrasing where a Lexicon term exists

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Taza-Lexicon-3cfe152fc19981e0a091d2487299036d_

---
## CULT-002 — Instructional panel system
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: mini-tutorial on every task card (auto-shown below competency threshold) explaining industry-default vs. Taza way and why it matters — training at the point of work.

**Functional Requirement Specification:**  
Instructional panel system: NocoDB table storing 3–5 panel visual mini-tutorials per practice (industry default / Taza way / client-experience difference / Lexicon term). Linked to task_type_id. On every task kanban card, a tap-to-view icon is always visible. For crew below competency threshold (CLOSE 27), the panel auto-surfaces inline before task start. Panels authored by Nick and Sandra; the V1 visual training asset.

**Failure Behavior:**  
Fallback: panels as static Notion images (no auto-surfacing, no competency gating).

**Acceptance Criteria:**  
NORMAL:
1. Tap-to-view icon is always visible on every task kanban card, linking to the correct panel(s) for that task_type_id.
2. Crew below the competency threshold (CLOSE 27) automatically sees the panel surfaced inline before task start, without tapping.

EDGE:
3. A crew member crossing the competency threshold mid-shift stops getting the auto-surface behavior on their very next task of that type, without requiring an app restart.
4. A task_type with no authored panels yet (content gap) shows a defined empty/graceful state, not a broken icon or blank auto-surfaced panel.

NEGATIVE:
5. A crew member above threshold attempting to tap-view the panel manually still can (opt-in access is not gated by competency, only the automatic surfacing is).

SILENT FAILURE:
6. Auto-surface logic silently failing to trigger for a genuinely below-threshold crew member (integration gap with CLOSE 27's experience score) would defeat the entire training-safety purpose of this row — verify with a real below-threshold test account, not just a mocked flag.
7. Panel content going stale (SOP changes but panel isn't updated) is a content-maintenance risk, not a code risk — flag as needing a periodic content-audit process tied to SOP changes, not assumed to stay in sync automatically.

**Verification Method:**  
1) Unit tests: tap-to-view always present, auto-surface triggers correctly for below-threshold accounts, opt-in view available for above-threshold accounts. 2) Integration test: real below-threshold test crew account, confirm actual CLOSE 27 experience score correctly drives the auto-surface behavior end-to-end. 3) Threshold-crossing test: confirm behavior changes on the very next task after crossing. 4) Content-gap test: task_type with no panels shows a graceful state. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Instructional-panel-system-3cfe152fc199811cbd5edefcb01a5781_

---
## CULT-003 — Kitchen culture poster
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: permanent physical poster stating The Taza Way + five core principles, visible from work positions, matching the OS visual system.

**Functional Requirement Specification:**  
Kitchen culture poster: permanent physical artifact in the Taza kitchen. Content: "The Taza Way" + five core principles — We Scan, We Sequence, We Anticipate, We Close Strong, We Exceed and Delight. Design matches the Taza OS visual system. Printed/framed/mounted, visible from primary work positions.

**Failure Behavior:**  
Fallback: handwritten list (functional but signals lower standard).

**Acceptance Criteria:**  
Poster printed and mounted in kitchen; visible from Sandra's and Edgar's primary work positions; design matches Taza OS visual system; text exactly matches the five principles

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Kitchen-culture-poster-3cfe152fc1998164badfcfe4d39a9971_

---
## CULT-004 — Visual design standard
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: one cohesive visual design system (fonts, colors, spacing, alert styling) across all crew/kitchen interfaces, driven from a single design-token set.

**Functional Requirement Specification:**  
Visual design standard: all crew-facing and kitchen-facing interfaces share one cohesive design system — font (Inter), weight hierarchy, color palette (dark bg, warm gold emphasis, cool white operational text, deep red alerts only), spacing, border radius, animation timing. Anti-glare hoods on TV displays. Design tokens in a single reference file consumed by all interfaces.

**Failure Behavior:**  
Fallback: per-interface styling (functional but culturally incoherent).

**Acceptance Criteria:**  
All interfaces visually consistent (fonts/colors/spacing/animation) across tablet, touchscreen, TV; design-tokens file exists and is referenced by all front-end code; anti-glare hoods installed on both TVs

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Visual-design-standard-3cfe152fc19981df99ecc53ed2a4ae2e_

---
## CULT-005 — Taza OS Brain as crew member
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: brief screen at event start crediting Taza OS with what it prepared (client story, prep sequence, setup spec, timeline).

**Functional Requirement Specification:**  
Taza OS Brain as crew member: at the start of every event, the tablet shows a ~10s system attribution screen — "Tonight's event was built by Taza OS" plus 3–4 lines of what the system prepared (client story, prep sequence, setup spec, timeline), pulled from the real event record, before the client story begins.

**Failure Behavior:**  
Fallback: no attribution screen (system stays invisible).

**Acceptance Criteria:**  
NORMAL:
1. At event start, tablet shows a ~10s attribution screen ("Tonight's event was built by Taza OS" + 3-4 lines pulled from the real event record) before the client story begins.

EDGE:
2. An event with incomplete record data (e.g. timeline not fully generated yet) still shows a coherent 3-4 line summary from whatever real data exists, not blank lines or placeholder text pretending to be real.
3. Screen duration is consistently ~10s across runs, not drifting significantly shorter/longer in a way that either flashes by unread or stalls the flow into the client story.

NEGATIVE:
4. The attribution content is never fabricated/templated filler presented as if pulled from the event — every line must trace to the actual event record (client story, prep sequence, setup spec, timeline).

SILENT FAILURE:
5. If the event record is missing entirely (edge case, data gap), the screen must not silently show generic/wrong content that looks like it's for this event — verify a defined fallback (skip screen, or clear 'data unavailable' state) rather than a plausible-looking but wrong summary.
6. This screen is brand/culture content, easy to deprioritize in a rebuild — flag alongside KANBAN 1's D-KIT-001 concern: verify this doesn't quietly disappear in a future UI refresh.

**Verification Method:**  
1) Unit test: screen renders correct 3-4 lines sourced from a real event record, timed at ~10s. 2) Data-gap test: incomplete or missing event record, confirm a defined graceful fallback rather than fabricated-looking content. 3) Real-event walkthrough: Nick/Sandra confirm the displayed summary accurately reflects an actual real event's data. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Taza-OS-Brain-as-crew-member-3cfe152fc199810ea24dc4c57f567f81_

---
## CULT-006 — Post-event feedback loop
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: short targeted post-breakdown questionnaire referencing tonight's specific anomalies (partial completions, substitutions, timing) — captures lessons while fresh.

**Functional Requirement Specification:**  
Post-event feedback loop: 20 minutes after event breakdown, Taza OS Brain sends Sandra and Nick an AI-generated targeted questionnaire referencing tonight's specific anomalies (partial completions, substitutions, timing deviations). Simple feedback writes directly to the event record as a KB refinement; complex feedback creates an enhancement note in Nick's review queue.

**Failure Behavior:**  
Fallback: manual post-event notes by Sandra (inconsistent, no system learning).

**Acceptance Criteria:**  
Questionnaire sent within 25 minutes of event close; questions reference specific tonight's-event data, not generic templates; simple responses write to NocoDB within 30s; complex responses create enhancement note; questionnaire length decreases as KB coverage grows

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Post-event-feedback-loop-3cfe152fc19981bd9313e5c3b4575394_

---
## CULT-007 — Sandra's decision capture (photo-inferred)
**Status:**  | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: photograph an event setup and have the system infer likely decisions worth capturing, asking 2-5 targeted questions vs. prior setups.

**Functional Requirement Specification:**  
Sandra's decision capture (photo-inferred): Sandra/Nick photographs event setup, uploads via phone.  AI analysis compares against KB of prior setups and generates 2–5 targeted questions about visible decisions. Answers write to the taza_way_notes field on the relevant NocoDB record. Question volume decreases as KB matures.

**Failure Behavior:**  
Fallback: Sandra verbally explains decisions to Nick, manually logged (slow, non-durable).

**Acceptance Criteria:**  
Photo upload succeeds; overnight analysis generates 2–5 targeted questions referencing specific visible decisions (not generic); answers write to taza_way_notes on correct records; system does not re-ask a question already answered in KB

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Sandra-s-decision-capture-photo-inferred-3cfe152fc19981c6bf67eb5029d9c13b_

---
## CULT-008 — KB taza_way_notes field
**Status:**  | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: searchable notes field on events/menu items/setups/tasks/equipment capturing reasoning behind Taza-specific decisions; task cards show an indicator when a note exists.

**Functional Requirement Specification:**  
KB taza_way_notes field: every relevant NocoDB table (event_templates, menu_items, setup_specs, task_types, equipment) gains a taza_way_notes text field storing the reasoning behind Taza-specific decisions. Written by Sandra/Nick directly, CULT-006, or CULT-007. Searchable; task cards show an indicator when a note exists.

**Failure Behavior:**  
Fallback: no rationale capture — Taza-way knowledge stays in Sandra's head.

**Acceptance Criteria:**  
taza_way_notes field added to all specified tables; content written by CULT-006/CULT-007 pipelines; field searchable; task cards show indicator when a note exists

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/KB-taza_way_notes-field-3cfe152fc19981a7ac8bf92138b397c7_

---
## CULT-009 — TV dashboard Lexicon header rotation
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV dashboard header rotates through Lexicon terms + definitions every 8-10 min — passive vocabulary reinforcement.

**Functional Requirement Specification:**  
TV dashboard Lexicon header rotation: the TV dashboard header rotates through Taza Lexicon terms and definitions, one at a time, every 8–10 minutes, styled subtly to match the dashboard. Pulled live from the CULT-001 Lexicon table.

**Failure Behavior:**  
Fallback: no ambient vocabulary reinforcement.

**Acceptance Criteria:**  
Header bar rotates through Lexicon terms at configured interval; design integrated not disruptive; adding a new term to the Lexicon causes it to appear in rotation automatically

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/TV-dashboard-Lexicon-header-rotation-3cfe152fc199811ea640d4e48688a295_

---
## CULT-010 — Task card language standard
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: task card text reads as terse kitchen craft language ("Done. Stored WIC-1-4.") not enterprise phrasing ("Task completed successfully").

**Functional Requirement Specification:**  
Task card language standard: all task card text (labels, confirmations, status, errors) uses terse craft-oriented kitchen language, not enterprise software phrasing. E.g. "Done. Stored WIC-1-4." not "Task completed successfully." Enterprise phrasing is prohibited on crew-facing surfaces.

**Failure Behavior:**  
Fallback: default NocoDB system language.

**Acceptance Criteria:**  
NORMAL:
1. All crew-facing card text (labels, confirmations, status, errors) uses terse craft-oriented language (e.g. "Done. Stored WIC-1-4."), not enterprise phrasing (e.g. "Task completed successfully.").

EDGE:
2. Error messages specifically (often the last place engineers default to generic library/framework text) also follow the standard — not just happy-path confirmations.
3. Dynamically generated text (e.g. AI-composed status strings) is checked against this standard too, not just hardcoded UI strings.

NEGATIVE:
4. Any new crew-facing string added in a future feature that doesn't match this standard should be catchable before shipping.

SILENT FAILURE:
5. This is a brand/culture requirement, not a functional one — the risk is it silently erodes over time as new features get added by people (or AI debate agents) unaware of the standard. Verify there's a concrete, checkable reference (a style guide doc or a lint-style checklist) that any new PR/spec can be checked against, not just tribal knowledge.
6. Third-party or system-default error messages (browser errors, library exceptions surfacing raw) leaking through to the crew-facing UI unfiltered would violate this standard even if all custom-authored text is correct — verify raw system errors are caught and translated, not just that authored copy is on-brand.

**Verification Method:**  
1) Content audit: review every crew-facing string (labels, confirmations, status, errors) against the standard, including error paths, not just happy path. 2) Raw-error leak test: force a low-level system/library error, confirm it's caught and translated to on-brand copy rather than leaking raw text to the crew UI. 3) Style-guide artifact: produce a checkable reference doc/examples list so future additions (human or AI-authored) can be validated against it. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Task-card-language-standard-3cfe152fc19981d6a28dda7f3faaee0e_

---
## CULT-011 — Event completion artifact
**Status:**  | **Priority:** P3 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: end-of-event done screen shows real summary (client, guest count, duration, tasks executed, substitutions), closing with "That's the Taza standard."

**Functional Requirement Specification:**  
Event completion artifact: the tablet done screen at end of every event displays real NocoDB event data — client name, guest count, duration, tasks executed, substitutions — followed by "That's the Taza standard."

**Failure Behavior:**  
Fallback: generic done screen (functional but misses cultural reinforcement).

**Acceptance Criteria:**  
Done screen displays real event data pulled from NocoDB, not static text; displays within 10s of event close; "That's the Taza standard." appears on every completion

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Event-completion-artifact-3cfe152fc19981eea94cf7478ed0c807_

---
## CULT-012 — The Taza Way declaration
**Status:**  | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: welcome declaration on a new crew member's first Taza event (detected via PIN, no prior history) — five Lexicon-aligned statements, revisitable via settings.

**Functional Requirement Specification:**  
The Taza Way declaration: a 60-second craft-language artifact shown on the tablet at a crew member's first Taza event (detected via PIN system, no prior event history) — "Welcome to Taza Crew" + five Lexicon-aligned statements + close. Displays once per crew member; accessible afterward via a settings icon.

**Failure Behavior:**  
Fallback: no first-event declaration (culture absorbed only through environment).

**Acceptance Criteria:**  
Declaration displays on first-event tablet start for new crew (no prior PIN history); displays once automatically; accessible via icon on subsequent events; content matches five Lexicon principles; reads in ≤60 seconds

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/The-Taza-Way-declaration-3cfe152fc1998123bff7eec7b404b428_
