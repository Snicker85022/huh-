# Taza OS URS — KIT cluster
_Exported: 2026-09-19 21:35 | 14 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-KIT-101 — Equipment cleaning creates auditable closing cards
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every equipment-cleaning obligation generates a card closable only by recording who cleaned it and when — an auditable record, no silent skips.

**Atomic Requirement:**  
The system shall generate auditable closing or post-use cleaning cards for each configured kitchen-equipment cleaning obligation.

**Functional Requirement Specification:**  
For each configured kitchen-equipment cleaning obligation (e.g. end-of-day, post-use), the system shall generate an auditable closing card. Closing that card shall require and record: equipment identifier, responsible crew (by PIN), and timestamp. One card per obligation per period; closure is idempotent on replay.

**Inputs:**  
Equipment cleaning schedule configuration; crew PIN at close; system timestamp.

**Outputs:**  
One auditable close record per obligation (equipment, crew, timestamp) in the audit log ([[SPEC:PROD-22]]).

**Trigger:**  
Scheduled end-of-period or post-use event per the equipment obligation configuration.

**Invariants:**  
One card per configured obligation per period; closure requires equipment + crew + timestamp; unclosed obligations are visible, not silently absent.

**Failure Behavior:**  
An equipment item with a configured obligation that has no corresponding closed card by end-of-period is flagged as a compliance gap — never silently skipped. Missing crew identity on a close blocks the close ([[SPEC:URS-KANBAN-002]] pattern).

**Failure Mode Addressed:**  
Equipment cleaned by nobody because the obligation was invisible — no card, no record, no accountability, and no way to prove compliance for health/safety review.

**Acceptance Criteria:**  
Each configured obligation produces one card and its closure records equipment, crew, and timestamp.

**Verification Method:**  
Configuration audit and end-of-day workflow test.

**Maintenance Requirements:**  
Keep the equipment obligation configuration current as kitchen kit changes; verify card generation after any task-engine update ([[SPEC:PROD-01]]).

**Dependency Notes:**  
Generated as a close_kind=EQUIPMENT_CLEANING card per [[SPEC:PROD-38]]/CLOSE 4. Closure writes equipment ID, crew PIN ([[SPEC:PROD-12]]), and timestamp to the audit log ([[SPEC:PROD-22]]). Configuration drives which equipment items have end-of-day obligations. Part of BUNDLE-KANBAN-EXECUTION. Parent CLOSE 4.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Equipment-cleaning-creates-auditable-closing-cards-8bd4e2e68b55461e98308e46f35c1dee_

---
## URS-KIT-102 — Receiving sets persistent allergen flags
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every major allergen entering the kitchen lights a persistent flag on every screen, staying on until formally recorded consumed/removed — never present but invisible.

**Atomic Requirement:**  
When a received shopping item contains a configured major allergen, the system shall set and display a persistent allergen flag until structured consumption or removal clears it.

**Functional Requirement Specification:**  
When a received shopping item contains a configured major allergen, the system shall immediately set a persistent allergen flag on that item and its bin location, display it on all relevant surfaces (kanban card dot, situational displays, mobile view), and maintain it until a structured consume-or-remove close explicitly clears it. Ordinary edits, renames, and location moves cannot clear the flag.

**Inputs:**  
Received item + its allergen attributes ([[SPEC:CAT-001]]); crew confirmation of receipt; structured consume/remove close to clear.

**Outputs:**  
A persistent, multi-surface allergen flag from receive through to structured clearance; a clearance record (who, when, how) in the audit log ([[SPEC:PROD-22]]).

**Trigger:**  
A shopping item with a configured major allergen is received; cleared only on structured consume/remove close.

**Invariants:**  
Flag is set synchronously on receive, before the receive is confirmed; flag persists across renames/edits/moves; only a structured close clears it; flag is visible on ALL surfaces that show operational context.

**Failure Behavior:**  
An allergen flag set on receive cannot be cleared by any edit, rename, or incidental action — only a structured consume or remove close. A stale allergen flag persists and displays with a staleness indicator rather than silently disappearing (per [[SPEC:URS-HEALTH-005]]/[[SPEC:URS-DISP-003]] fail-visible principle). A flag that fails to write on receive blocks the receive action — not silently dropped.

**Failure Mode Addressed:**  
A major allergen arriving in the kitchen without a persistent visible flag — crew unaware of its presence, cross-contact risk unmanaged, and no audit trail of when the allergen entered and was cleared.

**Acceptance Criteria:**  
NORMAL:
1. Receiving an item with a configured major allergen sets a persistent flag on the item AND its bin location, visible on kanban card dot, situational displays, and mobile view simultaneously.
2. Flag clears only on a structured consume-or-remove close — and clears correctly when that close happens.

