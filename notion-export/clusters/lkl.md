# Taza OS URS — LKL cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-LKL-001 — Location capture gates location-changing task close
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Crew should not be able to finish location-changing work without recording where the item went.

**Atomic Requirement:**  
A location-changing card shall not enter Done without a valid LKL/bin identifier.

**Functional Requirement Specification:**  
The system shall block task closure until a valid LKL/bin is supplied whenever the task changes item location.

**Inputs:**  
Task type (does it change item location?); crew-entered LKL/bin at close; bin master (KIT-001) for validity.

**Outputs:**  
A valid LKL/bin captured at close, handed to URS-LKL-002 for persistence.

**Trigger:**  
Crew attempts to close a location-changing card.

**Invariants:**  
A location-changing card cannot reach Done without a valid LKL/bin; validity is checked against the bin master, not free text.

**Failure Behavior:**  
Missing or invalid bin blocks closure with a clear prompt; the card stays active until a valid LKL is supplied. Non-location-changing tasks are not gated.

**Failure Mode Addressed:**  
Items disappearing into the kitchen with no record of where they went — the 'where are the cut strawberries' hunt that wastes time and interrupts people mid-event.

**Acceptance Criteria:**  
NORMAL:
1. Task changes item location and closes with a valid LKL/bin → closes successfully.

EDGE:
2. A task that does NOT change item location closes without requiring an LKL/bin — the gate correctly applies only to location-changing tasks, never blocks unrelated closes.
3. A task ambiguous about whether it changes location (edge-case task type) has a defined, tested answer for which side of the gate it falls on — not left to implementation guesswork.

NEGATIVE:
4. Location-changing task attempts to close with no LKL/bin supplied → blocked, cannot close.
5. Location-changing task attempts to close with an LKL/bin referencing a bin ID that doesn't exist in the bin master (CLOSE 23) → rejected, not silently accepted as a dangling reference.

SILENT FAILURE:
6. A close blocked by this gate must show crew a clear, specific reason ('location required') — not a generic failure that leaves crew guessing why the card won't close.
7. If the location-changing determination itself is wrong for a given task type (misconfigured), a task could either be wrongly blocked or wrongly allowed through — verify this classification is tested per task type, not just the gate mechanism in isolation.

**Verification Method:**  
1) Unit tests: location-changing task with/without valid bin, non-location-changing task closes freely, invalid bin ID rejected. 2) Classification test: enumerate task types and confirm each is correctly classified as location-changing or not. 3) UX test: confirm the blocked-close error message is specific and actionable, not generic. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the 'is this task location-changing?' classification current as task types are added; keep bin-master validation in sync with KIT-001.

**Dependency Notes:**  
Enforced at task close (CLOSE 11 / CLOSE 1 close contract). The captured LKL becomes the record in CLOSE 19. Bin validity checked against the bin master (CLOSE 23). Part of BUNDLE-LKL-TRUTH. Parent CLOSE 2.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Location-capture-gates-location-changing-task-close-c76240834e0b403f92ac100a17391207_

---
## URS-LKL-002 — LKL record preserves operational provenance
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every location record captures full provenance — item, qty, bin, event, task, crew, state, timestamp — detailed enough that crew trust it over asking a person.

**Atomic Requirement:**  
Each accepted LKL update shall create or idempotently update a record containing the complete provenance field set.

**Functional Requirement Specification:**  
The system shall persist the item, quantity, unit, bin, event, source task, crew member, state, and timestamp for every LKL update.

**Inputs:**  
The accepted LKL/bin from URS-LKL-001, plus item, quantity, unit, event, source task, crew member (PIN), state, timestamp.

**Outputs:**  
A complete, idempotent LKL record (item/qty/unit/bin/event/task/crew/state/timestamp) available to lookup and downstream consumers.

**Trigger:**  
An LKL update is accepted at task close.

**Invariants:**  
Every LKL record carries the full provenance field set; identical close event replayed → idempotent update, never a duplicate; each record ties back to its source task and crew member.

