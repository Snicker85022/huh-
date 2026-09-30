# Taza OS URS — KANBAN cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-KANBAN-001 — Kanban board uses hand, table, and done workflow states
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: task board shows work in three plain states (hand/not-started, table/in-progress, done) flowing top to bottom, unambiguous at a glance on any screen.

**Atomic Requirement:**  
The kitchen execution surface shall represent work using hand/not-started, table/in-progress, and done states with a clear top-to-bottom flow.

**Functional Requirement Specification:**  
The kitchen execution surface shall represent every task in one of three explicit states — hand (not-started), table (in-progress), done — laid out with a clear top-to-bottom flow, and shall permit only valid state transitions. The current state of any task shall be unambiguous on MT1, MT2, and z33 simultaneously.

**Inputs:**  
Task records + their current state from the task engine ([[SPEC:PROD-01]]); crew interaction (tap/PIN) on the kanban surface.

**Outputs:**  
A rendered three-column (hand/table/done) board with unambiguous per-task state on all surfaces.

**Trigger:**  
Continuous while the board is displayed; a transition fires on crew interaction.

**Invariants:**  
A task is always in exactly one of the three states; transitions follow the allowed order (no skipping to done without passing through in-progress except via explicit close); state is consistent across all surfaces.

**Failure Behavior:**  
An invalid transition attempt is rejected and the card stays in its prior state; the current state is always visibly unambiguous on every surface.

**Failure Mode Addressed:**  
Ambiguous or lost task state under event-day stress — a crew member unable to tell at a glance what's not-started vs in-progress vs done.

**Acceptance Criteria:**  
NORMAL:
1. Every task is in exactly one of hand/table/done; only valid transitions between them are permitted; state is unambiguous and identical on MT1, MT2, and z33 at the same moment.

EDGE:
2. A transition attempted out of sequence (e.g. hand → done, skipping table) is either explicitly allowed by design or explicitly blocked — verify this is a deliberate decision, tested, not an accidental gap.
3. Two devices (MT1 and z33) viewing the same task simultaneously never show different states, even momentarily during a state-change propagation window — measure actual cross-device sync latency.

NEGATIVE:
4. An invalid transition attempt (e.g. done → hand without the proper reopen mechanism) is rejected with a clear reason, not silently ignored or silently applied.

SILENT FAILURE:
5. A card that appears in 'table' on one screen and 'done' on another due to a sync lag would actively cause double-work or missed-work in a live kitchen — this is the single most dangerous failure mode for this row; verify cross-device consistency under real network conditions, not just a single-device unit test.
6. State transitions must be auditable — confirm every transition is logged with enough detail to reconstruct what happened if a discrepancy is ever reported.

**Verification Method:**  
1) Unit tests: valid transitions succeed, invalid transitions rejected with clear reason. 2) Cross-device consistency test: change state on one device, measure and confirm propagation time and correctness on the other two devices under real network conditions (not localhost). 3) Concurrency test: near-simultaneous conflicting transition attempts from two devices, confirm a defined, correct resolution. 4) Audit-trail test: confirm every transition is logged and reconstructable. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the three-state model and its transition rules identical across MT1/MT2/z33 renderers; re-test multi-device consistency after any kanban.html change.

**Dependency Notes:**  
Rendered by the deployed kanban surface (server_kanban.py :9003, kanban.html on MT1/MT2/z33). State transitions are driven by the task engine ([[SPEC:PROD-01]], Built-unverified). Close semantics are governed by [[SPEC:URS-KANBAN-002]] + [[SPEC:PROD-38]] (Canonical Task Close Contract, Spec Drafted).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Kanban-board-uses-hand-table-and-done-workflow-states-0cbd52df15c947349f7688145c99ed25_

---
## URS-KANBAN-002 — Kanban close captures accountable handoff
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every finished card records who (PIN)/when/how much/where, refusing to close if any is missing — no anonymous or double-counted 'done's.

**Atomic Requirement:**  
A completed kitchen card shall capture crew identity (their pin number), timestamp, completed quantity, and required LKL before leaving the active board.

**Functional Requirement Specification:**  
A kitchen card shall not leave the active board until it captures crew identity (PIN), timestamp, completed quantity, and any required Last-Known-Location. The close shall reject any missing required value, shall persist all captured values exactly once on success, shall display a brief confirmation, and shall be idempotent under retry.

**Intent / User Need:**  
Captured data seeds LKL, inventory, and competency tracking downstream.

