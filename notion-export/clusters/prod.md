# Taza OS URS — PROD cluster
_Exported: 2026-09-19 21:35 | 35 rows_
_Source: Notion Master URS & Specification Registry_

---
## PROD-01 — Task Engine Core (PostgreSQL Task Chains)
**Status:** Built (unverified live) | **Priority:**  | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every task the kitchen runs is tracked in one real system with clear status and clear dependencies — not scattered across notebooks, memory, or someone's head.

**Functional Requirement Specification:**  
The system shall maintain a PostgreSQL task-chain model where each task record carries: task type, status, assigned crew, due time, parent task FK (single FK — linear chains only in V1, multi-dependency junction table deferred to V2), and a depends_on pointer. Task state transitions are deterministic and LLM-free (D-025). DDL is deployed in the tazaos DB; Phase 4 wiring to watcher/kanban outputs is the outstanding build item.

**Inputs:**  
Task rows (description, assigned_surface, depends_on FK); status updates from kanban/forms

**Outputs:**  
Dependent tasks flipped LOCKED→PENDING with unlocked_at; recursive unlock down chain (max depth 5 v1)

**Trigger:**  
Task status UPDATE to COMPLETED fires AFTER UPDATE trigger; recursive chain unlock

**Acceptance Criteria:**
NORMAL: Parent task reaches COMPLETED → dependent task flips LOCKED→PENDING with unlocked_at set, recursively down the chain.
EDGE: Chain deeper than 5 → unlock halts at depth 5; deeper tasks flagged, never silently dropped.
EDGE: Task with no parent → closes normally, no unlock cascade.
NEGATIVE: Any state transition performed by an LLM → BLOCKED (D-025: transitions are deterministic and LLM-free).
SILENT-FAILURE: Parent COMPLETED but child still LOCKED after trigger → caught by orphan audit query.
CHALLENGE: 100-task chain, kill the DB mid-unlock → restart resumes cleanly, no half-unlocked state.

**Verification Method:**
1. [AUTO] Chain test: 5-deep chain, complete root → all 5 flip with unlocked_at. Evidence: psql result.
2. [AUTO] Depth-limit: 8-deep chain → unlock stops at 5, remainder flagged. Evidence: psql.
3. [AUTO] Orphan audit: query finds zero LOCKED tasks whose parent is COMPLETED. Evidence: query + result.
4. [AUTO] Crash test: kill DB mid-unlock, restart → no half-unlocked state. Evidence: log + psql.
5. [NICK] Live: Mom's Table card close unlocks the dependent card on the touchscreen. Evidence: observation log + screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Task-Engine-Core-PostgreSQL-Task-Chains-3b5e152fc19981cca975c34e0c9d5f3b_

---
## PROD-02 — LKL Completion Gate + PARTIAL_COMPLETE Auto-Spawn
**Status:** Approved | **Priority:** P0 | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need the moment a task is finished to always capture where the item went and to never quietly lose work that was only partly done — if someone completes 19 of 24, the system should record the 19, capture why they stopped, and automatically create the follow-up for the remaining 5, with the numbers always adding up.

**Functional Requirement Specification:**  
At task close, the system shall (1) enforce the LKL completion gate — no location-changing task reaches Done without a valid bin (CLOSE 18) — and (2) on partial completion (qty_completed < qty_target), record PARTIAL_COMPLETE, capture the limiting factor, and auto-spawn two tasks: an URGENT prep task for the missing input and a BLOCKED residual task for the remaining output, with completed+residual reconciling to the original quantity and idempotency on replay. Parent order completion % updates accordingly.

**Intent / User Need:**  
Make the close moment do two non-negotiable jobs: capture where the item went, and never let unfinished quantity vanish — the two ways a task close silently corrupts operational truth.

**Inputs:**  
Quantity produced, bin ID [Zone]-[Unit]-[Shelf] validated vs master (e.g. WIC-1-3), missing elements list

**Outputs:**  
Input manifest injected into dependent task cards (item/qty needed/qty avail/bin); RESIDUAL + PREP tasks auto-spawned on partial; staleness flags

**Trigger:**  
Task close attempt on physical-output tasks; PARTIAL_COMPLETE status set

**Failure Mode Addressed:**  
Lost location truth at close, and silent loss of unfinished work when a task is only partially completed (marked 'done' loses the remainder).

**Acceptance Criteria:**  
NORMAL:
1. Close at qty_completed = qty_target with valid LKL bin → closes cleanly, no auto-spawn, parent completion % updates correctly.
2. Close with qty_completed < qty_target and valid LKL bin → status PARTIAL_COMPLETE, limiting factor captured, exactly one URGENT prep task + one BLOCKED residual task spawned, completed+residual = original target exactly.

EDGE:
3. qty_completed = 0 still requires a valid LKL bin if location-changing; residual task spawned equals the full original qty, not skipped.
4. Retry of the same partial-close event (network hiccup, duplicate submit) creates no second URGENT/BLOCKED pair — idempotent.
5. Chained partial completions (partial → partial → partial on the same lineage) keep the running completed+residual reconciliation exact at every step, not just the first.

NEGATIVE:
6. Location-changing task with qty_completed < qty_target and no LKL bin is blocked entirely by the LKL gate — no auto-spawn on top of a rejected close.
7. qty_completed > qty_target (overshoot/bad data) is rejected with a specific validation error — never silently accepted or clamped.

SILENT FAILURE:
8. If the URGENT+BLOCKED auto-spawn partially succeeds (one task created, one fails), the close must not report as successful — caller gets an error.
9. If parent order completion % fails to update after a valid partial close, this must surface as an error, never leave a silently stale/wrong % visible to Sandra/Nick.

**Verification Method:**  
1) Unit tests: full-completion path, zero-progress partial path, overshoot rejection, missing-LKL rejection. 2) Integration test: multi-step partial-completion chain (3+ partials) verifying exact running reconciliation at each step. 3) Idempotency test: duplicate partial-close submission produces no duplicate spawned tasks. 4) Fault-injection test: force one of the two auto-spawned tasks to fail creation, assert the overall close reports as failed, not partially successful. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
Anchors CLOSE 22 and partial-complete behavior.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/LKL-Completion-Gate-PARTIAL_COMPLETE-Auto-Spawn-3b5e152fc19981e7a623d2d0a5d2e91a_

---
## PROD-03 — Mom's Table Kanban UI (Kitchen Task Boards)
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: a kitchen task board ("Mom's Table") that is a card game — makes the right way the fun way, teaches the Taza standard through play, carries our brand, feels calm under pressure — while reliably tracking every task through not-started / in-progress / done.

**Functional Requirement Specification:**  
Card-based kanban on MT1/MT2/z33 implementing: three-state flow (KANBAN 3), accountable close capture (CLOSE 11), per-card operational signals (KANBAN 4), Short Stop (CLOSE 33), commit-then-emit downstream events (CLOSE 12). The card-game mechanic is the mechanism itself, not a skin: brand/visual language (gold #c7ae59, diamond-filigree, LB monogram) and gamification (first-encounter fish animation 2s logged w/ timestamp+crew ID, question-awards-both-parties, compliance streak badge at 10, quality scoring 40% food quality / 40% food safety / 20% appearance) are first-class requirements per D-[[SPEC:KIT-001]]. Any rebuild preserves the game framing + brand language.

**Inputs:**  
Task rows from PostgreSQL; SSE pushes; staff card actions (game-night design language per CONFIRMED homage page)

**Outputs:**  
Card state changes → task status updates → [[SPEC:PROD-01]] trigger; card-closing captures LKL data (inventory = side effect of the game)

**Trigger:**  
Staff interaction on MT1 (192.168.2.104 east) / MT2 (192.168.2.108 west); SSE state updates

**Failure Behavior:**  
Addresses: a sterile enterprise task board crew ignore; loss of culture/brand transmission; event-day cognitive overload (the North-Star metric this design reduces).

**Acceptance Criteria:**  
NORMAL:
1. Card-based kanban runs on MT1/MT2/z33 with all listed child behaviors (KANBAN 3, CLOSE 11, KANBAN 4, CLOSE 33, CLOSE 12) working together as one coherent surface.
2. Brand/visual language (gold #c7ae59, diamond-filigree, LB monogram) and gamification elements (first-encounter animation, question-award, streak badge, quality scoring) are present and functioning, not treated as optional polish.

EDGE:
3. A rebuild or redesign of any single piece (e.g. a UI refresh) preserves the game framing and brand language per D-[[SPEC:KIT-001]] — verify this constraint is actually checked in any future redesign, not just true at initial build.

NEGATIVE:
4. Any of the 5 referenced child behaviors failing its own acceptance criteria means this package-level row cannot be considered passing — this row's own AC is not separable from its children's.

SILENT FAILURE:
5. The gamification/brand elements being quietly stripped out during a future 'simplification' pass (common failure mode — engineers deprioritizing 'decoration' under time pressure) would violate D-[[SPEC:KIT-001]]'s explicit first-class-requirement status — verify there's a way to catch this in review, e.g. a checklist item tied to D-[[SPEC:KIT-001]] for any future PR touching this surface.
6. Quality scoring (40% food quality / 40% food safety / 20% appearance) computing but never actually surfacing/affecting anything downstream would make it decorative math instead of a real mechanic — verify it has a real, tested downstream effect.

**Verification Method:**  
1) Integration test: full kanban surface exercised end-to-end across all 5 child behaviors on real MT1/MT2/z33 hardware. 2) Brand/gamification checklist: verify each D-[[SPEC:KIT-001]] element (animation, streak badge, quality scoring, visual language) is present and functioning, not just visually similar. 3) Downstream-effect test: confirm quality scoring actually feeds a real downstream consumer (leaderboard, review flag), not just computed and discarded. 4) Regression gate: document a required D-[[SPEC:KIT-001]] checklist item for any future PR touching this surface. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
CONFORMS TO [[SPEC:PROD-38]]. See [[SPEC:PROD-05-V2]] for a related dead-ternary bug note.

**Open Questions:**  
Event-driven wiring to watcher/AI outputs unevidenced (Phase 4 unaudited).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Mom-s-Table-Kanban-UI-Kitchen-Task-Boards-3b5e152fc199818fbdcad003313ec4be_

---
## PROD-04 — SSE Push Fabric + Kitchen Display System
**Status:** In Development | **Priority:**  | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: wall TVs showing NOW / NEXT / WHERE / WATCH, updating on their own in real time (<4s), so crew stop interrupting each other to ask. The room itself keeps them calm, disciplined, and on-brand.

**Functional Requirement Specification:**  
Drive wall display fleet (2×75" TCL + 55" Insignia + z33) with pushed state, <4s lag, no human action. Each screen renders its assigned per-screen mode (EVENT / PREP / DEAD DAY / OVERNIGHT) and role. Uncleared/cluttered board is an INTENTIONAL visual stress signal forcing disciplined task closeout — the display is a self-correcting calming mechanism, not just an information radiator. Dark/gold Taza brand + visible Mom's Table game state. Any redesign preserves both ambient-calm and brand/culture functions.