**Failure Behavior:**  
A malformed/incomplete update is rejected (missing required provenance field → no partial record). Replaying the same close event idempotently updates rather than duplicating the location record.

**Failure Mode Addressed:**  
Sparse or untrustworthy location records ('it says WIC-1-3 but who put it there and when?'); duplicate/conflicting records from replayed events.

**Acceptance Criteria:**  
NORMAL:
1. Every LKL update persists item, quantity, unit, bin, event, source task, crew member, state, and timestamp — all fields populated, none silently defaulted or blank.

EDGE:
2. An LKL update tied to an event-less task (if that's possible) still records a defined value for the event field, not null-by-accident.
3. Two LKL updates for the same item/bin within the same second (rapid crew action) both persist as distinct records with correct ordering, not overwritten/merged.

NEGATIVE:
4. An LKL write attempted with any required field missing is rejected — no partial LKL record is ever created.
5. A crew member field referencing a PIN/identity that doesn't resolve to a real crew record is rejected, not stored as an orphaned reference.

SILENT FAILURE:
6. If the write succeeds for most fields but one (e.g. timestamp defaults to write-time instead of actual event-time due to a bug) this must be caught — verify timestamp source is the actual event, not just 'whenever the DB write happened.'
7. A record that appears complete in the UI but is missing provenance server-side would defeat the entire purpose of this row ('detailed enough that crew trust it over asking a person') — verify server-side completeness, not just UI display.

**Verification Method:**  
1) Unit tests: full-field write, missing-required-field rejection, invalid-crew-reference rejection. 2) Concurrency test: two rapid updates to the same item/bin, confirm both persist distinctly and in correct order. 3) Field-provenance test: confirm the persisted timestamp reflects actual event time, not write time, under simulated latency. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the provenance field set aligned with KIT-003 if merged; enforce the idempotency key on the write path; retire/expire consumed records so lookups don't return stale locations (see staleness handling KIT-007).

**Dependency Notes:**  
Written at close (CLOSE 18 gate / CLOSE 11). Provenance fields feed lookup (CLOSE 20) and the downstream event (CLOSE 21). CROSS-REF: overlaps KIT-003 (LKL table schema) — reconcile field-level in debate. Part of BUNDLE-LKL-TRUTH. Parent CLOSE 2. Table: PostgreSQL, includes a notes field.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/LKL-record-preserves-operational-provenance-9dad3101919b4db49b84fccaa0dd6202_

---
## URS-LKL-003 — LKL lookup returns results rapidly, ideally  in under one second
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
A crew member should be able to find an item faster than asking another person.

**Atomic Requirement:**  
A valid LKL query shall return matching current records, ideally under 1 second at the 95th percentile.

**Functional Requirement Specification:**  
The system shall support lookup by item, event, category, allergen, or bin and return a result in under one second on the production LAN, for any items tracked by the LKL system.

**Inputs:**  
A lookup key: item, event, category, allergen, or bin (typed or voice).

**Outputs:**  
Matching current LKL records (bin + qty + placer + timestamp + staleness flag) returned in <1s p95.

**Trigger:**  
A crew member issues an LKL query (text or voice) on any device.

**Invariants:**  
p95 < 1.0s on the production LAN for every supported lookup key; results reflect current (not consumed/moved) records; staleness is surfaced, never hidden.

**Failure Behavior:**  
No match → explicit 'not found / not yet placed' rather than a wrong or empty guess. A stale record (older than threshold, KIT-007) returns with a 'verify before hunting' warning rather than silent confidence.

**Failure Mode Addressed:**  
Crew wasting time hunting for an item, or interrupting someone to ask where it is — the lookup must be faster than asking a person or it won't get used.

**Acceptance Criteria:**  
NORMAL:
1. Lookup by item, event, category, allergen, or bin returns a correct result in under one second on the production LAN.

