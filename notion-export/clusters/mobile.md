# Taza OS URS — MOBILE cluster
_Exported: 2026-09-19 21:35 | 6 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-MOB-001 — Staff mobile access requires passkey authentication
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: shopping/ops app requires a registered passkey — no passwords, a lost phone can't expose operational data.

**Atomic Requirement:**  
The staff mobile application shall require a registered passkey before exposing operational data or accepting updates.

**Functional Requirement Specification:**  
The staff mobile application shall require a registered WebAuthn passkey before any operational data is exposed or any update is accepted. No page shall render and no write shall be accepted without prior successful passkey authentication. Unregistered, revoked, or failed passkeys are denied unconditionally.

**Inputs:**  
WebAuthn passkey credential from the staff device; the credential registry on the backend.

**Outputs:**  
A valid session on the staff device that unlocks the mobile surface; denial and no-render on any auth failure.

**Trigger:**  
Any staff attempt to open the mobile application or submit a write.

**Invariants:**  
No operational content rendered before auth; passkey is the sole auth method (no password fallback); revoked credential never grants access.

**Failure Behavior:**  
Unregistered, revoked, or failed passkey → denied, no operational data rendered, no write accepted. No fallback to password/PIN on the mobile surface (passkey is the only auth method). Revoked credential cannot be re-used until explicitly re-registered by an admin.

**Failure Mode Addressed:**  
Operational data (shopping lists, event details, allergen flags) exposed on a lost or unattended phone; unauthorised writes entering the canonical backend from an unrecognised device.

**Acceptance Criteria:**  
Registered staff can authenticate; unregistered and revoked credentials are denied; no operational page renders before authentication.

**Verification Method:**  
Authentication, revocation, and unauthorized-access tests.

**Maintenance Requirements:**  
Keep the credential registry current as staff join/leave; verify revocation is effective within one login cycle; re-run auth tests after any dependency update to the WebAuthn library.

**Dependency Notes:**  
Passkey auth guards [[SPEC:PROD-05-V2]]/[[SPEC:PROD-05-V2]] (shopping) and any other mobile write path. Revocation updates must propagate before the next auth attempt. Ties to [[SPEC:SEC-001]] (authentication) and INFRA 21 (remote access hardening). Part of BUNDLE-STAFF-MOBILE. Parent SHOP 10.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Staff-mobile-access-requires-passkey-authentication-1f0d2531eb024acfa2cce902c9a1ff71_

---
## URS-MOB-002 — Staff mobile shopping view is vendor-grouped
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: one phone list sorted by store, with fridge/freezer items flagged to buy last — walk each store once, never double-buy.

**Atomic Requirement:**  
The staff mobile shopping view shall display the current shopping window grouped by preferred vendor from canonical shopping data.

**Functional Requirement Specification:**  
The staff mobile shopping view shall display the current shopping window grouped by preferred vendor, in frost-risk-first order within each vendor group, sourced from the canonical shopping plan ([[SPEC:PROD-05-V2]]). Every item in the current window appears exactly once under the correct vendor. Totals displayed by vendor and overall shall reconcile to the canonical shopping plan.

**Inputs:**  
Canonical shopping plan from [[SPEC:PROD-05-V2]] (aggregated items, preferred vendor assignments, frost-risk flags, quantities).

**Outputs:**  
A rendered vendor-grouped, frost-risk-first shopping list on the staff device with per-vendor and overall totals.

**Trigger:**  
Staff opens the shopping view (post auth); refreshes on canonical shopping-plan change events.

**Invariants:**  
Every current item appears exactly once; totals reconcile to the canonical plan; vendor grouping and frost-risk order are server-computed, not re-derived on the client.

**Failure Behavior:**  
Stale or unavailable shopping data → a visible staleness indicator rather than a silent wrong list. A missing vendor's items remain visible under 'unassigned' rather than being dropped.

**Failure Mode Addressed:**  
Staff shopping from a fragmented list (multiple sheets or tabs per item) and buying duplicate items or missing things because the list wasn't aggregated; shopping at the wrong store first because frost-risk items weren't surfaced early.