**Inputs:**  
PostgreSQL state changes; [[SPEC:W15]] BEO data; allergen flags; van/crew assignments

**Outputs:**  
Reactive SLA 4s to all surfaces; morning SLA 07:12am (systemd timer 07:05); green/amber/red stress logic (red = allergen or critical failure only)

**Trigger:**  
Any task/event/packing state change → webhook → Python SQL traversal → SSE push

**Failure Behavior:**  
Addresses: crew interrupting each other to ask 'where is X / what's next'; stale or blank wall displays; inference overload from active lookups (D-INF-001).

**Acceptance Criteria:**  
All wall displays update from pushed state with <4s lag; each TV shows its correct per-screen mode (EVENT/PREP/DEAD DAY/OVERNIGHT); completed items persist with visual suppression ([[SPEC:SSB-003]]); CRITICAL allergen updates reach displays fast; TV→content mapping matches the intended role split (repoint pass needed — see Notes); voice gating (display-persistence.js) wired to the live frontends.

**Open Questions:**  
TCL West=prep, TCL East=situational, Insignia=van loadout mode assignment mismatched vs 07-14 audit — needs repoint. Voice gated by display-persistence.js (built+tested, NOT wired to live TV — see DISPLAY 26). square-catalog-sync/square-menu-sync/taza-git-sync were FAILED on N100 — verify status, feeds [[SPEC:PROD-06]]/[[SPEC:SW-011]].

**Rationale:**  
D-INF-001: reduce inference demand, don't speed it up.

**Verification Method:**
1. [AUTO] Lag test: fire a state change → display updates <4s. Evidence: timestamp log.
2. [AUTO] Mode test: each TV renders its correct mode (EVENT/PREP/DEAD DAY/OVERNIGHT). Evidence: screenshot of each surface.
3. [NICK] Stress-signal: leave board cluttered → intentional visual stress signal renders. Evidence: screenshot.
4. [NICK] Allergen: CRITICAL allergen flag → red state reaches displays fast. Evidence: screenshot + observation log.
5. [AUTO] Voice-gate: display-persistence.js wired to live frontends. Evidence: code-search + grep.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/SSE-Push-Fabric-Kitchen-Display-System-3b5e152fc19981a980d4c537cf83175d_

---
## PROD-05 — Shopping Web App (Staff App, Passkey Auth)
**Status:** Spec Drafted | **Priority:**  | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: staff can update the shopping list from a phone, authenticated simply with no password, writing straight back to the one shared list — the original V1 version of this need, before frost-risk handling and vendor-grouping were added.

**Functional Requirement Specification:**  
The system shall provide a passkey-authenticated staff PWA on mobile that displays the shopping list and writes updates back to the canonical NocoDB backend using optimistic UI updates.

**Inputs:**  
Shopping lists generated from deposit trigger ([[SPEC:PROD-06]]); live watcher data; staff interactions

**Outputs:**  
Direct PostgreSQL writes <50ms deterministic; checked-state visible <100ms optimistic w/ rollback; morning lists on all surfaces by 07:12am

**Trigger:**  
Staff check/mark shopping items; watcher-generated list updates; 07:05am morning push

**Dependency Notes:**  
V1 spec, retained as historical record only — not in active use. Superseded by [[SPEC:PROD-05-V2]] ([[SPEC:PROD-05-V2]]).

**Rationale:**  
Kept for reference: [[SPEC:PROD-05-V2]] added the locked aggregation rule, Task Verb Library integration, frost-risk-first ordering, and vendor grouping, none of which this V1 design accounted for.

**Acceptance Criteria:**  
Deferred — Superseded by [[SPEC:PROD-05-V2]] — historical record only.

**Verification Method:**  
Deferred — Superseded by [[SPEC:PROD-05-V2]] — historical record only.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Shopping-Web-App-Staff-App-Passkey-Auth-3b5e152fc199814687c3d549dcdeed72_

---
## PROD-05-V2 — Shopping Web App v2 (Aggregated, Vendor-Grouped, Frost-Risk-First)
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: shopping for multiple events gets combined into one smart list — grouped by vendor, frost-risk items handled last so nothing thaws in the car — instead of shopping trip by trip and guessing.

**Functional Requirement Specification:**  
The system shall aggregate shopping needs across all events in the planning window, group items by preferred vendor (frost-risk items pulled last within each vendor group to minimise temperature exposure in-car), apply Task Verb Library governance (Buy / Pull / FLAG) so every line is a real task-engine task, enforce safety-stock thresholds, capture substitutions at check-off ([[SPEC:URS-KIT-105]]), and write all updates through the canonical backend with optimistic-update + conflict-revert on the mobile client. CAUTION: do not use an earlier draft sketch as a code reference — its frost-risk ternary is a no-op bug (both branches return 'Buy').

**Inputs:**  
Paid-deposit events in shopping window; [[SPEC:PROD-09]] item_components BOM; ingredient master (vendor, frost_risk, safety_stock_qty - schema incomplete, see Open Items)

**Outputs:**  
Buy/Pull tasks written to PostgreSQL tasks table, vendor-tagged; FLAG tasks for any quantity the system can't determine with confidence; vendor-grouped view in staff app

**Trigger:**  
Deposit paid (same trigger as [[SPEC:PROD-06]]) OR scheduled nightly aggregation run OR manual staff refresh

**Dependency Notes:**  
Supersedes-in-detail [[SPEC:PROD-05-V2]] v1 (kept, historical). Wired into [[SPEC:PROD-19]]'s task engine, not a parallel model.

**Rationale:**  
Rewritten 2026-08-07 per RAG Operations Content discovery to incorporate the locked aggregation rule, Task Verb Library, and Task Governance Rules that v1 never incorporated.

**Acceptance Criteria:**
NORMAL: Deposit paid → aggregated shopping list across all events in the window, grouped by vendor.
EDGE: Frost-risk item → pulled last within its vendor group.
EDGE: Item quantity below safety-stock threshold → FLAG task generated, not silently re-ordered.
NEGATIVE: Substitution at check-off → captured in the record, never silently dropped.
SILENT-FAILURE: Item whose required quantity can't be determined → FLAG, never Buy (no guessed quantity).
CHALLENGE: Two events share ingredients → one aggregated line, not two parallel buys.

**Verification Method:**
1. [AUTO] Aggregation: 2 overlapping events with shared ingredient → one merged line. Evidence: psql + screenshot.
2. [AUTO] Frost-risk: frost-risk item sorts last within vendor group. Evidence: list-order log.
3. [AUTO] Safety-stock: below-threshold item → FLAG task exists. Evidence: psql.
4. [NICK] Staff app: Sandra checks off an item on phone → optimistic write-back, conflict-revert on clash. Evidence: screenshot + observation log.
5. [AUTO] Substitution: substitute captured at check-off. Evidence: log.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Shopping-Web-App-v2-Aggregated-Vendor-Grouped-Frost-Risk-First-3b5e152fc19981c4b4fbcf891f33b061_

---
## PROD-06 — Square Watcher Service (Deposit → Tasks Trigger)
**Status:** Approved | **Priority:**  | **Release:** V1.0

**Domain:**  
Production Core

**Functional Requirement Specification:**  
The system shall watch for Square payment events (deposit received, payment completed, refund) via email-then-fetch (D1/D16: the dedicated inbox parses Square payment emails, then one targeted Square API call confirms the event), write to the payment_events ledger in PostgreSQL (D4/D5), update invoice status, and trigger the creation of event-prep task chains on confirmed deposit. Webhook is a V1.1 extension point, not the V1.0 path. Wix sync scope stripped (Wix retired — Square-only). Supersedes W8 Wix Payments Watcher.

**Inputs:**  
Square payment webhooks, invoice updates, catalog data

**Outputs:**  
Shopping lists + task chains written to PostgreSQL; visible in Mom's Table within SLA (<2 min target)

**Trigger:**  
Trigger A: deposit paid → shopping list + task chain scheduling. Trigger B: invoice update → recalculate. Weekly mirror cron via systemd timer

**Acceptance Criteria:**
NORMAL: Deposit payment email parsed (D16) → event status CONFIRMED → task-chain generation + shopping list triggered.
EDGE: Refund email → CONFIRMED rescinded; re-payment re-triggers, idempotent on invoice ID + Message-ID.
NEGATIVE: Unparseable payment email → exceptions_queue + Sandra manual confirm; never auto-confirms.
SILENT-FAILURE: Payment email missed by inbox poll → weekly mirror cron catches it.
CHALLENGE: Two payments for the same invoice in quick succession → one task chain, no duplicate.

**Verification Method:**
1. [AUTO] Confirm flow: deposit email → event CONFIRMED + task chain rows exist. Evidence: psql.
2. [AUTO] Refund drill: refund email → CONFIRMED rescinded; re-pay → exactly one re-trigger. Evidence: log.
3. [AUTO] Idempotency: duplicate payment event → one chain. Evidence: count + log.
4. [AUTO] Miss-recovery: force a missed poll → weekly mirror catches it. Evidence: log.
5. [NICK] Live: real deposit → task chain visible in Mom's Table <2 min. Evidence: screenshot + observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Square-Watcher-Service-Deposit-Tasks-Trigger-3b5e152fc19981e38bf3fa74f1153106_

---
## PROD-07 — Invoice Drafting Dashboard (Brain-Dump → Confidence Pre-Fill)
**Status:** Approved | **Priority:** P2 | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
As Sandra, I need to just brain-dump event details by voice or text and get a fully pre-filled invoice back, so I'm not manually retyping information I already gave a customer on the phone.

**Functional Requirement Specification:**  
The system shall provide an invoice-drafting interface where Sandra's voice/text brain-dump is processed by AI (via INFERENCE 1, endpoint env-var per D-061, composite confidence per D-060) into a structured pre-fill of all invoice fields, with per-field confidence display. Inference runs as a non-modal background worker so Sandra continues working during the draft. Fields flagged for pre-hand-off check: tables_required, linens_required, setup_type; kitchen_exit_time is computed, not Sandra-entered (D3). Output format per [[SPEC:CX-001]]..[[SPEC:CX-007]].

**Inputs:**  
Sandra brain-dump; RAG: menu items, service templates, customer history, logistics rules; Tier 1 catalog attributes

**Outputs:**  
Pre-filled invoice form w/ confidence per field; deltas + reasoning stored as RAG signal (confidence climbs Low→Med→High); Square invoice draft; background inference, 10-15s async on cores 2-3

**Trigger:**  
Sandra initiates invoice draft; Nick review via SMS link; each delta opens voice-reasoning box

**Rationale:**  
THE SPINE of the system per architecture doc.

**Acceptance Criteria:**
NORMAL: Sandra's voice/text brain-dump → structured pre-fill of invoice fields, per-field confidence label.
EDGE: Low-confidence field → flagged for pre-hand-off check, never silently accepted.
NEGATIVE: AI computes kitchen_exit_time → BLOCKED (computed deterministically, not AI; D3).
SILENT-FAILURE: Field populated from a record that doesn't exist → confidence audit catches phantom pull.
CHALLENGE: Empty brain-dump → form still loads, all fields blank with honest confidence.

