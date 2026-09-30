# Taza OS URS — PLANNER cluster (Seating, Layout & Room Intelligence)
_Exported: 2026-09-24 | 1 Spec Package + 8 Atomic Requirements_
_Source: Notion Master URS & Specification Registry_

This cluster supersedes the prior fragmented [[SPEC:URS-PLAN-PKG]] draft. It specifies the seating/layout/room-intelligence layer of the holistic Taza Client/Planner Portal — a living, shared command center for events. Decision-tree cost tracking, referral QR codes, vendor SLA monitoring, and post-event feedback are part of the same portal but specified elsewhere.

---

## URS-PLAN-PKG — Planner Portal: Seating, Layout & Room Intelligence (Spec Package)
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Spec Package

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
We want a planner or a customer to open one link and step into a living, shared command center for their event — not a form, not an email chain, not a static PDF floor plan. They see the current seating layout update in front of them as anyone else with access changes it, they can see and hold the real room in their hands before committing to a plan, and they never wonder whether what they're looking at is current.

This is a technological moat, not a single feature: the same portal that holds this seating/layout intelligence also holds the decision tree, the referral system, vendor SLA monitoring, and post-event feedback. A customer or planner should feel like they're in one coherent tool for their whole event, not a patchwork of disconnected screens — even though this package only specifies the seating/layout/room-intelligence piece in depth.

A free tier makes the tool something people discover and share — anyone can browse and fork a public plan as a starting point. A paid tier is what protects privacy once real guests' names are on a plan, priced cheaply enough that switching from generic tools like Asana and Monday is an easy yes, but structured so a high-volume user pays proportionally more than an occasional one.

The tool must work as well from a rural venue with one bar of signal as it does from an office — offline is not an edge case here, it's a normal Tuesday. And no one, regardless of what phone they're holding, should be shut out of checking whether their layout actually fits the real room: if their device can do it with AR, great; if not, the app itself — not the person — does the work of figuring out the room, whether that means asking a few good questions or reading a drawing they already have.

**Atomic Requirement (package scope):**
The system shall provide a real-time collaborative seating/layout editor for event planning, integrated with AI-powered room intelligence, access-controlled by a tiered (free/paid) fork model, operable offline, and backed by Cloudflare edge architecture — such that a planner or customer opens one link and steps into a living shared command center for their event.

**Functional Requirement Specification (package scope):**
The Planner Portal Seating/Layout layer shall implement:
1. A public-by-default fork model for free-tier events, with private-by-default access for paid-tier events ([[SPEC:URS-PLAN-001]]).
2. Per-event access control via signed tokens, with role-based grants (staff/planner/customer/guest) and guest attribution ([[SPEC:URS-PLAN-002]]).
3. Real-time collaborative layout editing over WebSocket, with last-write-wins conflict resolution per table/seat and live presence cursors ([[SPEC:URS-PLAN-003]]).
4. A draft/locked workflow that auto-locks events 72h before start for food-service-affecting changes, with staff-only override capability ([[SPEC:URS-PLAN-004]]).
5. Three room-capture paths (AR scan, AI-guided measurement Q&A, PDF/drawing upload) converging on a shared capacity/clearance check ([[SPEC:URS-PLAN-005]]).
6. Per-event change log with undo, revert, and batched staff notifications ([[SPEC:URS-PLAN-006]]).
7. Offline-tolerant client via Cloudflare Pages + service worker, with queued local edits and reconcile-on-reconnect ([[SPEC:URS-PLAN-007]]).
8. Tiered billing enforcement — free tier unlimited public events; paid tier flat monthly base + bundled private events + per-event overage ([[SPEC:URS-PLAN-008]]).

**Intent / User Need:**
Turn proprietary technique transmission from a lecture or a manual into something the crew experience through the card game itself — so the Taza standard is absorbed in the flow of work, not in a training room.

**Failure Mode Addressed:**
Planners and customers relying on static PDFs, email chains, and phone-tag to coordinate event layouts; dimension guesswork leading to seating-layout-timefield failures; no version control; no offline capability at rural venues; expensive generic tools (Asana, Monday) that don't understand event geometry.

**Out of Scope:**
Decision-tree cost tracking, referral QR codes, vendor SLA monitoring, and post-event feedback — these are part of the same holistic portal but specified in their own packages. The actual payment processor integration (FR-8). Rectangular/banquet-table-specific clearance rules (interim default used until defined). The pricing-model conflict between this spec's bundle-plus-overage model and the older V2 $50/instance proposal must be resolved in debate before implementation.

**Acceptance Criteria (package):**
All 8 child requirements pass their individual Acceptance Criteria. End-to-end test: a planner creates a free-tier event with a full layout (tables+guests) via the AI room-capture path, invites a customer who edits a table live while the planner sees the change in real time, the event auto-locks 72h before start, and a staff override is logged with upcharge decision. A second user forks the public event, gets a fully independent copy. The same flow works offline on reconnect. A paid-tier event is inaccessible to uninvited users. All events pass the clearance check with explicit "planning estimate" labeling.

**Verification Method:**
End-to-end black-box test covering all 8 FRs in sequence; plus adversarial tests (clock-skew, network-loss mid-edit, concurrent edits to same table, stale service-worker version, PDF-upload-of-menu-instead-of-floorplan, billing-service-unreachable) per each child requirement's verification method.

