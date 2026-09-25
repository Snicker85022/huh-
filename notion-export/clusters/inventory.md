# Taza OS URS — INVENTORY cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-INV-001 — Kanban closure creates inventory transaction
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: inventory stays accurate with no separate data entry — closing a thaw/repack/move/consume/waste/refreeze card automatically logs the stock movement exactly once.

**Atomic Requirement:**  
Closing a thaw, repack, move, consume, waste, or refreeze card shall create exactly one corresponding inventory transaction.

**Functional Requirement Specification:**  
Closing a thaw, repack, move, consume, waste, or refreeze card shall create exactly one corresponding inventory transaction. Inventory tracking is a side effect of correctly playing the kanban game — there is no separate inventory data-entry step. Each action maps to exactly one transaction and is idempotent on replay.

**Inputs:**  
The committed card-close event (action type, item, quantity, bin, crew, lot).

**Outputs:**  
Exactly one inventory transaction per qualifying card close, feeding the lot ledger.

**Trigger:**  
A thaw/repack/move/consume/waste/refreeze card closes.

**Invariants:**  
One inventory transaction per qualifying close; idempotent on replay; every transaction traces to its originating close.

**Failure Behavior:**  
A failed close creates no transaction; a retried close is idempotent (no duplicate transaction). Non-inventory card closures create none.

**Failure Mode Addressed:**  
Inventory drift — physical stock changing (thaw/repack/consume/waste) with no corresponding record, so the system's picture diverges from reality.

**Acceptance Criteria:**  
Each supported action maps to one transaction; retry does not duplicate it.

**Verification Method:**  
Action-matrix and idempotent replay test.

**Maintenance Requirements:**  
Keep the action→transaction-type map current as new card kinds are added; keep the idempotency key aligned with PROD-38.

**Dependency Notes:**  
Fires off the canonical task close (CLOSE 12 / CLOSE 1, close_kind=INVENTORY_LOT) through EXCEPT 2 (Event Bus). The transaction updates lot state (CLOSE 7/CLOSE 8). CROSS-REF: overlaps KIT-018 (inventory-as-side-effect) — reconcile in debate. Part of BUNDLE-INVENTORY-LOT-TRACKING. Parent CLOSE 5. Star printer prints a use-by label (date/item/qty/bin/packed-by/use-by + QR) on qualifying closes — see CLOSE 9.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Kanban-closure-creates-inventory-transaction-2f1b87498fbc4d9b809d79b4c0a6fd64_

---
## URS-INV-002 — Inventory supports parent-child lot lineage
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: trace every portion back to its exact source lot — splitting/repacking links child to parent so the full chain is reconstructable (quality, recalls, cost).

**Atomic Requirement:**  
The inventory model shall preserve parent-child lot lineage for partial use, portioning, thawing, repacking, freezer return, and overbuy.

**Functional Requirement Specification:**  
The inventory model shall preserve parent-child lot lineage across partial use, portioning, thawing, repacking, freezer return, and overbuy: when crew portion from a larger lot, a child lot is created, the parent is decremented, and the two are linked. Every derived lot shall reference its immediate parent, and complete lineage shall be reconstructable without cycles.

**Intent / User Need:**  
Traceability is bidirectional — back to source lot, forward to everywhere used.

**Inputs:**  
A parent lot + a portioning/repack/split action + resulting quantity.

**Outputs:**  
A parent-child lot graph reconstructable end-to-end for any lot.

**Trigger:**  
A portioning/repack/split/refreeze action on an existing lot.

**Invariants:**  
Every derived lot has exactly one immediate parent; no cycles; parent decrement + child creation are atomic; lineage is fully reconstructable.

**Failure Behavior:**  
A derived lot with no resolvable parent is rejected (no orphan lots); a lineage that would form a cycle is rejected.

**Failure Mode Addressed:**  
Losing the thread on where a portion came from — unable to trace a plated item back through repacks/portions to the original received lot (traceability + recall exposure).

**Acceptance Criteria:**  
Every derived lot references its immediate parent and complete lineage can be reconstructed without cycles.

**Verification Method:**  
Schema constraints and lineage-query test.

**Maintenance Requirements:**  
Enforce the acyclic constraint at the schema level; keep the portioning UI prompting crew with the correct open parent lots.

**Dependency Notes:**  
Built on the transactions from CLOSE 6. Lineage prompts crew with matching open lots at portioning time. CROSS-REF: overlaps KIT-019 (parent-child lot tracking) — reconcile in debate. Part of BUNDLE-INVENTORY-LOT-TRACKING. Parent CLOSE 5.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inventory-supports-parent-child-lot-lineage-c0ccf7e98f554904ac4b996da75db6c1_

---
## URS-INV-003 — Inventory lot retains complete traceability fields
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: each lot carries full provenance (item, original/remaining qty, unit, source, received date, parent lot, bin, status, event, responsible crew), with remaining qty always reconciling to recorded movements.

**Atomic Requirement:**  
Each inventory lot shall retain item, original quantity, remaining quantity, unit, source, received date, parent lot, bin, status, event, and responsible crew provenance.

**Functional Requirement Specification:**  
Each inventory lot shall retain: item, original quantity, remaining quantity, unit, source, received date, parent lot, bin, status, event, and responsible-crew provenance. Required fields shall be non-null where applicable, and every remaining-quantity value shall be explainable from the recorded transactions.

**Inputs:**  
Lot creation data (item/qty/unit/source/received/bin) + the running transaction ledger + parent-lot link.

**Outputs:**  
A complete, reconcilable lot record supporting cost/age/location/traceability queries.

**Trigger:**  
Lot creation, and every transaction that changes its remaining quantity.

**Invariants:**  
Required fields non-null where applicable; remaining_quantity always reconciles to original minus recorded transactions; every lot ties to its responsible crew + event.