**Verification Method:**
1. [NICK] Live: Sandra dictates a real brain-dump → watch fields pre-fill with confidence labels. Evidence: screenshot + observation log.
2. [AUTO] Confidence audit: every Pulled label traces to a real PostgreSQL row. Evidence: query.
3. [AUTO] Arithmetic guard: kitchen_exit_time computed by deterministic function, LLM only narrates. Evidence: code-search.
4. [NICK] Delta review: Nick reviews AI draft vs Sandra's edits. Evidence: before/after screenshots.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Invoice-Drafting-Dashboard-Brain-Dump-Confidence-Pre-Fill-3b5e152fc1998132a179f97c8e61a783_

---
## PROD-08 — Square CX Invoice Blocks + Order Attributes
**Status:** Approved | **Priority:** P2 | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need the invoice a customer receives to read like an event plan that shows we understood their event, not a bare price list — the story sells the trust, the price list doesn't.

**Functional Requirement Specification:**  
The system shall generate the seven CX invoice blocks (EVENT DETAILS, VENUE & LOGISTICS, SETUP SPECIFICATION, WHY context lines, food line items, four Square Order Custom Attributes, and deposit logic) via AI writing directly to Square line items. The invoice is the primary brand asset — the customer sees an event plan, not a price list. No logistics data lives in the Square catalog; AI computes and writes to line items directly. Deposit is a fixed dollar amount (not percent), locked at first publish.

**Inputs:**  
Confirmed invoice data + CRM decision history (WHY layer)

**Outputs:**  
Three $0 line items before food: EVENT DETAILS / VENUE & LOGISTICS / SETUP SPECIFICATION; Order attrs: setup_type, tables_count, linens_tier, venue_arrival_time (D3); WHY context inline (e.g. 'Based on your May 20 call…')

**Trigger:**  
Confirmed invoice ready for customer-facing generation

**Acceptance Criteria:**
NORMAL: All 7 CX invoice blocks generated — EVENT DETAILS, VENUE & LOGISTICS, SETUP SPECIFICATION, WHY lines, food line items, 4 Order Custom Attributes, deposit logic.
EDGE: deposit_basis_cents locked at first publish; later invoice edits never move it (D19).
NEGATIVE: Logistics data written to the Square catalog → BLOCKED (all logistics in line items only).
SILENT-FAILURE: A block silently missing from a published invoice → completeness check catches it.
CHALLENGE: Invoice published, then edited 3× → deposit figure unchanged throughout.

**Verification Method:**
1. [NICK] Live: generate a real invoice → all 7 blocks present, reads as a trust document. Evidence: screenshot.
2. [AUTO] Deposit lock: edit invoice after publish → deposit_basis_cents unchanged. Evidence: psql.
3. [AUTO] Catalog separation: zero logistics data in Square catalog. Evidence: code-search.
4. [NICK] Brand review: Nick confirms invoice reads premium, not commodity. Evidence: screenshot + observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Square-CX-Invoice-Blocks-Order-Attributes-3b5e152fc199812cb795c45f20ea7109_

---
## PROD-09 — Catalog Operational Tables (Tier 2 BOM/Packing/Equipment)
**Status:** Approved | **Priority:**  | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: the system has real, structured data about how each dish packs, what it's made of, what equipment it needs, and its SOP — not just a name and price — so invoices, packing, and scheduling can be generated correctly instead of guessed.

**Functional Requirement Specification:**  
The system shall build and populate the four Tier-2 PostgreSQL operational tables (item_packing_profiles, item_components/BOM, item_equipment, procedure_link) per the Catalog Operations Intelligence Design Spec. These tables feed [[SPEC:PROD-07]] RAG lookups (invoice pre-fill confidence) and will power the Tier-3 deterministic packing solver/backward scheduler ([[SPEC:PROD-16-V2]]) once built. The LLM retrieves parameters from these tables; it never computes pan geometry or hold-time arithmetic itself. V1.0 launch milestone (schema ref V2-FEAT-005).

**Inputs:**  
Item definitions; GN Pan footprints/depths/fill qty per service mode; component explosions; equipment occupancy

**Outputs:**  
Packing profiles, prep sub-task explosion from BOM, equipment contention detection, SOP wiring per item

**Trigger:**  
Referenced at invoice RAG lookup time + task chain generation; maintained by kitchen team via NocoDB

**Acceptance Criteria:**
NORMAL: item_components BOM explodes a composite item into its correct component tasks.
EDGE: Item with no BOM entry → flagged for enrichment, never exploded wrong.
NEGATIVE: LLM computes pan geometry or BOM arithmetic → BLOCKED (deterministic lookup only).
SILENT-FAILURE: BOM missing a component → reconciliation check catches the gap.
CHALLENGE: Mediterranean Grill Package → correct prep tree generated from BOM.

**Verification Method:**
1. [AUTO] BOM explosion: composite item → correct component tree. Evidence: psql result.
2. [AUTO] Missing-entry: item without BOM → flagged. Evidence: log.
3. [AUTO] Geometry guard: no LLM path computes pan geometry. Evidence: code-search.
4. [NICK] Live: Sandra verifies BOM for one package matches reality. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Catalog-Operational-Tables-Tier-2-BOM-Packing-Equipment-3b5e152fc199815abf2ec26a94cb89e4_

---
## PROD-10 — Inference Concurrency Infra (Confidence Routing + CPU Pinning)
**Status:** Built (unverified live) | **Priority:** P3 | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: voice commands stay fast even while a bigger AI task (like drafting an invoice) is running in the background — one doesn't freeze the other.

**Functional Requirement Specification:**  
The system shall route all AI inference calls through a single abstraction layer (env-var endpoint, per D-061) so the inference backend — cloud API or local model — can be swapped without a code change. V1.0 ships with cloud AI (cheapest capable/tested model per task) as the default backend. The architecture shall support 'plugging in' a local model later, without redesign, once that model is tested and proven to deliver materially better excellence²×speed/dollar than the current cloud default for that task. Local inference hosting is a designed-for capability, not a V1.0 requirement.

**Inputs:**  
LLM outputs w/ logprobs; threshold 0.87

**Outputs:**  
≥0.87 commit to PostgreSQL; <0.87 escalate to AI API, result written back. Nightly background-inference window 10pm-7am, 77k token budget, 06:50 safety cutoff → API escalation

**Trigger:**  
Any daytime LLM output scored by avg token probability

**Open Questions:**  
RESOLVED 2026-09-02 (Nick): local-vs-cloud is not an open architecture question — cloud-first for V1.0, pluggable-for-local by design. The underlying goal is great inference cheaply where appropriate; local hosting is aspirational, adopted only once it clears the excellence²×speed/dollar bar above the cloud default.

**Rationale:**  
Local AI hosting capability is an aspirational goal, not a V1.0 requirement — the actual goal is great AI inference cheaply where appropriate. Decided 2026-09-02 (Nick).

**Acceptance Criteria:**
NORMAL: LLM output avg token probability ≥0.87 → commit to PostgreSQL; <0.87 → escalate to AI API.
EDGE: Nightly window 10pm–7am, 77k token budget, 06:50 safety cutoff → escalation after cutoff.
NEGATIVE: A local model claimed faster/cheaper without clearing the excellence²×speed/dollar bar → not adopted.
SILENT-FAILURE: Escalation result not written back → audit catches missing write.
CHALLENGE: Big invoice draft running while a voice command arrives → voice stays fast (concurrency preserved).

**Verification Method:**
1. [AUTO] Threshold: outputs at 0.86 and 0.88 → escalate vs commit correctly. Evidence: log.
2. [AUTO] Budget: nightly batch respects 77k token budget + 06:50 cutoff. Evidence: log + count.
3. [AUTO] Backend swap: change env-var endpoint → no code change required. Evidence: code-search + config diff.
4. [NICK] Live: voice command during invoice draft → no freeze. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inference-Concurrency-Infra-Confidence-Routing-CPU-Pinning-3b5e152fc199814f8f91e59a03db84c2_

---
## PROD-11 — Emergency Print Path (Power-Fail Ops Truth)
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
As the kitchen, when we lose power I need the system to hand us the essential operating truth on paper automatically — so an outage never stops the event, and nobody has to remember to go print anything while the lights are off.

**Functional Requirement Specification:**  
On power loss, the system shall automatically print the current essential operating packet (remaining packout, open tasks, allergen flags, crew contacts, event/gig blocks, resolving QR codes) to the owned thermal printer, with no dependency on screens, network, or human action, and the UPS shall hold the N100 + printer long enough to complete the job.

**Inputs:**  
Open tasks + packout state from PostgreSQL

**Outputs:**  
Thermal receipt (80mm ≈ 42 chars/line): remaining pack/do items, checkbox per van/category, auto-cut. Paper becomes the operational control surface

**Trigger:**  
Power failure detected by UPS

**Failure Mode Addressed:**  
Operational blackout on power loss; reliance on screens/network that are themselves down during the outage; the lp/lpr mis-scaling trap (2h wasted — use StarTSPImage).

**Acceptance Criteria:**  
NORMAL:
1. On power loss, the essential operating packet (packout, tasks, allergens, contacts, event/gig blocks, resolving QR codes) prints automatically with no screen/network/human dependency, and the UPS holds long enough to complete the job.

EDGE:
2. A power loss occurring mid-print doesn't produce a half-printed, misleading packet — verify the UPS runtime margin is enough to complete a print reliably, not just barely.
3. A power loss during an active event (high data volume — many open tasks, multiple event blocks) still completes the print within the UPS runtime window, not just tested against a light/idle dataset.

NEGATIVE:
4. Printer itself being the point of failure (out of paper, jammed) at the moment of an outage is a real risk this can't software-fix — flag as requiring a physical paper-stock/jam-check as part of the verification, not just a code test.

SILENT FAILURE:
5. QR codes on the printed packet resolving to broken/unreachable endpoints (previously flagged as a ~67% failure rate issue elsewhere in the registry) would mean the packet looks complete but its most useful feature doesn't work — verify the resolving-QR-code claim specifically, with a real scan test, not just that a QR image renders.
6. This is functionally the same behavior as HEALTH 7 ([[SPEC:URS-HEALTH-003]]) — verify both rows describe the same actual implementation consistently, not two independently-drifting descriptions of one real print path.

**Verification Method:**  
1) Real power-down test: pull power during an active-event-like dataset (multiple open tasks/events), confirm the full packet prints correctly within the UPS window. 2) QR-scan test: physically scan each QR code on a real printed packet, confirm it resolves correctly (not the previously-flagged ~67% failure). 3) Physical-readiness check: confirm paper stock and printer jam-free state as part of the test, not assumed. 4) Consistency check against HEALTH 7 ([[SPEC:URS-HEALTH-003]]) to confirm no drift between the two descriptions of this path. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
Depends on INFRA 9 (UPS) + LABEL 2 (printer, StarTSPImage direct-USB). Groups HEALTH 7.

