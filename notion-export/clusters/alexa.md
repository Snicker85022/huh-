# Taza OS URS — ALEXA cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## ALC-001 — N100 cache builder
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: live operational context cache (event/staff/allergens/LKL/tasks/van) rebuilt within 2s of any change — voice queries answer from current state, not stale.

**Functional Requirement Specification:**  
N100 cache builder: Python-and/or-Rust/systemd job builds full operational context JSON on every push trigger event. Queries PostgreSQL for event, staff, allergens, LKL, tasks, van status. Writes to /opt/taza/cache/tonight.json. Triggers: task close, allergen write, LKL write, LKL consume, van status change, staff arrival, schedule (5AM + T-60/30/10). Cache version increments on every write. Build completes in <2s per trigger.

**Failure Behavior:**  
Fallback: pull-on-demand automation (slower, no pre-cache benefit).

**Acceptance Criteria:**  
NORMAL:
1. On every listed trigger (task close, allergen write, LKL write/consume, van status change, staff arrival, scheduled times), the cache builder queries Postgres and writes a complete operational context JSON to tonight.json, in under 2s, incrementing the version.

EDGE:
2. Two triggers firing in rapid succession (e.g. a task close immediately followed by an LKL write) both result in a correct final cache state — the second build reflects both changes, not just the second trigger's data with the first lost.
3. A trigger firing while a previous build is still in progress queues/debounces correctly rather than producing two concurrent writes that could corrupt tonight.json.

NEGATIVE:
4. A build that fails partway (Postgres query error mid-build) does not overwrite tonight.json with incomplete data — the previous good version remains until a successful rebuild completes.

SILENT FAILURE:
5. A build exceeding the 2s target under real data volume (a busy event night with many staff/tasks/allergens) must be caught — verify against realistic peak data volume, not a light test dataset.
6. The version-increment mechanism failing to actually increment (bug) would make staleness undetectable to consumers like ALEXA 2 — verify version always increments on every successful write, tested directly, not assumed.
7. A scheduled trigger (5AM, T-60/30/10) that silently fails to fire (cron/scheduler issue) would leave tonight.json stale through a critical pre-event window — verify scheduled triggers are monitored for actual execution, not just configured.

**Verification Method:**  
1) Trigger tests: each of the 9 documented trigger types individually fires a correct rebuild. 2) Rapid-sequence test: two triggers in quick succession, confirm final cache reflects both changes correctly. 3) Concurrency test: overlapping trigger firing during an in-progress build, confirm no corruption. 4) Failure-safety test: force a mid-build Postgres error, confirm tonight.json is not overwritten with incomplete data. 5) Load test: realistic peak event-night data volume, confirm build still completes under 2s. 6) Scheduled-trigger monitoring: confirm the 5AM/T-60/30/10 triggers are verified to actually execute, not just configured. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/N100-cache-builder-3cfe152fc19981c4b903ea156b1476d4_

---
## ALC-002 — Self-owned cache endpoint
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: tonight-cache reachable over a secure, self-owned, authenticated endpoint fast enough for voice — no exposure to open internet.

**Functional Requirement Specification:**  
The system shall expose a self-owned HTTP endpoint (not third-party-hosted) that serves the current contents of /opt/taza/cache/tonight.json (built by ALEXA 1) for fast (~50ms target) read access by ALEXA 3 (Custom Alexa Skill) and any other cache consumer, without requiring a full PostgreSQL query per request.

**Failure Behavior:**  
Fallback: DynamoDB cache (AWS dependency) if VPS not yet provisioned.

**Acceptance Criteria:**  
NORMAL:
1. Endpoint serves current tonight.json contents, self-hosted (no third-party dependency), responding within the ~50ms target.

EDGE:
2. A request arriving during a cache rebuild (ALEXA 1 mid-write) returns either the previous complete version or waits briefly for the new one — never a partially-written/corrupt JSON.
3. Endpoint under concurrent requests (multiple Alexa invocations near-simultaneously) maintains the ~50ms target, not degrading under realistic concurrent load.

NEGATIVE:
4. A request arriving before any cache has ever been built (cold start) returns a defined empty/default state, not an error or a hang.