EDGE:
3. An item with multiple configured allergens (e.g. contains both nuts and dairy) shows all applicable flags, not just one.
4. The same bin later receives a non-allergen item after the flagged item is removed — flag clears with the removal, doesn't linger on the bin for the new item.
5. Item is renamed or moved between bins while flagged — flag persists correctly on the right entity through the change (this is explicitly called out as a case that must NOT clear the flag).

NEGATIVE:
6. Ordinary edit/rename/location-move actions attempted as a way to clear the flag are rejected — only the structured consume-or-remove close clears it.
7. An item received without going through the structured receiving flow (if such a path exists) must not silently skip allergen detection.

SILENT FAILURE:
8. If the flag is set in the backend but fails to render on even one of the three required surfaces (kanban dot / situational display / mobile view), this is a P0 failure — verify all three are tested together, not independently assumed consistent.
9. A flag-clearing close that fails partway (clears on backend but a display doesn't refresh) must not leave a display showing 'safe' when the backend still considers it flagged, or vice versa.

**Verification Method:**  
1) Unit tests: single-allergen flag set/clear, multi-allergen flag set, rename/move does not clear. 2) Cross-surface integration test: verify flag state is consistent across kanban dot, situational display, and mobile view at the same moment, not tested in isolation. 3) Fault-injection test: force one surface's refresh to fail post-clear, confirm the mismatch is detectable, not silently inconsistent. 4) Food-safety review: Nick/Sandra confirm the flag behavior against actual allergen-handling SOP, not just the written spec. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the configured major-allergen list current (aligned with Taza's menu and the [[SPEC:CAT-001]] allergen_notes attribute); verify flag-clear behaviour after any close-path change; re-test multi-surface visibility after any display/push change.

**Dependency Notes:**  
Allergen detection keyed against the catalog allergen attribute ([[SPEC:CAT-001]] dietary_flags + allergen_notes). Flag surfaced on: kanban card signals (KANBAN 4 allergen dot), TCL East situational display (DISPLAY 23), and staff mobile situational view (SHOP 7). Clear only on structured consume/remove close (CLOSE 11 / [[SPEC:PROD-38]] close_kind=ALLERGEN_RECEIVING). Cross-ref: KIT-002 (task gate) overlaps CLOSE 11. Part of BUNDLE-KANBAN-EXECUTION. Parent CLOSE 4.

**Rationale:**  
P0, highest-priority row in the KIT-10x cluster — food-safety and liability requirement, not a UX nicety.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Receiving-sets-persistent-allergen-flags-86a3782302a0431ea2e4c1b9f6f2548e_

---
## URS-KIT-103 — Van-load card requires complete departure checklist
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: van-load card refuses to close until every required item is checked off or has a documented reason for absence — structurally impossible to depart incomplete.

**Atomic Requirement:**  
A van-load card shall not close until every required BEO and standard loadout item is checked or explicitly exception-routed.

**Functional Requirement Specification:**  
A van-load card shall block closure until every required BEO and standard loadout item is either checked (physically loaded) or explicitly exception-routed (with a recorded reason). The completed, queryable checklist is the departure gate. No departure can be confirmed without a fully resolved checklist.

**Intent / User Need:**  
Van-scoreboard shows every outstanding item.

**Inputs:**  
BEO-derived required items ([[SPEC:PROD-01]]/[[SPEC:W15]]); standard loadout configuration; crew check-off per item; exception routing reason per any unloaded item.

**Outputs:**  
A fully-resolved van-load close record (all items checked or exception-routed, with reasons) and an unlocked departure state.

**Trigger:**  
Crew attempts to close the van-load card.

**Invariants:**  
Every required item is either checked or exception-routed before closure; no partial or silent departure; the resolved checklist is canonical and queryable.

**Failure Behavior:**  
An unchecked required item blocks closure with a specific, named prompt (not a generic 'checklist incomplete'). An exception-routed item records the reason before closure is permitted. A duplicate close attempt is idempotent. The completed checklist is queryable in under one second.

**Failure Mode Addressed:**  
Departing for an event with an incomplete load — the most expensive and unrecoverable failure mode in catering operations. A missing item discovered at the venue cannot be retrieved in time.

**Acceptance Criteria:**  
NORMAL:
1. Every required BEO + standard loadout item checked (physically loaded) → card closes, departure confirmed.
2. Every item either checked or exception-routed with a recorded reason → card closes.

EDGE:
3. A loadout with zero standard items (unusual/minimal event) still requires the BEO-specific items to be resolved — an empty standard list must not be misread as 'nothing to check.'
4. An item exception-routed then later actually loaded before departure — system allows the exception to be converted back to checked, not stuck as a permanent exception.
5. Two crew members racing to check off the same item simultaneously — no double-count, no lost update.