**Open Questions:**  
D-057 phased screen-shed SOP + UPS sizing pending z33 draw measurement (EPR-005/006/007); confirm QR-endpoint resolution.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Emergency-Print-Path-Power-Fail-Ops-Truth-3b5e152fc19981a3908fc8b294d6a8af_

---
## PROD-12 — Staff PIN Auth + Experience-Gated Photo (Kitchen Accountability)
**Status:** Approved | **Priority:** P1 | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need every kitchen close tied to a real person via PIN, and I need photo proof from crew who haven't yet proven they do it right — using Sandra's own work as the standard everyone is measured against — so quality doesn't quietly slip when I'm not watching.

**Functional Requirement Specification:**  
The system shall require a 4-digit staff PIN before any task close on the kitchen kanban board, and shall require a close-out photo from staff whose experience level is below the Expert threshold (D-027/D-028). Sandra is hardcoded as the Expert reference standard; her photos constitute the training library baseline. Photo is mandatory for low-experience staff — this is a V1 launch requirement, not deferred. The only permitted photo override is a documented technical camera failure. Photos accumulate as a training-asset library; 4-panel training cards are a V2 feature.

**Inputs:**  
PIN entry at task close; camera photo (conditionally required); experience score vs .env thresholds (EXP_WINDOW_DAYS=28, EXP_RECENCY_THRESHOLD=3, EXP_TOTAL_THRESHOLD=6)

**Outputs:**  
Every task close signed by named staff; error attribution instant (task→PIN→name); error_count threshold auto-flags retraining; quality-tagged thumbnail library

**Trigger:**  
Any task completion form submit; error logged by Sandra/Edgar/Nick against a past task

**Acceptance Criteria:**
NORMAL: Crew member enters PIN → authenticated; photo captured and gated by experience level.
EDGE: 3 wrong PINs → lockout with a clear message, not a silent rejection.
NEGATIVE: Photo of a task without valid PIN → rejected.
SILENT-FAILURE: A task close recorded with no crew_pin_hash → audit catches the null.
CHALLENGE: New crew member (no experience) → photo required; veteran → optional.

**Verification Method:**
1. [NICK] Live: crew member closes a card with PIN + photo on the touchscreen. Evidence: screenshot + observation log.
2. [AUTO] Lockout: 3 wrong PINs → lockout. Evidence: log.
3. [AUTO] PIN audit: zero closes with null crew_pin_hash. Evidence: query.
4. [AUTO] Photo-gate: experience < threshold → photo mandatory. Evidence: code + log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Staff-PIN-Auth-Experience-Gated-Photo-Kitchen-Accountability-3b5e152fc199818a97e4c4d695ec7a04_

---
## PROD-13 — Zebra On-Demand Crew Labels (Type A, Kanban-Tied)
**Status:** Approved | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
As the kitchen, I need the system to produce a self-describing label on every container we prep or portion — printed automatically when crew close the right card, confirmed before printing, with a QR that scans every time and resolves to the full batch record — so nothing leaves the prep area anonymous and we can always trace a container back to its source.

**Functional Requirement Specification:**  
The on-demand crew-label subsystem shall produce Type A internal pedigree labels (V1.x) triggered by qualifying kanban card closes, subject to crew confirmation (CLOSE 9/LABEL 7). Each label shall carry the required Type A fields (LABEL 3) with a threshold-only QR (LABEL 5) that resolves to the canonical lot record (LABEL 4). The print path is exclusively raw ZPL over Ethernet TCP port 9100 (LABEL 6). Every print attempt is logged and reprints are distinguishable (LABEL 7). No LLM involvement (D-025). Type B customer labels are V2.0 (URS-LABEL-002).

**Inputs:**  
Task row (item, batch, qty, use-by) + LKL bin + crew name from PIN; on-demand request from any kanban card

**Outputs:**  
Printed 4x1 label: item, batch, qty, bin, crew, packed, use-by + QR → tazacateringevents.com/label/{batch}; label_log rows

**Trigger:**  
Crew taps Label button on any kanban card (any state); auto-propose at card close

**Failure Mode Addressed:**  
Mystery containers (no label or incomplete label), phantom prints (no confirmation), lost jobs (offline printer), QR codes that don't scan (dithering at 203 DPI), and broken print paths (USB port now physically occupied by AKiTiO).

**Acceptance Criteria:**  
A kanban close triggers a label proposal ([[SPEC:URS-INV-004]]); crew confirms and a Type A label ([[SPEC:URS-LABEL-001]]) prints over Ethernet TCP 9100 ([[SPEC:URS-LABEL-005]]); the attempt is logged ([[SPEC:URS-LABEL-006]]); the QR resolves to the correct canonical lot ([[SPEC:URS-LABEL-003]]); the bitmap uses threshold-only conversion ([[SPEC:URS-LABEL-004]]) and scans first try on the Zebra 203-DPI printer.

**Verification Method:**  
Print path proven 2026-07-14 (scanned first try).

**External Dependencies:**  
Zebra TLP 2844-Z; Ethernet TCP 9100; 4x1 label stock; resin ribbon.

**Open Questions:**  
QR endpoint reachability confirm post 07-07 fix (was ~67% failure).

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Zebra-On-Demand-Crew-Labels-Type-A-Kanban-Tied-3b5e152fc199817ebab3c2ae512fa7c5_

---
## PROD-14 — Square Nested Modifier Decision Tree (Upsell + Allergen Routing)
**Status:** Idea | **Priority:**  | **Release:** 

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: allergen and special-handling info is captured as clean structured choices, not free-text notes staff have to interpret — and the ordering experience reveals complexity gradually instead of overwhelming the customer with every option at once.

**Functional Requirement Specification:**  
The system shall leverage Square's 3-level nested/conditional modifier reveal to implement (1) allergen/special-handling as a structured decision tree (replacing free-text notes, flowing into task queue flags with no staff interpretation), (2) upsell via micro-commitment (each tier reveals the next, avoiding the full-option wall), (3) a clean customer-facing catalog card that unlocks complexity on demand, and (4) a structured sequential framework for custom-quote conversations. Hypothesis — direction confirmed by Nick, not yet built.

**Inputs:**  
Customer catalog selections; allergen self-declaration; upsell tier choices

**Outputs:**  
Structured allergen flags → feeds [[SPEC:PROD-02]] task queue automatically (no staff interpretation step); upsell selections → [[SPEC:PROD-07]] invoice draft; could integrate with allergen display logic already on [[SPEC:PROD-04]] KDS

**Trigger:**  
Customer selects an item with a nested modifier set during Wix/Square ordering flow

**Acceptance Criteria:**  
Deferred — Idea stage — no AC/VM until promoted to spec.

**Verification Method:**  
Deferred — Idea stage — no AC/VM until promoted to spec.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Square-Nested-Modifier-Decision-Tree-Upsell-Allergen-Routing-3b5e152fc199817b8087cec7cb00439a_

---
## PROD-15 — Cooking & Recipes Spec (Sandra Interview-Derived)
**Status:** In Development (partly deployed — KB design on n100) | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**Inputs:**  
Sandra interview responses (shop/prep/cook/pack/present per dish), structured via the Sandra-Claude interview process

**Outputs:**  
Per-dish packing profile, BOM/component explosion, equipment occupancy, SOP text -> [[SPEC:PROD-09]] catalog tables; Taza Method distinctions -> [[SPEC:PROD-03]] gamification content

**Trigger:**  
Sandra-Claude interview session(s), ad hoc

**Dependency Notes:**  
Output feeds [[SPEC:CAT-001]] catalog Tier 2 directly per-dish. Invoice RAG ([[SPEC:PROD-07]]) and task chain generation ([[SPEC:PROD-19]]) both depend on this for accuracy. Source: 📖 RAG — Operations Content db (recipe-type entries) — interview with Sandra in progress: 38 draft / 32 locked / 10 pending_approval / 2 superseded (82 total).

**Open Questions:**  
This row has no FRS — needs real FRS text once enough of the recipe interview (in progress) is locked.

**Rationale:**  
This is the deterministic recipe backbone the system currently lacks — no dish-level ground truth exists yet.

**Acceptance Criteria:**  
NORMAL: every active menu item has a locked recipe/method record covering portion, prep method, cook temp, and BOM components ([[SPEC:CAT-003]]).
EDGE: a recipe Sandra has not verified stays draft/pending_approval — never locked.
NEGATIVE: a BOM explosion runs against a draft recipe → flagged, never silently trusted.
SILENT-FAILURE: an active menu item with no recipe record at all → caught by completeness scan.
CHALLENGE: the Mediterranean Grill package explodes to its component tasks from locked recipes only.

**Verification Method:**  
1. [AUTO] Coverage: query % of active menu items with a locked recipe record; target >90% before V1 launch. Evidence: query.
2. [AUTO] Gate: BOM explosion refuses draft recipes. Evidence: test log.
3. [AUTO] Completeness: zero active menu items with no recipe record. Evidence: query.
4. [NICK] Live: Sandra locks a recipe during an interview session → it shows locked. Evidence: observation log.
NOTE: current state — 3 dishes seeded in the game-design KB (not 85%); 12 open items pending Sandra's interview (02-taza-rules.md §8); framework not yet migrated to live tazaos (cooking_rules = 0 rows).

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Cooking-Recipes-Spec-Sandra-Interview-Derived-3b5e152fc19981be88dddac7b6d648fd_

---
## PROD-16 — Packing & Carrier Logistics (Pan Geometry, 3-Zone Vehicle Load)
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: correct packing rules (pan sizes, hot/cold zones) applied consistently — never guessed by an LLM.

**Functional Requirement Specification:**  
The system shall encode the locked packing and carrier logistics rules from the RAG Operations Content: GN pan co-habitation geometry (2×half / 3×third / 6×sixth per 1/1 slot; halves and thirds cannot be cleanly mixed), 3-zone vehicle load (hot/cold/ambient), and per-item service-mode packing profiles. V1 = rule-set lookup; the deterministic constraint solver ([[SPEC:PROD-16-V2]]) is the V1.x upgrade. LLM never computes pan geometry — it retrieves parameters from the Tier-2 tables (CATALOG 3/CATALOG 5) and narrates results.

**Inputs:**  
Item quantity + service mode (from [[SPEC:PROD-09]] item_packing_profiles); event's composed-salad/charcuterie flags

**Outputs:**  
Correct pan size selected per item; correct carrier assigned; correct load position in 3-zone pattern; two-task trigger for presentation-ready items

**Trigger:**  
Task reaches PACK stage in the chain (post-cook, pre-load)

**Dependency Notes:**  
Pan Tetris packing-efficiency optimization remains draft/unextracted — candidate for [[SPEC:PROD-18]] knowledge graph.