**Open Questions:**
1. Does the 72-hour lock ([[SPEC:URS-PLAN-004]]) apply to the whole layout or only food-service-relevant fields (headcount, table count)?
2. Pricing-model conflict ([[SPEC:URS-PLAN-008]]) — bundle-plus-overage vs. older V2 $50/instance flat fee. Debate team must pick one, not merge both.
3. If a planner is removed from an event (reassigned) while a customer they invited still has active Editor access — does the customer's access survive the planner's removal? Needs a decision per [[SPEC:URS-PLAN-002]].
4. Rectangular/banquet table clearance rule — currently an interim default (72" edge-to-edge); needs a real rule before V1.x ships.
5. Exact monthly base price, bundle size, and overage fee — needs real Cloudflare usage-cost modeling once live.

**Rationale:**
The seating/layout/room-intelligence layer is the centerpiece of the Planner Portal's technological moat. The free-tier fork model drives organic discovery; the paid tier protects privacy. Offline capability is not optional for venues with poor connectivity. The three room-capture paths (AR/AI/upload) ensure no device or skill level is excluded from accurate room intelligence. Cloudflare's edge architecture (Durable Objects, Pages, Workers) provides the real-time, offline, globally-distributed backbone without managing servers.

**Acceptance Criteria:**
NORMAL: a planner or customer opens one link into a live shared command center — current layout, real-time collaboration, no email chain or static PDF.
EDGE: offline at a rural venue → the tool still works (offline is a normal case, not an exception).
EDGE: a device without AR → the app itself resolves the room via questions or a drawing; no one is shut out.
NEGATIVE: an unauthenticated user sees a paid-tier event with real guest names → impossible (private-by-default, signed tokens).
SILENT-FAILURE: a user views a stale layout believing it's current → caught (changes propagate in real time; staleness visible).
CHALLENGE: two planners edit the same layout simultaneously from different devices → both see the other's changes live.

**Required for Release:**
YES

---

## URS-PLAN-001 — Visibility & the Fork Model
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As a planner or event host, I want anyone to be able to browse and copy a public event plan as a starting point without my involvement, while my paid private events stay invisible to everyone I haven't explicitly shared the link with — because the free tier drives discovery and the paid tier protects privacy.

**Functional Requirement Specification:**
The system shall mark every free-tier event as publicly viewable and forkable by any authenticated user, showing the full plan including full guest names, no redaction. A "Fork" action shall create a brand-new, independently owned event seeded from a snapshot of the source — no shared state after that point. Paid-tier events shall be private by default: not listed, not viewable, not forkable by anyone the owner hasn't explicitly shared the link with. A fork's visibility shall follow the forker's own account tier, not the source's.

**Failure Behavior:**
Fallback: all events private by default (loses free-tier discovery but protects data). On billing/unreachable error, default to blocking new fork operations rather than allowing unlimited unowned forks.

**Acceptance Criteria:**
NORMAL:
1. A free-tier event is fully visible (including guest names) with a working Fork action to any authenticated user.
2. Forking creates a fully independent event; editing either the original or the fork afterward never affects the other.
3. An unauthorized user attempting to access a private event gets denied, no partial data leak.

EDGE:
4. A user forks a public event, then the original owner deletes their account — the fork survives intact with no data loss.
5. A forker on a free account forks a public event (which was created by a paid account while set to public) — the fork is itself publicly viewable and forkable per the forker's free-tier visibility, not private because the source was paid-tier.
6. Forking an event with a large layout (500+ seats) completes within a reasonable time and produces a complete copy, not a timeout or partial state.

NEGATIVE:
7. A paid-tier event's share link is accidentally shared broadly (e.g. posted to social media) — only the explicitly shared-link holders can view it; the event is not publicly listed or discoverable through any index.

SILENT FAILURE:
8. A fork that appears complete but silently drops data (e.g. missing a table or guest name due to a race condition during snapshot) would defeat trust in the fork model entirely — verify fork integrity with an after-fork audit comparing every object in the source vs. fork.
9. Guest names silently redacted on a free-tier public event (or, conversely, full names leaking on a private event) are both data-privacy failures — verify by rendering a free-tier event as an unauthenticated user and confirming full names are visible, and by checking a private event's rendered state and confirming they appear only with the correct access token.

**Verification Method:**
1) Free-tier event visibility test: authenticated user views full plan with guest names, Fork button is present and functional. 2) Fork-independence test: edit source after fork, verify fork unchanged; edit fork, verify source unchanged. 3) Private-event denial test: unauthenticated request and unauthorized authenticated request both get denied. 4) Account-deletion fork survival test: delete source owner's account, verify fork remains fully functional. 5) Integrity audit: post-fork, query all tables/seats/names in source vs. fork, confirm byte-identical snapshot. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
Fork implementation depends on Durable Object snapshot + new-event creation (BUNDLE-PLANNER-CORE in Known Design Specs).

**Open Questions:**
Does the fork action copy the change history of the source, or only the current layout state? Recommendation: current state only — the fork starts its own change log from zero.

**Required for Release:**
YES

---

## URS-PLAN-002 — Per-Event Access Control & Guest Attribution
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As a planner, I need to control exactly who can see and edit each event — invite customers by email, set their role, and revoke their access at any time — and I need every edit attributed to a real person's first name, not an anonymous cursor, so I always know who changed what.

**Functional Requirement Specification:**
Every access grant shall be a signed, per-event token carrying event ID, role (staff/planner/customer/guest), and level (editor/viewer). A customer shall have no access at all until their planner explicitly invites them; the planner shall be able to grant, change, or revoke that access at any time, independently per event. Any Editor-level user shall be able to invite guests; every guest shall authenticate with their own email address, never a shared/anonymous identity, and their first name shall appear on their cursor and in the change log for every edit.