NEGATIVE:
6. Any required item neither checked nor exception-routed → card refuses to close, departure cannot be confirmed — no override path except the documented exception-routing.
7. Exception-routing attempted with no reason text → rejected, reason is mandatory not optional.

SILENT FAILURE:
8. A checklist that appears 100% resolved in the UI but whose underlying record has an unresolved item (sync/race condition) must not allow departure confirmation — the close check re-validates server-side, not just trusts client state.
9. Exception-routed items must remain visibly flagged as exceptions (not visually indistinguishable from normally-checked items) so a reviewer can't mistake 'exception' for 'complete.'

**Verification Method:**  
1) Unit tests: full-checklist close, partial-checklist rejection, exception-routing with/without reason. 2) Integration test: concurrent check-off from two devices on the same card, assert no lost update. 3) Server-side re-validation test: manipulate client-side state to falsely appear complete, confirm server rejects the close. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the standard loadout configuration current; regenerate the BEO-derived required items whenever the event menu or logistics change; test the negative path (unchecked item blocks) after any close-path change.

**Dependency Notes:**  
Checklist items sourced from the BEO/event record ([[SPEC:PROD-19]]/[[SPEC:W15]]) plus the standard loadout configuration. Van scoreboard (DISPLAY 25/DISPLAY 4) displays checklist state. Closure conforms to [[SPEC:PROD-38]] (close_kind van-load). Exception-routing for genuinely missing items via EXCEPT 1. Queryable in <1s from the canonical record. Part of BUNDLE-KANBAN-EXECUTION. Parent CLOSE 4.

**Rationale:**  
P0, highest-stakes operational gate in the system — cost of a miss = emergency grocery runs, broken events.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Van-load-card-requires-complete-departure-checklist-3b612f84ec3046bba2666494df2dd237_

---
## URS-KIT-104 — Prep close captures portion count and size
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: prep-card close records exact portion count and size, available at service start with no recount needed.

**Atomic Requirement:**  
A prep-task close shall capture the number of prep portions and portion size before completion.

**Functional Requirement Specification:**  
A prep-task close shall require the crew to enter both the number of completed prep portions and the portion size before completion. Both values shall be stored, be available to downstream displays and inventory without recounting, and require a structured amendment to change post-close.

**Inputs:**  
Crew-entered portion count (integer) and portion size (quantity + unit) at prep close.

**Outputs:**  
A stored portion count + size on the close record, available to all downstream surfaces.

**Trigger:**  
Crew closes a prep-type task card.

**Invariants:**  
Both values required; neither can be zero or blank; values are stored immutably at close; downstream queries return the captured values directly.

**Failure Behavior:**  
Either value missing or zero blocks the prep close with a specific prompt. Stored values are immutable after close — corrections require a structured amendment, not a silent edit.

**Failure Mode Addressed:**  
Crew recounting portions at the point of service because nobody captured the number at prep close — wasted time, inaccurate count, and an unnecessary interruption during event execution.

**Acceptance Criteria:**  
Both values are required, stored, and available to downstream displays without recounting.

**Verification Method:**  
Task-close integration test.

**Maintenance Requirements:**  
Ensure the portion-size unit options align with the catalog ([[SPEC:CAT-001]] units); verify both fields populate on the downstream inventory lot record ([[SPEC:URS-INV-003]]).

**Dependency Notes:**  
Captured values feed downstream displays (portion-count availability removes the need for anyone to recount) and the inventory lot record (CLOSE 8 qty fields). Conforms to [[SPEC:PROD-38]] (close_kind=PREP). Part of BUNDLE-KANBAN-EXECUTION. Parent CLOSE 4.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Prep-close-captures-portion-count-and-size-666ea1282596447a91f2f8de1225a1f5_

---
## URS-KIT-105 — Shopping check-off captures actual substitution
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a shopper substitution records the actual item/quantity obtained right in the store, publishing to the kitchen immediately.

**Atomic Requirement:**  
When a shopper did not obtain the listed item exactly, check-off shall require the actual item and quantity and publish the substitution downstream.

**Functional Requirement Specification:**  
When a shopper checks off a listed item that was not obtained exactly as listed (different brand, size, quantity, or unavailable), the check-off shall require the actual item obtained and actual quantity, and shall publish the substitution to downstream prep information before closing. An exact purchase closes without the substitution fields.

**Inputs:**  
The listed item + intended quantity; crew indication that a substitution occurred; actual item obtained + actual quantity.

**Outputs:**  
A substitution record (listed item, actual item, actual qty) written to the canonical shopping record; affected prep information updated.

**Trigger:**  
Crew marks a shopping item as obtained with a deviation from the planned item or quantity.

**Invariants:**  
Substitution requires actual item + actual quantity (not optional); the substitution is published to prep information before the check-off is confirmed; an exact purchase never triggers the substitution flow.