**Inputs:**  
Crew PIN; system timestamp; completed quantity entered by crew; required LKL (bin/location) where the task type demands it.

**Outputs:**  
A committed task-close record (PIN, timestamp, qty, LKL) written once; a brief on-screen confirmation; the trigger for the downstream event ([[SPEC:URS-KANBAN-005]]).

**Trigger:**  
Crew attempts to close/complete a card on the kanban surface.

**Invariants:**  
No card leaves active without all required close values; each successful close writes exactly once; identical close request replayed → no additional effect.

**Failure Behavior:**  
Any missing required value (PIN, quantity, or required LKL) blocks closure with a clear prompt; the card stays active. A successful close stores all values exactly once and shows a brief confirmation; a retried close is idempotent (no double-write).

**Failure Mode Addressed:**  
Unaccountable handoffs (no idea who finished what, when, how much, or where it went); double-counting from a re-tapped close.

**Acceptance Criteria:**  
NORMAL:
1. Card close with valid PIN, timestamp, completed quantity, and required LKL all present → closes, persists once, shows brief confirmation.

EDGE:
2. A close_kind that doesn't require LKL (no location change) closes successfully without an LKL value, while one that does require it still enforces the gate — the 'any required LKL' condition is correctly conditional, not blanket.
3. Retry of an already-successful close (double-tap, network retry) is idempotent — no duplicate persisted record, confirmation still shows once.

NEGATIVE:
4. Close attempted with any single required value missing (PIN, timestamp, quantity, or required LKL) is rejected — test each field's absence independently, not just 'some field missing.'
5. Invalid PIN (doesn't resolve to a crew member) is rejected as an auth failure, distinct from a missing-PIN rejection.

SILENT FAILURE:
6. A close that fails validation must not show the brief confirmation UI — confirm the confirmation is gated on actual persisted success, not optimistically shown.
7. Idempotent retry must not silently swallow a genuinely different second attempt (e.g. a correction) if the crew intended to actually change a value — verify idempotency keys on the intended action, not just any resubmission.

**Verification Method:**  
1) Unit tests: successful close, each required field individually missing, invalid PIN, conditional-LKL correctness. 2) Idempotency test: duplicate submission of an identical close vs. a genuinely corrected resubmission, confirm each is handled correctly and distinctly. 3) UI-state test: confirm the success confirmation only ever renders after a persisted successful write, never optimistically. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the required-field set aligned with [[SPEC:PROD-38]]'s close contract as task kinds evolve; verify idempotency after any close-path change.

**Dependency Notes:**  
CONFORMS TO [[SPEC:PROD-38]] (Canonical Task Close Contract, Spec Drafted). PIN identity from [[SPEC:PROD-12]]/KIT-009 (Staff PIN). LKL capture per URS-LKL family / [[SPEC:PROD-02]]. Emits the downstream event via [[SPEC:URS-KANBAN-005]] + [[SPEC:PROD-20]] (Event Bus, Spec Drafted). CROSS-REF: overlaps KIT-002 (task completion form gate) — reconcile in debate.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Kanban-close-captures-accountable-handoff-c35fd4e8bc244aebaa5a150a4b6e1b4e_

---
## URS-KANBAN-003 — Kanban cards expose urgency, allergen, and dependency signals
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: each card shows urgency, allergen, and dependency/blocking status at a glance, each signal in a fixed spot, readable instantly under pressure.

**Atomic Requirement:**  
Each task card shall display applicable urgency, allergen, upstream-dependency, and downstream-waiting signals in their fixed visual locations.

**Functional Requirement Specification:**  
Each task card shall display, in fixed visual locations, the applicable signals: urgency (green/amber/red stripe), allergen (dot), upstream-dependency count, and downstream-waiting count. Each signal shall occupy its own reserved position so no two signals can be confused, and the correct signal shall render for the card's actual state.

**Inputs:**  
Task urgency/priority + timing; allergen flags on the item; upstream-dependency and downstream-waiting counts from the task graph.

**Outputs:**  
A rendered card showing the correct urgency stripe, allergen dot, dependency count, and waiting count in their fixed positions.

**Trigger:**  
Card render / re-render on any state or signal change.

**Invariants:**  
Every signal has a fixed, reserved position; the same visual never means two things; allergen and red-urgency are always legible at glance distance.

**Failure Behavior:**  
A missing signal simply doesn't render its badge (absence = not-applicable); signals never render in each other's fixed positions, so meanings can't be confused.

