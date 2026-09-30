# Taza OS URS — CATALOG cluster
_Exported: 2026-09-19 21:35 | 6 rows_
_Source: Notion Master URS & Specification Registry_

---
## CAT-001 — Catalog Intelligence: 12 Square Custom Attributes schema
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: the system understands each menu item — servings, pricing basis, allergens, service location, hold times, prep-ahead window, failure mode, and pan — for correct, defensible prep/packing plans from day one, not guesses.

**Atomic Requirement:**  
The system shall define, on the Square catalog, a set of custom attributes (6 visible + 5 hidden as enumerated in the Design Spec) and shall populate validated values for all active Catering items, such that every value is retrievable via the Square SearchCatalogItems endpoint by the automation layer.

**Functional Requirement Specification:**  
Tier 1 intrinsic item facts as Square custom attributes — 7 visible (Sandra-editable): serves_min, serves_max, pricing_unit, dietary_flags, allergen_notes, station_type; and 5 hidden (API/RAG only): hot_hold_max_min, cold_hold_max_min, prep_advance_max_hr, quality_risk, default_pan_footprint. 12 of Square's 20-definition cap used, 8 in reserve. Populated for all active Catering items. These attributes feed [[SPEC:W7]] invoice pre-fill confidence, [[SPEC:W9]] sync, [[SPEC:W15]] BEO timing, and the packing/backward-scheduler solver. Read via SearchCatalogItems (only endpoint returning custom attribute values). Governing principle: the LLM retrieves these parameters and narrates; a deterministic function does the hold-time/packing arithmetic — never let the LLM reason about pan geometry or hold-time math.

**Intent / User Need:**  
Every downstream workflow (invoicing, BEO timing, packing, scheduling) reads the same authoritative catalog data rather than re-deriving or hallucinating it.

**Inputs:**  
Sandra's product knowledge (serves counts, dietary/allergen facts, station placement); Nick/Sandra-validated food-safety hold times, prep-advance windows, quality-risk classes, and pan footprints (from the Square Menu RAG Tuning + Equipment & Capacity deliverables).

**Outputs:**  
Per-item custom-attribute values on every active Square Catering item, retrievable by the automation layer via SearchCatalogItems; consumed by [[SPEC:W7]] (invoice pre-fill + confidence), [[SPEC:W9]] (menu sync), [[SPEC:W15]] (BEO timing), [[SPEC:SW-011]] (local menu cache), and the [[SPEC:CAT-002]]..006 / [[SPEC:PROD-16-V2]] packing & scheduling layer.

**Trigger:**  
Definition step: one-time Square custom-attribute-definition creation via MCP/API. Population step: manual/assisted enrichment of all ~50 active Catering items. Read: on every [[SPEC:W7]]/[[SPEC:W9]]/[[SPEC:W15]] run and every [[SPEC:SW-011]] nightly cache sync.

**Invariants:**  
Every active Catering item carries a non-null serves_min, pricing_unit, station_type, and (for anything hot/cold-held) the relevant hold-time value. Attribute definitions are never deleted while any item references them. The visible/hidden split is fixed: hidden attributes never surface in the Sandra-facing Dashboard.

**Failure Behavior:**  
Missing/blank attribute on an item → downstream workflow flags low confidence and routes to human review rather than guessing (never fabricate a hold time or serves count). SearchCatalogItems unreachable → fall back to the [[SPEC:SW-011]] local PostgreSQL menu cache; if that is also stale, block the affected plan and alert rather than produce an unverified plan.

