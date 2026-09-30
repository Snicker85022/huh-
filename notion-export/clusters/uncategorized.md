# Taza OS URS — UNCATEGORIZED cluster
_Exported: 2026-09-19 21:35 | 17 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-CALL-001 — Consent-Gated Recording Trigger
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to ask for the customer's real, spoken consent before any AI note-taker starts recording — not just play them a notice — so I'm never recording someone who actually objected.

**Functional Requirement Specification:**  
Before any AI-assisted call recording begins, Sandra shall verbally disclose that an AI note-taking assistant may record the call and shall verbally request the customer's consent, waiting for an affirmative spoken response before starting the recording. Recording shall never start automatically, silently, or before an affirmative response is given. A declined or absent response shall route to the manual brain-dump path (URS-CALL-004), not to recording.

**Rationale:**  
The 2026 Otter.ai/Fireflies litigation turns on whether participants have a genuine opportunity to decline before recording starts, not merely a notification. Written to that stricter standard rather than Arizona's one-party-consent minimum, since customers may be calling from any state.

**Acceptance Criteria:**
NORMAL: recording starts only after verbal disclosure AND affirmative spoken consent.
EDGE: declined or absent response → manual brain-dump path (URS-CALL-004).
NEGATIVE: auto-start or silent recording → impossible.
SILENT-FAILURE: recording without a consent log → caught by URS-CALL-006 audit.
CHALLENGE: customer says no → zero audio captured of that customer.
**Verification Method:**
1. [AUTO] Decline: customer declines → no recording, brain-dump offered. Evidence: log.
2. [AUTO] Audit: consent event logged with timestamp. Evidence: query.
3. [NICK] Live: Sandra asks, customer consents → recording starts. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Consent-Gated-Recording-Trigger-3d0e152fc19981278590f6e55d1ddd07_

---
## URS-CALL-002 — Native iOS Call Recording Integration
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: get call recording and transcription working without building and maintaining a whole custom phone-calling system — use what the iPhone already does for free.

**Functional Requirement Specification:**  
The system shall use the iPhone's native Call Recording feature (iOS 18.1+/iOS 26, available on iPhone 17 Pro) to capture call audio and on-device transcription, rather than a custom VoIP/softphone recording pipeline. Sandra places/receives the call normally through the standard Phone app; the companion app does not mediate call initiation and instead picks up the resulting Notes recording/transcript afterward. Recording is enabled only after consent is obtained per URS-CALL-001.

**Rationale:**  
Decision (Nick, agnostic on call-through-app vs. app-on-the-side — chose whichever ships fastest): building a custom in-app dialer would require a VoIP/CallKit integration purely to get call-audio access Apple already provides for free via the Phone app on A14-chip-and-later devices, including automatic recording-in-progress announcement and on-device transcription to Notes. No dialer-mediated call initiation is required for V1.

**Acceptance Criteria:**
NORMAL: uses iPhone native Call Recording + on-device transcription; no custom dialer mediates call initiation.
EDGE: recording enabled only after consent per URS-CALL-001.
NEGATIVE: companion app mediating call initiation → out of scope (must not).
SILENT-FAILURE: recording captured but never retrieved → caught by post-call pickup.
CHALLENGE: a full real call → audio + transcript available in Notes after hangup.
**Verification Method:**
1. [AUTO] No-dialer: code search confirms no VoIP/CallKit mediation. Evidence: code-search.
2. [NICK] Live: Sandra records a real call via the Phone app → Notes entry appears. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Native-iOS-Call-Recording-Integration-3d0e152fc19981b6aa19df19aee6f1d5_

---
## URS-CALL-003 — Post-Call Transcript Review & Edit
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to see and fix the transcript before anything from the call goes into the CRM — I don't want an AI's raw guess of what was said becoming the permanent record.

**Functional Requirement Specification:**  
After a recorded call ends, the system shall retrieve the resulting transcript (from the Notes app Call Recording entry) and present it to Sandra for review and edit before it is submitted anywhere. No transcript shall be submitted to the CRM without Sandra's explicit review-and-submit action.