**Failure Mode Addressed:**  
Missed allergen risk or missed urgency because the signal wasn't visible or was ambiguous; crew not knowing a card is blocked upstream or blocking others downstream.

**Acceptance Criteria:**  
NORMAL:
1. Urgency stripe, allergen dot, upstream-dependency count, and downstream-waiting count each render in their own fixed, reserved position on every card.
2. The correct signal state renders for the card's actual current state (right urgency color, correct allergen presence/absence, accurate counts).

EDGE:
3. A card with all four signals simultaneously active (urgent + allergen + has dependencies + has waiters) shows all four clearly, none visually crowding out another.
4. A card with zero active signals (calm, no allergen, no deps) shows a clean default state, not empty-looking broken placeholders.

NEGATIVE:
5. A signal in an invalid/unrecognized state (data bug) does not render as a misleading valid-looking signal — fails visibly/obviously rather than silently showing wrong information.

SILENT FAILURE:
6. Two signals rendering in overlapping or ambiguous positions (a layout regression) would violate the entire point of this row ('no two signals can be confused') — verify with the all-four-active edge case specifically, since that's where crowding is most likely.
7. Dependency/waiting counts silently going stale (not updating as the task graph changes) would show crew inaccurate information they're relying on for prioritization — verify counts update live, not just at card creation.

**Verification Method:**  
1) Unit tests: each signal renders correctly in isolation, in its fixed position. 2) Visual stress test: all four signals simultaneously active, confirm no overlap/ambiguity (screenshot comparison against the fixed-position spec). 3) Live-update test: change the underlying task graph, confirm dependency/waiting counts update on the card without requiring a manual refresh. 4) Invalid-state test: inject a bad/unrecognized signal value, confirm it fails visibly rather than rendering a misleading valid-looking state. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the signal→position mapping and the color/shape legend identical across all card renderers; run visual-regression on fixture cards after any card-template change.

**Dependency Notes:**  
Urgency stripe driven by task timing/priority ([[SPEC:PROD-01]]). Allergen dot sourced from allergen flags ([[SPEC:URS-KIT-102]] receiving flags / catalog dietary_flags [[SPEC:CAT-002]]). Dependency/waiting counts from the task-chain graph ([[SPEC:PROD-01]]/[[SPEC:PROD-38]]). Renders on the deployed kanban surface (:9003).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Kanban-cards-expose-urgency-allergen-and-dependency-signals-5e3bcec9fbf546ec987d6741c783102c_

---
## URS-KANBAN-004 — Short Stop preserves partial work and creates residual task
**Status:** In Development | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: stopping a task partway records actual completed qty and auto-creates a follow-up task for the rest, without marking the whole thing done.

**Atomic Requirement:**  
Using Short Stop shall record completed quantity and state, then create one residual task for the unfinished quantity without marking the original work fully complete.

**Functional Requirement Specification:**  
Using Short Stop on a task shall record the completed quantity and state, then create exactly one residual task for the unfinished quantity, without marking the original work fully complete. Completed quantity plus residual quantity shall always equal the pre-stop quantity, and a retry shall create no duplicate residual task.

**Inputs:**  
Pre-stop target quantity; crew-entered completed quantity; the original task record + its state.

**Outputs:**  
An updated original task (partial, not complete) + exactly one residual task for the remaining quantity, with quantities reconciled.

**Trigger:**  
Crew invokes 'Short Stop' on an in-progress card.

**Invariants:**  
completed_qty + residual_qty = pre_stop_qty (exact reconciliation); original is never marked fully complete on a Short Stop; exactly one residual task per stop (idempotent).

**Failure Behavior:**  
If the residual-task creation fails, the original is NOT marked complete (no silent loss of the unfinished quantity); a retried Short Stop does not create a duplicate residual task.

**Failure Mode Addressed:**  
Silent loss of unfinished work (a partially-done task marked 'done' loses the remainder); duplicate residual tasks from a re-tapped Short Stop.

**Acceptance Criteria:**  
Completed plus residual quantity equals the pre-stop quantity; retry creates no duplicate residual task.

**Verification Method:**  
Quantity-reconciliation and idempotent replay tests.

**Maintenance Requirements:**  
Keep the reconciliation arithmetic and idempotency key aligned with [[SPEC:PROD-02]]/KIT-006 if those are merged; test replay after any close/short-stop change.

