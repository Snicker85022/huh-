# Taza OS URS — CX cluster
_Exported: 2026-09-19 21:35 | 7 rows_
_Source: Notion Master URS & Specification Registry_

---
## CX-001 — Three $0 custom line item blocks on every invoice
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: EVENT DETAILS, VENUE & LOGISTICS, SETUP SPECIFICATION as clear $0 blocks on every invoice, before food items.

**Functional Requirement Specification:**  
Every Square customer invoice must contain three dedicated $0 custom line items: (1) EVENT DETAILS, (2) VENUE & LOGISTICS, (3) SETUP SPECIFICATION — positioned before food line items.

**Failure Behavior:**  
Fallback: Sandra manually adds event details to Delivery & Setup note.

**Acceptance Criteria:**  
NORMAL:
1. Every Square customer invoice contains exactly three $0 custom line items (EVENT DETAILS, VENUE & LOGISTICS, SETUP SPECIFICATION), positioned before food line items.

EDGE:
2. An invoice with zero food line items (edge-case order type, if possible) still gets all three $0 blocks in correct position.
3. An invoice regenerated/edited after initial creation preserves exactly three blocks — doesn't duplicate them on a second generation pass.

NEGATIVE:
4. An invoice missing one or more of the three blocks (generation partially failed) is caught before publish — never ships to a customer with an incomplete block set.

SILENT FAILURE:
5. Block ORDER drifting (e.g. SETUP SPECIFICATION appearing before EVENT DETAILS) would be a subtle but real brand/clarity defect — verify exact ordering is enforced, not just presence of all three.
6. A $0 line item accidentally carrying a non-zero price (data/template bug) would be a direct billing error — verify price is hard-enforced at zero for these three blocks specifically, not just 'usually zero.'

**Verification Method:**  
1) Unit tests: exactly 3 blocks present, correct order, correct position relative to food items, price hard-locked at $0. 2) Regeneration test: regenerate an existing invoice, confirm no duplicate blocks. 3) Pre-publish gate test: simulate a partial-generation failure (one block missing), confirm publish is blocked. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
CONSOLIDATION CANDIDATE: [[SPEC:CX-001]]..007 (7 rows, one invoice-block feature) — consider merging.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Three-0-custom-line-item-blocks-on-every-invoice-3cfe152fc19981e5a729f8397cda54e8_

---
## CX-002 — EVENT DETAILS block
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: EVENT DETAILS block shows event name, date, day-of-week, service window, guest count breakdown.

**Functional Requirement Specification:**  
EVENT DETAILS block: event name, date, day-of-week, service window (start–end time), guest count (adults/kids/staff).

**Failure Behavior:**  
Fallback: partial data acceptable, blank fields flagged for Sandra review.

**Acceptance Criteria:**  
NORMAL:
1. Block shows event name, date, day-of-week, service window (start-end), and guest count broken out by adults/kids/staff.

EDGE:
2. Day-of-week is correctly computed from the date, not independently entered data that could disagree with the actual calendar date.
3. A guest count of zero for one category (e.g. no kids) shows correctly as zero, not omitted/blank in a way that reads as missing data.
4. Multi-day events (if they exist) are represented correctly, not truncated to a single date/window.

NEGATIVE:
5. Missing guest count blocks generation with a clear error — downstream quantity math (invoice food line items, packing) depends on this being real.

SILENT FAILURE:
6. Day-of-week silently disagreeing with the actual date (stale computation, timezone bug) would be a visible customer-facing error that undermines trust — verify against real calendar dates including a DST-boundary date.
7. Guest count categories that don't sum to a sensible total (e.g. displayed adults+kids+staff doesn't match a total referenced elsewhere in the invoice) must be caught as a consistency check.

**Verification Method:**  
1) Unit tests: full-data render, zero-count category, missing-guest-count blocks generation. 2) Date-correctness test: verify day-of-week against real dates including a DST transition date and a leap-year date. 3) Cross-block consistency test: confirm guest count here matches any guest-count reference elsewhere in the generated invoice. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/EVENT-DETAILS-block-3cfe152fc19981e496f8c75bcd4689e7_

---
## CX-003 — VENUE & LOGISTICS block
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: VENUE & LOGISTICS block shows venue address, crew arrival, computed kitchen departure, access notes.

**Functional Requirement Specification:**  
VENUE & LOGISTICS block: venue name + full address, crew arrival time, kitchen departure time (computed), access notes (gate code, parking, load-in door).

**Failure Behavior:**  
Fallback: access notes omitted if blank; departure shows 'TBD' if zip lookup unavailable.