**Failure Mode Addressed:**  
Sparse or absent catalog data producing vague/wrong prep instructions (the 'system doesn't understand food' trust-debt failure); LLM hallucinating hold-time or pan-geometry arithmetic; allergen/dietary data living in an un-queryable category workaround instead of a machine-readable attribute.

**Out of Scope:**  
Order-level event-logistics attributes (setup_type/tables_count/linens_tier/kitchen_departure) — those are [[SPEC:CX-006]]. Mode-dependent packing geometry — [[SPEC:CAT-002]]. Bill-of-materials explosion — [[SPEC:CAT-003]]. Equipment occupancy — [[SPEC:CAT-004]]. SOP wiring — [[SPEC:CAT-005]]. The deterministic solver/scheduler itself — [[SPEC:PROD-16-V2]] / [[SPEC:CAT-006]]. Do NOT populate the legacy 'Dietary & Allergy Flags' REGULAR_CATEGORY — dietary_flags replaces it.

**Acceptance Criteria:**  
NORMAL:
1. All 12 attributes (7 visible + 5 hidden) are populated for every active Catering item and readable via SearchCatalogItems.

EDGE:
2. An item added to the catalog after initial population is automatically flagged for these 12 attributes to be filled — not silently missing them until someone remembers.
3. An item near a Square attribute-cap boundary (approaching the 20-definition limit as more attributes get added over time) is monitored — verify there's visibility into remaining headroom (8 in reserve currently).

NEGATIVE:
4. SearchCatalogObjects (the wrong endpoint) is never used anywhere in the codebase for reading these attributes — verify by code search, since it silently returns no custom-attribute data rather than erroring.

SILENT FAILURE:
5. This row's own Open Questions flags a count discrepancy (7 visible claimed vs. 6 documented) — resolve this against Nick's actual intent before debate builds against an ambiguous field count.
6. The 'LLM narrates, deterministic function computes' governing principle is a discipline requirement, not a technical constraint enforced by the schema itself — verify there's an actual code-level guard (not just a written principle) preventing any LLM call from performing pan-geometry or hold-time arithmetic.
7. A hidden attribute silently missing for one item (data-entry gap) would cause downstream packing/scheduling to fail or guess — verify there's a completeness check across the active catalog, not just schema-level correctness for populated items.

**Verification Method:**  
1) Schema test: confirm all 12 attributes exist and are correctly typed on the Square catalog. 2) Completeness audit: query all active Catering items, confirm 100% have all 12 attributes populated (not just spot-checked). 3) Endpoint-usage code search: confirm SearchCatalogObjects is never used to read these attributes anywhere in the codebase. 4) Governing-principle enforcement test: confirm no LLM-facing code path performs pan-geometry/hold-time math directly — verify via code review plus a test that feeds the LLM ambiguous geometry and confirms it defers to the deterministic function. 5) Resolve the count-discrepancy open question with Nick before this ships to debate. 6) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Sandra maintains the 6 visible attributes in the Square Dashboard as the menu evolves. Nick/Sandra own the 5 hidden values (food-safety and packing facts) — reviewed when a recipe or service mode changes. New Catering item added to Square → its attributes must be populated before it can be quoted (enforced by the [[SPEC:W7]] flag-for-review path). Attribute-definition changes are rare and require confirming the account still sits under the Square cap.

**Dependency Notes:**  
FEEDS: [[SPEC:W7]] (invoice pre-fill + confidence), [[SPEC:W9]] (Square→NocoDB sync carries these 12 attributes), [[SPEC:W15]] (BEO timing uses prep_advance_max_hr/hot_hold_max_min/station_type), [[SPEC:SW-011]] (local PostgreSQL menu cache stores them for hot-path reads), [[SPEC:CAT-002]]/[[SPEC:CAT-004]] (packing/equipment tables key off station_type + default_pan_footprint), [[SPEC:CAT-006]] + [[SPEC:PROD-16-V2]] (TCS + backward scheduler consume hold-times). RECONCILE IN DEBATE: this catalog-level Tier-1 schema vs [[SPEC:CX-006]]'s 4 order-level attributes (separate namespace, keep both) and vs [[SPEC:PROD-09]] (which references 'Tier 2 BOM/Packing/Equipment' as a package — [[SPEC:CAT-002]] is Tier 1, distinct).

**External Dependencies:**  
Square Catalog API (custom attribute definitions + SearchCatalogItems read path); Square account tier's custom-attribute-definition cap; MCP/API write access to create the definitions.