**Failure Behavior:**  
A lot missing a required field (where applicable) is rejected; any remaining_quantity that can't be explained from the transaction history is flagged as a reconciliation error.

**Failure Mode Addressed:**  
Untrustworthy stock records — a quantity that doesn't reconcile, or a lot with no source/received-date/responsible-crew, making it useless for cost, freshness, or traceability.

**Acceptance Criteria:**  
Required fields are non-null where applicable and quantity changes are explainable from transactions.

**Verification Method:**  
Schema and reconciliation tests.

**Maintenance Requirements:**  
Keep the field set aligned with KIT-018/019 if merged; run periodic reconciliation of remaining vs ledger.

**Dependency Notes:**  
The lot record schema underlying CLOSE 6/CLOSE 7. remaining_quantity is explained by the transaction ledger (CLOSE 6). CROSS-REF: overlaps KIT-018/019 field sets — reconcile in debate. Part of BUNDLE-INVENTORY-LOT-TRACKING. Parent CLOSE 5.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inventory-lot-retains-complete-traceability-fields-d6e9887241174e95a4dd1bb2408a7a2a_

---
## URS-INV-004 — Inventory closures can propose labels
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: closing an inventory task offers a pre-filled label (lot/item/qty/bin) to confirm-and-print — nothing prints on cancel.

**Atomic Requirement:**  
A configured inventory-related card closure shall propose a pre-populated label without printing until crew confirmation.

**Functional Requirement Specification:**  
A configured inventory-related card closure shall PROPOSE a pre-populated label (lot/item/quantity/bin) without printing, until the crew confirms. Cancel prints nothing; confirm creates exactly one print request. The proposal is pre-filled from canonical lot data — crew confirm, they don't re-enter.

**Inputs:**  
The closing inventory lot record (URS-INV-003); crew confirm/cancel.

**Outputs:**  
A pre-populated label proposal, and on confirm exactly one print request to the label subsystem.

**Trigger:**  
A configured inventory-related card closes.

**Invariants:**  
No print without explicit crew confirmation; exactly one print request per confirmation; proposal data matches the canonical lot.

**Failure Behavior:**  
Cancel prints nothing (no accidental labels/waste); confirm creates exactly one print request. A malformed proposal blocks with a prompt rather than printing bad data.

**Failure Mode Addressed:**  
Wasted labels / mislabeled lots from auto-printing, and the friction of re-typing lot data that the system already knows.

**Acceptance Criteria:**  
Proposal contains lot/item/quantity/bin data; cancel prints nothing; confirm creates one print request.

**Verification Method:**  
Inventory-to-label integration test.

**Maintenance Requirements:**  
Keep the proposal template aligned with the Type A label spec (URS-LABEL-001) and the printer path (URS-LABEL-005).

**Dependency Notes:**  
Proposal is populated from the lot record (CLOSE 8). Confirmed print request goes to the label subsystem (URS-LABEL family / LABEL 1). CROSS-REF: KIT-018 (label print on inventory close). Part of BUNDLE-INVENTORY-LOT-TRACKING. Parent CLOSE 5.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Inventory-closures-can-propose-labels-93fde16b97b84536b53c26f16361768a_

---
## URS-INV-005 — MT2 inventory dashboard shows drawdown, age, bins, and alerts
**Status:** Spec Drafted | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: one screen (MT2) shows current stock, drawdown rate, aging, bin location, and alerts — numbers reconcile to the ledger, stale data clearly marked.

**Atomic Requirement:**  
The MT2 inventory view shall show current drawdown, lot age, bin map, and active inventory alerts from canonical lot and transaction data.

**Functional Requirement Specification:**  
The MT2 inventory view shall show current drawdown, lot age, bin map, and active inventory alerts, computed from canonical lot and transaction data. Dashboard totals shall reconcile to the lot ledger, and stale data shall be visibly identified (never shown as current).

**Inputs:**  
Canonical lot records + transaction ledger (URS-INV-001/002/003); configured alert thresholds (age, low-stock).

**Outputs:**  
A rendered MT2 inventory dashboard: drawdown rate, lot age (green/yellow/red), bin map, stock state, alerts — reconciling to the ledger.

**Trigger:**  
Continuous display; refresh on inventory-transaction events (URS-INV-001).

**Invariants:**  
Displayed totals always reconcile to the lot ledger; stale data is always visibly marked; MT2 is the canonical inventory surface (MT1=kanban, z33=scoreboard).

**Failure Behavior:**  
Dashboard totals that don't reconcile to the lot ledger are flagged, not silently shown; stale data is visibly identified rather than presented as current.

**Failure Mode Addressed:**  
Acting on wrong stock levels — over/under-buying, using expired product — because the inventory picture was stale or didn't match the ledger.

**Acceptance Criteria:**  
Dashboard totals reconcile to the lot ledger and stale data is visibly identified.

**Verification Method:**  
Reconciliation test and display inspection.

**Maintenance Requirements:**  
Keep alert thresholds tuned; verify reconciliation after any transaction-model change; MT2 already exists (no new hardware).

**Dependency Notes:**  
Reads canonical lot + transaction data (CLOSE 6/CLOSE 7/CLOSE 8). Renders on MT2 (the west kitchen MicroTouch). Staleness surfacing aligns with HEALTH 9 fail-visible principle. CROSS-REF: overlaps KIT-021 (MT2 inventory dashboard) — reconcile in debate. Part of BUNDLE-INVENTORY-LOT-TRACKING. Parent CLOSE 5.

**Open Questions:**  
Candidate for its own SCREEN-* row once built (see CLOSE 5).

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/MT2-inventory-dashboard-shows-drawdown-age-bins-and-alerts-b6964d4e2ad54c909eccbb54886e0d6f_