**Acceptance Criteria:**
NORMAL: transcript retrieved and presented for review/edit before any CRM submission.
EDGE: Sandra edits → the edited version is what submits.
NEGATIVE: raw transcript auto-submitted without review → blocked.
SILENT-FAILURE: transcript submitted but review step skipped → caught (no submit without review action).
CHALLENGE: a messy transcript → Sandra edits 10 lines → edited version submits.
**Verification Method:**
1. [AUTO] Gate: no submit path before review flag set. Evidence: log/test.
2. [NICK] Live: Sandra reviews and edits a real transcript. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Post-Call-Transcript-Review-Edit-3d0e152fc199817bb981e0f22acc3fbf_

---
## URS-CALL-004 — Manual Brain-Dump Fallback
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, when a customer doesn't want to be recorded, I still need an easy way to capture what we talked about right after we hang up, from memory.

**Functional Requirement Specification:**  
When consent is declined or not obtained, the system shall prompt Sandra immediately after the call ends for a manual brain-dump — either typed free text or a voice memo she records herself (not a recording of the customer) — and shall not attempt to capture any audio of the actual customer conversation.

**Acceptance Criteria:**
NORMAL: declined consent → immediate post-call prompt for typed or voice-memo brain-dump.
NEGATIVE: no customer audio captured in the fallback path.
SILENT-FAILURE: fallback not offered after a decline → caught.
CHALLENGE: Sandra hangs up a no-consent call → brain-dump offered and completed.
**Verification Method:**
1. [AUTO] No-capture: no customer-audio path in fallback. Evidence: code-search.
2. [NICK] Live: Sandra does a real brain-dump after a no-consent call. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Manual-Brain-Dump-Fallback-3d0e152fc19981f09e9bc85d07f304df_

---
## URS-CALL-005 — Submit-to-CRM Handoff
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: however Sandra captures a call — edited transcript or brain-dump — it ends up in the CRM the same way, tagged with how it was captured.

**Functional Requirement Specification:**  
On Sandra's submit action, the system shall send the finalized content — either the edited transcript (URS-CALL-003) or the manual brain-dump (URS-CALL-004) — to the CRM intake point (URS-CRM-008), tagged with which path was used and the consent status.

**Acceptance Criteria:**
NORMAL: edited transcript or brain-dump submits to URS-CRM-008 with path + consent tags.
EDGE: both paths tag correctly.
NEGATIVE: untagged content → blocked.
CHALLENGE: 5 calls in a day → all submit tagged correctly.
**Verification Method:**
1. [AUTO] Tagging: submitted record carries path + consent status. Evidence: query.
2. [NICK] Live: Sandra submits a real call. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Submit-to-CRM-Handoff-3d0e152fc19981a18623e9bf6d7d9e9f_

---
## URS-CALL-006 — Consent Audit Trail
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As the owner, I need proof that consent was asked and what the answer was for every call, kept separately from the call content itself, so we have a defensible record if it's ever questioned.

**Functional Requirement Specification:**  
The system shall log, for every call handled through this workflow, whether verbal consent was requested, whether it was granted, and a timestamp — independent of and in addition to any content captured. This log shall be retained per the business's record-retention policy and shall never itself contain recorded audio.

**Rationale:**  
Protects Sandra and the business with a defensible compliance record, separate from the call content itself.

**Acceptance Criteria:**
NORMAL: every call logs consent-requested / consent-granted / timestamp, separate from call content.
EDGE: log retained per policy and never contains audio.
NEGATIVE: consent log embedded in content → violates separation.
SILENT-FAILURE: a call with no consent log → caught.
CHALLENGE: legal review requests consent history → complete, defensible log.
**Verification Method:**
1. [AUTO] Separation: consent log table distinct from content, no audio column. Evidence: schema.
2. [AUTO] Completeness: zero calls without a consent log. Evidence: query.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Consent-Audit-Trail-3d0e152fc19981b9b97dd2b4181b7dc4_

---
## URS-CRM-001 — Prospect Intake & Central Record
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: one real prospect list, not a notebook plus a spreadsheet.

**Functional Requirement Specification:**  
The system shall provide a single canonical prospect record for every inbound sales inquiry, capturing at minimum: prospect name, phone number, event date, guest count, event type (corporate/wedding/birthday/other), lead source, and free-text notes. Every phone-originated or web-originated lead shall be entered into this record within the same interaction — no lead shall exist only in a notebook, spreadsheet, or unsynced local note.

**Dependency Notes:**  
Replaces Sandra's paper notebook + manual Google Sheet transcription step. Extends the existing Accounts/Contacts/Opportunities/Touchpoints tables (W4/CRM 3) rather than creating a parallel schema. Is the canonical record that CRM 21 (W1, Wix/Gmail lead capture) also writes into — phone-originated leads and web-originated leads land in the same record, not separate ones.

