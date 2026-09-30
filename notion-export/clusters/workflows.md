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

**Acceptance Criteria:**  
NORMAL: A Wix inquiry email arriving in the monitoring inbox creates a Lead (name/contact/event type/date/guest count/budget), creates a follow-up Task, and sends SMS to Sandra.
EDGE: Duplicate email (same Message-ID) → skipped, no second Lead. Same sender + event date within 30-day window → flagged for dedupe, never silently merged.
EDGE: Email missing guest count or budget → Lead still created, blank fields + FLAG for missing data; follow-up Task still fires.
NEGATIVE: Email from a non-Wix/Square sender → classified DIRECT/AUTO, zero side effects on Leads.
SILENT-FAILURE: A parse fails and drops the lead → impossible: unparseable email routes to exceptions_queue, never silently accepted.
CHALLENGE: Feed a malformed Wix email (missing fields, HTML artifacts) → Lead created with what was extracted + FLAGs on gaps; no crash, no partial row.

**Verification Method:**  
1. [NICK+AUTO] Live test: send a real Wix form inquiry; confirm Lead + Task + SMS. Evidence: phone SMS screenshot + psql result.
2. [AUTO] Dedupe test: resend the same Message-ID → zero new Leads. Evidence: row count before/after + log.
3. [AUTO] Parse-failure drill: inject a malformed email → appears in exceptions_queue with reason. Evidence: psql query + screenshot.
4. [AUTO] Wrong-sender test: send from a personal address → classified, no Lead row. Evidence: classification log.
5. [NICK] Nick hands-on review of a real week of inbox processing. Evidence: observation log.


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
## W11 — System Changelog View
**Status:** In Development (revised — read view only, D21) | **Priority:**  | **Release:** 

**Domain:**  
System Infrastructure

**Functional Requirement Specification:**  
The system shall provide a read-only changelog view over `audit_log` (PROD-22 — append-only, trigger-fired on every canonical write), filtered to the key tables: Leads, Customers, Invoices (= event records), Tasks. Nick/Sandra review field-level before/after history here. No separate capture path — PROD-22's audit trigger is the sole writer. Supersedes the earlier raw-diff design (duplicated PROD-22; folded in per D21).

**Inputs:**  
audit_log (PROD-22 — actor, table, old/new, timestamp)

**Outputs:**  
Read-only changelog view over audit_log, key tables (Leads, Customers, Invoices, Tasks)

**Trigger:**  
On-demand view query (no write path)

**Failure Behavior:**  
Fallback: manual changelog entries.

**Required for Release:**  
NO

**Acceptance Criteria:**  
NORMAL: Read-only view over audit_log shows before/after history for Leads/Customers/Invoices/Tasks.
EDGE: Query on a table with zero changes → empty result, no error.
NEGATIVE: Any write attempt through W11 → rejected (read-only view).
SILENT-FAILURE: A canonical write missing from audit_log → caught by PROD-22 trigger coverage; the view shows nothing missing.
CHALLENGE: 10k audit rows → view returns in reasonable time, filtered correctly.

**Verification Method:**  
1. [AUTO] Read test: change a Lead → appears in view with old/new. Evidence: psql + screenshot.
2. [AUTO] Write-reject: attempt INSERT via view → permission denied. Evidence: error log.
3. [AUTO] Filter test: view excludes non-key tables. Evidence: psql query.
4. [AUTO] PROD-22 coverage: every canonical write produces an audit row. Evidence: query + count.


_Notion: https://app.notion.com/p/Change-Log-Writer-3b5e152fc19981bf89ecc9f66f2ef5a0_

---
## W12 — Hourly Review Workflow
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Operational Monitoring

**Functional Requirement Specification:**  
On an hourly schedule, the system shall scan for: overdue Tasks, Leads with no response in >24 hours, and flagged Customer Events. Findings are written as alerts to the changelog (alert queue) and trigger W13.

**Inputs:**  
Overdue Tasks; unresponded Leads (>24h); flagged Customer Events

**Outputs:**  
Alert written to changelog (alert queue), triggers W13

**Trigger:**  
Schedule every hour (or on-demand)

**Failure Behavior:**  
Fallback: manual review by Nick.

**Required for Release:**  
NO