**Dependency Notes:**  
Builds on the close-capture gate ([[SPEC:URS-KANBAN-002]]) and the task engine's task-spawn capability ([[SPEC:PROD-01]]). CROSS-REF: overlaps [[SPEC:PROD-02]] (PARTIAL_COMPLETE auto-spawn) and KIT-006 (partial completion handling) — reconcile in debate; 'Short Stop' is the crew-facing name for this behavior.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Short-Stop-preserves-partial-work-and-creates-residual-task-000e25aaf5324e46b4c988bf93fe43bc_

---
## URS-KANBAN-005 — Kanban completion publishes downstream state changes
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: closing a task reliably updates everything downstream (location, inventory, scores, labels, displays) from one committed event — never fires on a failed close, never fires twice on retry.

**Atomic Requirement:**  
After a task closure commits, the system shall emit one correlated event for authorized LKL, inventory, scoring, label, and display consumers.

**Functional Requirement Specification:**  
After a task closure commits, the system shall emit exactly one correlated event for authorized consumers (LKL, inventory, scoring, label, display). A close that fails to commit shall emit no event. Event replay shall not duplicate consumer effects. The event shall carry correlation/provenance so every downstream effect traces back to its originating close.

**Intent / User Need:**  
Task close is the single fan-out point — never via direct cross-writes that can drift.

**Inputs:**  
The committed task-close record (from [[SPEC:URS-KANBAN-002]]); the event envelope (correlation id, provenance) per [[SPEC:URS-EVENT-001]].

**Outputs:**  
Exactly one correlated downstream event per committed close, consumed idempotently by LKL/inventory/scoring/label/display consumers.

**Trigger:**  
A task-close transaction commits (from [[SPEC:URS-KANBAN-002]]).

**Invariants:**  
commit-then-emit ordering (event only after commit); exactly one event per successful close; idempotent consumption on replay; every event correlated to its originating close.

**Failure Behavior:**  
If the close transaction does not commit, NO event is emitted (no downstream effects from a failed close). Replayed events do not duplicate consumer effects (idempotent consumers).

**Failure Mode Addressed:**  
Downstream consumers acting on a close that didn't actually commit (phantom inventory/label/score), or double-acting on a replayed event — the classic distributed-consistency failure.

**Acceptance Criteria:**  
NORMAL:
1. Task closure commits → exactly one correlated event emits for all authorized consumers (LKL, inventory, scoring, label, display).

EDGE:
2. A close with no applicable consumers for its close_kind (if any exist) still emits the event envelope correctly, just with an empty/appropriate consumer set — doesn't skip emission entirely by mistake.
3. Multiple consumers processing the same event at different speeds — slow consumer lag doesn't cause the event to be re-emitted or duplicated for faster ones.

NEGATIVE:
4. A close that fails to commit (validation failure, DB error) emits zero events — verify no partial/premature emission before commit is confirmed.
5. An unauthorized consumer attempting to subscribe to this event stream cannot receive it.

SILENT FAILURE:
6. Event replay (reprocessing, recovery scenario) must not duplicate consumer-side effects — explicitly test replay against each consumer type (does replaying an LKL-consumer event write a duplicate LKL record? Does replaying a label-consumer event print a duplicate label?).
7. Correlation/provenance data on the event must actually trace back to the originating close in practice, not just be present as a field — verify an auditor can follow the chain end-to-end for a real event.

**Verification Method:**  
1) Unit tests: successful commit emits exactly one event, failed commit emits zero. 2) Replay test: replay a committed event against each consumer type (LKL, inventory, scoring, label, display) individually, confirm none produce duplicate effects. 3) Traceability test: pick a real emitted event and manually trace its correlation ID back to the originating close, confirm the chain holds. 4) Load/lag test: slow consumer does not trigger re-emission for other consumers. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the consumer list and their idempotency keys current as new consumers (e.g. new label types, new dashboards) are added; verify commit-then-emit ordering after any close-path change.

**Dependency Notes:**  
Emitted through [[SPEC:PROD-20]] (System Event Bus, Spec Drafted) and governed by [[SPEC:PROD-38]] (Canonical Task Close Contract, Spec Drafted). Consumers: LKL ([[SPEC:PROD-02]]/URS-LKL), inventory (URS-INV/[[SPEC:PROD-36]]), competency scoring ([[SPEC:PROD-12]]), labels ([[SPEC:PROD-13]]/URS-LABEL), displays ([[SPEC:PROD-04]]/SSB). The commit-then-emit ordering is the same transactional-integrity pattern as [[SPEC:URS-EVENT-001]]/[[SPEC:URS-EVENT-002]].

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Kanban-completion-publishes-downstream-state-changes-d73b7126d6d243c39dbb3af630606f50_