SILENT FAILURE:
5. Endpoint silently serving a stale cache version (ALEXA 1's builder job stopped running but the endpoint keeps serving the last-known file) must be detectable — verify the served response includes a version/timestamp so staleness is visible to the caller, not presented as current.
6. This endpoint being unreachable must fail loudly to ALEXA 3's caller, triggering its documented fallback (POST to automation webhook), not hang or silently return empty as if 'not found.'

**Verification Method:**  
1) Confirm the inferred FRS with Nick before treating this as locked. 2) Latency test: endpoint response time under idle and concurrent-load conditions. 3) Concurrent-write test: request during an in-progress cache rebuild, confirm no corrupt/partial response. 4) Cold-start test: request before any cache exists, confirm defined behavior. 5) Staleness-visibility test: confirm served response includes version/timestamp. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
This row had no FRS at all (silent gap, not previously flagged) — the above is inferred from ALEXA 1's cache-build behavior and ALEXA 3's reference to reading 'the ALEXA 2 cache endpoint.' Confirm with Nick this matches actual intent before debate treats it as settled.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Self-owned-cache-endpoint-3cfe152fc19981d1aa45cb0760cebfa8_

---
## ALC-003 — Custom Alexa Skill
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: "Alexa, open Taza" + a question gets an immediate spoken answer for common location/status/task/allergen queries — cache-first for speed, full routing as fallback.

**Functional Requirement Specification:**  
Custom Alexa Skill — Taza operational interface: Alexa Skill built in Amazon Developer Console. Invocation: "Alexa, open Taza" or "Alexa, ask Taza [query]". On every invocation, Skill reads ALEXA 2 cache endpoint first (~50ms). If answer found in cache, speaks it immediately. If not found, POSTs to a Python-and/or-Rust/systemd automation webhook for W14 routing. Skill supports intent vocabulary: LocationQuery, StatusQuery, TaskCommand, AllergenQuery. Natural language within intents via AMAZON.SearchQuery slot.

**Failure Behavior:**  
Fallback: Google Home Routines only (display nav, no voice-to-database).

**Acceptance Criteria:**  
NORMAL:
1. "Alexa, open Taza" and "Alexa, ask Taza [query]" invoke the Skill; cache checked first (~50ms); cache hit speaks immediately; cache miss POSTs to the automation webhook for W14 routing.
2. All four intents (LocationQuery, StatusQuery, TaskCommand, AllergenQuery) function correctly, including natural-language variation via AMAZON.SearchQuery.

EDGE:
3. A query that's ambiguous between two intents (e.g. could be LocationQuery or StatusQuery depending on phrasing) resolves consistently, not randomly to either.
4. A cache-hit response and a webhook-fallback response for the same underlying question return consistent information — the two paths shouldn't diverge in what they report.

NEGATIVE:
5. A query outside all four supported intents is met with a clear "I can't help with that" style response, not a crash or a misrouted guess into the wrong intent.

SILENT FAILURE:
6. TaskCommand intent (this one can actually change system state via voice, unlike the read-only query intents) is the highest-risk path here — verify it requires appropriate confirmation/safeguards and can't be triggered by an accidental Alexa mishear of an unrelated phrase.
7. Webhook-fallback path silently timing out (N100 slow/unreachable) must give the user a clear "having trouble right now" response, not hang indefinitely or silently fail with no spoken response at all.
8. AllergenQuery giving a wrong/stale answer would be a food-safety risk, not just an inconvenience — verify this intent specifically against the cache-staleness concern flagged in ALEXA 2.

**Verification Method:**  
1) Invocation tests: both invocation phrasings, cache-hit and cache-miss paths, all four intents. 2) Natural-language variation test: multiple real phrasings per intent via AMAZON.SearchQuery, confirm correct intent resolution. 3) Consistency test: same underlying question via cache-hit vs. webhook-fallback path, confirm consistent answers. 4) TaskCommand safety test: confirm accidental/mishear scenarios don't trigger unintended state changes; verify any confirmation safeguard. 5) Timeout test: force webhook unreachability, confirm a clear spoken error rather than silence or hang. 6) AllergenQuery-specific staleness test tied to ALEXA 2's cache-freshness verification. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Custom-Alexa-Skill-3cfe152fc19981449565cc52adeef421_

---
## ALC-004 — Alexa proactive outbound alerts
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: Alexa proactively speaks critical alerts (allergen, departure countdown, timer, shortage) through kitchen TV speakers, deterministic message, no one has to ask.