EDGE:
2. A lookup with multiple filters combined (e.g. item + allergen) returns the correctly narrowed result set, not just the first filter applied.
3. A lookup for an item with zero current LKL records returns a clear 'not found,' not a timeout or error.
4. Voice lookup via fixed-vocabulary phoneme match correctly resolves close-sounding item names without cross-matching the wrong item.

NEGATIVE:
5. A lookup query outside the fixed vocabulary (voice) is rejected/unmatched rather than passed to any LLM inference path — this is explicitly required to stay deterministic.
6. A malformed or injection-style query string does not crash the lookup or return unintended results.

SILENT FAILURE:
7. A lookup that silently exceeds the 1s target under real load (not synthetic) must be caught — verify performance under production-realistic concurrent load, not just a clean single-query benchmark.
8. A lookup returning a stale result (item was moved but lookup shows the old bin) must be distinguishable from a correct current result — verify staleness is either impossible by design or visibly flagged.

**Verification Method:**  
1) Unit tests: single-filter lookup per type (item/event/category/allergen/bin), combined-filter lookup, not-found case. 2) Voice-lookup test: phoneme-match against a set of confusable item-name pairs, confirm no cross-matches. 3) Performance test: p95/p99 latency under concurrent-user load simulating event-rush conditions, not just single-query benchmark. 4) Security test: malformed/injection query strings handled safely. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Re-run the performance test at production data volume after schema/index changes; keep the voice item-list vocabulary current with the catalog; validate the MicroTouch local cache (MT-001) stays within the latency budget.

**Dependency Notes:**  
Queries the LKL records from CLOSE 19. Voice lookup path is phoneme-match against the item list (not LLM inference) per KIT-004. Served on the LAN; MicroTouch may answer from a local cache (CLOSE 31) to hit the latency target. CROSS-REF: overlaps KIT-004 (LKL query interface) — reconcile in debate. Part of BUNDLE-LKL-TRUTH. Parent CLOSE 2.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/LKL-lookup-returns-results-rapidly-ideally-in-under-one-second-f5198c5232c8433ea007e29f82c9fa76_

---
## URS-LKL-004 — LKL updates publish to all consuming surfaces
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every accepted LKL change publishes from one committed update to all consuming surfaces (wall boards, voice/Alexa, inventory, shopping, labels) — never from an unsaved move, never twice on retry.

**Atomic Requirement:**  
After an LKL write commits, one correlated location-change event shall be emitted for downstream consumers.

**Functional Requirement Specification:**  
The system shall publish each accepted LKL change to wall displays, voice cache, inventory, shopping, labels, and other subscribed consumers.

**Intent / User Need:**  
Driven by one event, never direct cross-writes that drift.

**Inputs:**  
The committed LKL record (URS-LKL-002) + the event envelope (correlation/provenance) per URS-EVENT-001.

**Outputs:**  
Exactly one correlated location-change event per committed LKL write, consumed idempotently by displays/voice-cache/inventory/shopping/labels.

**Trigger:**  
An LKL write commits (URS-LKL-002).

**Invariants:**  
commit-then-emit ordering; exactly one correlated event per successful write; idempotent consumption on replay; every event traces to its originating LKL write.

**Failure Behavior:**  
A failed LKL write emits no event (no phantom updates downstream); a successful write emits exactly one correlated event; replay does not duplicate consumer effects.

**Failure Mode Addressed:**  
Downstream surfaces (wall boards, voice cache, inventory) showing a location that didn't actually commit, or double-applying a replayed location change — divergence between where the system says an item is and where it is.

**Acceptance Criteria:**  
A successful write emits one event with matching entity and correlation ID; failed writes emit none.

**Verification Method:**  
Integration test against event bus and consumer fixtures.

**Maintenance Requirements:**  
Keep the subscribed-consumer list + idempotency keys current as surfaces are added; verify ordering after any LKL write-path change.

