# Taza OS URS — HAI cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## HAI-001 — Sandra override path
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As Sandra, I need a single-tap override with just my PIN — no reason field required — on every system recommendation, so that I can act on my own judgment quickly without the system demanding I justify myself.

**Functional Requirement Specification:**  
Sandra override path: every system recommendation presented to Sandra must include a single-tap override. Override requires Sandra's PIN (from CLOSE 3 PIN table) — tap override, enter PIN, confirm. Zero explanation or reason field. PIN is authentication, not justification. Override logged automatically for retrospective analysis by Nick only.

**Failure Behavior:**  
Fallback: Sandra verbally tells Nick; Nick manually applies.

**Acceptance Criteria:**  
NORMAL:
1. Every system recommendation shown to Sandra includes a visible single-tap override control.
2. Override with correct PIN and confirm → recommendation is overridden immediately, zero reason field ever presented.

EDGE:
3. Sandra overrides several different recommendations in quick succession — each is logged as a distinct override event, none merged or dropped.
4. Override is available and functions identically across every recommendation type/surface it appears on — no surface silently omits the override control.

NEGATIVE:
5. Incorrect PIN entered → override rejected, recommendation stands, attempt is not silently treated as a successful override.
6. Someone other than Sandra (wrong PIN) cannot use this override path — PIN is validated against Sandra's identity specifically, not just 'any valid PIN.'

SILENT FAILURE:
7. Override succeeds in the UI but the log write fails — this must not be possible; if the audit log can't be written, the override itself must not silently succeed (Nick's retrospective visibility is the entire point of this row).
8. Override log must never be readable/editable by anyone other than Nick — confirm no other role can view or alter the override history.

**Verification Method:**  
1) Unit tests: correct-PIN override succeeds, incorrect-PIN override rejected, no reason field ever rendered. 2) Integration test: override on every recommendation surface it appears on, confirm consistent behavior. 3) Fault-injection test: force the audit-log write to fail, assert the override itself does not silently succeed. 4) Access-control test: confirm override log is visible/editable by Nick only. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Sandra-override-path-3cfe152fc199818886d9fb004d97d608_

---
## HAI-002 — Alert format standard
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every alert states condition, severity, recommended action, and an override — never a bare status ping.

**Functional Requirement Specification:**  
Alert format standard: every Taza OS alert or recommendation sent to Sandra must follow the format: (1) Condition, (2) Severity, (3) Recommended action (pre-computed, specific, actionable), (4) Override tap. Bare status alerts without recommended action are prohibited.

**Failure Behavior:**  
Fallback: Sandra receives raw alert; Nick manually adds action context.

**Acceptance Criteria:**  
NORMAL:
1. Every alert/recommendation to Sandra includes all four elements: Condition, Severity, Recommended Action (specific, actionable), Override tap.
2. A bare status alert with no recommended action is never sent — rejected/blocked at the source.

EDGE:
3. A condition where no good recommended action exists (genuinely ambiguous situation) still produces a real, specific action (e.g. "call Nick") rather than a vague placeholder like "review and decide."
4. Multiple alerts firing in quick succession for related conditions are each individually well-formed, not collapsed into a single malformed combined alert.

NEGATIVE:
5. Any code path that attempts to send a Sandra-facing alert missing one of the four required elements fails to send / is rejected by the notifier, not sent in a degraded form.

SILENT FAILURE:
6. This standard is easy to violate accidentally when a new alert type is added later by someone unaware of the format requirement — verify there's a structural enforcement (a shared alert-construction function/template that makes it hard to skip a field), not just documentation discipline.
7. "Recommended action (pre-computed, specific, actionable)" is subjective — verify with Nick/Sandra review of a sample of real generated alerts that the actions are genuinely specific and actionable, not technically-present-but-vague boilerplate.

**Verification Method:**  
1) Structural enforcement test: confirm alerts are constructed via a shared function/template that structurally requires all 4 elements, not assembled ad hoc per call site. 2) Rejection test: attempt to send an alert missing one element, confirm it's rejected rather than sent degraded. 3) Content-quality review: Nick/Sandra review a sample of real generated alerts for genuine actionability, not just field-presence. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Alert-format-standard-3cfe152fc199810ea23ee5dd3d16dc4c_

---
## HAI-003 — Event brief format
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: narrative 7am event-day brief showing only open issues

**Functional Requirement Specification:**  
Event brief format: auto-generated morning brief delivered to Sandra's phone by 7am on every event day. Open issues only shown (confirmed items collapsed by default), each with a recommended action, brief is narrative not a checklist. Max 5 open items before 'show all' expansion.

**Failure Behavior:**  
Fallback: Nick manually texts Sandra key open items each event morning.

**Acceptance Criteria:**  
Brief delivered by 7am; open issues ≤5 shown by default; confirmed items collapsed; each open issue has a recommended action; Sandra can expand confirmed items

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Event-brief-format-3cfe152fc1998160b132de1133a8b53a_

---
## HAI-004 — Single-source truth enforcement
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: notifications reflect only state already committed to NocoDB, never in-flight changes.

**Functional Requirement Specification:**  
Single-source truth enforcement: all state changes must write to NocoDB before any notification is sent to Sandra or Nick. No notification may reference state not yet committed. Prevents competing hypotheses arising from different information sources.

**Failure Behavior:**  
Fallback: accept notification before write on NocoDB timeout only (log as exception).

**Acceptance Criteria:**  
Notifications trigger only after NocoDB write confirms; NocoDB timestamp precedes notification timestamp on every logged event; zero notifications referencing uncommitted state

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Single-source-truth-enforcement-3cfe152fc19981d99919fd4e7d6ddb34_

---
## HAI-005 — Conflict authority hierarchy
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: clear authority order when sources conflict (NocoDB confirmation > vendor email/text > verbal), with conflicting sources and winner named.

**Functional Requirement Specification:**  
Conflict authority hierarchy: when two information sources contradict, NocoDB written confirmation wins over vendor email/text over verbal confirmation. Sandra is notified with the conflicting sources named and the winning authority identified; can override via CLOSE 32.

**Failure Behavior:**  
Fallback: Nick manually adjudicates conflicts; Sandra calls Nick.

**Acceptance Criteria:**  
Conflict detection logic in automation; conflict notification names both sources and states which wins; Sandra override available; conflict and resolution logged in NocoDB

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Conflict-authority-hierarchy-3cfe152fc19981a79917f512162c8e5a_
