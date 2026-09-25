# Taza OS URS — CI cluster
_Exported: 2026-09-19 21:35 | 3 rows_
_Source: Notion Master URS & Specification Registry_

---
## REQ-CI-001 — External watchdog / dead-man's switch
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**Functional Requirement Specification:**  
External watchdog / dead-man's switch: an independent box alerts Nick/Sandra when the N100 goes dark.

**Rationale:**  
Relevant to the 2026-08-21 outage postmortem — an external watchdog would have caught the silent dnsmasq failure faster than the 2-week gap that occurred.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/External-watchdog-dead-man-s-switch-3cfe152fc199810f9262d243229ea11c_

---
## REQ-CI-002 — SPC health monitor over system_metrics
**Status:**  | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: tell normal variation apart from an actual process problem in the system's metrics — not chase noise.

**Functional Requirement Specification:**  
SPC health monitor over the system_metrics table, distinguishing special-cause from common-cause variation.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/SPC-health-monitor-over-system_metrics-3cfe152fc1998155886af5af78739b4c_

---
## REQ-CI-003 — Replay-DOE harness + TQAI scorer + human-gated Morning Brief
**Status:**  | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: test changes against real historical data before trusting them, and a human reviews daily quality findings before anything touches live records.

**Functional Requirement Specification:**  
Replay-DOE harness + TQAI scorer (Gage R&R first) + relay classifier + cache warm-failover + retrospective mining, feeding a human-gated Morning Brief. Governance: human-gated, no auto-write to canonical records.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Replay-DOE-harness-TQAI-scorer-human-gated-Morning-Brief-3cfe152fc19981cea225feec007fbd20_
