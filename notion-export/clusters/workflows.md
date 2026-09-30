# Taza OS URS — WORKFLOWS cluster
_Exported: 2026-09-19 21:35 | 14 rows_
_Source: Notion Master URS & Specification Registry_

---
## W1 — Lead Capture
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Lead Acquisition

**User Requirement Statement:**  
Need: a new lead that comes in by email or Wix form gets captured and turned into a task automatically, with Sandra notified right away — not sitting unread in an inbox.

**Functional Requirement Specification:**  
The system shall monitor a dedicated Gmail inbox for new lead notification emails (including Wix customer-inquiry notification emails — Wix still sends these), parse the lead data (name, contact, event type, date, guest count, budget signals), create a Lead record in NocoDB, create an associated follow-up Task, and send an SMS notification to Sandra. V1.0 trigger is Gmail-only. Fallback: manual NocoDB entry.

**Inputs:**  
Wix form payload, Gmail inbox

**Outputs:**  
NocoDB Leads table row; Task; SMS notification. Feeds W2

**Trigger:**  
Gmail (new Wix form submission email) — V1.0 email-only per D1; Wix webhook = V1.1 stub

**Open Questions:**  
A Wix API may be usable to pull inquiry data directly instead of relying on email parsing — evaluate.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Lead-Capture-3b5e152fc1998148923fff8bddd2d81b_

---
## W10 — Google Calendar Sync
**Status:** Superseded (D15 — replaced by Taza Calendar Web App, reads/writes `events` table directly) | **Priority:**  | **Release:** 

**Domain:**  
System Infrastructure

**Functional Requirement Specification:**  
On a 30-minute schedule, the system shall perform an incremental sync of the team Google Calendar, upserting changed events into the NocoDB Calendar Events table.

**Inputs:**  
Google Calendar API

**Outputs:**  
NocoDB Calendar Events (incremental upsert)

**Trigger:**  
Schedule every 30 minutes

**Failure Behavior:**  
Fallback: manual calendar checks.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Google-Calendar-Sync-3b5e152fc1998151a06bd5b924a9f1de_

---
## W11 — Change Log Writer
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
System Infrastructure

**Functional Requirement Specification:**  
On NocoDB webhooks fired by key table changes (Leads, Customers, Invoices, Tasks status changes), the system shall capture before/after field values and write a timestamped entry to the System Changelog.

**Inputs:**  
NocoDB webhook old/new value diffs

**Outputs:**  
System Changelog entries (audit trail)

**Trigger:**  
NocoDB webhooks on key tables (Leads, Customers, Customer Events, Tasks status changes)

**Failure Behavior:**  
Fallback: manual changelog entries.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Change-Log-Writer-3b5e152fc19981bf89ecc9f66f2ef5a0_

---
## W12 — Hourly Review Workflow
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Operational Monitoring

**Functional Requirement Specification:**  
On an hourly schedule, the system shall scan for: overdue Tasks, Leads with no response in >24 hours, and flagged Customer Events. Findings are written as alerts to the Change Log and trigger W13.

**Inputs:**  
Overdue Tasks; unresponded Leads (>24h); flagged Customer Events

**Outputs:**  
Alert written to Change Log, triggers W13

**Trigger:**  
Schedule every hour (or on-demand)

**Failure Behavior:**  
Fallback: manual review by Nick.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Hourly-Review-Workflow-3b5e152fc19981f19281e119ab71a7e7_

---
## W13 — Reminder & Alert Workflow
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Operational Monitoring

**Functional Requirement Specification:**  
On W12 output and on morning/afternoon schedules, the system shall format a digest of outstanding items and deliver it to Nick and Sandra via email, logging outbound customer-facing communications to the Communications table.

**Inputs:**  
Alert from W12; digest from W6

**Outputs:**  
Digest email to Nick + Sandra; Communications log

**Trigger:**  
W12 output or morning/afternoon schedule

**Failure Behavior:**  
Fallback: manual Slack/email check.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Reminder-Alert-Workflow-3b5e152fc19981199794f5451401e071_

---
## W14 — Voice Feedback Processor (Four-Path Routing)
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Exception Handling

**Functional Requirement Specification:**  
Voice input arrives via Chrome Web Speech API on MT1/MT2/z33, is processed on the N100, and is routed through four paths based on content: Path A (<3s) — match against command_registry.json → direct NocoDB update; Path B (<5s) — AI constrained JSON if confidence ≥0.80 → execute; Path C (<25s) — AI for complex exceptions → reason → execute → display summary; Path D (<3s) — system-observation prefix → log to voice_notes, respond "Noted for review," no system changes. SLA: A/D <3s, B <5s, C <25s. v0.5.1+. Fallback: manual task creation by Edgar.

**Inputs:**  
Transcribed voice text from Edgar/kitchen

**Outputs:**  
Direct NocoDB update (A/B), or plain-English summary+execute (C), or logged-only (D)

