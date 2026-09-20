# Taza OS URS — KIT-LEGACY cluster
_Exported: 2026-09-19 21:35 | 13 rows_
_Source: Notion Master URS & Specification Registry_

---
## KIT-001 — Bin master table
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every storage location has a unique labeled ID (Zone-Unit-Shelf) with matching physical shelf labels.

**Functional Requirement Specification:**  
Bin master table: all storage locations defined with unique IDs in format [Zone]-[Unit]-[Shelf] (WIC/WIF/RIC/RIF/DRY). Physical labels installed on all shelves before go-live.

**Failure Behavior:**  
Fallback: laminated paper labels as interim.

**Acceptance Criteria:**  
NORMAL:
1. Every storage location has a unique ID in [Zone]-[Unit]-[Shelf] format (WIC/WIF/RIC/RIF/DRY), and a matching physical label is installed before go-live.

EDGE:
2. Two zones with structurally similar naming (e.g. WIC vs WIF) never produce colliding IDs — the zone code alone disambiguates.
3. A newly added shelf/bin after go-live follows the same ID convention and gets a physical label before it's referenced by any other spec (URS-LKL-001 depends on this).

NEGATIVE:
4. Attempting to create a bin ID that duplicates an existing one is rejected at the data layer, not just caught by convention/discipline.
5. A bin referenced by an LKL record but missing from the bin master table is a detectable data-integrity violation, not a silent orphan reference.

SILENT FAILURE:
6. A physical label that doesn't match its system ID (typo, wrong shelf) is not something software can catch automatically — flag this as requiring the physical walkthrough/audit in the verification step, not just a DB check.
7. Bin master table edits (renames, deactivations) must not silently break existing LKL records that reference the old ID — verify referential integrity is enforced or migrations are required.

**Verification Method:**  
1) Data-integrity tests: uniqueness constraint on bin ID, orphan-reference detection for any LKL record pointing to a nonexistent bin. 2) Migration test: renaming/deactivating a bin and confirming existing LKL references are handled (blocked, migrated, or flagged — pick one and test it). 3) Physical walkthrough: Nick/Sandra/Edgar physically compare every installed shelf label against the system's bin master table, one by one. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Bin-master-table-3cfe152fc19981db84fbca6b34470246_

---
## KIT-005 — Downstream task input manifest
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: downstream task cards show item/qty/bin location from the upstream close, right on the card at unlock.

**Functional Requirement Specification:**  
Downstream task input manifest: when an upstream task closes with a valid LKL record, all dependent tasks automatically receive an input manifest in the card header (item name, qty_needed, qty_available, bin_id) at task unlock, not at task creation.

**Failure Behavior:**  
Fallback: manual task notes.

**Acceptance Criteria:**  
NORMAL:
1. Upstream task closes with a valid LKL record → every dependent downstream task receives the input manifest (item name, qty_needed, qty_available, bin_id) in its card header at unlock.

EDGE:
2. A task with multiple dependent downstream tasks — all of them receive the manifest, not just the first.
3. A downstream task already unlocked before the upstream close completes still receives the manifest update once the close lands, not left showing stale/blank data.
4. Upstream task closes with qty_available less than qty_needed — manifest still populates and visibly reflects the shortfall (doesn't hide the mismatch).

NEGATIVE:
5. Upstream task closes WITHOUT a valid LKL record (shouldn't be possible per CLOSE 18, but test the boundary) — downstream manifest does not populate with an invalid/empty bin_id.

SILENT FAILURE:
6. If the manifest fails to populate on a downstream card, that card must not silently show as 'ready' — crew should see a visible gap, not a card that looks normal but is missing sourcing info.
7. Manifest data must reflect the upstream close's actual final values, not a cached/stale snapshot from task creation time (this is explicitly the bug this row prevents — verify it's not reintroduced).

**Verification Method:**  
1) Unit tests: single dependent, multiple dependents, already-unlocked downstream task. 2) Integration test: upstream close with qty shortfall, confirm downstream manifest visibly reflects it. 3) Regression test: confirm manifest is populated at unlock time from live data, not at task-creation time (guards the original bug this row fixes). 4) Fault-injection test: force manifest population to fail, confirm the downstream card does not silently present as ready. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Downstream-task-input-manifest-3cfe152fc19981a7a084cc54d2dd6325_

