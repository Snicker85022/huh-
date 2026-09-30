# Taza OS URS — AI cluster
_Exported: 2026-09-19 21:35 | 8 rows_
_Source: Notion Master URS & Specification Registry_

---
## AI-001 — Prompt Library
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: AI prompt content hot-reloadable without redeploying code.

**Functional Requirement Specification:**  
All AI prompt text lives as standalone files at /opt/taza/prompts/, not embedded in code, and is loaded fresh on each call so edits take effect without a redeploy. See Dependency Notes for the individual prompt specs this row governs.

**Failure Behavior:**  
Fallback: Docker restart if hot-reload fails.

**Acceptance Criteria:**  
NORMAL:
1. All AI prompt text lives as standalone files at /opt/taza/prompts/, loaded fresh on each call — an edit to a prompt file takes effect on the very next call with no redeploy.

EDGE:
2. A prompt file edited mid-flight (while a call is in progress using the old version) doesn't corrupt that in-flight call — the in-flight call completes with whichever version it started with.
3. A malformed edit to a prompt file (broken syntax, if the format has any structure) is caught before it silently degrades output quality on the next call.

NEGATIVE:
4. No prompt text is found embedded in application code anywhere — verified by code search, since embedded prompts would silently require a redeploy and defeat this row's purpose.

SILENT FAILURE:
5. 'Loaded fresh on each call' has a real performance cost (file I/O per call) — verify this doesn't introduce a caching layer somewhere that would silently reintroduce the stale-prompt problem this row exists to prevent.
6. This row's own Open Questions flags a stale count discrepancy ("8 prompt files" claimed vs. 6 documented + 1 JSON registry) — resolve the actual current prompt-file inventory before treating this row as complete.

**Verification Method:**  
1) Live-edit test: edit a prompt file, confirm the very next call reflects the change with no redeploy/restart. 2) Code-search audit: confirm no prompt text is embedded in application code. 3) Caching-layer audit: confirm no intermediate cache silently serves a stale prompt version. 4) Inventory reconciliation: confirm the actual current count and list of prompt files against the open count-discrepancy question. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
Umbrella/container spec for the AI prompt library mechanism, governing PROMPT 2..PROMPT 8 collectively: PROMPT 2 (lead parser), PROMPT 3 (lead scoring), PROMPT 4 (voice note parser), PROMPT 5 (invoice postprocess), PROMPT 6 (CRM session opener), PROMPT 7 (precall brief) — 6 prompt files — plus PROMPT 8 (command_registry.json, voice command routing; a JSON config, not a text prompt).

**Open Questions:**  
FRS previously stated "8 prompt files" but only 6 are documented as individual specs ([[SPEC:AI-002]]..007), plus 1 JSON registry (PROMPT 8) that isn't a prompt file — confirm the real count on /opt/taza/prompts/ (are 2 prompts undocumented?) or correct the stale "8" figure.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Prompt-Library-3cfe152fc19981339fedfa2e1c7f791f_

---
## AI-002 — Lead Parser Prompt
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: incoming leads parsed to strict structured JSON, no manual cleanup.

**Functional Requirement Specification:**  
lead_parser.txt (AI): strict JSON for leads, including Wix-originated customer inquiries arriving via Gmail email notification.

**Failure Behavior:**  
Fallback: regex parsing for structured fields.

**Acceptance Criteria:**  
NORMAL:
1. lead_parser.txt produces strict JSON for leads, including Wix-originated inquiries arriving via Gmail notification email.

EDGE:
2. A Gmail notification email with unusual/reformatted content (Wix changes their email template) still parses correctly, or fails visibly rather than silently extracting wrong data.
3. A lead email containing multiple potential leads or ambiguous contact info is handled with a defined behavior (e.g. flags for review), not a guessed single extraction.

NEGATIVE:
4. A non-lead email that superficially resembles a lead notification (spam, unrelated Wix notification type) is not falsely parsed into a fabricated lead record.

SILENT FAILURE:
5. Silent misparse (extracts a real-looking but wrong name/date/guest-count from a genuine lead email) is worse than an outright failure — verify against a set of real historical lead emails with known-correct expected output, not just structurally-valid-JSON checking.
6. This feeds [[SPEC:W1]]/CRM 21 (Lead Capture) directly — verify the two specs' expected schemas actually match, not independently drifted.