**Open Questions:**  
COUNT DISCREPANCY (flag for debate): the source Catalog Ops spec header claims '7 visible + 5 hidden = 12 of 20' but its own tables enumerate only 6 visible + 5 hidden = 11. Either a 7th visible attribute is intended-but-unlisted, or '7/12' is a counting error and the real total is 11. Do NOT invent a 7th attribute to force the count — resolve against Nick's intent. RELATED OPEN DECISION (see [[SPEC:CAT-006]]): add tcs_food as an explicit 6th HIDDEN boolean, or derive TCS status from quality_risk = food_safety? Source recommends the explicit boolean; if adopted, the hidden set becomes 6 and the total 12 — which may be the origin of the '12' figure.

**Rationale:**  
The system's core value proposition is generating correct, defensible operational plans from day one — not just correct invoices. Hidden attributes cost the user nothing (Sandra/Edgar never see them) and no contractor hours (a data-enrichment task), but are non-negotiable for correct task generation: without hot_hold_max_min, prep scheduling is a guess. Shipping without them creates trust debt that is asymmetrically expensive to undo.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Catalog-Intelligence-12-Square-Custom-Attributes-schema-3cfe152fc1998109873ed1decdeb6a1a_

---
## CAT-002 — item_packing_profiles table (mode-dependent pan geometry)
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: the system knows that the same dish packs differently depending on how it's served (delivery vs. staffed buffet), so packing instructions are always right for the actual event, not a generic default.