**Acceptance Criteria:**
NORMAL: Packing plan maps items to pans and a 3-zone vehicle load.
EDGE: Item with no pan footprint → flagged for enrichment, never guessed.
NEGATIVE: LLM computes pan geometry → BLOCKED (deterministic lookup).
SILENT-FAILURE: Item missing from van load → departure-blocking manifest catches it.
CHALLENGE: Full event with mixed hot/cold/frozen → 3-zone load separates correctly.

**Verification Method:**
1. [AUTO] Pan mapping: items → correct pan footprints. Evidence: psql.
2. [AUTO] Completeness: manifest vs invoice items → 100%. Evidence: query.
3. [NICK] Live: Edgar loads van against manifest → nothing forgotten. Evidence: observation log + photo.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Packing-Carrier-Logistics-Pan-Geometry-3-Zone-Vehicle-Load-3b5e152fc19981459350fb7fc4b22141_

---
## PROD-16-V2 — Deterministic Packing Solver + Backward Event Scheduler (Full Spec)
**Status:** Approved | **Priority:** P1 | **Release:** V1.x

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: the system tells crew exactly how to load the van and by when, computed, not eyeballed — nothing sits in the danger zone.

**Functional Requirement Specification:**  
The system shall implement a three-layer deterministic packing solver: (1) thermal partition (hot/cold/ambient per carrier), (2) footprint tiling (GN pan geometry, integer-only), (3) vertical stacking by pan_depth_in until carrier height is consumed. A backward event scheduler derives latest_prep_finish = service_time − display_wait − transit − pack, enforcing TCS danger-zone hold times as hard constraints (never soft preferences) per CATALOG 7. Output: a named carrier manifest per event. LLM narrates; the solver computes — unconditionally. PULL-FORWARD CANDIDATE for V1 launch if core elements finish on time.

**Inputs:**  
[[SPEC:PROD-09]] item_packing_profiles (pan footprint/depth/fill qty) + [[SPEC:PROD-16]] pan geometry/3-zone vehicle load rules + event service_time/transit_time

**Outputs:**  
Named carrier manifests -> [[SPEC:PROD-02]] task generation (Pack tasks); item lifecycle stages (prep/pack/transit/setup/display) each with duration + hold-clock effect

**Trigger:**  
Event confirmed / production planning stage, before task chain generation

**Dependency Notes:**  
Full-spec version of placeholder PACK 1 (kept separate, no-overwrite rule — see [[SPEC:PROD-05-V2]]/[[SPEC:PROD-05-V2]]). [[SPEC:CAT-001]] anticipated this as [[SPEC:PROD-16-V2]].

**Acceptance Criteria:**
NORMAL: Backward schedule from service_start → pack_start → kitchen_exit, all deterministic.
EDGE: TCS item → danger-zone exposure treated as HARD constraint, not soft preference.
NEGATIVE: LLM reasons about hold-time math → BLOCKED (AI formats, deterministic computes).
SILENT-FAILURE: Item with missing hold time → flagged low confidence, routes to review.
CHALLENGE: 3 events same day → three schedules, zero cross-contamination, all deterministic.

**Verification Method:**
1. [AUTO] Math audit: kitchen_exit = crew_arrival − drive_time − pack_buffer for 5 events. Evidence: computed vs stored.
2. [AUTO] TCS test: TCS item schedule respects danger-zone window. Evidence: schedule + log.
3. [AUTO] Missing-data: item missing hold time → flagged, not guessed. Evidence: flag + review queue.
4. [NICK] Live: Nick reviews one generated schedule against reality. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Deterministic-Packing-Solver-Backward-Event-Scheduler-Full-Spec-3b5e152fc1998177972df154c219d33a_

---
## PROD-17 — Staffing Model & Scheduling (Guest-Count Interpolation, Role Counts)
**Status:** Spec Drafted | **Priority:**  | **Release:** V1.0

**Domain:**  
Production Core

**Functional Requirement Specification:**  
The system shall compute staffing role counts from guest count via a nonlinear interpolation curve (not a linear ratio) encoding the ~4.5× crew efficiency gain between 80 and 1,000 guests. Role counts are locked by service type. Two open HIGH/MED flags block completeness (buffet role counts, HD+passing counts) — system FLAGs rather than guesses these per task governance. Source: locked RAG Operations Content entries (Nick-authored).

**Inputs:**  
Guest count, service type, event type; historical staffing outcomes (none yet — first 24-40 real events needed per the DOE analysis referenced in KB)

**Outputs:**  
Operational + Scheduled staff counts; role assignments by service type; arrival/lead-time; feeds [[SPEC:PROD-07]] invoice dashboard (labor cost) and [[SPEC:PROD-06]] task scheduling (crew availability)

**Trigger:**  
Deposit paid (same trigger as [[SPEC:PROD-06]]) OR quote-stage estimate for pricing purposes

**Acceptance Criteria:**
NORMAL: Guest count → role counts via deterministic interpolation.
EDGE: Count at an interpolation boundary → correct bucket.
NEGATIVE: LLM invents a role count → BLOCKED (deterministic only).
SILENT-FAILURE: Staffing row missing for a confirmed event → completeness check catches it.
CHALLENGE: 150-guest wedding → role counts match Nick's manual estimate.

**Verification Method:**
1. [AUTO] Interpolation: counts at boundaries → correct buckets. Evidence: psql.
2. [AUTO] Completeness: every confirmed event has a staffing row. Evidence: query.
3. [NICK] Live: Nick compares generated staffing to his own estimate for one event. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Staffing-Model-Scheduling-Guest-Count-Interpolation-Role-Counts-3b5e152fc19981cb9305c6d92506de78_

---
## PROD-18 — Business Logic Knowledge Graph (Temporal, Conditional, Self-Improving)
**Status:** Idea | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**Functional Requirement Specification:**  
The system shall maintain a temporal, conditional business-logic knowledge graph where facts are scored by confidence and decay over time. The graph handles standardised-vs-semi-custom conditionality (e.g. 'if guest count > 150 AND outdoor, THEN extra equipment') that a static lookup table cannot represent. Confidence mechanism mirrors D-060 (composite signal, same mechanism as INFERENCE 1 applied to facts). Formalises the MemPalace 4-layer pattern and Reservoir Computing framing already logged (2026-06-18/20). Requires a dedicated design session before any build.

**Inputs:**  
Locked rules (Founding Decisions, RAG Operations Content), Sandra's evolving recipe/method corrections, crew corrections, [[SPEC:PROD-10]] confidence signal (shared mechanism)

**Outputs:**  
Feeds [[SPEC:PROD-09]] Tier 2 tables (proposed: materialized view of a graph subset); feeds [[SPEC:PROD-07]] RAG lookups; feeds [[SPEC:PROD-16]] Pan Tetris as first real use case

**Trigger:**  
Not yet triggered — design-stage only

**Open Questions:**  
RECON NEEDED: some elements already populated directly in Postgres — reconcile against spec before finalizing Design Spec.

**Rationale:**  
Direct response to Nick's framing that the classifier needs a knowledge graph, not a static lookup table; formalizes prior design work Nick recalled as "always been a core component."

**Acceptance Criteria:**  
Deferred — Idea stage — no AC/VM until promoted to spec.

**Verification Method:**  
Deferred — Idea stage — no AC/VM until promoted to spec.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Business-Logic-Knowledge-Graph-Temporal-Conditional-Self-Improving-3b5e152fc1998158badad362f18a1479_

---
## PROD-19 — Structured Task-Close Capture (Equipment, Allergen, Van Load, Portion)
**Status:** Approved | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: equipment cleaning, allergen receiving, van-load departure, and prep-portion counts all get captured automatically as part of closing the card that already does that work — not as separate manual bookkeeping steps crew have to remember.

**Functional Requirement Specification:**  
The system shall capture four close-time data types as side effects of normal kanban card close, all conforming to [[SPEC:PROD-38]] (TaskCloseEvent): equipment cleaning (close_kind=EQUIPMENT_CLEANING, requires equipment_id + cleaning_checklist_passed), allergen receiving (close_kind=ALLERGEN_RECEIVING, sets allergen_flag), van load departure (close_kind=VAN_LOAD, requires full checklist resolution), and prep portion count + size (close_kind=PORTION_CAPTURE, requires qty + unit). Same gate pattern as [[SPEC:PROD-02]]'s LKL bin-capture, applied to four different data types.

**Inputs:**  
Task close event; equipment ID ([[SPEC:URS-KIT-101]]); ingredient allergen_type ([[SPEC:URS-KIT-102]]); BEO requirements list ([[SPEC:URS-KIT-103]]); portion count/size entered by crew ([[SPEC:URS-KIT-104]])

**Outputs:**  
Equipment audit trail (health inspection ready); allergen_flags rows feeding [[SPEC:PROD-04]]'s persistent banner; van load manifest (departure-blocking if incomplete); portion counts feeding [[SPEC:PROD-04]] LKL display

**Trigger:**  
Task close attempt on: equipment-cleaning card, allergen-item receiving, van-load card, or prep-task card

**Dependency Notes:**  
CONFORMS TO [[SPEC:PROD-38]] — fixed a routing gap that had silently dropped equipment-cleaning/allergen-receiving kinds. [[SPEC:URS-KIT-105]]/SHOP 4 folded into [[SPEC:PROD-05-V2]] instead (shopping-flow specific).

**Acceptance Criteria:**
NORMAL: Card close with close_kind → correct side-effect (EQUIPMENT_CLEANING audit, ALLERGEN_RECEIVING flag, VAN_LOAD manifest, PORTION_CAPTURE count).
EDGE: VAN_LOAD close with incomplete checklist → departure-blocked.
NEGATIVE: Wrong handler for a kind (e.g. allergen close hits equipment handler) → BLOCKED by 7×7 routing matrix.
SILENT-FAILURE: PORTION_CAPTURE close without qty/unit → rejected.
CHALLENGE: All four kinds closed in one day → each routes to its own handler, zero cross-contamination.

**Verification Method:**
1. [NICK] Live: crew closes an equipment-cleaning card → audit trail health-inspection-ready. Evidence: screenshot.
2. [AUTO] Routing matrix: 7×7 cross-contamination check → zero wrong-handler routes. Evidence: code-search + test.
3. [NICK] Allergen: allergen flag → persistent banner on displays. Evidence: screenshot.
4. [AUTO] Gate: PORTION_CAPTURE without qty/unit → rejected. Evidence: log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Structured-Task-Close-Capture-Equipment-Allergen-Van-Load-Portion-3b5e152fc19981aa81eacebaae3a40b5_

---
## PROD-20 — System Event Bus (Cross-Module Nervous System)
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every module talks through one shared event system, not direct calls to each other, so nothing gets missed or bypassed.

**Functional Requirement Specification:**  
The system shall provide a central event bus (emit() / emit_failure()) backed by an append-only system_events table in PostgreSQL. Every cross-module state change — task close, LKL write, inventory transaction, exception — is published through this bus. Consumers ([[SPEC:PROD-22]] audit log, EXCEPT 1 exception router, INFERENCE 12 cache router, EXCEPT 3 notifier, DISPLAY 1 displays) subscribe to topics. No direct inter-module calls bypass the bus.

