# Taza OS URS — DOC cluster
_Exported: 2026-09-19 21:35 | 4 rows_
_Source: Notion Master URS & Specification Registry_

---
## DOC-001 — Operations runbook
**Status:**  | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: ops runbook (daily ops, nightly SLA, per-workflow troubleshooting, escalation) so Nick can self-diagnose without a contractor.

**Functional Requirement Specification:**  
Operations runbook covering daily ops, nightly SLA, per-workflow troubleshooting, and escalation — Nick can diagnose/fix common issues without a contractor.

**Failure Behavior:**  
Fallback: contractor retainer 30 days.

**Acceptance Criteria:**  
Nick can diagnose/fix common issues without contractor

**Verification Method:**
1. [NICK] Live: Nick, with no help, diagnoses and fixes a common failure using only the runbook. Evidence: observation log.
2. [NICK] Coverage: runbook has daily ops, nightly SLA, per-workflow troubleshooting, escalation. Evidence: document review.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Operations-runbook-3cfe152fc19981838c68d9cdc214c788_

---
## DOC-002 — System README
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: README covering every service, port, credential location, cost profile — new contractor productive in 30 min.

**Functional Requirement Specification:**  
System README covering all services, ports, credentials location, and costs — a new contractor understands the system within 30 minutes.

**Failure Behavior:**  
Fallback: Notion docs hub as backup.

**Acceptance Criteria:**  
New contractor understands system within 30min

**Verification Method:**
1. [NICK] Live: a new contractor, reading only the README, locates services/ports/credentials/costs within 30 min. Evidence: timed observation log.
2. [NICK] Coverage: README lists every service, port, credential location, cost profile. Evidence: document review.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/System-README-3cfe152fc19981258f1bc9c0d21102c2_

---
## DOC-003 — Automation jobs exported as JSON for version control
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: automation jobs exported as version-controlled JSON, importing cleanly into a fresh deployment.

**Functional Requirement Specification:**  
All automation jobs exported as JSON for version control — each imports cleanly into a fresh deployment.

**Failure Behavior:**  
Fallback: screenshots, manual rebuild.

**Acceptance Criteria:**  
JSONs exported per job; each imports cleanly into a fresh deployment

**Verification Method:**
1. [AUTO] Export: each automation job exported as JSON. Evidence: file listing.
2. [AUTO] Import: a fresh deployment imports each JSON cleanly. Evidence: import log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Automation-jobs-exported-as-JSON-for-version-control-3cfe152fc19981c4882acb9951c8bc52_

---
## DOC-004 — Sandra 5-minute training script for Invoice Form PWA
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: 5-minute training script for Invoice Form PWA.

**Functional Requirement Specification:**  
Sandra 5-minute training script for Invoice Form PWA

**Failure Behavior:**  
Fallback: Nick walks Sandra through live.

**Acceptance Criteria:**  
Sandra completes walkthrough <5min; no questions on core flow

**Verification Method:**
1. [NICK] Live: Sandra completes the invoice-form walkthrough in <5 min with no questions on core flow. Evidence: timed observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Sandra-5-minute-training-script-for-Invoice-Form-PWA-3cfe152fc1998127987dfffdfbcf6bbc_