**Functional Requirement Specification:**  
NocoDB table keyed (item_id, service_mode) holding pan_footprint (full/half/third/sixth), pan_depth_in (2/4/6), fill_qty_per_pan, container_override, notes. Encodes how the same item packs differently by service mode (e.g. broccoli: delivery → disposable half; staffed buffet → 4" third-or-half by co-occupants). Feeds the deterministic packing solver ([[SPEC:PROD-16-V2]]). Target: top 15 frequency items populated before V1 launch.

**Acceptance Criteria:**  
Table exists with the keyed schema; top-15 items populated; packing solver reads pan geometry from here, not from LLM inference.

**Open Questions:**  
Reconcile scope with [[SPEC:PROD-09]] during debate: break out as own table vs. keep as [[SPEC:PROD-09]] child.

**Verification Method:**
1. [AUTO] Schema: `item_packing_profiles` exists keyed (item_id, service_mode) with pan_footprint/pan_depth_in/fill_qty_per_pan. Evidence: psql \d.
2. [AUTO] Coverage: top-15 frequency items populated with packing profiles. Evidence: query count.
3. [AUTO] Mode-split: the same item has distinct rows for delivery vs. staffed-buffet. Evidence: query.
4. [AUTO] LLM-free: packing solver reads pan geometry from this table, zero inference calls. Evidence: code-search.
5. [NICK] Live: Sandra confirms broccoli packing profiles match reality (delivery vs. buffet). Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/item_packing_profiles-table-mode-dependent-pan-geometry-3cfe152fc19981f28e3ce983940477da_

---
## CAT-003 — item_components table (Bill of Materials for composite items)
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: composite/bundled menu items (platters, packages) automatically break down into the correct individual prep tasks — not one vague task that leaves crew guessing what's actually in it.

**Functional Requirement Specification:**  
NocoDB BOM table (parent_item_id, component_item_id, qty_per_parent, notes) so composite items (Mezza Platter, Mediterranean Grill Package, Charcuterie, Gyro Platter, Brunch/Dessert Packages) explode into correct sub-task prep chains automatically. Without it, the system cannot generate correct prep trees for bundled items. Population priority: the ~6 composite parents that cover most complexity.

**Acceptance Criteria:**  
BOM table exists; the ~6 composite parents populated; closing a parent order explodes into the correct component prep tasks.

**Open Questions:**  
Reconcile scope with [[SPEC:PROD-09]] during debate (this BOM table is currently listed under the [[SPEC:PROD-09]] package).

**Verification Method:**
1. [AUTO] Schema: `item_components` BOM table exists (parent_item_id, component_item_id, qty_per_parent). Evidence: psql \d.
2. [AUTO] Coverage: ~6 composite parents populated (Mezza, Medi Grill, Charcuterie, Gyro Platter, Brunch/Dessert Packages). Evidence: query.
3. [AUTO] Explosion: closing a parent order generates the correct component prep tasks. Evidence: psql + test log.
4. [AUTO] LLM-free: no inference in the explosion path. Evidence: code-search.
5. [NICK] Live: Nick verifies one composite explosion matches actual prep. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/item_components-table-Bill-of-Materials-for-composite-items-3cfe152fc199811b8ae5efeaa8b1d95e_

---
## CAT-004 — item_equipment table (equipment-contention detection)
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: the system can see when multiple items are competing for the same oven/equipment at the same time, so scheduling conflicts get caught before they become a crisis in the kitchen.

**Functional Requirement Specification:**  
NocoDB table (item_id, equipment_id → equipment_list, occupancy_min, notes) capturing how long each item occupies each piece of equipment — equipment contention (one oven, three items each needing 40 min) is the #1 source of scheduling branch complexity, and this table makes it detectable and schedulable. Depends on the equipment_list seed data from the Equipment & Capacity interview.

**Acceptance Criteria:**  
Table exists and joins to equipment_list; scheduler can detect oven/burner/carrier contention and branch accordingly.

**Open Questions:**  
Reconcile scope with [[SPEC:PROD-09]] during debate (this equipment-contention table is currently listed under the [[SPEC:PROD-09]] package).

**Verification Method:**
1. [AUTO] Schema: `item_equipment` table exists and joins to equipment_list. Evidence: psql.
2. [AUTO] Contention: scheduler detects two items competing for the same oven in one window. Evidence: test log.
3. [AUTO] Branch: detected contention triggers a scheduling branch, never a silent double-book. Evidence: log.
4. [NICK] Live: Nick confirms equipment_list seed data matches the real kitchen. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/item_equipment-table-equipment-contention-detection-3cfe152fc199810da2c0fd0da207c86c_

---
## CAT-005 — procedure_link table (catalog item → Atomic SOP wiring)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every catalog item is linked to its actual prep procedure, so the system (and new crew) always know which SOP applies, without duplicating those steps in multiple places.

**Functional Requirement Specification:**  
NocoDB table (item_id → catalog, procedure_id → Procedures/Atomic SOPs, service_mode with null = all modes) wiring each catalog item or component to its existing Atomic SOP. Step-level durations and dependencies live in the SOP, not duplicated here — this table is the join only.

**Acceptance Criteria:**  
NORMAL:
1. Every catalog item/component is joined to its correct Atomic SOP via item_id/procedure_id, with service_mode correctly null (all modes) or scoped.

EDGE:
2. A catalog item with no applicable SOP (if that's a valid state) is distinguishable from a catalog item that's simply missing this join by mistake — verify these two states aren't conflated.
3. An item requiring different SOPs per service_mode (e.g. different prep for delivery vs. staffed) correctly resolves to the mode-specific procedure, not always falling back to the null/all-modes default.

NEGATIVE:
4. A join pointing to a procedure_id that doesn't exist in the Procedures/Atomic SOPs table is a detectable data-integrity violation.

SILENT FAILURE:
5. Since 'step-level durations and dependencies live in the SOP, not duplicated here,' verify no code path accidentally duplicates or caches stale SOP timing data locally in this join table — the join must always resolve live to the SOP as source of truth.
6. A composite item ([[SPEC:CAT-003]], BOM) whose components each have different SOPs must correctly surface all relevant procedures, not just the parent item's single procedure_link.

**Verification Method:**  
1) Join-integrity test: every procedure_id referenced resolves to a real SOP record. 2) Mode-resolution test: item with mode-specific SOPs correctly resolves per service_mode, confirmed against the null/all-modes fallback case too. 3) Staleness test: confirm SOP timing/dependency data is always read live from the SOP record, never cached/duplicated in this join table. 4) Composite-item test: BOM item with multiple component SOPs surfaces all of them correctly. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
Reconcile scope with [[SPEC:PROD-09]] during debate (this SOP-wiring table is currently listed under the [[SPEC:PROD-09]] package).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/procedure_link-table-catalog-item-Atomic-SOP-wiring-3cfe152fc19981ce91f2ee800162d86a_

