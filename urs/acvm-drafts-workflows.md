# AC/VM drafts — workflows cluster (exemplars: W9, W7)

Status: DRAFT for Nick review. Not yet applied to corpus.

---

## W9 — Square Menu Sync (class: D)

### Acceptance Criteria

NORMAL:
- A new item added in Square appears in `menu_items` within one 6h sync cycle,
  with all 11 attributes populated.
- A price change in Square is reflected in `menu_items` on the next sync.

EDGE:
- Item deactivated in Square → `is_active=false` only after 2 consecutive misses
  (not on the first miss — network-blip protection).
- Item reactivated in Square → `is_active=true` on the next sync.
- Item at Square's attribute-cap boundary (approaching the 20-definition limit)
  → remaining headroom is visible.

NEGATIVE:
- `SearchCatalogObjects` used anywhere in the codebase → BLOCKER (it silently
  returns no custom-attribute values). Code-search must show zero hits.
- 2 consecutive full-sync failures → Twilio SMS to Nick fires. Never silent.

SILENT-FAILURE:
- One item silently missing an attribute after sync → a completeness check catches
  it and routes to review; it does not pass as synced.

CHALLENGE:
- Kill Square API access mid-sync → sync fails loudly, no partial/corrupt write to
  `menu_items`, next scheduled cycle retries cleanly.
- Inflate the test catalog to a large set (≥1,000 items) → sync completes within
  the SLA window without dropping attributes.

### Verification Method

1. Live insert: add a test item in Square; confirm it lands in `menu_items` via psql
   within ≤6h. Evidence: Square dashboard screenshot + psql result.
2. Code-search: `grep -rn SearchCatalogObjects` across the repo → zero hits. Evidence:
   command + output.
3. Completeness audit: psql join Square catalog vs `menu_items` → 100% attribute
   coverage. Evidence: query + result screenshot.
4. Failure drill: stop the sync service, force 2 consecutive failures, observe Twilio
   SMS to Nick. Evidence: phone SMS screenshot + timestamped observation log.
5. Blip test: block Square API for one cycle → item NOT deactivated; block two cycles
   → item deactivated. Evidence: observation log of both states.

---

## W7 — Invoice Draft Workflow (class: INF)

### Acceptance Criteria

NORMAL:
- "Create AI Draft" pre-fills all 8 form sections from PostgreSQL within ~10–15s,
  with a confidence label (Pulled/Inferred/Guessed) on every field.

EDGE:
- A field whose source data is missing → left blank with honest low confidence;
  never fabricated.
- `kitchen_departure_time` is computed deterministically (crew_arrival − drive_time −
  pack_buffer), shown read-only with its confidence label — not AI-generated.
- Customer with an unusual dietary combination (e.g. nut-free + halal + vegan) →
  dietary flags correct on every food line.

NEGATIVE:
- AI attempts to invent a serves count, hold time, or pan geometry → BLOCKED;
  the field routes to Sandra review. Never a fabricated number.
- AI draft generated from an empty CRM record → no invented "WHY" sentences;
  those lines are absent or explicitly blank.

SILENT-FAILURE:
- A value the AI "pulled" that does not actually exist in PostgreSQL → caught in
  audit (every Pulled label must trace to a real row). No phantom pulls.

CHALLENGE:
- Feed a lead with 0 CRM notes + 0 call summaries → output is still structurally
  valid (sections present, food lines from catalog, blanks where unknown).
- Sandra changes 5 fields after draft; Nick reviews → the delta between AI draft
  and Sandra's edits is visible and reviewable, not silently overwritten.

### Verification Method

1. Scenario battery: run 20 lead scenarios (rich/empty/edge dietary) through the
   draft generator; inspect output. Evidence: screenshots of form states + log.
2. Fabrication check: feed deliberately empty CRM → confirm zero invented WHY
   sentences, confidence labels honest. Evidence: screenshot + observation log.
3. Arithmetic guard: code-review + code-search proving `kitchen_departure_time`
   comes from a deterministic function, LLM only narrates. Evidence: diff + grep.
4. Live pilot: Sandra runs one real invoice draft; Nick reviews delta. Evidence:
   before/after screenshots + observation log.
5. Confidence audit: sample 20 drafts; every "Pulled" label traces to a real
   PostgreSQL row. Evidence: query + result log.
