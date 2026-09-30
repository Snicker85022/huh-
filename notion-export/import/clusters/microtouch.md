# Taza OS URS — MICROTOUCH cluster
_Exported: 2026-09-19 21:35 | 2 rows_
_Source: Notion Master URS & Specification Registry_

---
## MT-001 — MicroTouch local LKL cache
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: LKL queries on MicroTouch answered instantly from a local on-device cache (push-updated), not a network round trip. Stale cache (>10s) triggers REST pull before answering.

**Functional Requirement Specification:**  
MicroTouch local LKL cache: each MicroTouch receives push updates including the full LKL snapshot in the delta payload, stored in browser memory. LKL queries (voice or touch) answered from local cache without an N100 round trip; stale cache (>10s since last push) triggers a REST pull before answering.

**Failure Behavior:**  
Fallback: direct N100 LKL query per [[SPEC:URS-LKL-003]] (functional, slower).

**Acceptance Criteria:**  
NORMAL:
1. MicroTouch receives a push update → full LKL snapshot stored in browser memory; subsequent LKL queries (voice or touch) answer from that local cache with no N100 round trip.

EDGE:
2. A query arrives exactly at the 10s staleness boundary — behavior is deterministic (defined as either side of the boundary, not a race).
3. Rapid back-to-back queries immediately after a fresh push all answer from the same cache snapshot without triggering redundant REST pulls.
4. A push arrives mid-query — the in-flight query completes against a consistent snapshot (old or new, not a mixed/torn read).

NEGATIVE:
5. Cache older than 10s since last push → a REST pull is triggered before answering, never answered from stale cache silently.
6. MicroTouch loses network mid-session — queries against the existing (now-aging) cache still work until staleness threshold, then fail gracefully with a clear signal, not a silent wrong answer.

SILENT FAILURE:
7. If the REST pull-on-staleness fails (N100 unreachable), the query must not silently fall back to the stale cache and answer as if current — crew needs to know the answer might be wrong.
8. Push payload delivery failure (dropped packet) must not leave the local cache in a partially-updated, internally-inconsistent state.

**Verification Method:**  
1) Unit tests: fresh-cache query, boundary-condition query at exactly 10s, stale-cache-triggers-pull. 2) Integration test: push arriving mid-query, confirm no torn read. 3) Network-failure test: N100 unreachable during a stale-triggered REST pull, confirm the query fails visibly rather than silently answering from stale data. 4) Load test: rapid repeated queries post-push, confirm no redundant REST calls. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/MicroTouch-local-LKL-cache-3cfe152fc19981ceab28e707e963513e_

---
## MT-002 — MicroTouch wake word + on-device intent classification
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: simple voice commands recognized + acted on-device within 2s via MT8390 NPU wake word ("Hey Taza"), no audio leaves device for Path A intents.

**Functional Requirement Specification:**  
MicroTouch wake word + on-device intent classification: always-on wake word detection ("Hey Taza") on the MT8390 NPU at ~1-3% CPU. On detection, captures the next utterance and classifies intent on-device. Path A intents POST directly to the automation webhook with structured JSON — no audio transmitted. Path B/C route to N100 for AI processing per [[SPEC:W14]]. Total Path A target <2s wake-to-write.

**Failure Behavior:**  
Fallback: on-device inference on N100 (audio over LAN, higher latency).

**Acceptance Criteria:**  
NOTE: this is the on-device NPU wake-word + intent-classification path — per the resolved local-vs-cloud/NPU decision, this is Nick's preferred long-term direction but not required for V1.0 (V1.0 ships with [[SPEC:PROD-37]]/[[SPEC:PROD-37]]'s Chrome Web Speech API + N100 approach). Scope this row's debate/build priority accordingly.

NORMAL:
1. "Hey Taza" wake word detected on-device at ~1-3% CPU; next utterance captured and classified on-device; Path A intents POST directly to the automation webhook with structured JSON, no audio transmitted; total wake-to-write under 2s.

EDGE:
2. Background kitchen noise (equipment, conversation) doesn't cause false wake-word triggers at an operationally disruptive rate — verify false-positive rate under real kitchen noise, not a quiet test room.
3. An utterance that's ambiguous between Path A (direct) and Path B/C (needs N100 AI) is correctly routed — verify the on-device classifier's routing decision boundary, not just Path A's happy path.

NEGATIVE:
4. A wake word detected but followed by an unintelligible/silent utterance fails gracefully (no action taken, or a clear "didn't catch that" signal) rather than misfiring an unintended command.

SILENT FAILURE:
5. Path A's core promise is 'no audio transmitted' for privacy/speed — verify this with actual network traffic inspection during a Path A interaction, not just trusting the code path description.
6. The <2s wake-to-write target must be verified under real load (NPU also handling other tasks) not just an idle-device benchmark.
7. A misclassified intent that's confidently wrong (routes to Path A when it should have gone to N100 for disambiguation) could execute an unintended action — verify the classifier's confidence threshold actually gates Path A vs. deferring to Path B/C when uncertain.

**Verification Method:**  
1) Real-environment false-positive test: run wake-word detection in actual kitchen noise conditions over an extended period, measure false-trigger rate. 2) Network-traffic inspection: confirm zero audio bytes leave the device during a Path A interaction. 3) Latency test: wake-to-write timing under real concurrent NPU load, not idle benchmark. 4) Routing-boundary test: ambiguous utterances near the Path A/B-C decision boundary, confirm correct and safe routing (defers when uncertain, doesn't confidently misfire). 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/MicroTouch-wake-word-on-device-intent-classification-3cfe152fc1998176affdcdd17b188709_
