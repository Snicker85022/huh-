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

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inference-call-human-correction-logging-3cfe152fc199816c8d85f754942937b0_