**Failure Behavior:**
Fallback: token-auth service unreachable → deny all access (fail-closed). Offline: locally-cached token grants access to the last-known state with read-only capability until re-authentication succeeds.

**Acceptance Criteria:**
NORMAL:
1. A new event's link grants no access until the planner explicitly invites the recipient; the uninvited recipient sees a denial, not a partial view.
2. A planner-granted Editor customer can edit live and their first name shows on their cursor and in the change log.
3. A guest invited by a Viewer-level user inherits only Viewer access, never more than the inviter's own level.

EDGE:
4. Revoking access mid-session rejects that user's very next write attempt — the next edit they attempt after revocation fails, not just the next session.
5. Two different guests on one event share the same first name — attribution is unambiguous: first name on cursor/compact label, full name on hover.
6. A planner is removed from an event (reassigned) while a customer they invited still has active Editor access — **open question**: does the customer's access survive? Decision needed before implementation.
7. A guest authenticates with a new email address (changed email) but is already known to the event under their old address — the system resolves them to the same identity.

NEGATIVE:
8. An attempt to grant a role level not authorized by the grantor's own level (e.g. a Viewer trying to grant Editor) is rejected.
9. A malformed or expired token is rejected with a clear error message, not a silent redirect or blank page.

SILENT FAILURE:
10. A token that leaks (e.g. shared link forwarded to an unintended recipient) is only as secure as the link — verify tokens are sufficiently opaque and short-lived enough that a leaked planning-session link can't be used to access the event days later without re-authorization.
11. Token revocation that only takes effect on next page load but not during an active WebSocket session would leave a revoked user editing for up to the heartbeat interval — verify revocation closes the active connection within a bounded time (e.g. within 30s via token check on the DO's message handler, not only on HTTP request boundaries).

**Verification Method:**
1) Invite/deny test: uninvited user gets denied, invited user gets correct access. 2) Edit attribution test: Editor's first name appears on cursor and in change log entries. 3) Revocation test: revoke mid-session, confirm next write attempt is rejected, confirm WebSocket is terminated within 30s. 4) Same-name test: two guests with same first name, verify hover shows full name. 5) Token-expiry test: expired token gets clear error. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
Token signing depends on the Worker auth layer (BUNDLE-PLANNER-CORE). Token-check on WebSocket messages implemented inside the Durable Object's message handler.

**Open Questions:**
Does a removed planner's invited customers retain their access? Decision needed: two approaches — (a) customer access is independent and survives (more permissive), or (b) customer access is transitive and dies with the planner's role (stricter, forces new planner to re-invite). Spec does not prescribe — debate team decides.

**Required for Release:**
YES

---

## URS-PLAN-003 — Real-Time Collaborative Layout Editing
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As a planner working with a customer, I need to see their layout changes appear on my screen instantly as they make them, and I need to know who else is in the room with me — so we're never looking at different versions and wondering which one is current.

**Functional Requirement Specification:**
The system shall hold one live, canonical layout (tables, seats, room geometry) per event, editable over a live WebSocket connection by any connected Editor-level client, with every edit broadcast to every other connected client for that event. Conflicting edits to the same object shall resolve last-write-wins, scoped per table/seat, never per whole layout. Every connected client shall see lightweight presence signals (who's connected, what they're dragging) rendered as live cursors/highlights. On reconnect, a client shall request full current state rather than replaying missed edits.

**Failure Behavior:**
Fallback: WebSocket connection fails → client shows last-known state with "Reconnecting…" overlay and retries with exponential backoff. On successful reconnect, client requests full current state.

**Acceptance Criteria:**
NORMAL:
1. Two clients on the same event: one moves a table, the other sees it move with no manual refresh, within <500ms of the edit.
2. Two clients edit different tables simultaneously: both changes persist, both clients converge to the combined state.
3. Two clients edit the same table in the same instant: later write wins, both clients converge to the winning state.
4. A client reconnecting after a drop receives full current state, never a partial replay.

EDGE:
5. A client's clock is significantly wrong — timestamp-dependent logic (change log, lock scheduling) must not rely on client-reported time for anything authoritative; server timestamps are used for conflict resolution and logging.
6. A client with a very slow connection (high latency) sends edits that arrive out of order — the server orders them by server receipt time, not client send time, for last-write-wins resolution.
7. 10+ clients simultaneously connected to one event (e.g. a large planning session) — presence signals remain lightweight and the DO does not degrade.

NEGATIVE:
8. A client whose WebSocket drops but whose HTTP session is still valid (e.g. network blip) reconnects without data loss — no edits are silently lost in the gap.
9. A client that loses connectivity while dragging a table does not leave the table in a transient "mid-drag" state on other clients — the table stays at its last confirmed position.

SILENT FAILURE:
10. Presence signals that show a user as "connected" when they've actually disconnected (stale presence) would mislead planners into thinking a customer is watching when they've left — verify presence signals have a heartbeat timeout and are cleaned up within 2 missed heartbeats.
11. Two clients that both believe their edit won (same-table conflict) but one silently lost due to last-write-wins must both converge to the same final state — verify with automated adversarial testing (both clients submit edits to the same table in the same millisecond via controlled test harness) that both end up with the winner's state, not diverged.