**Rationale:**  
Directly addresses Sandra's stated pain point: "I don't have a spot that has all the prospect lists with details about their event" — her spreadsheet is a manual, easily-abandoned workaround.

**Acceptance Criteria:**
NORMAL: every inbound inquiry (phone or web) creates or updates one canonical prospect record within the same interaction — name, phone, event date, guest count, type, source, notes.
EDGE: web leads (W1) and phone leads land in the SAME record type, no separate schema.
EDGE: partial data (call comes in mid-task) → minimum fields captured; full detail later per URS-CRM-009.
NEGATIVE: a lead existing only in notebook/spreadsheet → impossible: intake writes the record immediately.
SILENT-FAILURE: a lead dropped between capture and record → caught by W1 record-count reconciliation.
CHALLENGE: 10 leads in one day, mixed phone/web → all land in canonical records, zero duplicates.
**Verification Method:**
1. [AUTO] Create: phone-originated lead → record appears with all fields. Evidence: psql.
2. [AUTO] Unify: web and phone leads → same table, same shape. Evidence: psql.
3. [AUTO] Dedupe: same name+phone re-entered → flagged, no silent duplicate. Evidence: query.
4. [NICK] Live: Sandra captures a real call → record visible. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Prospect-Intake-Central-Record-3d0e152fc199816b830ed9b202fe763d_

---
## URS-CRM-002 — Pipeline Stage Model
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: see where each prospect actually stands, not just booked or not.

**Functional Requirement Specification:**  
The system shall track every prospect record through a defined pipeline: Lead Captured → Contacted → Qualified → Proposal Sent → Negotiation → Booked (Won) / Lost (Ghosted or Declined). Each stage transition shall be explicit (user-initiated or system-triggered per URS-CRM-004), timestamped, and visible in the record's history. A prospect shall be in exactly one stage at any time.

**Rationale:**  
Sandra's current process is binary — a name is either on the spreadsheet or off it once booked. A defined pipeline makes partial progress (contacted-but-not-booked) visible instead of invisible.

**Acceptance Criteria:**
NORMAL: every prospect is in exactly one stage; every transition is timestamped and visible in history.
EDGE: Booked→Won and Lost→(Ghosted/Declined) are explicit transitions.
NEGATIVE: a prospect in two stages at once → impossible (single-stage invariant).
SILENT-FAILURE: a stage change not timestamped → caught by history audit.
CHALLENGE: 50 prospects across all stages → each has exactly one current stage, full history.
**Verification Method:**
1. [AUTO] Single-stage: zero prospects in >1 stage. Evidence: psql.
2. [AUTO] Transition: move a lead → timestamp + history row. Evidence: psql.
3. [NICK] Live: Sandra moves a real prospect → sees the history. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Pipeline-Stage-Model-3d0e152fc19981128f0cf310431bb75e_

---
## URS-CRM-003 — Follow-Up Task & Auto-Nag Engine
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: the system reminds Sandra when a follow-up is due, not her memory.

**Functional Requirement Specification:**  
For every prospect not yet in Booked or Lost status, the system shall maintain a next-follow-up-due date and shall proactively notify Sandra (push notification and/or SMS) when a follow-up is due or overdue. Notification cadence shall escalate (e.g. due-today reminder, then daily overdue reminders) rather than firing once and going silent.

**Dependency Notes:**  
Extends the existing nightly digest (W6/CRM 5, top-5 follow-ups at 7am) to real-time, due-date-driven nagging rather than a single daily batch.

**Rationale:**  
Sandra: "I sometimes hear back, sometimes I don't," with no structured re-contact process. Auto-nag closes the gap between deciding to follow up and actually doing it.

**Acceptance Criteria:**
NORMAL: every non-Booked/Lost prospect has a next-follow-up-due date; system notifies Sandra when due or overdue.
EDGE: overdue → daily escalation, never one-and-done.
EDGE: follow-up completed → next due date re-armed.
NEGATIVE: notification fires once then goes silent → violates escalation; caught.
SILENT-FAILURE: a prospect with no due date → caught by completeness scan.
CHALLENGE: 30 prospects, 10 overdue → all 10 nag daily until resolved, zero missed.
**Verification Method:**
1. [AUTO] Escalation: one overdue prospect → notifies daily until resolved. Evidence: log.
2. [AUTO] Completeness: zero non-closed prospects lacking a due date. Evidence: query.
3. [NICK] Live: Sandra receives a due-today push/SMS. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Follow-Up-Task-Auto-Nag-Engine-3d0e152fc199818ca504d61c96af0582_