---
## KIT-007 — LKL staleness flag
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a warning shown when a location record is old (default 8h), before relying on it.

**Functional Requirement Specification:**  
LKL staleness flag: any LKL record older than a configurable threshold (default 8h) shows a visual warning on downstream task cards and query results — "Placed Xh ago — verify before hunting." Threshold configurable via .env.

**Failure Behavior:**  
Fallback: static 8h hardcoded threshold.

**Acceptance Criteria:**  
Records older than threshold show staleness warning; threshold configurable without code change; fresh records show no warning

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/LKL-staleness-flag-3cfe152fc1998134b481c0f9bfeca384_

---
## KIT-008 — Consumed/moved LKL tracking
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a location record marked consumed/moved when a crew member pulls from it at task close.

**Functional Requirement Specification:**  
Consumed/moved tracking: when a task pulls from a storage location, staff marks the LKL record consumed or moved via a form field on the pull-task close, preventing stale active records from giving false locations.

**Failure Behavior:**  
Fallback: manual NocoDB status update.

**Acceptance Criteria:**  
LKL status updates to consumed within 5s of pull-task close; downstream tasks referencing the item show a 'pulled' indicator

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Consumed-moved-LKL-tracking-3cfe152fc1998141b620d995e1858500_

---
## KIT-010 — Staff task experience table
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: execution history and error count tracked per staff per task type, with an experience score computed at task close.

**Functional Requirement Specification:**  
Staff task experience table: tracks total_executions, executions_in_trailing_window, error_count per staff per task_type. Experience score computed at task-close time against .env thresholds. Sandra hardcoded Expert (bypasses all checks). Thresholds modifiable by Nick/Sandra/Edgar only.

**Failure Behavior:**  
Fallback: manual supervisor judgment.

**Acceptance Criteria:**  
NORMAL:
1. A staff member's task close increments total_executions and executions_in_trailing_window for their task_type, and the experience score recomputes against current .env thresholds.
2. Sandra is always scored/treated as Expert regardless of computed values — bypasses all experience-gated checks.

EDGE:
3. A staff member crossing an experience threshold mid-shift (e.g. their Nth execution flips them from non-Expert to Expert) takes effect on the very next task close, not retroactively on the one that crossed it.
4. executions_in_trailing_window correctly ages out old executions as the window rolls forward — an execution from outside the window no longer counts toward the current score.

NEGATIVE:
5. A non-Nick/Sandra/Edgar user attempting to modify thresholds is rejected — thresholds are not editable by regular crew or via any other path.
6. A task_type with zero execution history computes a defined default score (not null, not a crash) so downstream experience-gating logic never receives an undefined value.

SILENT FAILURE:
7. If the trailing-window recompute silently fails (e.g. a bad date calc), the system must not default to treating the staff member as Expert — fail toward more scrutiny, not less.
8. error_count increments must never be lost on a close that also updates other staff-experience fields in the same transaction — partial writes are not acceptable here (this table gates photo-verification requirements).

**Verification Method:**  
1) Unit tests: increment on close, threshold-crossing behavior, trailing-window aging, zero-history default. 2) Permission test: non-authorized user blocked from editing thresholds. 3) Fault-injection test: force the trailing-window recompute to fail, assert the staff member is NOT defaulted to Expert. 4) Transactional-integrity test: confirm error_count and experience fields commit atomically, no partial writes. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Staff-task-experience-table-3cfe152fc1998118827aec122fbd6c72_

---
## KIT-012 — Supervisor PIN photo override
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a supervisor override for a genuine camera failure — logged, with a follow-up nudge and expiry escalation to Nick.

**Functional Requirement Specification:**  
Supervisor PIN override for camera technical failure: supervisor enters override PIN, system logs photo_override + override_by/at, queues daily nudge for photo upload within 5 days, escalates to Nick's review queue at expiry. Override is for technical failure only, not convenience.

**Failure Behavior:**  
Fallback: manual tracking by Nick.