**Verification Method:**
1) Live-edit broadcast test: one client moves a table, second client observes the move without refresh, measure latency. 2) Simultaneous-edit test: two clients edit different tables, then same table — both converge. 3) Reconnect test: force network drop, confirm reconnected client receives full state. 4) Clock-skew test: set client clock 5 minutes ahead, confirm edit is resolved with server timestamp, not client. 5) Presence-heartbeat test: disconnect a client, confirm presence is removed within 2 heartbeat intervals. 6) Adversarial conflict test: scripted concurrent edits to same object, verify convergence. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
Depends on Durable Object per event for canonical state (BUNDLE-PLANNER-CORE). WebSocket routing through the Worker for token checks.

**Required for Release:**
YES

---

## URS-PLAN-004 — Draft/Locked Workflow
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As a planner, I need the event to automatically lock down food-service-relevant changes 72 hours before start so the kitchen has a firm count to prep against — no last-minute guest-count bumps without a formal override. As staff, I need the ability to unlock or override with an explicit upcharge decision logged, because sometimes the client does need to add two tables at T-48h and we need to track the cost.

**Functional Requirement Specification:**
Every event shall default to draft, editable live by any Editor-level user. The system shall automatically transition an event to locked exactly 72 hours before its scheduled start for any change affecting food service (guest count, table count, anything feeding kitchen prep); customer and external-planner access shall become view-only at that point. Only staff shall be able to unlock or directly edit a locked event; every such change shall be flagged as an "override," require an explicit upcharge decision (yes/no/amount) before being applied, and be logged with who requested it, who approved it, what changed, and when.

**Failure Behavior:**
Fallback: the scheduled lock job fails to fire (cron/scheduler miss) — event must be flagged for manual staff review, not silently stay unlocked past the deadline. An alert is sent to staff if an event passes its lock deadline without being locked.

**Acceptance Criteria:**
NORMAL:
1. An event more than 72 hours from its scheduled start is editable by any Editor-level user.
2. An event exactly 72 hours from start auto-locks; customer/planner access becomes view-only.
3. A locked event rejects customer/planner edit attempts with a clear "locked" message.
4. A staff override on a locked event is logged with who requested it, who approved it, what changed, when, and the upcharge decision (yes/no/amount).

EDGE:
5. The scheduled lock job fails to fire — event is flagged for manual staff review within 15 minutes of the missed deadline.
6. An event's scheduled start time changes (moved earlier or later) — the lock deadline recomputes correctly from the new time.
7. A staff override that makes no food-service change (e.g. purely cosmetic: move a table 6 inches, change a seat label) — does this need an override at all? **Open question**: if lock applies only to food-service-relevant fields, purely cosmetic edits in locked state go through without override.

NEGATIVE:
8. A customer attempting to edit a locked event is shown a clear explanation ("This event is locked 72 hours before start. Contact your planner to request changes.") not a technical error.

SILENT FAILURE:
9. The 72-hour lock transitioning the event while a user is actively editing (mid-edit) must not silently lose their in-flight change — the edit attempt is rejected and the user is shown the lock notice, with their unsaved change preserved in the UI so they can decide whether to request a staff override.
10. A staff override that is logged but whose upcharge decision is never followed up on (approved with amount X, but invoice never updated) is a revenue-leak risk — verify the override log is surfaced in a billing/invoicing review queue, not just stored invisibly.

**Verification Method:**
1) Auto-lock test: create an event with start time T+73h, verify it's editable; advance time to T+72h, verify it becomes locked and view-only for non-staff. 2) Override test: staff performs an override, verify full audit log entry. 3) Lock-miss test: simulate job failure, verify flag/alert is raised within 15 min. 4) Time-change test: change event start time, verify lock recalculates. 5) Mid-edit-lock test: have a user editing as the lock fires, confirm graceful rejection with preserved draft. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**
Does the 72-hour lock apply to the whole layout or only food-service-relevant fields (guest count, table count)? Two approaches exist:
- Whole-layout lock (simpler, safer): no changes of any kind after lock without override.
- Food-service-field lock only (more flexible): cosmetic edits (move a table 2 inches, rename a seat label) still allowed without override.
Debate team must decide before implementation. Spec recommends whole-layout lock for V1.x, food-service-only as a V2.x enhancement.

**Required for Release:**
YES

---

## URS-PLAN-005 — Room Capture, AI Room Intelligence & Capacity Check
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As a planner or customer, I need to know that my seating layout actually fits the real room — regardless of what device I'm holding or whether I have a floor plan. If my phone supports AR, show me. If not, help me figure out the room by asking a few good questions or by reading the drawing I already have. And every layout, no matter how it was created, gets checked against a consistent clearance rule so tables aren't too close together for food service.

**Functional Requirement Specification:**
The system shall offer three ways to capture a venue's real dimensions, chosen automatically or by the user based on what's available, all converging on the same room data object and the same capacity/clearance check:

1. **AR scan** (device-capable): when the user's device/browser supports AR, capture real-world dimensions and obstacles (pillars, doorways, a stage) via the phone's camera/AR sensors and overlay the planned layout on the live camera view at true scale.

2. **AI-guided measurement fallback** (no AR support): the system's AI shall step in to do what AR would have done — asking the user a short, targeted series of questions to gather the measurements it needs (wall lengths, doorway placement, ceiling height where relevant), then deducing the room's shape and usable floor area from the answers plus any photos the user provides. This is an interactive, conversational capture, not a one-shot form.

3. **PDF/drawing upload** (planner-facing): a planner shall be able to upload a PDF or architectural drawing of the venue; the system's AI shall deduce room dimensions and layout directly from the drawing, and reconcile that deduction against any measurements or photos also provided — flagging a conflict to the user rather than silently picking one source over the other if the two disagree.