---
## URS-CRM-004 — Stale/Ghosted Lead Detection & Resolution
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: system flags a lead as stale instead of Sandra deciding alone.

**Functional Requirement Specification:**  
After N consecutive unanswered follow-up attempts over a configured window (default: 3 attempts over 14 days — value to be locked with Sandra), the system shall automatically flag the prospect as Stale and prompt Sandra for an explicit disposition (continue following up / mark Lost-Ghosted / mark Lost-Declined). A prospect shall never remain indefinitely in an ambiguous state; every non-Booked prospect shall carry a current, explicit status.

**Open Questions:**  
Lock the attempt-count and day-window default with Sandra before build — 3 attempts/14 days is a placeholder based on her description, not a confirmed value.

**Rationale:**  
Sandra named this her single biggest pain point, verbatim: leads that don't respond just sit until she personally decides they're ghosting her, with nothing prompting that decision.

**Acceptance Criteria:**
NORMAL: after N unanswered attempts over the window (default 3 attempts/14 days — placeholder pending Sandra), prospect auto-flags Stale and prompts Sandra for disposition.
EDGE: disposition options — continue / Lost-Ghosted / Lost-Declined.
NEGATIVE: a prospect lingering ambiguous forever → impossible: every non-Booked prospect carries an explicit status.
SILENT-FAILURE: Stale flag set but Sandra never prompted → caught.
CHALLENGE: 20 stale leads → all flagged, all prompted, dispositions recorded.
**Verification Method:**
1. [AUTO] Flag: 3 unanswered attempts in 14d → Stale set. Evidence: log.
2. [AUTO] Prompt: Stale set → prompt/SMS to Sandra. Evidence: log.
3. [NICK] Live: Sandra dispositions a stale lead. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Stale-Ghosted-Lead-Detection-Resolution-3d0e152fc1998172a407dd45ff2fc71e_

---
## URS-CRM-005 — Event/Opportunity Detail Record
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need every event detail — date, guest count, type, venue, budget signals, allergies, what's been promised — visible in one place, not scattered across my notebook, texts, and memory.

**Functional Requirement Specification:**  
For every prospect/opportunity, the system shall capture and present in one view: event date, guest count, event type, venue/location, budget signals, dietary/allergen notes, and decision history (what has been discussed, quoted, or promised). This detail shall be visible to Sandra without needing to search her notebook, texts, or memory.

**Dependency Notes:**  
Overlaps with but is distinct from invoice pre-fill (INVOICE 1/PROD-07): this is pre-booking opportunity detail, invoice pre-fill is post-decision.

**Acceptance Criteria:**
NORMAL: one view shows date, guest count, type, venue, budget signals, allergen notes, and decision history per prospect.
EDGE: pre-booking detail stays distinct from post-decision invoice pre-fill (PROD-07).
NEGATIVE: a promised item not recorded → caught by decision-history requirement.
SILENT-FAILURE: detail scattered across notebook/texts → impossible (single view).
CHALLENGE: complex wedding → every detail in one view.
**Verification Method:**
1. [AUTO] Field coverage: every prospect row has required fields or explicit nulls. Evidence: query.
2. [NICK] Live: Sandra opens a real prospect → all detail visible. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Event-Opportunity-Detail-Record-3d0e152fc19981bab576f56f5c8d01df_

---
## URS-CRM-006 — Contact Activity Timeline
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to see everything that's happened with a prospect — calls, texts, notes, stage changes — in one timeline, not by digging through multiple tools.

**Functional Requirement Specification:**  
The system shall present a single chronological activity timeline per prospect/contact, combining calls, texts, notes, stage changes, and follow-up attempts. Sandra shall be able to see the full history of contact with a prospect without cross-referencing multiple tools.

**Acceptance Criteria:**
NORMAL: chronological timeline per contact combining calls, texts, notes, stage changes, follow-ups.
EDGE: timeline survives across tools (single source of truth).
NEGATIVE: an activity missing from the timeline → caught (URS-CRM-008 routes everything to it).
CHALLENGE: six months of a hot prospect's activity → renders in order, complete.
**Verification Method:**
1. [AUTO] Order: activities render chronologically. Evidence: screenshot + query.
2. [NICK] Live: Sandra sees a real prospect's full history. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Contact-Activity-Timeline-3d0e152fc1998157bb64dd716066175d_