**Acceptance Criteria:**  
Every current item appears once under the correct vendor and totals reconcile to the canonical shopping plan.

**Verification Method:**  
UI/data reconciliation test.

**Maintenance Requirements:**  
Keep preferred-vendor assignments current as supplier relationships change; re-run reconciliation tests when [[SPEC:PROD-05-V2]]'s aggregation logic changes.

**Dependency Notes:**  
Reads from the canonical shopping plan generated by [[SPEC:PROD-05-V2]] (aggregated, vendor-grouped, frost-risk-first). Vendor grouping and frost-risk ordering computed server-side ([[SPEC:PROD-05-V2]] SQL/aggregation); mobile surface renders, does not re-compute. Writes back via SHOP 8 (one-source-of-truth). [[SPEC:URS-KIT-105]] (substitution capture at check-off) applies to this view. Part of BUNDLE-STAFF-MOBILE. Parent SHOP 10.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Staff-mobile-shopping-view-is-vendor-grouped-78412c6d30444b079ad5a0c1200c4066_

---
## URS-MOB-003 — Staff mobile view provides current event awareness
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: one phone screen shows today's events, allergen flags, departure status, and active issues — no surprises en route to a venue.

**Atomic Requirement:**  
The staff mobile situational view shall show today’s events, allergens, departure status, and active operational issues from canonical sources.

**Functional Requirement Specification:**  
The staff mobile situational view shall show today's events (name, time, guest count, venue), current allergen flags, departure status, and any active operational exceptions, all sourced from the canonical event and exception records. Any stale or unavailable signal shall be visibly identified — never shown as current without a fresh read.

**Inputs:**  
Canonical event records (today); active allergen flags; departure status; active exception records ([[SPEC:PROD-23]]).

**Outputs:**  
A rendered situational summary (events/allergens/departure/exceptions) with staleness indicators on the staff device.

**Trigger:**  
Staff opens the situational view (post auth); refreshes on canonical event or exception change events.

**Invariants:**  
All displayed values sourced from canonical records (no mobile-local state); stale or unavailable data is always visibly flagged.

**Failure Behavior:**  
Stale or unavailable data → visibly identified (timestamp + degraded indicator); never shown as current. Unknown/missing exception state → explicit 'not available' rather than silent green.

**Failure Mode Addressed:**  
Staff leaving for a venue without knowing about an allergen flag, a departure-time change, or an active exception — the mobile surface is often the last thing staff check before heading out.

**Acceptance Criteria:**  
Displayed values match current event and exception records and visibly identify stale or unavailable data.

**Verification Method:**  
Source-to-screen reconciliation test.

**Maintenance Requirements:**  
Keep the allergen and exception source alignment current; re-run staleness tests after any signal-source change.

**Dependency Notes:**  
Reads today's events, allergen flags, departure status, and active exceptions from the canonical event and exception records. Staleness detection aligned with HEALTH 9 (never default-healthy). Active exceptions routed through EXCEPT 1 (Exception Router). Part of BUNDLE-STAFF-MOBILE. Parent SHOP 10.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Staff-mobile-view-provides-current-event-awareness-367a39b7339540308ce911562cb34277_

---
## URS-MOB-004 — Staff mobile updates preserve one source of truth
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every phone check-off/update immediately updates the same canonical list everyone sees — one source of truth, no separate reconciliation.

**Atomic Requirement:**  
Mobile check-offs, substitutions, and field updates shall write through canonical backend services and shall not maintain an independent planning ledger.

**Functional Requirement Specification:**  
Mobile check-offs, substitutions, and field updates shall write directly through the canonical backend services, producing one canonical write and one correlated event per accepted action. The mobile client shall not maintain an independent planning ledger; no mobile-only record shall become authoritative. Write idempotency is enforced at the backend.

**Inputs:**  
Staff action on the mobile surface (check-off, substitution, field update); the backend canonical service for that data type.

**Outputs:**  
One canonical write + one correlated event per accepted mobile action.

**Trigger:**  
Any staff check-off, substitution, or field update on the mobile surface.