All three paths shall run the same capacity/clearance check against the current layout, using the heuristic: minimum center-to-center spacing for round tables = table radius + 72" (6') of clearance (e.g. a 6'-diameter round, 3' radius, placed 9' center-to-center from its neighbors) — accounting for chairs pushed back with seated guests plus a walkable aisle for someone carrying food or drinks. Rectangular/banquet tables shall use the same 72" clearance measured edge-to-edge until a rectangular-specific rule is defined. Every result of this check shall be presented explicitly as a planning estimate, never as a fire-code or occupancy-compliance determination.

**Failure Behavior:**
Fallback: manual room-dimension entry (user provides length/width/obstacles directly). If AI Q&A produces a low-confidence estimate, prompts for clarification or falls back to manual entry — never silently proceeds with a bad estimate.

**Acceptance Criteria:**
NORMAL:
1. Device with AR support is offered the AR path; device without AR support is offered the AI-guided fallback instead, with no AR option shown.
2. AI-guided Q&A: the AI's question sequence produces a room estimate; user can override any value it proposes.
3. PDF/drawing upload: AI deduces room shape from a floor-plan-style PDF, asks for one reference dimension (e.g. "how long is this wall?") to calibrate scale before trusting the deduction.
4. Capacity check: two round tables placed closer than radius+72" are flagged, naming both tables and the shortfall in inches.
5. Clearance check result is always labeled "Planning estimate — not a fire-code or occupancy-compliance determination."

EDGE:
6. AI Q&A produces a low-confidence estimate (e.g. contradictory or implausible answers) — must prompt for clarification or fall back to manual entry, never silently proceed with a bad estimate.
7. PDF-deduced room and user's separately entered measurements disagree — system flags the conflict explicitly and lets the user pick or correct, never silently prefers one source.
8. Uploaded PDF is not a floor plan at all (e.g. a menu, a contract) — AI detects this and asks for a real drawing rather than fabricating a room from irrelevant content.
9. AR scan captures a room with irregular shape (L-shaped, pillars, multiple levels) — obstacles are correctly represented in the room data object and capacity check accounts for reduced usable floor area.

NEGATIVE:
10. A room capture path that fails mid-way (AR session drops, AI Q&A times out, PDF unparseable) surfaces a clear error and offers an alternative path or manual entry — never hangs or silently produces a default "standard room" estimate.
11. A capacity check against an empty layout (no tables placed) shows a clean "no conflicts" state, not an error.

SILENT FAILURE:
12. The clearance-adjacent capacity math is deterministic, not AI-driven — verify the code path for capacity checking never calls an AI model but always computes against a hardcoded rule. This is a safety-adjacent requirement, not a suggestion.
13. The "planning estimate" disclaimer is omitted from the check result in any rendering context (embedded view, tooltip, export) — verify every surface that shows capacity/clearance information carries the disclaimer.
14. AR path overlays the layout on the live camera view but the scale calibration is slightly off (e.g. the virtual table appears 10% larger than real) — this would give a false sense of fit. Verify AR scale accuracy against a known-reference object of known size (e.g. overlay a 6' circle over a real 6' table and confirm within 5% size match).

**Verification Method:**
1) AR path test: on an AR-capable device, scan a known room, confirm captured dimensions are within 5% of measured. 2) AI Q&A test: feed a set of measurement answers for a known room shape, confirm the deduced room matches. 3) Low-confidence test: feed contradictory answers, confirm system asks for clarification rather than proceeding. 4) PDF upload test: upload a floor-plan PDF with known dimensions, confirm AI deduces correctly after scale calibration. 5) PDF-not-floorplan test: upload a menu PDF, confirm system rejects it gracefully. 6) Conflict-reconciliation test: upload a PDF and separately enter conflicting measurements, confirm conflict is flagged for user resolution. 7) Clearance-check test: place two tables at radius+70" spacing, confirm they're flagged; place them at radius+74", confirm they pass. 8) Disclaimer audit: check every UI surface that shows capacity/clearance info for the planning-estimate disclaimer. 9) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
AR depends on WebXR API support in browser. AI Q&A and PDF deduction call a vision-capable model via AI Gateway (OpenRouter / Workers AI) on gflip. Room data object is the common output format for all three paths. Clearance check is a deterministic function called on the room data object + layout.