**Acceptance Criteria:**  
NORMAL:
1. Supervisor enters override PIN for a genuine camera failure → photo_override + override_by/at logged, daily nudge queued for 5-day photo-upload window, escalates to Nick's queue at expiry.

EDGE:
2. Photo is uploaded on day 4 of the 5-day window — nudges stop, no escalation to Nick fires.
3. Photo is uploaded exactly at expiry — defined, deterministic behavior on the boundary (counts as met, not a race with the escalation).
4. Same task gets a second override attempt before the first's window expires — does not reset/duplicate the nudge cycle incorrectly.

NEGATIVE:
5. Override PIN entered by someone who isn't an authorized supervisor is rejected.
6. Override used as a convenience shortcut (no actual camera failure) is not technically distinguishable by the system — flag as a known limitation requiring Nick's retrospective review of override logs, not a software gap to silently ignore.

SILENT FAILURE:
7. If the daily nudge job fails to run (cron/scheduler failure), the 5-day window must not silently expire without the nudges actually having been sent — verify nudge delivery is confirmed/logged, not just scheduled.
8. Escalation to Nick's review queue at expiry must not be silently skippable — confirm it fires even if the nudge job had prior failures.

**Verification Method:**  
1) Unit tests: override logging, nudge scheduling, expiry escalation, boundary-day upload. 2) Integration test: simulate nudge-job failure mid-window, confirm expiry escalation still fires correctly. 3) Access-control test: non-supervisor PIN rejected. 4) Audit-review process: Nick periodically reviews override logs for convenience-use patterns (documented as a process control, not a software gate). 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Supervisor-PIN-photo-override-3cfe152fc19981fa8b8ae74c503762be_

---
## KIT-013 — Error logging against staff + task
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: look up a task by item/time/event, view staff + photo, and log a required error note that increments error count and adds a visible retraining note.

**Functional Requirement Specification:**  
Error logging against staff + task: a reviewer queries a task by item/time/event, views the staff name and thumbnail, and enters required error notes. System increments error_count, marks the execution failed (excluded from competency score), and adds a retraining note visible to Nick + Sandra.

**Failure Behavior:**  
Fallback: manual notes in NocoDB.

**Acceptance Criteria:**  
NORMAL:
1. Reviewer queries a task by item/time/event, sees the correct staff name + thumbnail, enters required error notes → error_count increments, execution marked failed, retraining note visible to Nick + Sandra.

EDGE:
2. A task with multiple crew members touching it (handoff mid-task) attributes the error to the correct responsible crew member, not just whoever closed it last.
3. The same task queried and error-logged twice (double submission) does not double-increment error_count.

NEGATIVE:
4. Error note submitted with empty/blank text is rejected — notes are required, not optional.
5. A reviewer without appropriate permission cannot log an error against a task — this is a gated action, not open to any logged-in user.

SILENT FAILURE:
6. If error_count increments but the retraining note fails to save (or vice versa), this is a partial failure and must surface as an error — not a silent half-completed error log.
7. Marking an execution 'failed' must actually exclude it from the staff member's competency score calculation — verify this isn't just a status flag with no real effect downstream.

**Verification Method:**  
1) Unit tests: full error-log flow, blank-note rejection, permission gate. 2) Idempotency test: duplicate error-log submission on same task, confirm no double-increment. 3) Attribution test: multi-crew task, confirm error logged against the correct responsible party. 4) Downstream-effect test: confirm a 'failed' execution is actually excluded from the competency score computation (KIT-010/CLOSE 27), not just flagged. 5) Fault-injection test: force the retraining-note write to fail after error_count increments, confirm this surfaces as an error. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Error-logging-against-staff-task-3cfe152fc199818f9af2f4aa5085dd0f_

---
## KIT-014 — Thumbnail library table
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every submitted task photo stored with staff, task type, and quality tag; Sandra's auto-approved, Nick/Sandra can approve/flag any image.

**Functional Requirement Specification:**  
Thumbnail library table: stores all submitted photos with staff_id, task_type_id, quality_tag (pending/approved/error), error_notes, approved_by. Sandra's images auto-approve. Nick + Sandra can approve or error-tag any image. This library is the V1 asset base for V2 training card generation.