---
## URS-CRM-007 — Cloudflare Zero Trust Hosting
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As the owner, I need the CRM only reachable by people I've actually authorized — no public route to prospect or customer data.

**Functional Requirement Specification:**  
The CRM web application shall be hosted behind Cloudflare Zero Trust (Access), served from a Taza-owned domain, and reachable only by authenticated, authorized users (Sandra, Nick; others as later granted). No unauthenticated public route to prospect or customer data shall exist.

**Dependency Notes:**  
Infra-layer requirement. Related to but distinct from the existing Tailscale remote-access tunnel (INFRA 21) — this is an application-level Access policy, not the same tunnel.

**Acceptance Criteria:**
NORMAL: CRM reachable only by authorized users (Sandra, Nick) via Cloudflare Zero Trust Access.
EDGE: granting a new user needs no redeploy.
NEGATIVE: an unauthenticated public route to prospect data → must not exist.
SILENT-FAILURE: Access policy misconfigured to allow public → caught by periodic policy check.
CHALLENGE: attempt access from an unauthorized identity → blocked.
**Verification Method:**
1. [AUTO] Policy: unauthenticated request → blocked (403). Evidence: curl + log.
2. [AUTO] Authorized: Sandra's identity → allowed. Evidence: screenshot.
3. [AUTO] Audit: periodic policy snapshot shows no public route. Evidence: config.
4. [NICK] Live: Nick accesses from his phone off-network. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Cloudflare-Zero-Trust-Hosting-3d0e152fc19981e1aa83f9f8f9049d46_

---
## URS-CRM-008 — Call Note Intake Bridge
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
Need: whatever comes out of a sales call — an edited transcript or a manual brain-dump — lands in the same place and updates the same prospect record, regardless of which path was used.

**Functional Requirement Specification:**  
The system shall provide a single intake point that accepts either (a) an edited call transcript with consent-status metadata, or (b) a manual post-call brain-dump, and shall write the result into the corresponding prospect's activity timeline (URS-CRM-006) and update pipeline stage / next-follow-up-due as appropriate.

**Dependency Notes:**  
This is the landing point for the companion call-capture app's output — see URS-CALL-005.

**Acceptance Criteria:**
NORMAL: edited transcript OR manual brain-dump lands in the same intake; writes to activity timeline and updates stage/next-follow-up.
EDGE: consent-status metadata rides along with either path.
NEGATIVE: a transcript submitted without Sandra's review → blocked (URS-CALL-003 gate).
SILENT-FAILURE: intake accepted but timeline not updated → caught.
CHALLENGE: both paths used in one day → both land identically, tagged with capture path.
**Verification Method:**
1. [AUTO] Both paths: transcript and brain-dump → same record update. Evidence: psql.
2. [AUTO] Tagging: capture-path + consent-status recorded. Evidence: query.
3. [NICK] Live: Sandra submits a real call note. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Call-Note-Intake-Bridge-3d0e152fc199813fbc75dd19ea4d3fe3_

---
## URS-CRM-009 — Interruption-Safe Quick Capture
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
As Sandra, I need to capture a new lead's name, number, and a quick note in under 30 seconds, one-handed, the moment the call comes in — anything slower and I'll just reach for the notebook instead.

**Functional Requirement Specification:**  
The system shall provide a minimal-tap, mobile-first quick-entry form, usable one-handed and completable in under 30 seconds, capturing at minimum name, phone number, and a free-text note, for use the moment a call comes in mid-task. Full detail (event date, guest count, type) may be completed later without blocking the initial capture.

**Rationale:**  
Sandra: "I have to stop what I'm doing to focus on their request." The capture tool has to be faster than reaching for the notebook, or she won't use it.

**Acceptance Criteria:**
NORMAL: one-handed mobile form captures name+phone+note in <30s.
EDGE: full detail deferrable without blocking initial capture.
NEGATIVE: form requiring >30s → fails the design bar.
SILENT-FAILURE: capture lost on interruption → caught (record written on first tap).
CHALLENGE: capture mid-prep, one hand, phone in the other → completes in <30s.
**Verification Method:**
1. [AUTO] Timing: form load → submit <30s for minimum fields. Evidence: timing log.
2. [NICK] Live: Sandra captures a call one-handed mid-task. Evidence: observation log + screenshot.
3. [NICK] Usability: Sandra confirms she'd use it over the notebook. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Interruption-Safe-Quick-Capture-3d0e152fc1998167aadadd3aa5593b52_