**Open Questions:**
Rectangular/banquet table clearance rule is currently an interim default (72" edge-to-edge). A real rule accounting for rectangular table geometry (long side vs. short side clearance, aisle width along the length) needs to be defined before V1.x ships — or the interim rule must be explicitly documented as conservative/over-estimating.

**Required for Release:**
YES

---

## URS-PLAN-006 — Change Tracking & Staff Notification
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As staff, I need to see every change made to an event after it was created, know who made it and when, and be able to undo or revert to any earlier state. I also don't want to be notified twenty times when a customer makes a burst of edits — batch it up and tell me once.

**Functional Requirement Specification:**
Every applied edit shall be appended to a per-event change log tagged with the acting user's identity and timestamp. The system shall support in-session undo and reverting the whole layout to any earlier logged point. Staff shall be notified, batched (e.g. every 15 minutes of activity or on session end, not per edit), whenever a customer- or external-planner-linked session edits an event in draft.

**Failure Behavior:**
Fallback: no undo capability (changes still tracked, revert handled manually). Notification failure: fall back to queued notification delivered on next successful send.

**Acceptance Criteria:**
NORMAL:
1. Every edit is appended to the per-event change log with acting user's identity and server timestamp.
2. In-session undo reverses the most recent edit in the current session.
3. Reverting to an earlier logged point restores the full layout state to that exact snapshot.
4. A customer's burst of edits over 15 minutes produces one batched staff notification, not individual per-edit notifications.

EDGE:
5. Undo after a session has been closed and re-opened: the undo stack persists across sessions (the change log is the source of truth; "undo" on reconnect uses the latest entry from the log that hasn't been explicitly reverted, not a client-side-only stack).
6. Revert to a point that is still within the locked period ([[SPEC:URS-PLAN-004]]) — reverting food-service-relevant fields while locked requires an override just like a direct edit would.
7. Two revert operations in rapid succession (someone clicks "revert to point A" then immediately "revert to point B" before the first finishes) are queued and applied sequentially, not raced.

NEGATIVE:
8. A revert target's data is missing/corrupted (snapshot storage failure) — system refuses the revert and reports the failure rather than applying a broken partial state.
9. Attempting to undo when the change log is empty (fresh event with no edits) shows a graceful "nothing to undo" state, not an error.

SILENT FAILURE:
10. The change log grows unboundedly for a long-lived event with many edits — verify there's a retention/compaction strategy (e.g. keep last N edits; periodic full-state snapshots so old history can be pruned) and that it does not silently cause performance degradation on the Durable Object (bloated memory usage, slow log appends).
11. Batched notification that groups a customer's edits but the batch description is too vague (e.g. "Customer made 23 edits") to be actionable — verify the batch summary includes a human-readable description of what changed (e.g. "Added 2 round tables, moved the head table, changed 3 seat assignments"), not just a count.

**Verification Method:**
1) Change-log test: make an edit, verify it appears in the log with correct user and timestamp. 2) Undo/redo test: make 3 edits, undo one, verify the layout state matches. 3) Revert test: revert to point A, verify full layout matches the snapshot at point A. 4) Revert-corruption test: corrupt the stored snapshot at point A, confirm revert is refused with clear error. 5) Batching test: make 10 edits as a customer in 10 minutes, verify one notification sent, not ten. 6) Batch-summary test: verify the batched notification includes a human-readable change summary. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
Change log stored in the Durable Object's storage for the active draft period. Full snapshots pushed to Postgres on lock or periodic save (see BUNDLE-PLANNER-CORE: Durable-Object-to-Postgres sync). Staff notifications routed through existing N100 dashboard/notification path.

**Required for Release:**
YES — P1 priority (change tracking itself is P0; batched notification is P1 and may be deferred)

---

## URS-PLAN-007 — Offline-Tolerant Client
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As a planner visiting a rural venue with one bar of signal, I need the app to open instantly and let me keep working on the layout even with no internet. When I get back online, my changes should sync up without losing anything or silently overwriting someone else's work.

**Functional Requirement Specification:**
The app shell shall load from Cloudflare Pages' edge cache and be precached by a service worker after first load, so it opens instantly and remains usable with zero connectivity. Offline, the user shall be able to edit solo with changes queued locally; on reconnect, queued changes shall sync and the client shall reconcile to full current state under the same last-write-wins rule as [[SPEC:URS-PLAN-003]]. A persistent, honest UI indicator shall distinguish "Live" from "Offline — changes will sync," and any conflict discovered on reconnect shall surface a visible notice, never a silent overwrite.

**Failure Behavior:**
Fallback: app requires connectivity (degraded — offline editing lost, but app shell still loads from cache for instant-on experience). If service worker cache is invalidated while the user is offline, show a "New version available — reconnect to update" notice and continue with the cached version.

**Acceptance Criteria:**
NORMAL:
1. App shell loads from cache with zero signal, after having been opened once with connectivity — page renders and UI is usable.
2. Edits made offline sync and reconcile correctly once connectivity returns — the layout state after sync matches what last-write-wins would produce.
3. A conflicting edit made elsewhere while the user was offline surfaces a visible notice on reconnect ("Some of your changes were overwritten by another editor"), never a silent overwrite.
4. The Live/Offline UI indicator always matches actual connection state and is updated within 5s of a state change.

EDGE:
5. User is offline long enough that the app shell itself has a newer version available — the service worker cache-invalidation strategy must not strand the user on a broken stale version once they reconnect. On reconnect, the new version is fetched and presented with a "Updated — reload to see latest features" notice.
6. User makes edits offline on an event that was locked ([[SPEC:URS-PLAN-004]]) during their offline period — on reconnect, the edits are rejected with a clear explanation ("This event was locked while you were offline. Your changes have been saved locally but not applied") rather than silently failing sync.
7. The offline queue grows very large (500+ edits over a long offline period) — verify it syncs within a reasonable time on reconnect (e.g. all edits processed within 30s on a typical connection), or if not, shows a progress indicator.

NEGATIVE:
8. Opening the app for the first time with zero signal (no prior cache) shows an appropriate offline fallback state, not a broken/blank page.
9. A service worker install failure does not prevent the app from loading online on subsequent visits.

SILENT FAILURE:
10. The "Live" indicator showing "Live" when the WebSocket is actually disconnected (zombie connection) would cause the user to think edits are being broadcast when they're only queued locally — verify the Live indicator reflects WebSocket health, not just connectivity, and has a heartbeat-based disconnection detection with <10s latency.
11. Offline edits that are synced out of order (user edits table A, then table B, sync sends B's edit before A's due to async timing) must still produce the correct final state — verify the sync algorithm orders by local timestamp (or presents a sequence number) to ensure in-order application on the server.

