# Taza OS URS — INTEGRATIONS cluster
_Exported: 2026-09-19 21:35 | 6 rows_
_Source: Notion Master URS & Specification Registry_

---
## INT-001 — Square API integration
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: Square wired for catalog sync, invoice creation, and payment webhooks — Square stays source of truth without manual re-entry.

**Functional Requirement Specification:**  
Square API: catalog sync ([[SPEC:SW-011]]), invoice creation ([[SPEC:PROD-07]]), payment webhooks (W8) — all three flows end-to-end, rate limits respected.

**Failure Behavior:**  
Fallback: manual Square console.

**Acceptance Criteria:**  
All 3 flows e2e; rate limits respected

**Verification Method:**
1. [AUTO] Sync: catalog sync ([[SPEC:W9]]) completes end-to-end. Evidence: log + row count.
2. [AUTO] Invoice: invoice creation via Square API succeeds. Evidence: test invoice.
3. [AUTO] Webhook: payment webhook triggers the deposit flow. Evidence: test event.
4. [AUTO] Rate limits: no 429s under normal volume. Evidence: log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Square-API-integration-3cfe152fc19981329fcad92bebddd3c5_

---
## INT-003 — Twilio SMS integration
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: SMS delivery for hot alerts, briefs, digests, reminders — fast, cheap, no dependency on checking email/dashboard.

**Functional Requirement Specification:**  
Twilio SMS integration: hot alerts ([[SPEC:W2]]), briefs ([[SPEC:W3]]), digest ([[SPEC:W6]]), reminders ([[SPEC:W13]]). SMS delivered under 60s to the correct recipient, under 300 chars, under $0.01/msg.

**Failure Behavior:**  
Fallback: email fallback; manual call for urgent items.

**Acceptance Criteria:**  
SMS <60s; correct recipient; <300 chars; <$0.01/msg

**Open Questions:**  
TOOL CHOICE OPEN: Twilio requires install/registration on Nick's and Sandra's phones. Alternatives to evaluate: carrier SMS gateway, push instead of SMS, ntfy (already proven, [[SPEC:PROD-25]]).

**Verification Method:**
1. [AUTO] Latency: SMS delivered <60s. Evidence: timestamp log.
2. [AUTO] Cost: <$0.01/msg. Evidence: Twilio billing.
3. [AUTO] Recipient: correct recipient, <300 chars. Evidence: log.
4. [NICK] Live: Sandra receives a hot-alert SMS on her phone. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Twilio-SMS-integration-3cfe152fc19981188648c25cbdfca396_

---
## INT-004 — AI API Integration
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: an AI API (cheapest capable/tested for the task) for CRM sessions, complex voice-command reasoning, and BOM substitution — cases too nuanced for deterministic logic/small models, predictable cost.

**Functional Requirement Specification:**  
AI API integration (cheapest capable/tested model per task type): CRM sessions ([[SPEC:W4]]), voice reasoning Path C ([[SPEC:W14]]), on-the-fly BOM substitution/unrecognized item ([[SPEC:KIT-015]]); JSON extraction on 'done'.

**Failure Behavior:**  
Fallback: a backup AI provider for CRM and Path C.

**Acceptance Criteria:**  
Coherent responses; JSON extraction on 'done'; Path C <25s

**Verification Method:**
1. [AUTO] JSON: CRM session and Path C return valid JSON on 'done'. Evidence: test.
2. [AUTO] Latency: Path C voice reasoning <25s. Evidence: timing log.
3. [NICK] Live: Sandra runs a real CRM session. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/AI-API-Integration-3cfe152fc19981a8bf2ff11a02c442cb_

---
## INT-005 — Whisper API integration
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: fast, accurate voice-to-text transcription for hands-free CRM notes.

**Functional Requirement Specification:**  
Whisper API integration: voice-to-text for CRM ([[SPEC:W5]]); under 1s latency, roughly $0.06/10min.

**Failure Behavior:**  
Fallback: "Type instead"; Web Speech API.

**Acceptance Criteria:**  
Accurate; <1s latency; budget compliant

**Verification Method:**
1. [AUTO] Latency: transcription <1s. Evidence: timing log.
2. [AUTO] Accuracy: golden-set transcripts match. Evidence: test.
3. [NICK] Live: Sandra dictates a real note. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Whisper-API-integration-3cfe152fc1998123ac75eae18a579d6d_

---
## INT-006 — On-device NPU voice inference (audio never leaves device)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: voice commands processed on-device via MicroTouch NPU — audio never leaves the building.

**Functional Requirement Specification:**  
On-device voice inference on the MicroTouch NPU for [[SPEC:W14]] — audio never leaves the device. (Note: D-051 overturned the original Sherpa-ONNX assumption; implementation path is now TFLite + NeuroPilot/NNAPI via the confirmed MT8390 NPU access, capability target unchanged.)

**Failure Behavior:**  
Fallback: on-device inference on WI-6 (LAN audio).

**Acceptance Criteria:**  
Runs on MT8390 NPU; no network audio; <3s short commands

**Verification Method:**
1. [AUTO] On-device: runs on MT8390 NPU; zero network audio. Evidence: code-search + network capture.
2. [AUTO] Latency: short commands <3s. Evidence: timing log.
3. [NICK] Live: crew issues a voice command on the MicroTouch. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/On-device-NPU-voice-inference-audio-never-leaves-device-3cfe152fc1998170b44bd24c47eb46da_

---
## INT-007 — Google Calendar + Places API integration
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: Google Calendar auto-sync and Phoenix-scoped address autocomplete on invoice form — no manual re-entry/full-address typing.

**Functional Requirement Specification:**  
Google Calendar + Places API integration: calendar sync ([[SPEC:W10]]) every 30min, address autocomplete on the Invoice Form returning Phoenix-area results.

**Failure Behavior:**  
Fallback: manual calendar; manual address entry.

**Acceptance Criteria:**  
Sync every 30min; Places returns Phoenix-area results

**Verification Method:**
1. [AUTO] Sync: calendar syncs every 30 min. Evidence: log.
2. [AUTO] Places: address autocomplete returns Phoenix-area results. Evidence: test.
3. [NICK] Live: Sandra types an address and gets Phoenix results. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Google-Calendar-Places-API-integration-3cfe152fc199811cb15bf401c67968ac_