**Failure Behavior:**  
A check-off with no deviation closes normally; a deviation without actual item/quantity entered blocks the check-off until values are supplied. A successfully submitted substitution updates affected prep information before the shopper leaves the store.

**Failure Mode Addressed:**  
A substituted item silently recorded as the original — the kitchen expecting X and prepping for X while the shopper bought Y — discovered only when the cook reaches for it.

**Acceptance Criteria:**  
Exact purchase closes normally; substitution requires actual values and updates affected prep information.

**Verification Method:**  
Shopping substitution end-to-end test.

**Maintenance Requirements:**  
Align the substitution schema with the vendor-reliability tracker ([[SPEC:URS-KIT-106]]); verify downstream prep propagation after any shopping-plan schema change.

**Dependency Notes:**  
Writes through the canonical shopping backend (SHOP 8) so the kitchen board reflects the actual item purchased. Substitution data propagates to affected prep information and feeds the vendor-reliability tracker (SHOP 4). Folded into [[SPEC:PROD-05-V2]] (SQL/JS, [[SPEC:URS-KIT-105]]). Part of BUNDLE-SHOPPING-AGGREGATION.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Shopping-check-off-captures-actual-substitution-5a921a6f74f14797a829524e939e3aef_

---
## URS-KIT-106 — Vendor substitution reliability triggers review
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: automatic notification when the same store fails to reliably supply the same category 3+ times in a rolling 30 days.

**Atomic Requirement:**  
Three substitutions in the same category from the same store within thirty days shall create one review flag for Nick.

**Functional Requirement Specification:**  
When three or more substitutions are recorded in the same item category from the same store within any rolling 30-day window, the system shall create exactly one review flag for Nick. The flag is idempotent on replay and on additional substitutions beyond the third in the same window.

**Inputs:**  
Substitution records ([[SPEC:URS-KIT-105]]) filtered by category + store + 30-day window.

**Outputs:**  
One review flag for Nick when the threshold is met; no flag below threshold.

**Trigger:**  
A substitution record is written ([[SPEC:URS-KIT-105]]); rolling-window count evaluated.

**Invariants:**  
Threshold is exactly three in 30 days per category/store pair; exactly one flag per triggered threshold regardless of additional subs or replays.

**Failure Behavior:**  
Counts below three produce no flag; the third qualifying substitution creates exactly one idempotent flag; a retry of the count does not duplicate the flag.

**Failure Mode Addressed:**  
A systematically unreliable vendor or store silently degrading prep quality through repeated substitutions that are individually tolerable but collectively indicate a sourcing problem.

**Acceptance Criteria:**  
Counts below three create no flag; the third qualifying substitution creates one idempotent flag.

**Verification Method:**  
Boundary and replay tests.

**Maintenance Requirements:**  
Keep the 30-day window configurable; review the threshold if the substitution volume materially changes.

**Dependency Notes:**  
Counts substitution records from [[SPEC:URS-KIT-105]] by category + store + 30-day window. Review flag routed to Nick via EXCEPT 1 (Exception Router) + EXCEPT 3 (Notifier). Idempotent: three subs create one flag; a fourth does not create a second. Part of BUNDLE-SHOPPING-AGGREGATION.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Vendor-substitution-reliability-triggers-review-1c26f8d0a8fb4cc4be9204bc04494f6a_

---
## URS-KIT-107 — Random bonus cards collect food-safety temperatures
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: random bonus cards prompt crew for a physical temperature reading during service, reward the check, and immediately alert if out of safe range.

**Atomic Requirement:**  
The system shall issue randomized bonus cards for physical temperature sampling, record entered readings, award points, and alert on threshold exceedance.

**Functional Requirement Specification:**  
The system shall issue randomised bonus cards during service for physical temperature sampling. On card close, the crew enters the actual measured temperature reading; the system stores it, awards points to the crew member, and triggers an immediate exception alert if the reading exceeds configured safe thresholds. Randomisation of timing and target item prevents predictable sampling patterns. Cadence (Nick 2026-10-01): semi-rare by design — 1 to 4 cards per high-cadence week, roughly 1 per low-cadence two-week cycle; random within that envelope, never clumped in one shift.

**Inputs:**  
Randomised trigger (time + target item); crew-entered measured temperature reading; configured safe-temperature thresholds.

**Outputs:**  
A stored temperature reading; crew points; an immediate exception alert if the reading is unsafe.

**Trigger:**  
Randomised system event during service; crew close with an entered reading.

**Invariants:**  
Sampling timing is randomised within a bounded cadence (1–4/week high-cadence, ~1/two-week low-cadence — Nick 2026-10-01); a reading that exceeds threshold triggers an immediate alert, not a deferred log entry; points awarded only on a completed, valid reading.