**Invariants:**  
Every accepted mobile action produces exactly one canonical write; no mobile-local record is authoritative; idempotency enforced server-side.

**Failure Behavior:**  
A write rejected by the backend → the mobile action reverts ([[SPEC:URS-MOB-005]]), the mobile-local state is discarded, and no orphan mobile record becomes authoritative. A duplicate write attempt is idempotent (backend enforces).

**Failure Mode Addressed:**  
Two sources of truth diverging — a mobile-only shadow ledger accumulating check-offs that never make it to the canonical backend, causing the kitchen and the shopper to be looking at different lists.

**Acceptance Criteria:**  
NORMAL:
1. A mobile check-off/substitution/field update writes directly through canonical backend services, producing exactly one canonical write and one correlated event.

EDGE:
2. A rapid double-tap on the same action from the mobile client produces exactly one write, not two (idempotency at the backend, not just client-side debounce).
3. Mobile app backgrounded mid-write, then resumed — the write either completes or clearly fails/retries, never left in an ambiguous half-sent state the user can't see.

NEGATIVE:
4. Any attempt to read or act on a mobile-only cached record as if it were authoritative is rejected — the mobile client has no independent ledger that could diverge from canonical truth.

SILENT FAILURE:
5. This is the P0 data-integrity invariant the whole SHOP surface rests on (per its own Rationale) — the specific risk is a network drop between the mobile client's optimistic UI update and the backend's actual write. Verify: if the backend write fails after the UI already showed success, the UI is corrected/reverted, never left showing a false-positive success.
6. Backend idempotency must hold even across app restarts/reinstalls (not just within one session) — verify a retried write from a fresh app instance doesn't duplicate.

**Verification Method:**  
1) Idempotency test: rapid duplicate submission, and duplicate submission from a fresh app instance/session, confirm single canonical write both times. 2) Fault-injection test: kill network mid-write after optimistic UI update, confirm the client correctly reverts/flags the failure rather than leaving a false-positive success displayed. 3) Backgrounding test: background and resume the app mid-write, confirm a clean completion or a visible retry/failure state. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Verify write-through for every new action type added to the mobile surface; keep idempotency keys consistent with the backend close-contract pattern ([[SPEC:PROD-38]]).

**Dependency Notes:**  
Writes route through the canonical shopping/task/event backend ([[SPEC:PROD-05-V2]], [[SPEC:PROD-19]], EXCEPT 2 event bus). The mobile surface is a thin client over the canonical services — it does not own any data. Idempotency enforced at the backend per [[SPEC:PROD-38]]/CLOSE 11 patterns. Part of BUNDLE-STAFF-MOBILE. Parent SHOP 10.

**Rationale:**  
V1.x P0 — highest priority in this cluster; the data-integrity invariant the whole surface rests on.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Staff-mobile-updates-preserve-one-source-of-truth-1e2256fb57b04b2788e744bf3624dba1_

---
## URS-MOB-005 — Mobile optimistic updates expose and recover conflicts
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: check-offs feel instant, but a failed save is shown clearly — never looks done while the kitchen still shows it open.

**Atomic Requirement:**  
The mobile client shall show an optimistic local update immediately, then confirm, revert, or visibly conflict-route it based on the canonical write result.

**Functional Requirement Specification:**  
The mobile client shall display an optimistic local update immediately on staff action, then resolve it based on the canonical write result: confirm (write accepted, no duplication), revert visibly (write rejected), or surface a conflict for staff resolution (concurrent update detected). A network-loss before confirmation shall leave a visible, retryable pending state rather than a silent commit or silent loss.

**Inputs:**  
Staff action (triggers optimistic update); canonical write result (confirm / reject / conflict); network state.

**Outputs:**  
A confirmed, reverted, conflicted, or retryable visible state on the staff device for every action attempted.

**Trigger:**  
Any staff action on the mobile surface (initiates optimistic update); canonical write result received (resolves it).

**Invariants:**  
Optimistic state is always resolved (confirmed/reverted/conflicted), never left permanently pending; a rejected write always reverts visible state; network loss produces a retryable state, not a committed state.