**Failure Behavior:**  
Fallback: manual photo folder with naming convention.

**Acceptance Criteria:**  
Images stored with correct metadata; Sandra's auto-approve; Nick/Sandra approve/error-tag functional; images queryable by task_type + quality_tag

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Thumbnail-library-table-3cfe152fc19981d98065cc7e13d61e85_

---
## KIT-015 — On-the-fly BOM modification routing
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: simple structured BOM changes (qty/add/remove) handled instantly; anything more complex (substitution) routed to a supervisor for PIN approval before commit.

**Functional Requirement Specification:**  
On-the-fly BOM modification routing: structured changes (qty adjustment, add-from-master, remove item) handled deterministically with zero inference. Substitutions/unrecognized items route to AI (Path C, <25s), which returns a structured proposal only (no direct write). Supervisor PIN approval required before commit; audit log captures proposal + approving supervisor.

**Failure Behavior:**  
Fallback: manual Sandra/Nick review; block task until resolved.

**Acceptance Criteria:**  
Structured changes commit within 5s with no AI call; substitution/unknown item routes to AI within 25s; no canonical write without PIN approval; audit log entry on every substitution

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/On-the-fly-BOM-modification-routing-3cfe152fc199813bbe45cc553acb8a7f_

---
## KIT-017 — Voice card closing
**Status:**  | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: close a kanban card hands-free by voice ("Hey Taza, [completion statement]") at MT1/MT2, auto-matched and confirmed.

**Functional Requirement Specification:**  
Voice card closing: crew says "Hey Taza, [completion statement]" at MT1/MT2. Wake word on NPU (<100ms). Android on-device STT transcribes. System matches to active card, confirms, awards points, moves to done pile. Replaces tap for card closing.

**Open Questions:**  
RESOLVED 2026-09-02: this is Nick's preferred long-term approach (local NPU edge compute for intent classification) but is not required for V1.0 — NPU 5 (PROD-37, Chrome Web Speech API + N100) ships for V1.0. Revisit this as the V1.x/V2 upgrade once the NPU wake-word path is tested and proven.

**Rationale:**  
Game mechanic IS the inventory capture.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Voice-card-closing-3cfe152fc1998109b21be7e49ba17d23_

---
## KIT-020 — Binary image verification on card close
**Status:**  | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a quick automated visual check on card close (e.g. is the poly wrap tight enough) as a supporting cue, not the final call.

**Functional Requirement Specification:**  
Binary image verification on card close: NPU runs a MobileNet INT8 classifier (~30 training images/class) for yes/no checks like "Did the poly wrap look tight enough?" Camera is verification, not identification — the crew member is the authority. Thumbnail stored for audit trail.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Binary-image-verification-on-card-close-3cfe152fc19981de81d5ec89fb13d9b2_

---
## KIT-022 — Kitchen soundscape classification
**Status:**  | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: kitchen ambient sound classified during active service (alert if unusually quiet), correlated anonymously with shift productivity.

**Functional Requirement Specification:**  
Kitchen soundscape classification: YAMNet INT8 on NPU samples the mic every 5s, classifying laughter/silence/arguing/clanging. Dashboard shows a "quiet kitchen" alert during active service. Mood correlated with shift productivity in nightly N100 analysis. Anonymized, SPC control chart framing.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Kitchen-soundscape-classification-3cfe152fc19981de9999d9c466a01ca0_

---
## KIT-023 — Person detection for spaghetti diagrams
**Status:**  | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: anonymized movement tracking generating heatmaps, station dwell-time, and cross-traffic hotspots to spot layout inefficiencies with real data.

**Functional Requirement Specification:**  
Person detection for spaghetti diagrams: SSD-MobileNet/YOLO-v5n INT8 on NPU at 5fps, bounding-box centroids logged to Postgres. Nightly analysis produces movement heatmaps, station dwell-time, and cross-traffic hotspots. All anonymized (Person A/B/C). Pre/post Taza OS comparison via SPC control chart.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Person-detection-for-spaghetti-diagrams-3cfe152fc19981e688bbca74b91b40f8_