**Failure Behavior:**  
An unsafe reading (outside configured thresholds) creates an immediate exception alert — not a logged-and-forgotten record. A duplicate card submission is idempotent. A card that generates no reading is not closed as a successful sampling.

**Failure Mode Addressed:**  
Temperature monitoring reduced to a paper-checklist exercise that crew fill in from memory rather than physical measurement — missing real exceedances and providing false compliance evidence.

**Acceptance Criteria:**  
Sampling is randomized within the bounded cadence (1–4 per high-cadence week, ~1 per low-cadence two-week cycle); valid reading is stored and rewarded; unsafe reading creates an immediate alert.

**Verification Method:**  
Statistical scheduling test and threshold integration test.

**Maintenance Requirements:**  
Keep the configured safe-temperature thresholds aligned with TCS food-safety requirements ([[SPEC:CAT-006]]); verify the alert path ([[SPEC:PROD-23]]/[[SPEC:PROD-25]]) after any exception-router change; tune randomisation window as event cadence evolves.

**Dependency Notes:**  
Temperature reading stored in the audit log ([[SPEC:PROD-22]]) and flagged to EXCEPT 1 (Exception Router) on threshold exceedance. Points awarded via the gamification layer (KANBAN 9/KANBAN 10 pattern). Randomisation prevents predictable sampling patterns. Part of BUNDLE-KANBAN-EXECUTION. Ties to CATALOG 7 (TCS danger-zone constraints).

**External Dependencies:**  
Calibrated physical thermometer.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Random-bonus-cards-collect-food-safety-temperatures-dbe233ae4ac740dcbab4df8b0030579a_

---
## URS-KIT-METHOD-001 — Taza Method cards use distinct visual identity
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a Taza Method card is instantly recognizable on the board (gold border + brand mark) — crew know to slow down before starting.

**Atomic Requirement:**  
Every Taza Method card shall render the approved gold border, brand mark, and TAZA METHOD label.