**Verification Method:**
1) Offline-load test: first load with connectivity, then enable airplane mode, verify app loads from cache and is usable. 2) Offline-edit-and-sync test: make edits offline, reconnect, verify they sync correctly and layout state converges. 3) Conflict test: while offline, have another client edit the same table online; on reconnect, verify a visible conflict notice is shown. 4) Indicator test: toggle connectivity, verify Live/Offline indicator updates within 5s. 5) Large-queue test: enqueue 500 edits offline, reconnect, verify all sync within 30s with a progress indicator. 6) First-load-offline test: clear all caches, enable airplane mode, open app for first time — verify graceful fallback. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
Service worker managed via Cloudflare Pages' built-in service worker integration or a custom script. Offline edit queue stored in IndexedDB or a similar client-side storage. Sync reconciliation uses the same last-write-wins rule as the online Durable Object path. The WebSocket health indicator must check actual connection state, not just navigator.onLine.

**Required for Release:**
YES

---

## URS-PLAN-008 — Tiered Billing Enforcement
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**
Atomic Requirement

**Domain:**
Event Planning — Planner Portal

**User Requirement Statement:**
As the business owner, I need free-tier users to be able to create unlimited public events (driving discovery and viral fork growth), while paid accounts pay a predictable monthly fee for private events — but proportionally more if they're a high-volume user, so I'm not subsidizing heavy users on a flat rate.

**Functional Requirement Specification:**
The free tier (public/forkable events) shall be unlimited and free, with no usage cap. Paid accounts shall be charged a flat monthly base fee including a bundled number of private events per month, plus a small per-event overage fee beyond that bundle — enforced at the point of creating or converting an event to private, with overage confirmed before it's incurred, never billed as a silent surprise.

**Failure Behavior:**
Fallback: billing/usage-count service unavailable when a private-event creation is attempted — default to blocking creation, never to unlimited free overage. The user is shown "Billing service temporarily unavailable — please try again" rather than being allowed to create a private event that may not be billed.

**Acceptance Criteria:**
NORMAL:
1. A free-tier account can create unlimited public events; attempting to create a private event is blocked or prompts an upgrade.
2. A paid account within its monthly bundle creates private events with no overage charge and no billing prompt.
3. A paid account past its bundle is prompted to confirm the overage fee before the event is created, with the fee clearly stated — never billed after the fact without warning.

EDGE:
4. A paid account right at the bundle boundary (e.g. 5 of 5 private events used for the month) — the 6th private event triggers the overage confirmation prompt.
5. A paid account that converts a public event to private mid-month — the conversion counts as a private event creation and is billed/enforced at that point, not at the original public creation.
6. A free account that upgrades to paid mid-month — previously created public events remain public; any new private events count against the current month's bundle.

NEGATIVE:
7. Billing service is unreachable at the moment of private-event creation — event creation is blocked, user sees a clear error message, not a silent denial or an unlimited free pass.
8. An overage confirmation prompt that the user dismisses or lets time out (no response) defaults to not creating the event — the event is not created, the user's existing data is preserved.

SILENT FAILURE:
9. Usage count drifting out of sync with actual event count (e.g. billing counter decrements on event deletion but the deletion wasn't tracked, or counter increments on failed creation) — verify usage-counter logic is auditable against the actual event table, with a nightly reconciliation job that alerts on discrepancy.
10. A paid account that cancels mid-month — verify their events switch to read-only (or appropriate degraded state) at the end of the paid period, not immediately, and that the user is warned before cancellation about what happens to their private events.

**Verification Method:**
1) Free-tier test: create 10 public events on a free account, all succeed; attempt to create a private event, blocked with upgrade prompt. 2) Bundle test: paid account creates events up to the bundle limit, no overage; creates one past the limit, prompted for overage confirmation. 3) Billing-unavailable test: simulate billing service down, confirm private event creation is blocked with clear error. 4) Convert-to-private test: create a public event, convert to private, verify overage confirmation triggers if past bundle limit. 5) Counter-audit test: verify usage counter against actual event table, run reconciliation job, confirm no discrepancy. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired outcome. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**
Billing enforcement lives in the Worker at event-creation/visibility-change time (BUNDLE-PLANNER-CORE). Usage-count service must be highly available (not a single point of failure for event creation). Payment processor integration is out of scope — this spec covers enforcement points only.

**Open Questions:**
1. **Pricing-model conflict**: The older V2 Client/Planner Portal proposal priced planner access at a flat $50/plan/customer/instance (Module 7). This spec's bundle-plus-overage model is a different shape entirely. The debate team needs to pick one, not merge both.
2. Exact monthly base price, bundle size, and overage fee — need real Cloudflare usage-cost modeling once live.

**Required for Release:**
YES — P1 priority (billing enforcement is P1; the access-control model (free public / paid private) from [[SPEC:URS-PLAN-001]] is P0 and can launch with manual billing enforcement in V1.x if the automated billing service is deferred)

---

## Known Design Specs

### BUNDLE-PLANNER-CORE (Cloudflare Edge Architecture)

The backbone underlying [[SPEC:URS-PLAN-001]] through [[SPEC:URS-PLAN-004]], [[SPEC:URS-PLAN-006]], and [[SPEC:URS-PLAN-007]].