**Trigger:**  
Voice feedback webhook from MicroTouch feedback page (Sherpa-ONNX transcribed text)

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Voice-Feedback-Processor-Four-Path-Routing-3b5e152fc199818e9bf1de6c6396ef2c_

---
## W15 — Day-of BEO & Event Timeline Generator
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Event Execution

**Functional Requirement Specification:**  
On Event status → "Confirmed" (or manual trigger), the system shall generate a full day-of timeline and BEO. Model: AI for formatting only — all arithmetic is deterministic. Process: (1) zip-code drive-time lookup from the flat Phoenix-metro matrix, (2) back-calculate kitchen_departure = crew_arrival − drive_time − pack_buffer, (3) back-calculate pack_start from item count + guest count + setup buffer, (4) generate the full timeline from pack_start through breakdown_complete. Output: formatted BEO stored in the event NocoDB record + SMS to Nick with key times + available on Edgar's display. Confidence labels: drive-time estimates = Medium (zip-lookup, no live traffic); all other times are deterministic. Document watermark: "AI-estimated — confirm before distributing to staff." SLA: <60 seconds from trigger to SMS delivery. V2-FEAT-006 (PACK 2) replaces the zip-lookup drive time with the deterministic solver output; the W15 architecture stays the same. Fallback: manual timeline creation by Sandra.

**Inputs:**  
Confirmed invoice record from W7; menu timing attributes from W9 (prep_advance_max_hr, hot_hold_max_min, station_type); zip-code drive-time table

**Outputs:**  
Formatted BEO timeline in NocoDB event record; SMS to Nick; MicroTouch dashboard (Edgar)

**Trigger:**  
Event status to Confirmed (auto) OR manual trigger

**Verification Method:**  
SMART 23/25, Impact 19/20 — approved 2026-05-29.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Day-of-BEO-Event-Timeline-Generator-3b5e152fc19981cd83cae7c3c90675cb_

---
## W2 — Lead Scoring
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Lead Acquisition

**User Requirement Statement:**  
As the owner, I need incoming leads automatically sorted by how promising they are, so Sandra knows which ones deserve an immediate call and which can wait for the weekly review.

**Functional Requirement Specification:**  
On new Lead creation (W1 output), the system shall fetch the lead data, pass it to AI with Nick's scoring rubric, and return structured JSON: profit_score (1–5), category (Hot/Warm/Low/Pass), talking_points, red_flags. Hot leads trigger an immediate SMS to Sandra with the brief; Warm leads queue to the morning digest; Low/Pass route to weekly review.

**Inputs:**  
NocoDB Lead record from W1

**Outputs:**  
profit_score, category, talking_points, red_flags. Hot to SMS Sandra; Warm to digest W6; Low/Pass to weekly review

**Trigger:**  
New Lead created (W1 output)

**Failure Behavior:**  
Fallback: default score + manual review.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Lead-Scoring-3b5e152fc199814da3fbea5f4d2054a0_

---
## W3 — Pre-Call Brief SMS
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Lead Acquisition

**User Requirement Statement:**  
As Sandra, I need a quick refresher on who I'm calling and why, texted to me right before a scheduled follow-up call, so I'm not walking into it cold.

**Functional Requirement Specification:**  
When a Task of type 'follow-up call' is assigned to Sandra and is due within 60 minutes, the system shall fetch the customer profile + recent touchpoints, pass them to AI with the pre-call brief prompt, and deliver a 3-paragraph brief (3 paragraphs, ≤900 chars, ~150 words — phone-readable on the go) via Twilio SMS to Sandra. SLA: delivered per D9: fire at 60-min window entry, 5-min floor before due, poll 5 min, delivery SLA ≤2 min.

**Inputs:**  
NocoDB Customer profile from W2/W4

**Outputs:**  
3-paragraph SMS brief via Twilio to Sandra

**Trigger:**  
Task type follow-up call assigned to Sandra, due within 60 min

**Failure Behavior:**  
Fallback: manual reminder in NocoDB.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Pre-Call-Brief-SMS-3b5e152fc1998185b35ff2a7110d9b56_

---
## W4 — CRM Interview Session
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to talk through an update on a customer by voice or chat and have the system pull it into the right records itself, instead of me typing structured notes by hand.

**Functional Requirement Specification:**  
The system shall provide a multi-turn CRM session interface (SCREEN-10, port 3001) where Sandra selects a customer, and the system fetches the customer profile + recent voice notes + communications, opens a conversation with AI (cheapest capable/tested model for the task) as the CRM assistant, and manages the conversation turn-by-turn. On 'Done', the AI extracts structured updates as JSON; the system writes them to NocoDB Accounts/Contacts/Opportunities/Touchpoints and creates follow-up Tasks. The full conversation is stored in crm_sessions. Fallback: if the primary AI provider is down, use a backup AI provider.

**Inputs:**  
NocoDB Customer profile; Sandra's turns (text or via W5 voice)

**Outputs:**  
Structured JSON updates to NocoDB Customers table; follow-up Tasks; session summary

**Trigger:**  
Sandra opens CRM Session page and selects Customer and Start, OR replies GO to morning SMS