**Functional Requirement Specification:**  
Every task card flagged as a Taza Method shall render all three identifiers in their correct positions: the approved gold border (#c7ae59), the diamond-filigree brand mark, and the TAZA METHOD label. No standard task card shall carry any of these three identifiers. The visual distinction shall be unambiguous at the display distances used on MT1/MT2.

**Inputs:**  
Task record with is_taza_method flag; the approved gold/filigree/label assets.

**Outputs:**  
A rendered Taza Method card with gold border, brand mark, and TAZA METHOD label, visually unambiguous from a standard card.

**Trigger:**  
Kanban card render when the task has is_taza_method=true.

**Invariants:**  
All three identifiers present on every Method card; none present on any standard card; the gold colour is exactly #c7ae59 (not approximate).

**Failure Behavior:**  
A Taza Method card missing any of the three identifiers is a rendering bug — logged and surfaced, not silently served. A standard task card that accidentally carries any Method identifier is equally a rendering bug.

**Failure Mode Addressed:**  
Crew unable to distinguish a proprietary Taza Method from a standard task at a glance — leading to the method being executed casually without pausing to read the guidance.

**Acceptance Criteria:**  
A flagged method card displays all three identifiers; a standard card displays none of them.

**Verification Method:**  
UI inspection and automated component test.

**Maintenance Requirements:**  
Keep the brand assets version-controlled; test the three-identifier assertion on every kanban renderer release.

**Dependency Notes:**  
Visual identity applied by the kanban renderer (KANBAN 1/KANBAN 2). The gold border + diamond-filigree mark + TAZA METHOD label are the same brand language as the Mom's Table card-game visual system (D-KIT-001). Part of BUNDLE-TAZA-METHOD. Parent KANBAN 11. Hex: #c7ae59.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Taza-Method-cards-use-distinct-visual-identity-651ed383052b4953805bbb4019645537_

---
## URS-KIT-METHOD-002 — First encounter plays Taza Method animation
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a crew member's first encounter with any Taza Method plays an unskippable ~2s animation — a guaranteed pause before executing an unseen technique.

**Atomic Requirement:**  
On a crew member’s first encounter with a Taza Method card, the system shall play the approved unskippable animation once.

**Functional Requirement Specification:**  
On a crew member's first encounter with a specific Taza Method card, the system shall play the approved ~2-second fish-and-starburst animation once, unskippably, before revealing the card content. Subsequent encounters with the same method by the same crew member do not auto-play the animation. The animation is method-specific, not global (a crew member who has seen Method A still gets the animation on first encounter with Method B).

**Inputs:**  
Current crew member identity (PIN); current method/card ID; first-encounter state from the crew record.

**Outputs:**  
A ~2-second unskippable animation displayed to the crew member on first encounter with the specific method.

**Trigger:**  
A crew member opens a Taza Method card for the first time (per crew + method ID combination).

**Invariants:**  
Unskippable for the full ~2-second duration; plays exactly once per crew + method combination; subsequent encounters never auto-play.

**Failure Behavior:**  
If the first-encounter state cannot be read, treat the encounter as first (play the animation) — err on the side of reinforcement, not silent skip. The animation cannot be dismissed early by any tap or swipe.

**Failure Mode Addressed:**  
A proprietary Taza technique being executed by a crew member who has never paused to see it explained — the animation creates a forced moment of attention that cannot be skipped.

**Acceptance Criteria:**  
First encounter plays for approximately two seconds and cannot be skipped; subsequent encounters do not autoplay it.

**Verification Method:**  
Automated state test plus UI demonstration.

**Maintenance Requirements:**  
Keep the animation asset version-controlled; re-test the once-per-crew-method state after any crew-record schema change.

**Dependency Notes:**  
First-encounter state stored per crew member + method ID (KANBAN 7 writes the acknowledgment record that marks the encounter as seen). Animation plays before acknowledgment. State stored in the local device or the canonical crew record — reconcile in debate (local vs server). Part of BUNDLE-TAZA-METHOD. Parent KANBAN 11. Animation: ~2s fish-and-starburst (D-KIT-001).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/First-encounter-plays-Taza-Method-animation-4f9af41c07684ce79c23cdbd0e0239ea_

---
## URS-KIT-METHOD-003 — First encounter requires method acknowledgment
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: crew actively confirm they've seen a Taza Method before the SOP shows, logged with name/method/time — evidence of training.

**Atomic Requirement:**  
The system shall record crew ID, method/card ID, and timestamp when first-encounter acknowledgment is completed.

**Functional Requirement Specification:**  
After the first-encounter animation (KANBAN 6), the system shall present an 'I understand — show me how' acknowledgment gate before revealing the SOP content. On confirmation, the system shall write exactly one durable acknowledgment record containing crew ID, method/card ID, and timestamp. The SOP is not accessible until this record is written.

**Intent / User Need:**  
Also serves as liability protection.

**Inputs:**  
Crew confirmation tap ('I understand — show me how'); crew ID (from active PIN session); method/card ID; system timestamp.

**Outputs:**  
One durable acknowledgment record (crew, method, timestamp) in the audit log; access to the SOP content unlocked.

**Trigger:**  
Crew taps 'I understand — show me how' after the first-encounter animation.

**Invariants:**  
SOP gated until acknowledgment is written; exactly one record per crew + method (idempotent); record is durable and audit-log backed.

**Failure Behavior:**  
If the acknowledgment write fails, the SOP remains gated and the crew member cannot proceed with the method card — no silent pass-through. A replay of the acknowledgment action is idempotent (one record, not duplicated).

**Failure Mode Addressed:**  
A crew member clicking past the animation and executing the method without any evidence that they saw it — Taza has no record and no defence if the technique is later disputed.

**Acceptance Criteria:**  
The SOP remains gated until acknowledgment; one durable acknowledgment record is written with crew, method, and timestamp.

**Verification Method:**  
Database inspection and end-to-end UI test.

**Maintenance Requirements:**  
Keep the acknowledgment schema aligned with [[SPEC:PROD-22]] audit log; verify SOP-gating logic after any card-rendering change.

**Dependency Notes:**  
Acknowledgment record is written to the audit log ([[SPEC:PROD-22]]) with crew ID (from PIN/[[SPEC:PROD-12]]), method/card ID, and timestamp. The SOP remains gated until this acknowledgment is recorded. Feeds the leaderboard/streak system (KANBAN 10) as a qualifying encounter. Part of BUNDLE-TAZA-METHOD. Parent KANBAN 11.

**Rationale:**  
Phrasing "I understand — show me how" is a first-class UX requirement (not generic "OK") — frames as seeking guidance, not dismissing a warning.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/First-encounter-requires-method-acknowledgment-85d15ac9b6c54573adb69a69814cd678_

---
## URS-KIT-METHOD-004 — Method cards expose inline Show Me instruction
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: tapping a Method card shows technique guidance right there on the same screen — no navigating away — dismiss with one tap.

**Atomic Requirement:**  
A Taza Method card shall open its associated instructional content in a non-blocking, tap-to-dismiss panel.

**Functional Requirement Specification:**  
A Taza Method card shall expose its associated instructional content (SOP link or 3–4 panel Show Me sequence) in a non-blocking panel that opens directly from the card without navigating away from the kanban board. The panel shall dismiss with a single tap and shall not obscure the full board behind it.

**Inputs:**  
The instructional asset linked from the task record (SOP URL or embedded Show Me panels); crew tap on the 'Show Me' affordance.

**Outputs:**  
A non-blocking instructional panel showing the correct SOP or Show Me sequence, dismissible in one tap.

**Trigger:**  
Crew taps the 'Show Me' affordance on a Taza Method card.

**Invariants:**  
Panel is non-blocking (board remains visible/operable); single-tap dismiss; the correct asset opens (not a generic SOP library landing page).

**Failure Behavior:**  
If the instructional asset is unavailable (SOP not yet authored or link broken), the panel opens with a 'guidance not yet available' state rather than a blank or an error, so the crew member knows the gap exists.

**Failure Mode Addressed:**  
Crew leaving the card to search for technique guidance on a phone or by asking someone — breaking their task-flow and creating an interruption during prep. The instruction should be where the work is.

**Acceptance Criteria:**  
The correct asset opens from the card, does not block the entire screen, and closes with one tap.

**Verification Method:**  
UI demonstration using at least one method card.

**Maintenance Requirements:**  
Keep SOP links current as procedures are updated ([[SPEC:PROD-15]]); verify panel render on all kanban surfaces (MT1/MT2) after any UI change.

**Dependency Notes:**  
The instructional asset (SOP or 3–4 panel Show Me) is linked from the task record / [[SPEC:PROD-15]] SOP library. The panel must not block the full kanban board (MT1/MT2 remain operable while the panel is open). Part of BUNDLE-TAZA-METHOD. Parent KANBAN 11. 3–4 panel Show Me format is V1 target; full SOP pages linked in V1.x+.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Method-cards-expose-inline-Show-Me-instruction-b746bceb18eb43e5906c9d1f25bc7c7f_

---
## URS-KIT-METHOD-005 — Questions reward both learner and teacher
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: points awarded to both the asker and the answerer of a question — asking for help rewarded as much as knowing the answer.

**Atomic Requirement:**  
Closing an “I have a question” interaction shall create one learner award and one teacher award linked to the same interaction.

**Functional Requirement Specification:**  
Closing an 'I have a question' interaction shall create exactly two attributable point transactions: one for the learner (crew member who asked) and one for the teacher (crew member recorded as teaching). Both are linked to the same interaction ID. The award is atomic and idempotent on replay.

**Inputs:**  
Learner crew ID; teacher crew ID; interaction close event with unique interaction ID.

**Outputs:**  
Two atomic, linked point transactions (learner + teacher) on the scoring ledger.

**Trigger:**  
An 'I have a question' interaction is closed with both crew IDs recorded.

**Invariants:**  
Exactly two transactions per interaction; atomic write (both or neither); idempotent on replay; both transactions carry the same interaction ID.

**Failure Behavior:**  
If either award write fails, both are rolled back (atomically) — no partial award where learner gets points but teacher doesn’t, or vice versa. Idempotent on retry (same interaction ID produces no additional transactions).

**Failure Mode Addressed:**  
A kitchen culture where asking questions feels like admitting weakness or slowing the team down — the dual reward makes asking and teaching equally valued, reinforcing the 'I have a question' behaviour as a positive contribution.

**Acceptance Criteria:**  
Exactly two attributable point transactions are created and no duplicate award occurs on retry.

**Verification Method:**  
Integration test with idempotent retry.

**Maintenance Requirements:**  
Keep point values configurable; verify atomic write after any scoring-ledger change.

**Dependency Notes:**  
Both point transactions written to the scoring ledger via [[SPEC:PROD-22]] (audit log) with learner crew ID, teacher crew ID, and interaction ID. The interaction ID provides the idempotency key (retry creates no duplicate). Points feed the leaderboard (KANBAN 10). Part of BUNDLE-TAZA-METHOD. Parent KANBAN 11.

**Rationale:**  
"Awards both asker and teacher" is a first-class cultural design decision (D-KIT-001), not a nice-to-have.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Questions-reward-both-learner-and-teacher-e7cc042a54454fe19a15c1f86d5c4c3a_

---
## URS-KIT-METHOD-006 — Correct method closures produce streaks and leaderboard
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: 10 consistent correct Taza Method executions earns a visible badge and updates the kitchen leaderboard.

**Atomic Requirement:**  
Ten qualifying correct Taza Method closures shall produce one streak badge and update the MT1/MT2 leaderboard.

**Functional Requirement Specification:**  
After ten qualifying correct Taza Method closures by the same crew member, the system shall award exactly one compliance streak badge to that crew member and update the MT1/MT2 leaderboard to reflect the new ranking. 'Qualifying correct closure' means the Method card was closed with acknowledgment and correct execution (not a Short Stop or exception). Badge award is idempotent at the threshold.

**Inputs:**  
Qualifying correct method closure events per crew member; current closure count from the scoring ledger.

**Outputs:**  
One streak badge awarded to the crew member at count 10; updated leaderboard on MT1/MT2.

**Trigger:**  
The 10th qualifying correct Taza Method closure is recorded for a crew member.

**Invariants:**  
Exactly one badge per 10-close threshold; idempotent; counts 1–9 produce no badge; leaderboard reflects the current ranking within one push cycle of the badge award.

**Failure Behavior:**  
Counts 1–9 produce no badge; count 10 produces exactly one badge; a replay of count 10 produces no duplicate. Leaderboard update is near-real-time after the badge is awarded.

**Failure Mode Addressed:**  
A gamification system that gives points but no visible milestone — crew accumulate score invisibly and the motivation decays. The streak badge creates a visible, social moment at count 10.

**Acceptance Criteria:**  
Counts 1–9 do not award the badge; count 10 awards it once; leaderboard reflects the new score.

**Verification Method:**  
Boundary-value test and display inspection.

**Maintenance Requirements:**  
Keep the qualifying-closure definition aligned with [[SPEC:PROD-12]] acknowledgment requirements; verify leaderboard push after any display-push change ([[SPEC:PROD-04]]).

**Dependency Notes:**  
Counts qualifying correct Taza Method closures per crew member from the scoring ledger ([[SPEC:PROD-22]]). Badge award is idempotent at count 10 (count 11+ does not create a second badge for the same streak). Leaderboard ranking displayed on MT1/MT2 (KANBAN 1/KANBAN 2 gamemaster view). Part of BUNDLE-TAZA-METHOD. Parent KANBAN 11.

**Open Questions:**  
Does a Short Stop on a Method card count as a qualifying closure for the streak? Does an exception-routed close count? The qualifying definition needs to be locked in debate before this can be implemented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Correct-method-closures-produce-streaks-and-leaderboard-bfcf424b3ae1468cabe36facfd334ec1_

---
## URS-KIT-METHOD-PKG — Taza Method Card Experience
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need the system to teach the Taza way through the card game itself — every proprietary method pauses crew with an animation, makes them acknowledge before they proceed, shows them how without leaving the board, and rewards them for mastering it and for asking questions — so the training happens in the kitchen during real work, not in a classroom.

**Atomic Requirement:**  
The system shall present proprietary Taza Methods as visually distinct, guided, acknowledged, and gamified experiences that transmit the Taza standard through play rather than lectures.

**Functional Requirement Specification:**  
The Taza Method Card Experience shall (1) render every Method card with a distinct gold visual identity (KANBAN 5), (2) play a ~2s unskippable animation on first encounter (KANBAN 6), (3) require and log an 'I understand — show me how' acknowledgment before SOP access (KANBAN 7), (4) expose inline Show Me guidance without leaving the board (KANBAN 8), (5) award points to both learner and teacher on a question interaction (KANBAN 9), and (6) award a streak badge and update the leaderboard at 10 qualifying correct closures (KANBAN 10). The card-game mechanic IS the training mechanism, not a skin over it.

**Intent / User Need:**  
Turn proprietary technique transmission from a lecture or a manual into something the crew experience through the card game itself — so the Taza standard is absorbed in the flow of work, not in a training room.

**Failure Mode Addressed:**  
Proprietary techniques executed casually without pause, guidance, or accountability; a kitchen culture where asking questions feels risky; training records that exist only on paper.

**Out of Scope:**  
Standard (non-Method) kanban mechanics (URS-KANBAN family); operational-capture cards ([[SPEC:URS-KIT-101]]..107). This package is the proprietary Taza Method experience layer only.

**Acceptance Criteria:**  
Method cards render with gold border/mark/label ([[SPEC:URS-KIT-METHOD-001]]); first-encounter animation plays unskippably ([[SPEC:URS-KIT-METHOD-002]]); acknowledgment is logged before SOP access ([[SPEC:PROD-12]]); Show Me panel opens non-blocking from the card ([[SPEC:URS-KIT-METHOD-004]]); question interactions award both learner and teacher atomically ([[SPEC:URS-KIT-METHOD-005]]); 10 qualifying closures produce exactly one streak badge and update the leaderboard ([[SPEC:URS-KIT-METHOD-006]]).

**Verification Method:**  
End-to-end test covering all six child requirements; plus a cultural validation that the game framing is preserved and the tone is aspirational throughout.

**Open Questions:**  
Does a Short Stop on a Method card count as a qualifying closure for the streak? Does an exception-routed close count? The qualifying definition needs to be locked in debate before this can be implemented.

**Rationale:**  
The method-experience design philosophy (the homage IS the mechanic, not the paint) is a Founding Design principle from D-KIT-001 that governs any future redesign.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Taza-Method-Card-Experience-839f7f9c1d764511b0bcca224edf3631_