**Functional Requirement Specification:**  
Alexa proactive outbound alerts via Notifications API: N100 Python-and/or-Rust/systemd job POSTs to Alexa Notifications API on critical alert conditions. Alexa speaks alert through Insignia TV speakers. Alert conditions: allergen field populated on active event (immediate, highest priority), departure countdown at T-10 min, task timer completion, shortage alert requiring supervisor attention. Alert text is deterministic template, not LLM.

**Failure Behavior:**  
Fallback: TTS via ADB on Google TV speakers (TV-005).

**Acceptance Criteria:**  
NORMAL:
1. Each of the 4 alert conditions (allergen populated, T-10 departure, task timer completion, shortage) triggers a POST to the Alexa Notifications API, spoken through Insignia TV speakers, using a deterministic (non-LLM) template.

EDGE:
2. Multiple alert conditions firing near-simultaneously (e.g. departure countdown AND a task timer complete at the same moment) are each spoken, not one silently dropped/overwritten by the other.
3. The allergen alert (highest priority) correctly preempts or properly sequences against a lower-priority alert already in progress, per its 'immediate, highest priority' designation.

NEGATIVE:
4. An alert condition that's momentarily true then immediately resolves (flicker) doesn't cause a spoken alert for a non-issue — verify against realistic sensor/state noise, not just clean state transitions.

SILENT FAILURE:
5. This overlaps with DISPLAY 29 (TV-005)'s visual alert for the same conditions — verify audio and visual alerts stay synchronized/consistent, and resolve whether both firing is intentional redundancy or should be deduplicated (per the existing recon flag).
6. The Alexa Notifications API call failing (network issue, API error) must not silently mean the highest-priority allergen alert simply never gets spoken with no fallback — verify there's a fallback signal path for the allergen case specifically, given its food-safety stakes.
7. Deterministic-template requirement ("not LLM") must be verified by testing the actual alert-generation code path, not just trusting it was built that way — confirm no LLM call sits anywhere in this path.

**Verification Method:**  
1) Trigger tests: each of the 4 alert conditions individually fires the correct spoken alert. 2) Priority test: allergen alert correctly preempts/sequences against a concurrent lower-priority alert. 3) Flicker test: momentary true-then-false condition state, confirm no false alert. 4) Redundancy reconciliation: resolve against DISPLAY 29's overlapping alert, confirm intentional vs. needs-dedup, and that audio/visual stay consistent either way. 5) API-failure fallback test: force the Notifications API call to fail, confirm a fallback path exists for the allergen case. 6) Code-path audit: confirm zero LLM involvement in alert text generation. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
OVERLAP: same alert conditions (allergen/departure/timer) as DISPLAY 29, both may fire on Insignia's speakers. Intentional redundancy or conflict? Reconcile in debate.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Alexa-proactive-outbound-alerts-3cfe152fc199815091d0f14e171f680d_

---
## ALC-005 — Alexa Guard passive monitoring
**Status:**  | **Priority:** P3 | **Release:** V2.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: passive 24/7 monitoring for smoke/CO/glass-break in the kitchen, pushing an immediate phone alert to Nick — zero extra hardware.

**Functional Requirement Specification:**  
Alexa Guard passive monitoring: Alexa Guard enabled on Insignia NS-55F501NA2x via Alexa app. Monitors kitchen audio 24/7 for smoke alarm, CO detector, glass break sounds. On detection: immediate push notification to Nick's phone with alert type and timestamp. Zero additional hardware/CPU cost.

**Failure Behavior:**  
Fallback: no passive monitoring (accept risk for V1).

**Acceptance Criteria:**  
Guard enabled and active; test alarm sound triggers phone notification within 60s; notification identifies alert type correctly; Guard active during all hours including overnight

**Verification Method:**
1. [AUTO] Arm: Alexa Guard enabled and active on the Insignia, including overnight hours. Evidence: Alexa app screenshot.
2. [AUTO] Detection: play a smoke-alarm test tone → push notification to Nick's phone <60s, alert type correct. Evidence: phone screenshot + timestamp.
3. [AUTO] Types: test smoke, CO, and glass-break tones → each identifies the correct alert type. Evidence: notification log.
4. [NICK] Live: Nick receives a real Guard alert on his phone. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Alexa-Guard-passive-monitoring-3cfe152fc199819780b6df79b2d1dcad_