---
## URS-SYS-INTENT-001 — Overall System Intent
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
System Intent

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
The team needs Taza OS to remember, organize, connect, and surface operational knowledge so people can perform excellent work with substantially less cognitive load, stress, uncertainty, and frustration.

**Atomic Requirement:**  
Every Taza OS specification shall demonstrably support, or at minimum not undermine, reduced cognitive load, shared operational memory, human judgment, and sustainable high-performance flow.

**Functional Requirement Specification:**  
The system shall function as a shared operational memory and cognition space that captures durable context, makes relevant knowledge available at the point of work, reduces avoidable human recall and coordination burdens, and supports a high-performing yet enjoyable team flow state.

**Intent / User Need:**  
Reduce mental effort and operational stress while improving clarity, coordination, confidence, enjoyment, and sustained team performance.

**Invariants:**  
Taza OS supports human judgment rather than replacing it; shared context remains understandable and recoverable; optimization for throughput must not create unnecessary stress or a punitive work environment.

**Out of Scope:**  
Maximizing automation, surveillance, engagement, or raw throughput at the expense of human judgment, wellbeing, clarity, trust, or enjoyment.

**Acceptance Criteria:**  
During specification review, each requirement identifies how it supports the system intent or is marked as a necessary enabling constraint; requirements that add avoidable cognitive load, ambiguity, interruption, or frustration are revised, justified, deferred, or rejected.

**Verification Method:**  
Evaluate requirements during manual and Fusion Harness review against cognitive-load reduction, shared-memory quality, coordination clarity, stress/friction reduction, human-control preservation, and ability to support enjoyable flow.

**Maintenance Requirements:**  
Reassess this intent during major architecture reviews and before approving features that materially change interfaces, alerts, automation authority, worker measurement, or operational workflows.

**Rationale:**  
Humans perform best when they can focus on judgment, craft, hospitality, and creative problem-solving instead of remembering scattered details, repeatedly reconstructing context, or resolving preventable uncertainty.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Overall-System-Intent-8fcab66045454ed28039210e9203bd34_

---
## V1.0-IG — Taza Input Grammar + Clarification Nudging + Confidence Display
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Roadmap V1.5

**Functional Requirement Specification:**  
The system shall parse raw voice/text input into the Taza Input Grammar — a 5-field structure (EVENT_TYPE, VENUE, GUEST_COUNT required; DATE, NOTES optional) — using an LSI (Language Stress Index) pre-processor score to derive a per-field confidence percentage. Confidence bands: >85% green (auto-accept), 65-85% yellow (accept but flagged for review), <65% red (block auto-accept, trigger a structured clarification nudge naming the uncertain field). Confidence % is displayed at the point of input in both Open WebUI and the kitchen display. Parsed grammar + confidence feed forward into the INVOICE 13 (Invoice Draft Workflow) extraction pipeline.

**Inputs:**  
Raw voice/text input; LSI (Language Stress Index) pre-processor score

**Outputs:**  
Confidence % display (Open WebUI + kitchen display); structured Taza Input Grammar nudge on low confidence; feeds W7 extraction.

**Trigger:**  
Any voice/text input to W7/W11 extraction pipeline

**Acceptance Criteria:**  
Given a voice/text input, the system extracts EVENT_TYPE, VENUE, GUEST_COUNT (required) and DATE, NOTES (optional) with a confidence % per field. Inputs scoring >85% pass through without interruption. 65-85% are accepted but visibly flagged. <65% block auto-accept and surface a structured clarification nudge naming the low-confidence field(s). Confidence % is visible in both Open WebUI and the kitchen display for every parse.

**Verification Method:**
1. [AUTO] Bands: inputs >85% pass; 65–85% accepted+flagged; <65% blocked + clarification nudge naming the field. Evidence: test battery.
2. [AUTO] Display: confidence % visible in Open WebUI and kitchen display for every parse. Evidence: screenshots.
3. [NICK] Live: Sandra speaks a raw request and sees the confidence readout. Evidence: screenshot.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Taza-Input-Grammar-Clarification-Nudging-Confidence-Display-3b5e152fc199811498abf6e526d61c69_