**Acceptance Criteria:**  
NORMAL: Hourly scan finds overdue Tasks, Leads >24h no response, flagged Customer Events → alerts to changelog (alert queue), triggers W13.
EDGE: Lead at exactly 24h → flagged; 23h59m → not flagged.
NEGATIVE: Duplicate alert for the same item every hour → impossible: idempotent per item+state.
SILENT-FAILURE: Scan runs but writes nothing on failure → alert to exceptions; never silent.
CHALLENGE: 500 tasks + 300 leads scanned → completes within window, no missed items.

**Verification Method:**  
1. [AUTO] Live scan: create overdue task + 25h lead → both alert. Evidence: psql + screenshot.
2. [AUTO] Boundary: lead at 23h59m → no alert. Evidence: log.
3. [AUTO] Idempotency: two consecutive hours → no duplicate alert for the same item. Evidence: alert log.
4. [AUTO] Volume: synthetic 500/300 → all caught. Evidence: count + log.


_Notion: https://app.notion.com/p/Hourly-Review-Workflow-3b5e152fc19981f19281e119ab71a7e7_

---
## W13 — Reminder & Alert Workflow
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Operational Monitoring

**Functional Requirement Specification:**  
The system shall be the sole delivery layer for W6 digest + W12 alerts. On W12 output and the W6 digest, deliver via canonical channels per D10 (Twilio SMS to Sandra for actionable items; email to Nick), logging every outbound communication to the Communications table. One delivery path for the whole system.

**Inputs:**  
Alert from W12; digest from W6

**Outputs:**  
Twilio SMS to Sandra (actionable); email to Nick; Communications log

**Trigger:**  
W12 alert; W6 digest ready; morning/afternoon schedule

**Failure Behavior:**  
Fallback: manual Slack/email check.

**Required for Release:**  
NO

**Acceptance Criteria:**  
NORMAL: W6 digest + W12 alerts delivered via canonical channels (Twilio SMS to Sandra for actionable; email to Nick), logged to Communications.
EDGE: SMS delivery failure → retry, then fallback channel (email), logged.
NEGATIVE: Delivery without logging → impossible: log write is part of the transaction.
SILENT-FAILURE: A notification generated but never sent → surfaced by delivery-status tracking.
CHALLENGE: 30 alerts at once → all delivered, none dropped, all logged.

**Verification Method:**  
1. [NICK+AUTO] Live: W12 alert → Sandra's phone receives SMS, Communications has a row. Evidence: screenshot + psql.
2. [AUTO] Fail drill: block Twilio → fallback email + retry logged. Evidence: log.
3. [AUTO] Volume: 30 alerts → 30 logs, zero drops. Evidence: count + log.
4. [AUTO] Audit: sample 10 Communications rows → each traces to a real trigger. Evidence: query.


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

**Acceptance Criteria:**  
NORMAL: Voice feedback routes via 4 paths: registry match → D, simple → AI constrained, complex → AI multi-step, else → log.
EDGE: Unknown command not in registry → routed to log, never guessed.
NEGATIVE: AI path fails → command logged, no silent drop.
SILENT-FAILURE: Empty/garbled transcription → routed to log for review, not treated as a valid command.
CHALLENGE: 10 voice commands of mixed types → each routes to the correct path, no cross-contamination.

**Verification Method:**  
1. [AUTO] Registry-match test: known command → D path, direct update. Evidence: log.
2. [AUTO] Unknown-command test → log path. Evidence: log.
3. [AUTO] AI-fail drill: block AI → command logged. Evidence: log.
4. [AUTO] Batch: 10 mixed commands → correct routing. Evidence: routing log.


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

**Required for Release:**  
NO

**Acceptance Criteria:**  
NORMAL: On event Confirmed, timeline generated from kitchen_exit = crew_arrival − drive_time − pack_buffer, pack_start back-calculated, full timeline through breakdown; BEO stored + SMS to Nick <60s.
EDGE: Missing venue zip → drive time flagged Medium confidence or blocked; never guessed.
EDGE: Refund rescinds Confirmed → re-payment re-triggers one authorized W15 run (idempotent on invoice ID + Message-ID).
NEGATIVE: LLM attempts arithmetic → blocked (AI formats only; deterministic math).
SILENT-FAILURE: Hold-time attribute missing for an item → downstream flags low confidence, routes to review, never fabricates.
CHALLENGE: 3 events confirmed within 5 min → three timelines generated correctly, no cross-event contamination.