**Verification Method:**  
1) Golden-set test: real historical Wix/Gmail lead emails with known-correct expected JSON, verify exact field accuracy, not just valid-JSON-ness. 2) Template-drift test: a reformatted/unusual email structure, confirm graceful failure or correct adaptation, not silent misparse. 3) False-positive test: non-lead emails that superficially resemble lead notifications, confirm no fabricated lead created. 4) Schema-consistency check against CRM 21 ([[SPEC:W1]])'s expected lead record shape. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Lead-Parser-Prompt-3cfe152fc1998141af01c0f2a88ce54b_

---
## AI-003 — Lead Scoring Prompt
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: each lead auto-scored Hot/Warm/Low/Pass against Nick's rubric.

**Functional Requirement Specification:**  
lead_scoring.txt: Nick's rubric → Hot/Warm/Low/Pass

**Failure Behavior:**  
Fallback: default Warm, manual categorization.

**Acceptance Criteria:**  
NORMAL:
1. lead_scoring.txt applies Nick's rubric and correctly classifies a lead into Hot/Warm/Low/Pass.

EDGE:
2. A borderline lead (sits near a category boundary in Nick's rubric) is classified consistently on repeated runs of the same input, not flip-flopping between adjacent categories.
3. A lead with sparse/incomplete data (missing budget signals, vague event type) still produces a defined classification, not a crash or null result.

NEGATIVE:
4. A lead that's clearly Hot by Nick's stated rubric criteria is never misclassified as Low/Pass — this has real business cost (a good lead not getting Sandra's immediate attention).

SILENT FAILURE:
5. Classification drift over time (if the underlying model changes) without anyone noticing the scoring behavior shifted would silently change which leads get prioritized — verify against a fixed golden-set of example leads with known-correct classifications, re-run periodically, not just validated once at launch.
6. This directly feeds [[SPEC:W2]]/CRM 22's SMS-to-Sandra trigger for Hot leads — verify the full path (score → SMS) is tested end-to-end, not just this prompt's output in isolation.

**Verification Method:**  
1) Golden-set test: a fixed set of real/representative leads with Nick-confirmed correct classifications, verify accuracy, and re-run this set periodically to catch drift. 2) Consistency test: repeated runs of the same borderline input, confirm stable classification. 3) Sparse-data test: minimal-info lead still classifies without error. 4) End-to-end test: confirm a Hot classification actually triggers the CRM 22 ([[SPEC:W2]]) SMS-to-Sandra path. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Lead-Scoring-Prompt-3cfe152fc1998177b1e0daeba59ff6f1_

---
## AI-004 — Voice Note Parser Prompt
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: voice notes auto-extracted to intents/entities/linked records — structured data by morning, no transcription.

**Functional Requirement Specification:**  
voice_note_parser.txt:  extraction of intents, entities, linked records

**Failure Behavior:**  
Fallback: manual voice note review.

**Acceptance Criteria:**  
NORMAL:
1. Voice note text is parsed into extracted intents, entities, and linked records correctly.

EDGE:
2. A voice note covering multiple customers/topics in one recording is correctly split/attributed, not merged into one confused record.
3. Ambiguous entity references ("the venue" without a name, relying on conversational context) are handled with a defined fallback — flagged for review rather than guessed, if genuinely ambiguous.

NEGATIVE:
4. A voice note transcript with transcription errors (Whisper mishears a word) doesn't cascade into a confidently-wrong entity extraction — verify some resilience to minor transcription noise.

SILENT FAILURE:
5. A wrong linked-record match (voice note about Customer A gets linked to Customer B's record due to a name-similarity error) would corrupt CRM data in a way that's hard to notice until a customer complains — verify with a specific test using similarly-named customers/accounts.
6. This feeds the nightly deep analysis (CRM 5/[[SPEC:W6]]) and CRM record promotion — a bad extraction here propagates forward; verify with an end-to-end test through to the actual NocoDB write, not just the prompt's isolated JSON output.

**Verification Method:**  
1) Golden-set test: real anonymized voice-note transcripts with known-correct expected extraction, verify field accuracy. 2) Similarity-confusion test: similarly-named customers/accounts, confirm correct linked-record resolution, not cross-contamination. 3) Transcription-noise test: inputs with realistic Whisper transcription errors, confirm resilience. 4) End-to-end test: voice note through to actual NocoDB write via CRM 5 ([[SPEC:W6]]), confirm the full pipeline lands correct data, not just the prompt's isolated output. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Voice-Note-Parser-Prompt-3cfe152fc1998179afeccaec408f81a4_