**Acceptance Criteria:**  
NORMAL:
1. Block shows venue name + full address, crew arrival time, computed kitchen departure time, and access notes (gate code, parking, load-in door).

EDGE:
2. Kitchen departure time computation correctly accounts for drive time to the specific venue address, not a flat default regardless of location.
3. A venue with no special access notes (no gate code needed) shows a clean state, not an empty-looking placeholder.

NEGATIVE:
4. Missing venue address blocks kitchen-departure-time computation with a clear error — the system does not silently compute a meaningless departure time from missing location data.

SILENT FAILURE:
5. Access notes containing sensitive info (gate codes) must only appear on this internal crew-facing context, never leak onto anything customer-visible — verify this block's data doesn't get reused in a customer-facing surface by mistake.
6. Kitchen departure time silently using stale/cached drive-time data (traffic pattern changes, venue changes) must be caught — verify it's computed fresh at generation time, not cached from an earlier draft.

**Verification Method:**  
1) Unit tests: full-data render, missing-address blocks computation, missing-access-notes clean render. 2) Data-leak test: confirm gate codes/access notes never appear on any customer-facing surface (cross-check against [[SPEC:CX-001]]..007's customer-visible blocks). 3) Freshness test: confirm kitchen_departure recomputes from current data at generation time, not a stale cached value. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/VENUE-LOGISTICS-block-3cfe152fc19981c0a040d3c15e01b8ce_

---
## CX-004 — SETUP SPECIFICATION block
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: SETUP SPECIFICATION block shows setup type, table count/size, linens tier, decor/equipment notes.

**Functional Requirement Specification:**  
SETUP SPECIFICATION block: setup type (Indoor/Outdoor/Hybrid), tables count + size, linens tier, any decor/equipment notes from invoice form.

**Failure Behavior:**  
Fallback: omit missing fields, Sandra reviews before publishing.

**Acceptance Criteria:**  
NORMAL:
1. Block shows setup type (Indoor/Outdoor/Hybrid), tables count + size, linens tier, and any decor/equipment notes, sourced from the invoice form.

EDGE:
2. An event with no decor/equipment notes shows a clean empty/omitted state, not a blank-looking placeholder that reads as an error.
3. Hybrid setup type correctly reflects mixed indoor/outdoor logistics in the notes, not just the single label with no supporting detail.

NEGATIVE:
4. A required field (setup type, tables count) missing from source data blocks invoice generation with a clear error rather than publishing an incomplete block.

SILENT FAILURE:
5. Setup type silently defaulting to a wrong value (e.g. Indoor) when the source data is actually ambiguous/missing would misinform kitchen_departure and logistics planning downstream — verify there's no silent default, only explicit values or a blocking error.
6. This block feeds [[SPEC:CX-006]]'s backend setup_type attribute — verify the customer-visible text and the backend attribute value never disagree (single source, not two independently-set values that can drift).

**Verification Method:**  
1) Unit tests: full-data render, missing-decor-notes clean render, missing-required-field blocks generation. 2) Consistency test: confirm this block's setup_type text and [[SPEC:CX-006]]'s backend setup_type attribute are derived from the same source value, never independently divergent. 3) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/SETUP-SPECIFICATION-block-3cfe152fc199812ba7e8c22d3c3683db_

---
## CX-005 — WHY context (decision rationale on invoice)
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: invoice includes 1-3 sentences of decision context (e.g. referencing an earlier call) so it reflects the actual conversation, not a generic template.

**Functional Requirement Specification:**  
WHY context: AI reads customer CRM notes + decision history + preference fields → adds 1–3 decision-context sentences to EVENT DETAILS or VENUE block, e.g. "Based on your May 20 call with Sandra, we've selected salmon as requested."

**Failure Behavior:**  
Fallback: no WHY context, invoice contains logistics only.

**Acceptance Criteria:**  
When CRM notes contain a preference or decision, at least one WHY sentence appears on the invoice; no hallucinated facts; only confirmed CRM data used

**Verification Method:**
1. [AUTO] Trigger: a CRM note containing a preference/decision → at least one WHY sentence appears on the invoice. Evidence: test output.
2. [AUTO] No-hallucination: empty CRM notes → zero WHY sentences. Evidence: test output.
3. [NICK] Live: Nick reviews a real invoice and confirms WHY text matches the call record. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/WHY-context-decision-rationale-on-invoice-3cfe152fc19981b1996bcf4645b81ee0_

---
## CX-006 — Square Order Custom Attributes (backend)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: setup_type/tables_count/linens_tier/kitchen_departure captured as backend Square Order Custom Attributes for downstream routing, not customer-visible.