**Failure Behavior:**  
Canonical write rejected → local optimistic state reverts to pre-action value with a clear visible indicator (not a silent snap-back). Network loss before confirmation → action flagged as retryable, not lost and not silently committed. A conflict (another client updated the same record) → visibly surfaced to the staff member, not silently resolved or overwritten.

**Failure Mode Addressed:**  
A check-off that appears done on the shopper's phone but silently failed to write — the crew never knew the item wasn't actually marked off; or a conflict overwrite where two staff touched the same item and one change was silently lost.

**Acceptance Criteria:**  
Successful write confirms without duplication; rejected write reverts or flags; network loss leaves a visible retryable state.

**Verification Method:**  
Latency, conflict, and offline-transition tests.

**Maintenance Requirements:**  
Verify the three resolution paths (confirm, revert, conflict) after any write-path change; test offline-to-online transition; keep conflict-routing logic aligned with [[SPEC:PROD-23]].

**Dependency Notes:**  
The optimistic layer sits on top of SHOP 8 (write-through to canonical). Confirmation/revert driven by the canonical write result. Conflict routing connects to EXCEPT 1 (Exception Router). Part of BUNDLE-STAFF-MOBILE. Parent SHOP 10.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Mobile-optimistic-updates-expose-and-recover-conflicts-19105017aad4464380b7121753306ac6_

---
## URS-MOB-PKG — Staff Mobile Application Surface
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need staff to have everything they need on their phones — a shopping list that matches what the kitchen sees, a pre-departure check of what's happening today, and real-time updates that flow back instantly — so the person in the store and the person in the kitchen are always looking at the same picture.

**Atomic Requirement:**  
The system shall provide a passkey-authenticated mobile surface that displays vendor-grouped shopping and current event situational awareness, accepts write-through updates with no independent mobile ledger, and handles optimistic update resolution visibly.

**Functional Requirement Specification:**  
The staff mobile application surface shall provide (1) passkey-only authentication (SHOP 5), (2) a vendor-grouped frost-risk-first shopping view from the canonical plan (SHOP 6), (3) a situational view of today's events, allergens, departure status, and active exceptions (SHOP 7), (4) write-through updates that produce one canonical record with no independent mobile ledger (SHOP 8), and (5) optimistic-update resolution (confirm/revert/conflict/retryable) visible to staff (SHOP 9). Implemented as SHOP 2 (shopping staff web app).

**Intent / User Need:**  
Put the right operational information in the right person's hand at the right moment — whether they're in a store, driving to a venue, or on-site — with writes that keep the whole operation in sync and failures that are visible, not silent.

**Failure Mode Addressed:**  
Staff operating from fragmented, out-of-date information — a paper shopping list that diverges from the kitchen's list, missed allergen flags before departure, undetected write failures that look successful on the phone.

**Out of Scope:**  
The shopping computation logic itself ([[SPEC:PROD-05-V2]]); label printing ([[SPEC:PROD-13]]/URS-LABEL); the desktop kanban/display surfaces ([[SPEC:PROD-03]]/04). This package is the mobile client surface only.

**Acceptance Criteria:**  
Registered staff authenticate in one tap ([[SPEC:URS-MOB-001]]); shopping view shows vendor-grouped, frost-risk-first items reconciling to the canonical plan ([[SPEC:URS-MOB-002]]); situational view shows current events/allergens/departure/exceptions with stale-data indicators ([[SPEC:URS-MOB-003]]); every check-off/substitution writes through to canonical with one record and no mobile shadow ledger ([[SPEC:URS-MOB-004]]); optimistic updates resolve clearly as confirmed/reverted/conflicted/retryable ([[SPEC:URS-MOB-005]]).

**Verification Method:**  
End-to-end integration: auth, shopping view reconciliation, situational-view freshness, write-through from mobile to kitchen board, optimistic-update resolution under latency and offline conditions.

**Dependency Notes:**  
Implemented by SHOP 2.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Staff-Mobile-Application-Surface-b58f88bd4ce54680bcf42aaa1ee030c3_