```
Customer / Planner phone
   │ (QR code or direct link)
   ▼
Cloudflare Pages ─── app shell, edge-cached ([[SPEC:URS-PLAN-007]])
   │
   ▼
Cloudflare Worker ── auth ([[SPEC:URS-PLAN-002]] tokens), billing checks ([[SPEC:URS-PLAN-008]]), routing
   │
   ▼  WebSocket
Durable Object (one per event) ── live layout state, presence, change log ([[SPEC:URS-PLAN-003]], [[SPEC:URS-PLAN-004]], [[SPEC:URS-PLAN-006]])
```

**Component responsibilities:**
- **Durable Objects**: one per event, holding canonical live state while in draft. A fork ([[SPEC:URS-PLAN-001]]) is a state snapshot copied into a new Durable Object under a new event ID.
- **Worker**: enforces every access-token check ([[SPEC:URS-PLAN-002]]), the 72-hour lock transition and override gate ([[SPEC:URS-PLAN-004]]), and billing/bundle checks ([[SPEC:URS-PLAN-008]]) before requests reach the Durable Object.
- **Pages + service worker**: serves the app shell from the edge and precaches it client-side for offline use ([[SPEC:URS-PLAN-007]]).

### AI Room Intelligence ([[SPEC:URS-PLAN-005]])

Two AI-dependent capture paths, both routed through an AI Gateway sitting in front of the model:
- **AI-guided measurement Q&A**: a conversational flow (not a static form) that asks the user targeted questions, feeding answers plus any photos into a vision-capable model to deduce room shape and floor area.
- **PDF/drawing deduction**: an uploaded PDF or drawing is parsed by a vision-capable model to extract room dimensions and layout; requires a scale-reference question (e.g. one known wall length) before the deduction can be trusted, and must reconcile against any independently provided measurements rather than silently preferring one source.
- **Model routing**: AI Gateway routes to a vision-capable model on OpenRouter (via gflip) or to Workers AI — gives caching, fallback, and cost visibility across whichever model actually handles a given request.
- **Clearance check**: a deterministic rule (not AI-driven) run against whatever room object either capture path (or the AR path) produces — keeps the safety-adjacent capacity math auditable and independent of model behavior.

### Storage & Sync
- **R2**: stores uploaded room photos and PDF/drawing files ([[SPEC:URS-PLAN-005]]), and any other user-uploaded media — zero egress fees make this cheap even at volume.
- **D1 / KV**: read-optimized copies of catalog data (table types, room presets) synced one-way from the canonical Postgres store on the N100 — fast edge reads without making Postgres the request path for every planner-app lookup.
- **Durable-Object-to-Postgres sync**: on lock or periodic autosave, the Worker pushes a snapshot of an event's Durable Object state back to Postgres on the N100, which remains the canonical system of record for anything downstream (invoicing, reporting, the rest of the holistic portal).

### Notification & Billing Integration
- **Staff notifications ([[SPEC:URS-PLAN-006]])**: routed through the existing N100 dashboard/notification path already in production use elsewhere in the stack — no new notification system needed.
- **Billing ([[SPEC:URS-PLAN-008]])**: enforcement point lives in the Worker at event-creation/visibility-change time; the actual payment processor is not yet selected and is out of scope for this spec.

---

## Cross-Cluster Dependencies

| This Spec | Depends On | Nature |
|-----------|-----------|--------|
| [[SPEC:URS-PLAN-005]] AR path | WebXR API (browser) | Platform capability, not code dependency |
| [[SPEC:URS-PLAN-005]] AI paths | AI Gateway on gflip | Production infrastructure |
| BUNDLE-PLANNER-CORE | Cloudflare Workers, Durable Objects, Pages | Platform |
| Storage & sync | R2, D1/KV, Postgres on N100 | Production infrastructure |
| Staff notifications | N100 dashboard | Existing system |
| Layout data for invoicing | Postgres sync → invoice generator | Downstream consumer |

---

## Conflict Register

1. **Pricing model ([[SPEC:URS-PLAN-008]])**: this spec's bundle-plus-overage model conflicts with the older V2 Client/Planner Portal's flat $50/plan/customer/instance (Module 7). Must be resolved in debate — do not merge both.
2. **Lock scope ([[SPEC:URS-PLAN-004]])**: whole-layout lock vs. food-service-fields-only lock. Spec recommends whole-layout for V1.x.
3. **Planner-removal access ([[SPEC:URS-PLAN-002]])**: does a removed planner's invited customers retain access? Two valid approaches — debate team decides.
4. **Rectangular table clearance rule ([[SPEC:URS-PLAN-005]])**: interim 72" edge-to-edge default is not a real rule for rectangular geometry — needs definition before V1.x ships.

---

## Implementation Sequence (Recommended)

**Phase 1 — Core (P0, ship first):**
[[SPEC:URS-PLAN-001]] (Fork model), [[SPEC:URS-PLAN-002]] (Access control), [[SPEC:URS-PLAN-003]] (Real-time editing), [[SPEC:URS-PLAN-007]] (Offline client) — these form the spine. Without these, the app isn't fundamentally usable. Ship with manual billing enforcement and manual lock management.

**Phase 2 — Intelligence (P0, ship next):**
[[SPEC:URS-PLAN-005]] (Room capture + AI) — the technological moat. Can ship as soon as the AI Gateway integration is ready.

**Phase 3 — Governance (P0/P1):**
[[SPEC:URS-PLAN-004]] (Lock workflow), [[SPEC:URS-PLAN-006]] (Change tracking + notifications) — operational rigor.

**Phase 4 — Monetization (P1):**
[[SPEC:URS-PLAN-008]] (Billing enforcement) — automated payments can follow manual billing for initial launch.