**Verification Method:**  
1. [NICK] Live: confirm a real event → BEO + SMS within 60s. Evidence: SMS screenshot + BEO document.
2. [AUTO] Math audit: verify kitchen_departure = crew_arrival − drive_time − pack_buffer for 5 events. Evidence: computed vs stored.
3. [AUTO] Refund drill: rescind + re-pay → exactly one W15 run each, no duplicate BEO. Evidence: log.
4. [AUTO] Missing-data test: event with missing hold time → flagged, not guessed. Evidence: flag + review queue.
5. [NICK] Nick reviews a real BEO against the event. Evidence: observation log.


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

**Acceptance Criteria:**  
NORMAL: profit_score 5/4 → Hot, 3 → Warm, 2 → Low, 1 → Pass, computed deterministically from ~/repo/config/lead_scoring_rubric.md; rubric_version = commit hash embedded.
EDGE: AI unavailable → category=Low + scoring_ai_unavailable=true (fail safe, D7).
EDGE: AI adjusts category by exactly one level with written red_flags reason → allowed; two levels → rejected.
NEGATIVE: Silent override (AI changes category without red_flags) → BLOCKED; score_history records the attempt.
SILENT-FAILURE: Re-score overwrites history → impossible: score_history is append-only; standing score = latest entry.
CHALLENGE: Re-score fires 3× in one day (W4 Done + field update + manual) → three append-only entries, standing score correct, no duplicates.

**Verification Method:**  
1. [AUTO] Threshold test: 5 leads with scores 1–5 → categories Pass/Low/Warm/Hot/Hot exactly. Evidence: psql result.
2. [AUTO] Fail-safe test: kill AI endpoint, score a lead → Low + flag. Evidence: psql + log.
3. [AUTO] Append-only audit: re-score one lead 3× → score_history has 3 rows, never overwritten. Evidence: psql query.
4. [AUTO] Rubric version: edit + commit rubric, score a lead → rubric_version = new commit hash. Evidence: psql + git log.
5. [AUTO] Code-search: no code path writes category except through the threshold function. Evidence: grep output.


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

**Acceptance Criteria:**  
NORMAL: Follow-up Task enters its 60-min window → 3-paragraph brief (≤900 chars: who / last interaction / angle) generated and delivered within 2 min (D9).
EDGE: No recent touchpoints → brief reads "no recent touchpoints — call fresh"; never fabricated context.
EDGE: due_time shifts ≥15 min after delivery → exactly one re-brief with logged reason; otherwise no duplicate.
NEGATIVE: Two briefs for the same task_id → impossible: idempotent on task_id.
SILENT-FAILURE: Brief generated from stale customer data → caught: data fetched at generation time, timestamp on brief.
CHALLENGE: 20 tasks enter windows simultaneously → all briefs delivered within SLA, zero dropped, zero duplicated.

**Verification Method:**  
1. [NICK+AUTO] Live test: create a task due in 70 min → brief fires on window entry. Evidence: SMS screenshot + log timestamp.
2. [NICK] Empty-touchpoint test → "call fresh" copy. Evidence: screenshot.
3. [AUTO] Idempotency: replay the trigger → no second SMS. Evidence: delivery log.
4. [AUTO] Shift test: move due_time +20 min → re-brief logged with reason. Evidence: log.
5. [AUTO] Load: batch of 20 → 20 briefs, zero dupes. Evidence: log + count.


_Notion: https://app.notion.com/p/Pre-Call-Brief-SMS-3b5e152fc1998185b35ff2a7110d9b56_

---
## W4 — CRM Interview Session
**Status:** Deployed | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to talk through an update on a customer by voice or chat and have the system pull it into the right records itself, instead of me typing structured notes by hand.

**Functional Requirement Specification:**  
The system shall provide a multi-turn CRM session interface (SCREEN-10, port 3001) where Sandra selects a customer, and the system fetches the customer profile + recent voice notes + communications, opens a conversation with deepseek-v4-flash as the CRM assistant, and manages the conversation turn-by-turn. On 'Done', the AI extracts structured updates as JSON; the system writes them to NocoDB Accounts/Contacts/Opportunities/Touchpoints and creates follow-up Tasks. The full conversation is stored in crm_sessions. Fallback: backup AI provider — TBD, wire later.

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

