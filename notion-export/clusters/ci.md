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

**Acceptance Criteria:**
NORMAL: independent watchdog box alerts Nick/Sandra when the N100 goes dark.
EDGE: watchdog itself fails → caught by its own heartbeat.
NEGATIVE: an N100 silent failure goes unnoticed for weeks → prevented (2026-08-21 dnsmasq postmortem).
SILENT-FAILURE: watchdog alerts but nobody receives → caught by delivery check.
CHALLENGE: kill the N100 → alert arrives within minutes.
**Verification Method:**
1. [AUTO] Kill test: power off N100 → alert fires. Evidence: log + SMS screenshot.
2. [AUTO] Heartbeat: watchdog self-reports alive. Evidence: log.
3. [NICK] Live: Nick receives the dead-man's alert on his phone. Evidence: screenshot.

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

**Acceptance Criteria:**
NORMAL: SPC distinguishes special-cause from common-cause variation in system_metrics.
EDGE: baseline too short → flags insufficient data, not a false special-cause.
NEGATIVE: a real special-cause signal ignored → caught.
SILENT-FAILURE: monitor stops updating → caught by heartbeat.
CHALLENGE: inject a known anomaly → flagged as special-cause, and only it.
**Verification Method:**
1. [AUTO] Anomaly: inject a spike → flagged special-cause. Evidence: log.
2. [AUTO] Baseline: short history → 'insufficient data' not false alarm. Evidence: log.
3. [AUTO] Heartbeat: monitor alive. Evidence: log.

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

**Acceptance Criteria:**
NORMAL: replay historical data; TQAI scorer passes Gage R&R first; relay classifier; cache warm-failover; retrospective mining → human-gated Morning Brief.
EDGE: Gage R&R fails → scorer not trusted for automatic decisions.
NEGATIVE: auto-write to canonical records → BLOCKED (human gate).
SILENT-FAILURE: a finding auto-applied → caught by audit.
CHALLENGE: replay a month of history → scorer output matches human judgment.
**Verification Method:**
1. [AUTO] Replay: run DOE on historical data → results report. Evidence: report file.
2. [AUTO] Gate: zero auto-writes to canonical records. Evidence: audit query.
3. [NICK] Live: Nick reviews the Morning Brief before anything touches live records. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Replay-DOE-harness-TQAI-scorer-human-gated-Morning-Brief-3cfe152fc19981cea225feec007fbd20_