**Failure Behavior:**  
Fallback: Sandra continues manually, saves notes later.

**Maintenance Requirements:**  
~$0.10-0.30/session AI cost.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/CRM-Interview-Session-3b5e152fc1998139b87bff0888eb731f_

---
## W5 — CRM Voice Input Handler
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to just talk and have my words show up as editable text, instead of typing everything myself.

**Functional Requirement Specification:**  
When Sandra clicks 'Record' in the CRM session UI, the browser captures audio from the device microphone, sends the audio blob to the Whisper API, receives the transcript, and presents it in the CRM session as Sandra's text input for her to review/edit before sending. SLA (D13): ≤15s audio → <1s, 16–60s → <3s, >60s → rejected at capture. Measured clip-end to transcript in browser.

**Inputs:**  
Browser mic audio blob

**Outputs:**  
Transcribed text feeds into W4 as Sandra's message

**Trigger:**  
Sandra clicks Record on CRM Session page

**Failure Behavior:**  
Whisper down → fail visibly: 'transcription unavailable, please type' (D13).

**Maintenance Requirements:**  
~$1.80/mo at 10min/day.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/CRM-Voice-Input-Handler-3b5e152fc19981cea6f8da10eef3955c_

---
## W6 — Nightly CRM Deep Analysis
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need my voice notes and recent customer activity turned into a short morning briefing of what needs my attention today, without me reviewing everything myself overnight.

**Functional Requirement Specification:**  
At midnight, the system shall: throttle CPU, fetch all unprocessed voice notes + recent customer communications + all Active Accounts/Leads/Opportunities, run AI overnight analysis (intent tagging, entity extraction, CRM record promotion, opportunity flags, follow-up ranking), write results to NocoDB, compose a morning digest (top 5 follow-ups + hot opportunities), and schedule SMS to Sandra at 7:00am. Must complete by 5:00am. SLA failure triggers retry at 1am and an alert to Nick by 5am if still failing.

**Inputs:**  
All Leads + Customer profiles from W1/W2/W4; Wix Shop Customers 30-day window

**Outputs:**  
opportunity_flags, follow_up_rank, next_action_suggestion, reactivation_flag, upsell_angle; Wix conversion candidates; morning digest SMS 7am feeds W13

**Trigger:**  
Schedule midnight 00:00 UTC

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Nightly-CRM-Deep-Analysis-3b5e152fc199818fae84dd74324cb466_

---
## W7 — Invoice Draft Workflow
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: once a lead is ready to invoice, the invoice drafts itself from everything already captured about the event — the WHY behind the setup, not just line items — so Sandra/Nick only review and approve instead of building it from scratch.

**Functional Requirement Specification:**  
On Lead status → 'Ready to Invoice', the system shall fetch lead data + CRM notes + decision history, pass them to AI (invoice_blocks_generator prompt, INFERENCE 10 XML-delimited input, output-delimited JSON), and generate: three $0 custom line items (EVENT DETAILS, VENUE & LOGISTICS, SETUP SPECIFICATION with WHY context from CRM notes), four Square Order Custom Attributes (setup_type, tables_count, linens_tier, kitchen_departure), and food line items from the Square catalog. Creates an approval Task for Nick/Sandra review before publish. Output format per CX-001..CX-007. Fallback: manual Square invoice.

**Inputs:**  
Lead data (event date, guest count, service level, menu SKUs); CRM notes from W4; Square catalog attributes from W9

**Outputs:**  
3 $0 custom line items (EVENT DETAILS/VENUE & LOGISTICS/SETUP SPEC); 4 Square Order Custom Attributes; food line items; approval Task for Nick/Sandra. Feeds W15

**Trigger:**  
Lead status to Ready to Invoice

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Invoice-Draft-Workflow-3b5e152fc1998163bfc6f6de072d8f90_

---
## W9 — Square Menu Sync
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: menu changes made in Square (price, new item, updated attributes) show up in the system automatically, without anyone re-entering them by hand.

**Functional Requirement Specification:**  
On a Square catalog.version.updated webhook (primary trigger) or a 6-hour fallback schedule, the system shall fetch all active Catering items including all 12 Catalog Intelligence custom attributes via SearchCatalogItems (NOT SearchCatalogObjects — only SearchCatalogItems returns custom attribute values), and upsert the canonical NocoDB Menu Items table. The catalog_version cursor is stored in NocoDB for incremental sync; on webhook miss, the Square Events API replay path is used before falling back to a full re-fetch. Fallback: manual NocoDB edit as last resort.

**Inputs:**  
Square Catalog (11 Catalog Intelligence attributes: 6 visible + 5 hidden, per D18)

**Outputs:**  
NocoDB Menu Items table (incremental upsert), catalog_version cursor. Feeds W7 (RAG lookups), V2-FEAT-006 Backward Scheduler

**Trigger:**  
catalog.version.updated Square webhook (primary) + 6hr fallback schedule

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Square-Menu-Sync-3b5e152fc19981d8b3c3e961396f7fc9_