**Acceptance Criteria:**  
NORMAL: Sandra runs a multi-turn session with deepseek-v4-flash; on Done, structured JSON extraction writes to canonical CRM tables + creates follow-up Tasks.
EDGE: Tab close before Done → session=partial, no auto-extract; transcript preserved (D12).
EDGE: 24h inactivity → session=abandoned; no extraction.
NEGATIVE: Extraction fails schema validation → raw transcript to exceptions_queue + SMS to Sandra; nothing bad written to CRM.
SILENT-FAILURE: Partial write (some fields written, others failed) → impossible: extraction validates all-or-nothing before writing.
CHALLENGE: Feed a rambling 20-turn transcript with contradictory info → extraction flags ambiguity, Sandra resolves, no silent guess.

**Verification Method:**  
1. [NICK+AUTO] Live session: Sandra runs a real session → JSON lands in correct tables + task created. Evidence: psql + screenshot.
2. [AUTO] Abandon test: open session, simulate inactivity → abandoned, no extraction. Evidence: status log.
3. [AUTO] Validation-fail drill: inject bad extraction → exceptions_queue + SMS. Evidence: screenshot + psql.
4. [AUTO] Schema audit: sample 10 extractions → every field validates against CRM schema. Evidence: query + log.
5. [NICK] Nick reviews a real session end-to-end. Evidence: observation log.


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

**Acceptance Criteria:**  
NORMAL: ≤15s clip → transcript in browser <1s (clip-end to displayed text, D13).
EDGE: 16–60s clip → <3s.
EDGE: >60s clip → rejected at capture with "clip too long, please re-record".
NEGATIVE: Whisper down → visible "transcription unavailable, please type"; never a silent hang.
SILENT-FAILURE: Audio captured but transcript never delivered → timeout surfaces an error state, not an endless spinner.
CHALLENGE: 10 consecutive clips in a live session → all meet tiered SLA, no degradation.

**Verification Method:**  
1. [AUTO] Timing test: 10 clips at 10s → measure clip-end to text. Evidence: browser timings log.
2. [AUTO] Boundary: 60s and 61s clips → 60s accepted, 61s rejected. Evidence: screenshots.
3. [AUTO] Whisper-down drill: block the API → visible failure message. Evidence: screenshot.
4. [NICK] Real use: Sandra dictates a real note → transcript editable, feeds W4. Evidence: observation log + screenshot.


_Notion: https://app.notion.com/p/CRM-Voice-Input-Handler-3b5e152fc19981cea6f8da10eef3955c_

---
## W6 — Morning CRM Digest
**Status:** In Development (revising — digest only) | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need my voice notes and recent customer activity turned into a short morning briefing of what needs my attention today, without me reviewing everything myself overnight.

**Functional Requirement Specification:**  
At midnight, the system shall: aggregate the day's touchpoints + W2 scores + open tasks, rank follow-ups (who needs contacting today), compose a morning digest (top 5 follow-ups + hot opportunities), and write the digest to the changelog, triggering W13 for delivery. Must complete by 5:00am. SLA failure triggers retry at 1am and an alert to Nick by 5am if still failing. Lead scoring itself lives in W2 (real-time); this spec only ranks and composes.

**Inputs:**  
W2 scores; touchpoints; open tasks from W12

**Outputs:**  
Morning digest (top 5 follow-ups + hot opportunities) → feeds W13 for delivery

**Trigger:**  
Schedule midnight 00:00 UTC

**Required for Release:**  
NO

**Acceptance Criteria:**  
NORMAL: At midnight, digest of top-5 follow-ups + hot opportunities composed from W2 scores + touchpoints + open tasks, written to changelog, triggers W13; complete by 5am.
EDGE: Zero touchpoints → digest says so; no fabricated entries.
NEGATIVE: Scoring inputs missing → digest ranks only what it can source; no invented scores.
SILENT-FAILURE: Digest composed but W13 never triggered → alert to Nick by 5am if undelivered.
CHALLENGE: A day with 100 touchpoints + 20 open tasks → top-5 ranked correctly, rest omitted, complete by 5am.