**Inputs:**  
Every PROD-XX write module (task close, invoice ready, allergen flag, service failure)

**Outputs:**  
system_events rows -> [[SPEC:PROD-22]] audit log, [[SPEC:PROD-23]] exception router, [[SPEC:PROD-25]] notifier, [[SPEC:PROD-04]] dashboard state (all subscribe)

**Trigger:**  
Any workflow module completing a state-changing action

**Failure Mode Addressed:**  
Every module was implicitly assuming some 'something tells the rest of the system this happened' mechanism existed. It didn't. Without this, [[SPEC:PROD-22]]/23/24/25 and the dashboard have no way to know a state change occurred except polling.

**Acceptance Criteria:**  
Any module can call emit() with a topic and payload; system_events row is written; [[SPEC:PROD-22]]/23/25 subscribers receive it within the SLA their own spec states, without the emitting module knowing who's listening.

**Rationale:**  
Foundational — every consumer spec implicitly assumed some trigger mechanism; this is it.

**Verification Method:**
1. [AUTO] Publish: emit() → system_events row + subscribers receive within their own spec SLA. Evidence: psql + log.
2. [AUTO] Isolation: emitting module has no knowledge of listeners. Evidence: code-search.
3. [AUTO] Append-only: no update/delete path on system_events. Evidence: schema check.
4. [NICK] Live: task close → wall displays update without any polling. Evidence: observation log.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/System-Event-Bus-Cross-Module-Nervous-System-3b5e152fc19981bb82a6fddfd8ab8eb8_

---
## PROD-21 — Inbox Promotion (Raw Input Staging + Validation)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: raw incoming data (webhooks, leads) gets checked before becoming real records — bad or ambiguous input gets flagged, not silently written in wrong.

**Functional Requirement Specification:**  
The system shall stage all raw external inputs (Square webhooks, Gmail leads) into append-only inbox tables before any canonical write. A promotion step validates and transforms staged rows; invalid or ambiguous inputs are routed to the Exceptions Queue (D-006) rather than silently dropped or written as-is. Square-only scope for V1 (Wix retired). Implements D-005 and D-006.

**Inputs:**  
Raw Square invoice/payment webhooks, voice notes, customer comms landing in staging tables

**Outputs:**  
Promoted canonical records -> [[SPEC:W1]]/[[SPEC:W2]] lead capture, [[SPEC:W6]] CRM nightly, [[SPEC:PROD-07]] invoice prefill; invalid rows -> [[SPEC:PROD-23]] exceptions queue; [[SPEC:PROD-22]] audit log

**Trigger:**  
New row lands in any raw staging/inbox table

**Failure Mode Addressed:**  
Raw Square/voice/comms input reaching canonical tables unvalidated — one bad webhook payload corrupts a customer record or invoice with no trace of where the bad data came from.

**Acceptance Criteria:**  
A malformed or incomplete raw row never reaches a canonical table — it either promotes cleanly or lands in [[SPEC:PROD-23]]'s exceptions_queue with the specific validation failure attached, never silently dropped or silently accepted.

**Dependency Notes:**  
Wix retirement per D-062; supersedes [[SPEC:W7]]-SHOP/W8-SHOP.

**Verification Method:**
1. [AUTO] Validation: malformed input → flagged, not promoted. Evidence: log.
2. [AUTO] Append-only staging: raw input never edited in place. Evidence: schema.
3. [NICK] Live: malformed Wix email → appears in review queue, not as a Lead. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inbox-Promotion-Raw-Input-Staging-Validation-3b5e152fc19981ce8aa4d9c3a8860ff0_

---
## PROD-22 — Audit Log (Append-Only Write History)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need a complete, tamper-proof record of every change made to the system's data — who did what and when — so I can trust and investigate what happened if something goes wrong.

**Functional Requirement Specification:**  
The system shall maintain an append-only audit log in PostgreSQL capturing every write across all operational tables: who (crew/module), what (table + old/new values), when (timestamp), and the originating correlation ID. No write to a canonical table succeeds without a corresponding audit record. Implements D-004, D-019, D-021. Target inference-demand composition per D-INF-001: 65% deterministic / 25% KB retrieval / 8% small model / 2% T3 / <1% AI API.

**Inputs:**  
[[SPEC:PROD-20]] event bus; every canonical write across all PROD-XX modules

**Outputs:**  
audit_log rows -> [[SPEC:PROD-04]] dashboard state, health monitoring, [[SPEC:W6]] nightly brief (change-history context)

**Trigger:**  
Any canonical table write, human or AI-assisted

**Failure Mode Addressed:**  
"Who changed this and when" has no answer today for most writes — makes disputes, debugging, and AI-write accountability impossible to reconstruct after the fact.

**Acceptance Criteria:**  
Every write to a canonical table (human or AI-originated) produces an audit row with before/after values, actor, and timestamp; audit rows are never editable or deletable by any write path, only appendable.

**Dependency Notes:**  
See INFERENCE 12 for the V1 local-vs-cloud AI pivot recon flag on this D-INF-001 target.

**Rationale:**  
Cross-cutting reliability layer with zero prior registry coverage — every PROD-XX spec that writes to Postgres implicitly needs this and none of them specced it.

**Verification Method:**
1. [AUTO] Every-write audit: sample 50 writes → 50 audit rows. Evidence: query + count.
2. [AUTO] Immutability: no update/delete path on audit_log. Evidence: schema check.
3. [AUTO] Correlation: audit rows carry correlation_id across a chain. Evidence: query.
4. [NICK] Live: Nick investigates a disputed change using the audit log. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Audit-Log-Append-Only-Write-History-3b5e152fc1998174834dce9e4ad06bfa_

---
## PROD-23 — Exception Router (Gentle Failure Handling)
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: when something fails, it gets logged and flagged automatically — never silently dropped or guessed past.

**Functional Requirement Specification:**  
The system shall route processing failures from any module to the exception router (EXCEPT 1), which (1) persists the error and full event context before notifying (persist-before-notify per EXCEPT 5), (2) classifies severity (informational/warning/critical), and (3) dispatches to EXCEPT 3 (notifier) for warning/critical. Implements the Task System Governance Rule 'FLAG rather than guess' (D-006) as a real routing mechanism rather than a text convention.

**Inputs:**  
[[SPEC:PROD-20]] event bus; validation failures from [[SPEC:PROD-21]] inbox promoter and any other workflow

**Outputs:**  
exceptions_queue rows -> [[SPEC:PROD-25]] notifier (alerts owner), [[SPEC:PROD-04]] dashboard state, [[SPEC:PROD-22]] audit log

**Trigger:**  
Any workflow hitting a validation/API/parse/timeout/missing-data failure

**Failure Mode Addressed:**  
The system's own "FLAG, don't guess" governance rule had no actual mechanism behind it — a module hitting an ambiguous case had nowhere defined to send it.

**Acceptance Criteria:**  
Any module that can't confidently complete an action routes it here instead of guessing or silently failing; [[SPEC:PROD-25]] fires an alert for WARNING/CRITICAL severity; the exception is visible in one place, not scattered across module-specific error logs.

**Verification Method:**
1. [AUTO] Routing: each exception class → its documented handler. Evidence: log.
2. [AUTO] Persist-before-notify: exception persisted before any notify attempt. Evidence: code-search.
3. [NICK] Live: kill a dependency → gentle failure, SMS to Sandra, no crash. Evidence: observation log.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Exception-Router-Gentle-Failure-Handling-3b5e152fc199818cb4eee2773d4034e4_

---
## PROD-24 — Cache/Precompute Router (Inference Demand Reduction, INV-005 Target)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: don't burn AI time/cost on a question the system can already answer from its own data — check the database and cache first.

**Functional Requirement Specification:**  
The system shall intercept any inference request and check the canonical DB and KB cache before dispatching to an AI model. Target demand composition (D-INF-001 / INV-005): 65% deterministic DB lookup, 25% KB retrieval, 8% small AI model, 2% T3 (AI API), <1% AI API escalation. Cache hits return without touching the inference stack. The cache is warmed on every state-change event.

**Inputs:**  
[[SPEC:PROD-20]] event bus (rebuild triggers); [[SPEC:PROD-02]] LKL state; [[SPEC:PROD-01]] task engine; allergen/van/event records

**Outputs:**  
Cached answers -> dashboard/browser; only cache-miss queries -> [[SPEC:PROD-10]] inference layer

**Trigger:**  
State-change event (task close, LKL write, allergen flag, van status, event open/close, scheduled tick) OR an incoming operational query