**Functional Requirement Specification:**  
Square Order Custom Attributes — four backend fields written by AI: setup_type (Indoor/Outdoor/Hybrid), tables_count (number), linens_tier (None/Standard/Premium), kitchen_departure (timestamp). Not customer-visible; used for routing and timeline generation.

**Failure Behavior:**  
Fallback: store in NocoDB event record only.

**Acceptance Criteria:**  
NORMAL:
1. Four backend attributes (setup_type, tables_count, linens_tier, kitchen_departure) are written by AI, not customer-visible, used for routing/timeline.

EDGE:
2. tables_count = 0 (no tables needed, e.g. passed-appetizer-only event) is stored as a real zero, not null/omitted in a way that breaks downstream math.
3. linens_tier = None is a valid, distinct value from 'not yet determined' — verify these two states aren't conflated.

NEGATIVE:
4. An attempt to set these attributes to a value outside their defined enum/type (invalid setup_type string, non-numeric tables_count) is rejected, not silently coerced or stored malformed.

SILENT FAILURE:
5. These attributes must genuinely never appear on any customer-visible surface (Square customer view, printed invoice) — verify this with an actual customer-view render check, not just 'not customer-visible' as a design intent.
6. kitchen_departure (timestamp) drifting out of sync with the customer-visible VENUE & LOGISTICS block's departure time ([[SPEC:CX-003]]) would mean routing/timeline logic operates on a different value than what the crew sees — verify these are the same source value, not independently computed.

**Verification Method:**  
1) Unit tests: each attribute's valid values including edge values (zero, None), invalid-value rejection. 2) Customer-view render test: render the actual customer-facing Square invoice, confirm none of these four attributes appear anywhere on it. 3) Consistency test: confirm kitchen_departure here is byte-identical to the value shown in [[SPEC:CX-003]], sourced from the same computation, not two independent ones. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Square-Order-Custom-Attributes-backend-3cfe152fc19981e89972fcea21bacbc6_

---
## CX-007 — invoice_blocks_generator prompt
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Need: prompt reads event data + CRM notes → outputs the 3 customer blocks + 4 backend attributes as structured JSON, zero hallucination.

**Functional Requirement Specification:**  
invoice_blocks_generator prompt: AI prompt that reads event data + CRM notes → outputs three $0 line item objects + four Order Custom Attribute values as structured JSON. Zero hallucination — only confirmed data used.

**Failure Behavior:**  
Fallback: template-based blocks with Sandra-entered values (degrades WHY layer).

**Acceptance Criteria:**  
NORMAL:
1. Prompt reads event data + CRM notes, outputs exactly three $0 line-item objects + four Order Custom Attribute values as valid structured JSON.

EDGE:
2. Event data with sparse/minimal CRM notes still produces valid output for all seven fields — the model doesn't invent detail to fill gaps (zero-hallucination requirement).
3. Event data containing conflicting information (e.g. two different guest counts mentioned in notes) surfaces the conflict for human review rather than silently picking one.

NEGATIVE:
4. Malformed or unparseable JSON output from the model is caught before reaching Nick/Sandra's approval task, triggering a retry (per the JSON retry loop, [[SPEC:SW-004]]) not a broken invoice draft.
5. Any output field NOT traceable to confirmed source data is rejected — this needs an actual verification mechanism, not just a prompt instruction trusted to be followed.

SILENT FAILURE:
6. 'Zero hallucination' is the core promise of this row and the hardest to verify — this requires adversarial testing (deliberately sparse/ambiguous inputs) to catch cases where the model fills gaps with plausible-sounding invented detail, since a hallucinated value looks identical to a real one until checked against source.
7. Prompt-injection risk: CRM notes may contain customer-supplied text (via voice transcription); confirm this prompt's XML-tag input isolation ([[SPEC:SW-012]]) actually prevents injected instructions in notes from altering output structure.

**Verification Method:**  
1) Golden-set tests: run against a set of real historical events with known-correct expected output, verify exact field accuracy. 2) Adversarial hallucination test: deliberately sparse/ambiguous input sets, manually verify every output field traces to actual source data with nothing invented. 3) Malformed-output test: force a bad JSON response, confirm the retry loop ([[SPEC:SW-004]]) engages rather than a broken draft reaching approval. 4) Prompt-injection test: CRM notes containing an injected instruction (e.g. "ignore previous instructions"), confirm output structure is unaffected. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/invoice_blocks_generator-prompt-3cfe152fc19981488fede8521df9b830_