---
## AI-005 — Invoice Postprocess Prompt
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: invoice description text polished for clarity/tone, no value changes.

**Functional Requirement Specification:**  
invoice_form_postprocess.txt: polish invoice description (no value changes)

**Failure Behavior:**  
Fallback: skip post-processing, raw template.

**Acceptance Criteria:**  
Polished prose; zero data changes; amounts/dates/names untouched

**Verification Method:**
1. [AUTO] No-change: run postprocess over 10 invoices → amounts, dates, names byte-identical before/after. Evidence: diff.
2. [AUTO] Polish: prose reads clearly; only description fields changed. Evidence: before/after sample.
3. [NICK] Live: Nick reviews a polished invoice. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Invoice-Postprocess-Prompt-3cfe152fc199811aaf0ed762f9f86efc_

---
## AI-006 — CRM Session Opener Prompt
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: warm CRM session greeting referencing 2-3 real customer facts, not a blank slate.

**Functional Requirement Specification:**  
crm_session_opening.txt (AI): warm greeting with 2-3 customer facts

**Failure Behavior:**  
Fallback: generic greeting.

**Acceptance Criteria:**  
AI opens with name + last event + preference

**Verification Method:**
1. [AUTO] Facts: greeting references 2–3 real customer facts pulled from the record, zero invented facts. Evidence: test output.
2. [AUTO] Empty: no customer facts available → generic greeting (fallback), never fabricated. Evidence: test.
3. [NICK] Live: Sandra sees a real session opener referencing a real fact. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/CRM-Session-Opener-Prompt-3cfe152fc19981bfa01ef0af3fc32355_

---
## AI-007 — Precall Brief Prompt
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: 3-paragraph precall brief (<300 chars) to get up to speed in seconds before dialing.

**Functional Requirement Specification:**  
precall_brief.txt: 3-paragraph brief <300 chars

**Failure Behavior:**  
Fallback: Sandra checks profile manually.

**Acceptance Criteria:**  
Brief: who / last interaction / suggested angle; <300 chars

**Verification Method:**
1. [AUTO] Format: brief contains who / last interaction / suggested angle, <300 chars. Evidence: sample output + char count.
2. [AUTO] Empty: no history → brief says so, never fabricated. Evidence: test.
3. [NICK] Live: Sandra reads a real precall brief before dialing. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Precall-Brief-Prompt-3cfe152fc199818197c6c1dd0d176e2c_

---
## AI-008 — Voice Command Registry
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: registry of recognized voice commands so [[SPEC:W14]] Path A matches spoken commands to actions without invoking a model.

**Functional Requirement Specification:**  
command_registry.json: voice commands for [[SPEC:W14]] Path A

**Failure Behavior:**  
Fallback: reduce to 5 core commands.

**Acceptance Criteria:**  
NOTE: this is the command registry for Path A (on-device NPU classification, PROMPT 9) — same V1.0 scoping caveat applies: preferred long-term, not required for V1.0.

NORMAL:
1. command_registry.json defines the voice commands recognized by [[SPEC:W14]] Path A, and every registered command routes to its correct action.

EDGE:
2. Two registered commands with similar phrasing don't ambiguously overlap in matching — each phrase maps deterministically to exactly one command.
3. Adding a new command to the registry doesn't require touching classifier code, only this config file — verify this is actually true, not aspirational.

NEGATIVE:
4. An utterance close to but not matching any registered command correctly falls through to Path B/C (or a 'not understood' state), not fuzzy-matched to the nearest registered command.

SILENT FAILURE:
5. A malformed entry in the registry (typo, bad JSON) must fail loudly at load time, not silently drop that command from being recognized with no indication why voice control for that feature 'just doesn't work.'
6. Registry drifting out of sync with what the classifier model was actually trained/tuned against (if applicable) would cause silent misclassification — verify registry changes are tested against the actual live classifier, not just validated as well-formed JSON.

**Verification Method:**  
1) Registry-load test: malformed entry fails loudly at load time. 2) Command-coverage test: every registered command triggers its correct action via a real utterance. 3) Near-miss test: utterances close to but not matching any command correctly fall through rather than fuzzy-matching. 4) Extensibility test: add a new command via config only, confirm no code change was needed. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Voice-Command-Registry-3cfe152fc19981e680f5fcfde87f4e1c_