**Failure Mode Addressed:**  
Routine operational questions (what's next, what's missing, what's behind) were hitting live inference for answers that a cached state-change already contains — burns the N100's limited inference budget on questions that don't need a model.

**Acceptance Criteria:**  
INV-005's target composition (65% deterministic/25% KB/8% small model/2% T3/<1% AI) is measurable from real query logs, not aspirational; a cache-hit query never touches the inference layer at all.

**Open Questions:**  
RESOLVED 2026-09-02: cloud-first for V1.0 (see INFERENCE 1). This cache/precompute layer is backend-agnostic — it intercepts before dispatch regardless of whether the eventual model is cloud or local, so no rework needed if/when a local model is plugged in later.

**Rationale:**  
Canonical numeric source for D-INF-001 (cited elsewhere, e.g. DISPLAY 1/INFERENCE 1, as a principle with no number attached) — cite this target composition wherever D-INF-001 comes up.

**Verification Method:**
1. [AUTO] Cache hit: deterministic lookup answered from cache, zero inference call. Evidence: log.
2. [AUTO] Composition: demand mix within D-INF-001 targets (65/25/8/2/<1). Evidence: metrics.
3. [NICK] Live: cold cache warms on a state change. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Cache-Precompute-Router-Inference-Demand-Reduction-INV-005-Target-3b5e152fc199813a9416e634e4d0f36c_

---
## PROD-25 — Unified Notifier (SMS/ntfy Routing)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: one notification system for the whole app, not five modules each texting Nick and Sandra their own way.

**Functional Requirement Specification:**  
The system shall route all outbound notifications through a unified notifier: ntfy push to Nick's phone and Twilio SMS to Sandra as the PRIMARY channel for time-sensitive alerts (D10). All callers use a single notify(recipient, severity, message, correlation_id) interface — never direct Twilio or ntfy calls from business logic. All callers use a single notify(recipient, severity, message, correlation_id) interface — never direct Twilio or ntfy calls from business logic. Implements D-008.

**Inputs:**  
[[SPEC:PROD-20]] event bus; [[SPEC:PROD-23]] exception router; [[SPEC:W2]] lead scoring (hot lead alerts); [[SPEC:PROD-01]] task engine

**Outputs:**  
Twilio SMS (Sandra), ntfy (Nick/ops), [[SPEC:PROD-22]] audit log, [[SPEC:PROD-04]] dashboard state

**Trigger:**  
[[SPEC:PROD-23]] exception created, hot lead scored, task-engine alert condition, or any module calling alert() directly

**Failure Mode Addressed:**  
Alerts were being wired ad hoc per module (some to ntfy, some nowhere) — no single place guarantees a critical alert actually reaches the right human.

**Acceptance Criteria:**  
Every module that needs to alert a human calls the same alert() interface; ntfy-to-Nick path is proven and routes correctly; SMS-to-Sandra fails loudly (visible stub, not a silent no-op) until the Twilio adapter is real.

**Verification Method:**
1. [NICK] Live: [[SPEC:W2]] Hot lead → Twilio SMS to Sandra. Evidence: screenshot.
2. [AUTO] Channel rule: actionable → SMS, non-urgent → ntfy, per D10. Evidence: code-search.
3. [AUTO] Logging: every notification logged. Evidence: query.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Unified-Notifier-SMS-ntfy-Routing-3b5e152fc199810891e3ec0ee9c2b675_

---
## PROD-26 — Runtime Configuration (Env-Var Service Endpoints)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: changing which server or service an integration points to is a config change, not a code change — nothing hardcoded that has to be found and edited by hand when something moves.

**Functional Requirement Specification:**  
The system shall load all service endpoints, ports, API keys, and inference backend URLs from environment variables at startup via a single config module. No module hardcodes any endpoint URL or port (D-061 build rule: OLLAMA_BASE_URL and all service addresses are env-vars). A missing required env-var raises a startup error, not a runtime exception. This module is the bootstrap layer all other modules depend on for their connection config.

**Inputs:**  
.env file, systemd unit definitions, current N100 service ports

**Outputs:**  
Env-var-driven endpoints ([[SPEC:SW-001]] mandatory) consumed by every module: [[SPEC:PROD-27]] DB layer connection string, [[SPEC:PROD-20]] event bus, [[SPEC:PROD-10]] LLM client endpoint (reconciles legacy OLLAMA_BASE_URL naming), [[SPEC:PROD-25]] notifier (ZEBRA_HOST/PORT), cache path settings for [[SPEC:PROD-24]]

**Trigger:**  
Service start / systemd unit boot

**Dependency Notes:**  
INFRA 19 and other modules depend on this for connection config.

**Acceptance Criteria:**
NORMAL: Service starts with required env vars; missing required var → startup error, not runtime exception.
EDGE: Endpoint URL changes → env var only, zero code change.
NEGATIVE: Hardcoded credential in code → BLOCKED.
SILENT-FAILURE: Required var silently defaulted → caught (no silent defaults for required vars).
CHALLENGE: Move a service from n100 to gflip → env-only changes.

**Verification Method:**
1. [AUTO] Startup-fail: launch with missing required var → clean startup error. Evidence: log.
2. [AUTO] Hardcode search: grep for connection strings/keys in code → zero. Evidence: grep.
3. [NICK] Live: Nick verifies one service relocates via env only. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Runtime-Configuration-Env-Var-Service-Endpoints-3b5e152fc1998189937bfda1dbb9504e_

---
## PROD-27 — Database Access Layer (Connection + Query + Audit-Trigger Gate)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: every part of the system reads and writes the database through the same guarded path — enforced connection limits, safe queries, and an audit trail — so no module can bypass safety and quietly corrupt or leak data.

**Functional Requirement Specification:**  
The system shall route all PostgreSQL reads and writes through a single database access layer that enforces: connection pooling (config from INFRA 1), query parameterisation (no string interpolation into SQL), an ALLOWED_TABLES allowlist derived from information_schema after schema stabilisation, and an audit trigger that fires [[SPEC:PROD-22]] on every write. No module opens a raw psycopg2/asyncpg connection directly.

**Inputs:**  
[[SPEC:PROD-26]] runtime config (connection string)

**Outputs:**  
DB connections/queries -> [[SPEC:PROD-01]] task engine, [[SPEC:PROD-20]] event bus, [[SPEC:PROD-22]] audit log, and every other module reading/writing PostgreSQL

**Trigger:**  
Any module needing a DB connection or query

**Dependency Notes:**  
Distinct from [[SPEC:PROD-19]]'s schema DDL — this is the connection layer.

**Acceptance Criteria:**
NORMAL: All DB access through the layer with parameterized queries.
EDGE: Table not in ALLOWED_TABLES → rejected.
NEGATIVE: Raw connection outside the layer → BLOCKED.
SILENT-FAILURE: Write without audit trigger → caught (every canonical write audited).
CHALLENGE: SQL-injection payload → parameterized, rejected.

**Verification Method:**
1. [AUTO] Allowlist: query to non-allowed table → rejected. Evidence: log.
2. [AUTO] Audit trigger: every write → audit row. Evidence: query.
3. [AUTO] Injection: injection payload → rejected. Evidence: test log.
4. [AUTO] Hardcode search: no raw connection strings. Evidence: grep.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Database-Access-Layer-Connection-Query-Audit-Trigger-Gate-3b5e152fc19981e4b459d60ae740459d_

---
## PROD-28 — System Health Monitor (Service/Temp/UPS Status)
**Status:** Deployed | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
As the owner running a lights-out box in a kitchen, I need one always-on health monitor that watches every critical part of the system and shows me the truth at a glance, so I catch failures in minutes instead of finding out days later.

**Functional Requirement Specification:**  
The system shall run a health-monitoring service that continuously collects and displays the state of every event-critical resource — services, UPS/power, CPU temp, memory, disk, thermal history, display-fleet network presence, AI-engine readiness, printer, and backup freshness — with per-signal timestamps and fail-visible semantics (never default healthy). It shall be systemd-managed, auto-start on reboot, and be reachable on LAN and via the approved private remote path.

**Inputs:**  
systemd unit list, N100 temp/UPS sensors, llama-server /health endpoint, [[SPEC:PROD-26]] runtime config for service names/ports

**Outputs:**  
Health status -> [[SPEC:PROD-25]] notifier (alert on failure/threshold breach), [[SPEC:PROD-04]] dashboard state (status tile)

**Trigger:**  
Scheduled health-check tick (systemd timer) or service failure event

**Failure Mode Addressed:**  
Silent infrastructure failure invisible until it damages an event (the 08-21 dnsmasq outage that read 'active' the whole time).

**Acceptance Criteria:**  
All configured signals render with timestamp + explicit state; stale/unreadable signals show degraded not healthy ([[SPEC:URS-HEALTH-005]]); service auto-starts healthy after cold reboot ([[SPEC:URS-HEALTH-004]]); reachable on LAN + Tailscale.

**Verification Method:**
1. [AUTO] Service-down: kill a service → alert fires. Evidence: log.
2. [AUTO] Threshold: temp/UPS breach → alert. Evidence: log.
3. [NICK] Live: Nick sees the alert on his phone. Evidence: screenshot.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/System-Health-Monitor-Service-Temp-UPS-Status-3b5e152fc19981f7a762e9043061674e_

---
## PROD-29 — Crew Event Tablet / Hospitality Coaching Display (Taza OS Crew Display v1)
**Status:** Built (unverified live) | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Spec Package

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: standalone offline HTML/PWA on Galaxy Tab A8 showing client story + hospitality coaching prompts during live events, so contract/temp crew get the emotional context and service discipline without a training session.

**Functional Requirement Specification:**  
Standalone offline HTML/PWA (taza-crew-display.html) deployed via Chrome 'Add to Home Screen' on Galaxy Tab A8. Mode 1: animated client story reveal (large gold typography, configurable hold); Mode 2: 14 approved hospitality scanning prompts cycling through the event arc; Mode 3: wind-down reminders. Wake Lock API prevents screen sleep. No network calls after initial load. V2: story auto-generated from CRM event record via AI.

**Inputs:**  
V1: manual event setup screen (client/event name, guest count, event type, story hold time, scan prompt duration). V2: NocoDB event record (client name, guest count, event type, occasion notes, VIP context)

**Outputs:**  
On-screen client story + rotating hospitality/service-attention prompts displayed to crew during live service (one-way display, no data written back)

**Trigger:**  
Event day setup at crew staging area (V1 manual); V2: morning-of-event automation trigger

**Dependency Notes:**  
Distinct from KANBAN 1 (kitchen kanban) and DISPLAY 1 (wall TVs). This is the event-service/hospitality-culture surface — standalone, offline, complete for V1. Implemented by CREW 2.

**Acceptance Criteria:**
NORMAL: Tablet loads event config, presents hospitality prompts full-screen, Wake Lock keeps screen on.
EDGE: Late crew member taps Replay → story restarts from the beginning.
NEGATIVE: Network call after initial load → none (offline-capable).
SILENT-FAILURE: Screen sleeps mid-service → caught (Wake Lock must stay active).
CHALLENGE: Full service on airplane mode → tablet survives, screen never sleeps.

**Verification Method:**
1. [NICK] Live: crew tablet runs a real service. Evidence: observation log + screenshot.
2. [AUTO] Offline: airplane-mode run → still works. Evidence: test log.
3. [AUTO] Wake Lock: screen stays awake through service. Evidence: device log.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Crew-Event-Tablet-Hospitality-Coaching-Display-Taza-OS-Crew-Display-v1-3b5e152fc199810ca65fd23441c12295_

---
## PROD-34 — MT8390 NPU V1.x Capabilities (Kitchen Vibe Index, Voice Timer, Trip Hazard Detection)
**Status:** Idea | **Priority:**  | **Release:** 

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: crew can set a timer or get a trip-hazard warning hands-free — no tapping a screen mid-task.

**Functional Requirement Specification:**  
The system shall deploy three V1.x NPU capabilities on the MT8390 via MediaTek NeuroPilot SDK (TF/PyTorch/ONNX → MDLA 3.0 INT8, ADB sideloaded, 100% offline): (1) V1.1 — Voice Timer: crew speaks a timer, NPU classifies and starts it on-device; (2) V1.2 — Trip Hazard Detection: ambient floor-area camera monitoring via TFLite; (3) V1.1/V1.2 shared infrastructure — the voice/camera close infrastructure from NPU 5. V1.0 NPU scope is passive mood-ring logging only (already decided). V2.0 capabilities are in [[SPEC:PROD-35]].

**Inputs:**  
MT1/MT2 MicroTouch NPU (MDLA 3.0 Deep Learning Accelerator + Tensilica VP6 Vision Processor, confirmed hardware per 2026-07-13 research), mic array, front camera

**Outputs:**  
Vibe/timer/hazard signals -> [[SPEC:PROD-04]] kitchen displays (alert overlay), [[SPEC:PROD-25]] notifier (hazard alerts)

**Trigger:**  
Continuous passive monitoring during kitchen operation

**Failure Mode Addressed:**  
Kitchen stress signals and hands-full moments (need a timer, spot a trip hazard) currently require either nothing happening or interrupting someone — the NPU sits unused hardware capable of catching these passively.

**Dependency Notes:**  
Shares NPU 5's NPU authority boundary (verifies/assists, humans authoritative) — same code guard should gate V1.1/V1.2, not a separate one. See [[SPEC:PROD-35]] for V2.0 tier (6 capabilities, hardware-gated).

**Rationale:**  
10-capability MT8390 NPU roadmap locked 2026-07-13 (confidence 0.85), split V1.0/V1.x/V2.0.

**Acceptance Criteria:**  
Deferred — Idea stage — no AC/VM until promoted to spec.

**Verification Method:**  
Deferred — Idea stage — no AC/VM until promoted to spec.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/MT8390-NPU-V1-x-Capabilities-Kitchen-Vibe-Index-Voice-Timer-Trip-Hazard-Detection-3b5e152fc19981e5b150e38cc27cbd9a_

---
## PROD-36 — Inventory Lot Tracking & MT2 Dashboard (Parent-Child Lots)
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Spec Package

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I want accurate, fully-traceable inventory to fall out of the crew simply closing their kanban cards — every thaw/repack/portion/consume automatically updates stock and lot lineage, every lot traces back to where it came from, and MT2 shows me the trustworthy live picture — without anyone running a separate inventory count.

**Functional Requirement Specification:**  
The system shall maintain parent-child lot lineage across the full inventory lot lifecycle (thaw/repack/portion/refreeze/consume/waste/overbuy), decrementing parent lots and creating child lots on split, and shall present the MT2 inventory dashboard (drawdown rate, lot age, bin map, stock state, alerts) reconciling to the canonical lot + transaction ledger. Close events fire via [[SPEC:PROD-38]] close_kind=INVENTORY_LOT. MT2 is the designated inventory dashboard surface. V1.x.

**Intent / User Need:**  
Turn accurate, fully-traceable inventory into a free byproduct of the crew closing cards — no separate counting step — with MT2 as the shared inventory picture.

**Inputs:**  
[[SPEC:PROD-02]] LKL completion-gate closures (bin/location + quantity captured at task close)

**Outputs:**  
MT2 inventory dashboard display; future barcode/NPU predictive-prep-counting ([[SPEC:PROD-33]]) as an alternate input path

**Trigger:**  
Kanban card close where the task type implies a lot transformation (repack, freeze, portion, split)

**Failure Mode Addressed:**  
Inventory drift and lost traceability — physical stock diverging from the system, and inability to trace a portion back to its source lot — plus buying/using on stale stock data.

**Acceptance Criteria:**  
Every qualifying card close creates exactly one inventory transaction ([[SPEC:URS-INV-001]]); parent-child lineage is reconstructable without cycles ([[SPEC:URS-INV-002]]); lot records carry the full field set and reconcile to transactions ([[SPEC:URS-INV-003]]); inventory closures propose (not auto-print) labels ([[SPEC:URS-INV-004]]); the MT2 dashboard reconciles to the ledger and marks stale data ([[SPEC:URS-INV-005]]).

**Dependency Notes:**  
NPU sub-tier V1.3. Distinct from [[SPEC:PROD-02]]: [[SPEC:PROD-02]]/LKL = WHERE; CLOSE 5/inventory = HOW MUCH/WHICH LOT.

**Open Questions:**  
MT2 dashboard aspect is a candidate for its own SCREEN-* row.

**Verification Method:**
1. [AUTO] Parent-child: thaw/portion creates child lot, decrements parent. Evidence: psql.
2. [AUTO] Ledger reconcile: transactions reconcile to canonical ledger. Evidence: query.
3. [NICK] Live: Edgar portions a lot → child lot appears on MT2 dashboard. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inventory-Lot-Tracking-MT2-Dashboard-Parent-Child-Lots-3b5e152fc19981d39f8ccfc9956f0db6_

---
## PROD-37 — Voice/NPU Card Close Verification Layer
**Status:** Idea | **Priority:**  | **Release:** V2.0

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: crew can close a card by voice or by showing the camera the finished item, instead of always tapping — but the NPU only advises, the crew's own claim still decides.

**Functional Requirement Specification:**  
The system shall provide two alternative card-close modalities on top of [[SPEC:PROD-38]]'s canonical TaskCloseEvent: (1) V1.1 — Voice close: crew speaks the close command; Chrome Web Speech API on MT1/MT2 captures audio, N100 processes it, sets close_method=VOICE + voice_transcript on the TaskCloseEvent; (2) V1.2 — Camera-verified close: crew holds up the completed item; MT8390 camera captures and NPU classifies it, sets close_method=CAMERA_VERIFIED + verification_thumbnail_path + classification_confidence. NPU output is a plausibility check only — humanClaim remains the authority (NPU cannot override a crew close).

**Inputs:**  
[[SPEC:PROD-02]] completion-gate schema (already pre-wired for null closed_by_method/verification_thumbnail_path/voice_transcript fields per V1.0 design); [[SPEC:PROD-34]] NPU capability base

**Outputs:**  
Card close events -> [[SPEC:PROD-02]] (alternate close modality alongside tap/PIN) and [[SPEC:PROD-36]] (voice/camera as a lot-transaction input path)

**Trigger:**  
Crew member closes a kanban card via voice command or camera gesture instead of tap+PIN

**Dependency Notes:**  
CONFORMS TO [[SPEC:PROD-38]].

**Open Questions:**  
RESOLVED 2026-09-02 (Nick, agnostic — prefers local NPU edge compute for intent classification but doesn't need it for V1.0): this spec's Chrome Web Speech API + N100 approach ships for V1.0. [[SPEC:KIT-017]]'s NPU wake-word approach is Nick's preferred long-term direction — treat it as the V1.x/V2 upgrade path once tested and proven, not a launch blocker.

**Rationale:**  
Cites D-051 OVERTURNED (2026-07-09, NPU confirmed accessible via NNAPI/NeuroPilot) as technical foundation; confirms NPU 1/[[SPEC:PROD-35]]'s NeuroPilot assumption.

**Acceptance Criteria:**  
Deferred — V2.0 ask. No AC/VM until promoted.

**Verification Method:**  
Deferred — V2.0 ask. No AC/VM until promoted.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Voice-NPU-Card-Close-Verification-Layer-3b5e152fc1998124834de3d7be674d0b_

---
## PROD-38 — Canonical Task Close Contract (TaskCloseEvent)
**Status:** Spec Drafted | **Priority:**  | **Release:** 

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: no matter what kind of card a crew member closes — prep, equipment, allergen, van-load, inventory — 'close' behaves the same reliable way underneath. One trusted mechanism, not different bespoke close logic per module that could each hide their own bugs.

**Functional Requirement Specification:**  
The system shall define a canonical, frozen TaskCloseEvent dataclass (fields: task_id, crew_id, crew_pin_hash, close_kind [7 variants], close_method [4 variants], event_id, occurred_at, plus kind-specific optional fields for qty/unit/lkl_bin_id/lot/allergen/equipment/voice/camera) and a TaskCloseRouter that validates, audit-logs, and fans out to the correct downstream handlers (LKL, inventory, labels, equipment, allergen, event bus) based on close_kind. All callers emit a TaskCloseEvent — there is no bespoke close schema per module.

**Inputs:**  
Crew PIN, task_id, close method (tap/voice/camera/supervisor override), and kind-specific fields (bin_id, qty/unit, lot_id, allergen_flag, voice_transcript, verification_thumbnail_path)

**Outputs:**  
TaskCloseEvent consumed by: [[SPEC:PROD-02]] (LKL), [[SPEC:PROD-19]] (equipment/allergen/van/portion), [[SPEC:PROD-36]] (inventory lots), [[SPEC:PROD-37]] (voice/camera close), [[SPEC:PROD-22]] (audit), [[SPEC:PROD-20]] (event bus emit)

**Trigger:**  
Any crew member closes a task card, by any method (tap/voice/camera/supervisor override)

**Failure Mode Addressed:**  
Every task-close-adjacent spec (LKL, inventory, labels, allergen capture, van load, portion capture, voice close, camera verify, kanban scoring) was inventing its own close payload shape independently — guaranteed drift the first time two of them needed to agree on a field name.

**Acceptance Criteria:**  
NORMAL PATH:
1. A valid TaskCloseEvent (all required fields present + valid kind-specific fields for its close_kind) is validated, produces exactly one audit-log entry, and fans out to exactly the documented handler set for that close_kind — no more, no fewer.
2. Each of the 7 close_kind variants routes only to its own documented handlers; an INVENTORY_LOT close never triggers the ALLERGEN_RECEIVING handler, etc. (cross-contamination check, all 7×7 pairs).
3. Each of the 4 close_method variants is accepted and recorded verbatim on the event.

EDGE CASES:
4. A close_kind requiring optional kind-specific fields (e.g. qty/unit for PORTION_CAPTURE) succeeds when present, fails with a field-specific error (not generic) when absent.
5. Retry with the same event_id is idempotent — no duplicate audit record, no duplicate downstream effect.
6. An unrecognized close_kind value is rejected before reaching dispatch logic — fails closed, never silently routed to a default handler.

NEGATIVE / FAILURE CASES:
7. Any TaskCloseEvent missing a required field (task_id, crew_id, crew_pin_hash, close_kind, close_method, event_id, occurred_at) is rejected outright — zero downstream handlers fire. Decide and test whether a rejected attempt itself gets an audit record distinct from a successful close (open sub-question — flag for debate).
8. crew_pin_hash that doesn't match a valid crew record is rejected as an authentication failure — never silently accepted as an anonymous/unknown-crew close.
9. A downstream handler failure mid-fan-out (e.g. LKL write fails) does not let the close report as fully successful — caller receives a failure/partial-failure signal, audit log reflects actual outcome (full/partial/total failure), never a blanket 'closed.'

SILENT FAILURE MODES:
10. Audit-log write succeeds but a downstream handler write fails — the crew-facing UI must not show 'closed' without an accompanying error; no silent partial-success masquerading as success.
11. No module may bypass TaskCloseRouter and write directly to LKL/inventory/label/allergen tables — must be detectable via static analysis/CI, not just code review discipline.
12. A close_kind with an unimplemented or misconfigured downstream handler must raise/alert, never silently no-op and return success.

**Verification Method:**  
1) Unit tests: one per close_kind (7) × one per required field (7) = each individually-missing required field rejected with a specific error, for every close_kind. 2) Integration tests: full close→audit→fan-out path per close_kind, asserting exactly the documented handler set fires and no others (7×7 cross-contamination matrix). 3) Idempotency test: identical event_id submitted twice → single audit record, single downstream effect. 4) Auth test: invalid crew_pin_hash rejected. 5) Fault-injection test: force one downstream handler to fail mid-fan-out → assert non-success signal to caller and accurate partial/total-failure audit record. 6) CI/static-analysis check: lint rule or code-search confirming no module writes directly to LKL/inventory/label/allergen tables outside TaskCloseRouter's dispatch path. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Canonical-Task-Close-Contract-TaskCloseEvent-3b5e152fc1998121b279c2b63eafecda_