**Dependency Notes:**  
Emitted through EXCEPT 2 (Event Bus, Spec Drafted) after the LKL write commits (CLOSE 19). Same commit-then-emit pattern as CLOSE 12 / EXCEPT 4/EXCEPT 5. Consumers: wall displays (DISPLAY 1/SSB), voice/Alexa cache (ALC), inventory (URS-INV/CLOSE 5), shopping (SHOP 11), labels (LABEL 1/URS-LABEL). Part of BUNDLE-LKL-TRUTH. Parent CLOSE 2.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/LKL-updates-publish-to-all-consuming-surfaces-ceb4f32892e644509b282abc10ac09f0_

---
## URS-LKL-PKG — Last Known Location Truth Capture & Lookup
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner and crew, I need the system to always know where every item is — captured the moment work moves it, recorded accurately with who/when, and findable in a second by anyone — so we stop losing time hunting for things and interrupting each other during events.

**Atomic Requirement:**  
The system shall capture, persist, expose, and publish Last-Known-Location truth for every tracked item, such that any crew member can find any item faster than asking a person and every consuming surface stays consistent with physical reality.

**Functional Requirement Specification:**  
The LKL subsystem shall (1) gate closure of any location-changing task on a valid bin (CLOSE 18), (2) persist a complete, idempotent, fully-provenanced location record for every update (CLOSE 19), (3) return lookups by item/event/category/allergen/bin in under one second p95 (CLOSE 20), and (4) publish each committed change as one correlated event to all subscribed consumers (CLOSE 21). Capture is deterministic and form-gated; voice lookup is fixed-vocabulary phoneme match, not LLM inference.

**Intent / User Need:**  
Turn 'where is the thing?' from a person-to-person interruption into an instant, trusted system lookup — the LKL subsystem is the kitchen's shared spatial memory.

**Failure Mode Addressed:**  
The single biggest day-to-day time sink and stress source in the kitchen: not knowing where something is, and the interruptions/hunting that follow.

**Out of Scope:**  
Inventory quantity/lot lineage (URS-INV family / PROD-36) — LKL is 'where is it', inventory is 'how much/what lot'. Labels (URS-LABEL). These consume LKL but are separate specs.

**Acceptance Criteria:**  
This is a package row (Record Type: Spec Package) — its acceptance criteria is the aggregate of its 4 child atomic requirements passing independently AND working correctly together end-to-end:

NORMAL:
1. A full location-changing task lifecycle (gate → capture → lookup → publish) runs end-to-end without manual intervention: task blocked without valid bin (CLOSE 18) → closes with bin → record persists with full provenance (CLOSE 19) → lookup returns it in <1s (CLOSE 20) → change publishes to all consumers (CLOSE 21).

EDGE:
2. Voice lookup (fixed-vocabulary phoneme match) correctly handles near-miss pronunciations without falling back to LLM inference — verify it fails closed (no match) rather than guessing.
3. High-frequency LKL activity (many closes in a short window, e.g. event rush) doesn't degrade the <1s p95 lookup target.

NEGATIVE:
4. Any one of the 4 child requirements failing independently (verified via their own AC) must cause the package-level end-to-end flow to visibly fail, not silently continue with a gap.

SILENT FAILURE:
5. The full chain succeeding on 4 isolated unit tests but failing when run end-to-end (integration gap between the 4 pieces) is the specific risk this package-level row exists to catch — the 4 child rows passing individually is necessary but not sufficient.

**Verification Method:**  
1) End-to-end integration test: full lifecycle from blocked-close through published-event, using real data, not mocked child components. 2) Performance test: p95 lookup latency under simulated event-rush load. 3) Voice-lookup fail-closed test: near-miss pronunciation returns no match rather than a guessed one. 4) Regression suite: run all 4 child rows' (CLOSE 18/19/20/21) own acceptance tests as a precondition gate before running this package's end-to-end test. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
Parent/anchor CLOSE 2.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Last-Known-Location-Truth-Capture-Lookup-f23e82b1f1644a00aae4195f9744878c_
