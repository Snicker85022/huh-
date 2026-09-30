# Taza OS URS — TELEMETRY cluster
_Exported: 2026-09-19 21:35 | 2 rows_
_Source: Notion Master URS & Specification Registry_

---
## REQ-TELE-001 — Append-only telemetry capture tables
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: every AI call and every human correction of it gets logged permanently — the raw data to actually measure and improve quality over time.

**Functional Requirement Specification:**  
Four append-only capture tables in PostgreSQL: inference_traces, human_corrections, system_metrics, interaction_events. Immutable, idempotent inserts. Logging only — no new hardware.

**Rationale:**  
History cannot be backfilled — capture-now/analyze-later.

**Acceptance Criteria:**
NORMAL: four append-only tables exist — inference_traces, human_corrections, system_metrics, interaction_events — immutable, idempotent inserts.
EDGE: duplicate insert → idempotent, no double row.
NEGATIVE: UPDATE/DELETE on telemetry rows → BLOCKED.
SILENT-FAILURE: capture fails silently → caught by row-count check.
CHALLENGE: high-volume event day → zero dropped rows.
**Verification Method:**
1. [AUTO] Append-only: no UPDATE/DELETE grants on the four tables. Evidence: schema check.
2. [AUTO] Idempotent: same insert twice → one row. Evidence: query.
3. [AUTO] Volume: 10k rows/day → zero loss vs source. Evidence: count comparison.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Append-only-telemetry-capture-tables-3cfe152fc19981259512c2cb177a5586_

---
## REQ-TELE-002 — Inference call + human correction logging
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: every time a human edits or overrides AI output, that correction is captured as a labeled defect, not lost.

**Functional Requirement Specification:**  
Every llama-server call writes an inference_traces row; every human edit/override of AI output writes a human_corrections row (each row is one labeled defect).

**Acceptance Criteria:**
NORMAL: every llama-server call writes an inference_traces row; every human edit writes a human_corrections row (one labeled defect).
EDGE: failed call → failure logged too.
NEGATIVE: human edit without a correction row → BLOCKED.
SILENT-FAILURE: logging silently skipped under load → caught by sampling.
CHALLENGE: 1,000 calls in a day → 1,000 trace rows, zero missing.
**Verification Method:**
1. [AUTO] Trace: every call → row. Evidence: count match.
2. [AUTO] Correction: every edit → labeled row. Evidence: query.
3. [AUTO] Sampling: random 100 calls → all logged. Evidence: query.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inference-call-human-correction-logging-3cfe152fc199816c8d85f754942937b0_
