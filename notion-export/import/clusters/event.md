# Taza OS URS — EVENT cluster
_Exported: 2026-09-19 21:35 | 2 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-EVENT-001 — System event envelope preserves correlation and provenance
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: every event carries a correlation ID and full provenance to trace the entire chain from origin — for recovery and audit reconstruction.

**Atomic Requirement:**  
Every system event shall include topic, source module, entity type, entity ID, severity, payload, correlation ID, and occurrence timestamp in an append-only event record.

**Functional Requirement Specification:**  
Every system event emitted through [[SPEC:PROD-20]] shall carry the required envelope: topic, source module, entity type, entity ID, severity, payload, correlation ID, and occurrence timestamp. The event shall be stored in an append-only record. The record shall be retrievable by topic, entity ID, and correlation ID.

**Inputs:**  
Emitting module's topic, source, entity type/ID, severity, payload, and correlation ID (generated or propagated from the originating action).

**Outputs:**  
An append-only event record carrying all eight required fields, retrievable by topic/entity/correlation ID.

**Trigger:**  
Any module calls emit() on [[SPEC:PROD-20]].

**Invariants:**  
All eight fields present and non-null; correlation ID is always either generated at the origin action or propagated from the triggering event (never absent); the record is append-only (no mutation after write).

**Failure Behavior:**  
A missing required field causes the event to be rejected at emission time — the emitting module receives a schema error, not a silent drop. No partial or malformed event is stored in the append-only record.

**Failure Mode Addressed:**  
Untraceable side effects — a kanban close triggering downstream inventory, label, and display changes with no shared correlation ID, making it impossible to audit what a specific close caused or to replay events during recovery.

**Acceptance Criteria:**  
Schema rejects missing required fields; emitted record can be retrieved by topic, entity, and correlation ID.

**Verification Method:**  
Schema constraint and indexed-query tests.

**Maintenance Requirements:**  
Keep the schema enforced at the [[SPEC:PROD-20]] emit layer, not by convention; add new required fields only with a migration plan for existing consumers; verify indexed retrieval performance as the event volume grows.

**Dependency Notes:**  
Implemented by [[SPEC:PROD-20]] (System Event Bus, Spec Drafted). The correlation ID is what ties a kanban close → LKL write → inventory transaction → label proposal → display push into one traceable chain. Indexed retrieval by topic/entity/correlation ID feeds [[SPEC:PROD-22]] (Audit Log) and [[SPEC:PROD-23]] (Exception Router). Every emit across [[SPEC:URS-KANBAN-005]], [[SPEC:URS-LKL-004]], [[SPEC:URS-INV-001]], [[SPEC:URS-LABEL-006]] must conform to this envelope. Part of BUNDLE-EVENT-BUS-EXCEPTIONS.

**Rationale:**  
This envelope is the shared contract every other emit-on-commit requirement implicitly depends on.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/System-event-envelope-preserves-correlation-and-provenance-83c7ac06402440a88646199d8f7a30a7_

---
## URS-EVENT-002 — Exceptions are persisted before notification
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Exception Handling

**User Requirement Statement:**  
Need: alerted only after the failure is already saved and lookupable — an alert before the record exists is useless.

**Atomic Requirement:**  
When event processing fails, the exception router shall persist the error and event context before notifying for warning or critical severity.

**Functional Requirement Specification:**  
When event processing fails, [[SPEC:PROD-23]] shall persist the exception record (error, event context, correlation ID, severity, timestamp) before calling the notifier ([[SPEC:PROD-25]]) for warning or critical severity. Informational failures follow a configured policy (may not notify). Persist-before-notify is an ordering invariant: the notification shall not be dispatched until the persistence write confirms. One idempotent exception record per failure event.

**Inputs:**  
Failed event context (topic, entity, error, severity, correlation ID from [[SPEC:URS-EVENT-001]] envelope); the exception persistence store; the notifier ([[SPEC:PROD-25]]).

**Outputs:**  
One persisted exception record (error, context, correlation, severity, timestamp) confirmed before the notifier is called; a notification dispatched only after persistence confirms for warning/critical severity.

**Trigger:**  
Event processing fails in any consumer module.

**Invariants:**  
Persist-before-notify is unconditional for warning and critical severity; idempotent record per failure event; if the persistence write fails, the notification is not sent (not the reverse).

**Failure Behavior:**  
If the exception persistence write itself fails, the notifier is NOT called — a notification without a record is worse than no notification (crew respond to an alert they can't investigate). In this case the failure is escalated through a separate out-of-band channel (e.g. ntfy direct write) rather than through the normal exception router. A duplicate failure event produces one idempotent exception record.

**Failure Mode Addressed:**  
An exception notification (SMS, ntfy) that arrives with no corresponding persisted record — crew or Nick can't look up what failed, the event context is lost, and the exception is unrecoverable. Equally: a notify that silently fails because the notifier was called before the write completed.

**Acceptance Criteria:**  
NORMAL:
1. On event-processing failure, the exception record persists (error, context, correlation ID, severity, timestamp) BEFORE the notifier is called for warning/critical severity.
2. Informational failures follow configured policy (may not notify) but are still recorded.

EDGE:
3. A failure occurring during the persistence write itself (double failure — the thing failing AND the exception-logging failing) has a defined fallback so the failure isn't completely invisible.
4. Multiple failures occurring in rapid succession each get their own idempotent exception record, not merged/deduplicated incorrectly into one.

NEGATIVE:
5. A notification that somehow fires before the persistence write confirms (race condition) is a direct violation of this row's core invariant — must be actively tested against, not just assumed correct by code structure.

SILENT FAILURE:
6. This row's own Rationale states the specific failure mode it prevents: 'inverting it produces actionable-looking alerts with no backing record.' Verify with a direct test: force a race between persist and notify, confirm persist always wins the ordering under load/timing pressure, not just in a clean sequential test.
7. Idempotency claim (one record per failure event) must hold even under retry/replay of the same underlying failure — verify a retried failure event doesn't create a duplicate exception record.

**Verification Method:**  
1) Ordering test: force concurrent/racing persist-and-notify calls under load, confirm persistence always completes before notification dispatches, every time. 2) Idempotency test: replay the same failure event, confirm no duplicate exception record. 3) Double-failure test: simulate the persistence write itself failing, confirm a defined fallback exists rather than total silence. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the severity tiers and their notification policies configurable; verify persist-before-notify ordering after any change to [[SPEC:PROD-23]] or [[SPEC:PROD-25]]; test the out-of-band escalation path (the case where persistence itself fails).

**Dependency Notes:**  
Implemented by [[SPEC:PROD-23]] (Exception Router, Spec Drafted). The persisted exception record carries the full event envelope from [[SPEC:URS-EVENT-001]] (correlation ID, entity, payload, source). Notification routed via [[SPEC:PROD-25]] (Unified Notifier) only after the record is written. Severity tiers: informational (configured policy, may not notify), warning (persists → notifies), critical (persists → notifies immediately). Part of BUNDLE-EVENT-BUS-EXCEPTIONS.

**Open Questions:**  
What is the out-of-band escalation channel when the exception persistence write itself fails? ntfy direct write? Direct SMS to Nick? Needs a decision before [[SPEC:PROD-23]] is built.

**Rationale:**  
The persist-before-notify ordering is the most important invariant here — inverting it produces actionable-looking alerts with no backing record.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Exceptions-are-persisted-before-notification-037a193921cc4784adc1b6385f26cfae_