**Verification Method:**  
1. [NICK] Live run: full digest on a real day → top-5 matches Nick's expectation. Evidence: screenshot + observation log.
2. [AUTO] Empty-day run → "nothing to report" digest. Evidence: screenshot.
3. [NICK+AUTO] Fail drill: block W13 trigger → Nick alerted by 5am. Evidence: SMS screenshot.
4. [AUTO] Volume: synthetic 100-touchpoint day → completes by 5am, top-5 only. Evidence: log + timestamps.


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

**Acceptance Criteria:**  
NORMAL: "Create AI Draft" pre-fills all 8 form sections from PostgreSQL within ~10–15s, with a confidence label (Pulled/Inferred/Guessed) on every field.
EDGE: Field with missing source data → blank with honest low confidence; never fabricated.
EDGE: kitchen_departure_time computed deterministically (crew_arrival − drive_time − pack_buffer), shown read-only with confidence label — not AI-generated.
EDGE: Unusual dietary combination (nut-free + halal + vegan) → dietary flags correct on every food line.
NEGATIVE: AI invents a serves count, hold time, or pan geometry → BLOCKED; field routes to Sandra review.
NEGATIVE: Draft generated from an empty CRM record → no invented WHY sentences; those lines absent or blank.
SILENT-FAILURE: A value labeled Pulled that does not exist in PostgreSQL → caught in audit; every Pulled label traces to a real row.
CHALLENGE: Feed a lead with 0 CRM notes + 0 call summaries → structurally valid output, blanks where unknown.
CHALLENGE: Sandra changes 5 fields after draft → delta between AI draft and her edits visible and reviewable, not silently overwritten.

**Verification Method:**  
1. [NICK+AUTO] Scenario battery: 20 lead scenarios (rich/empty/edge dietary) → inspect output. Evidence: screenshots + log.
2. [AUTO] Fabrication check: deliberately empty CRM → zero invented WHY sentences, honest confidence. Evidence: screenshot + observation log.
3. [AUTO] Arithmetic guard: code-review + grep proving kitchen_departure_time comes from a deterministic function. Evidence: diff + grep.
4. [NICK] Live pilot: Sandra runs one real draft; Nick reviews delta. Evidence: before/after screenshots + observation log.
5. [AUTO] Confidence audit: sample 20 drafts; every Pulled label traces to a real PostgreSQL row. Evidence: query + result log.


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

**Acceptance Criteria:**  
NORMAL: A new item added in Square appears in menu_items within one 6h sync cycle, with all 11 attributes populated.
NORMAL: A price change in Square is reflected in menu_items on the next sync.
EDGE: Item deactivated in Square → is_active=false only after 2 consecutive misses (not on first miss).
EDGE: Item reactivated → is_active=true on next sync.
EDGE: Item near Square's 20-definition attribute cap → remaining headroom visible.
NEGATIVE: SearchCatalogObjects used anywhere → BLOCKER (silently returns no custom-attribute values).
NEGATIVE: 2 consecutive full-sync failures → Twilio SMS to Nick fires. Never silent.
SILENT-FAILURE: One item silently missing an attribute after sync → completeness check catches it, routes to review.
CHALLENGE: Kill Square API mid-sync → loud failure, no partial/corrupt write, next cycle retries cleanly.
CHALLENGE: ≥1,000 items in catalog → sync completes within SLA without dropping attributes.

**Verification Method:**  
1. [AUTO] Live insert: add a test item in Square; confirm it lands via psql ≤6h. Evidence: Square screenshot + psql result.
2. [AUTO] Code-search: grep SearchCatalogObjects → zero hits. Evidence: command + output.
3. [AUTO] Completeness audit: psql join Square catalog vs menu_items → 100% attribute coverage. Evidence: query + screenshot.
4. [NICK+AUTO] Failure drill: stop sync, force 2 consecutive failures → SMS to Nick. Evidence: phone screenshot + observation log.
5. [AUTO] Blip test: block API one cycle → item NOT deactivated; two cycles → deactivated. Evidence: observation log.


_Notion: https://app.notion.com/p/Square-Menu-Sync-3b5e152fc19981d8b3c3e961396f7fc9_