---
## CAT-006 — TCS food-safety scheduling constraint (danger-zone hard limit)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As the owner, I need food-safety temperature-danger-zone limits enforced as a hard rule in scheduling, not a suggestion the system can quietly ignore under time pressure — this protects customers and the business.

**Functional Requirement Specification:**  
Tag TCS (Temperature Control for Safety) items and treat danger-zone exposure (40–140°F) as a HARD scheduling constraint, not a soft preference, in the backward scheduler. The hold clock starts at pack time, not service time: latest_prep_finish = service_time − display_wait − transit − pack; a generated plan must verify (service_time − latest_prep_finish) ≤ hot_hold_max_min, and branch to 'assemble/sear on-site' or 'substitute hold-stable item' when it fails. Both a robustness win and liability protection. Recommended implementation: an explicit tcs_food boolean rather than deriving from quality_risk.

**Acceptance Criteria:**  
NORMAL:
1. TCS items are tagged; danger-zone (40-140°F) exposure is enforced as a hard constraint in the backward scheduler, hold clock starting at pack time.
2. A plan where (service_time − latest_prep_finish) ≤ hot_hold_max_min passes; a plan that violates it branches to 'assemble/sear on-site' or 'substitute hold-stable item.'

EDGE:
3. An item exactly at the hot_hold_max_min boundary is handled deterministically (defined as pass or fail, not a coin-flip based on floating-point rounding).
4. Multiple TCS items on the same event with different hold-time limits are each evaluated independently — one item's slack doesn't mask another's violation.

NEGATIVE:
5. A TCS item with no configured hot_hold_max_min (data gap) is rejected/flagged rather than silently treated as having unlimited hold time.

SILENT FAILURE:
6. This is explicitly 'liability protection' — a scheduling bug here isn't a UX annoyance, it's a food-safety and legal risk. Verify with adversarial test cases specifically designed to violate the constraint (tight timelines, long transit) and confirm the system always catches it, never silently produces an unsafe plan that 'looks fine.'
7. The branch to 'assemble/sear on-site' or 'substitute hold-stable item' must be an actual actionable output crew can follow, not just an internal flag with no visible instruction — verify it surfaces clearly.
8. Open question flags this needs reconciling with [[SPEC:PROD-16-V2]] (backward scheduler) — resolve whether this constraint lives here or there as the source of truth before debate builds both independently.

**Verification Method:**  
1) Boundary tests: exactly-at-limit and just-over-limit cases, confirm deterministic pass/fail. 2) Adversarial scheduling test: construct tight-timeline/long-transit scenarios specifically designed to violate hold times, confirm the system always catches and branches correctly, never silently produces an unsafe plan. 3) Multi-item test: multiple TCS items with different limits on one event, confirm independent evaluation. 4) Missing-data test: TCS item with no hot_hold_max_min configured is flagged, not defaulted to unlimited. 5) Output-actionability check: confirm the on-site-assemble/substitute branch produces a clear, crew-visible instruction. 6) Resolve the [[SPEC:CAT-006]] / [[SPEC:PROD-16-V2]] scope-overlap open question before parallel debate work begins on both. 7) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
Reconcile with [[SPEC:PROD-16-V2]] during debate (TCS danger-zone constraint currently partly implicit there).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/TCS-food-safety-scheduling-constraint-danger-zone-hard-limit-3cfe152fc199818a82ffe9f3b2f52a2d_
