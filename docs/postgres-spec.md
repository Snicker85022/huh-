# Taza OS — PostgreSQL Specification (Living Document)

**Author:** Cortex (DeepSeek-based agent) / Nick Lockard | **Status:** Living — updated as the URS cluster review progresses
**Relationship to DB-001:** DB-001's source of truth is the Notion "Data Schemas & Field Maps" doc, which is **frozen** (Notion manual-only, 2026-08-03). This file is the living surrogate; when DDL is written it must satisfy DB-001's schema-diff acceptance criteria against this file.

## Revision log

| Date | Source | Change |
|------|--------|--------|
| 2026-09-20 | Workflows cluster review (Topics 1–2, Nick decisions) | Initial seed. Mail-loop decision, event-confirmation-by-email, kitchen_exit_time / venue_arrival_time split, event lifecycle, task close contract inventory. |
| 2026-09-20 | Topic 3 (Nick decision) | **D4 LOCKED — collapse to single store.** Everything into tazaos PostgreSQL; NocoDB = UI skin over external DB. MIGRATION-001 added, blocks all V1.0 code. D5 canonical store rule incl. "no NocoDB API from workflow code". `close_kind` 7th variant identified by Nick as STANDARD_COMPLETE (flagged; confirmed at PROD-38 review). |
| 2026-09-20 | Nick directive | Standing schema rule (§5.0): `created_at`/`updated_at` + `set_updated_at()` trigger on EVERY table (existing + future). Named tables `pack_rate_config`, `lkl_records`, `crm_sessions` → object model. Timestamps folded into MIGRATION-001 scope. |
| 2026-09-20 | W2 review (Nick Q1–Q5) | **W2 v2 LOCKED.** Category = deterministic thresholds on profit_score (5/4→Hot, 3→Warm, 2→Low, 1→Pass; one-level AI override with written red_flags reason only). Rubric → ~/repo/config/lead_scoring_rubric.md, git-versioned, embed rubric_version=commit hash per score. Fail-to-Low + scoring_ai_unavailable. Re-score triggers (W4 Done / material field update / manual); score_history JSONB append-only. Handoff: W2 tags + Hot SMS only; W6/W12/W13 route. Leads table scoring fields added (D6–D8). |
| 2026-09-20 | Nick confirm | lkl_bins + lkl_records split **confirmed** — keep separate. Bin master (slowly changing) vs append-only close-capture log (high frequency); FK lkl_records→lkl_bins is correct architecture. §2.4 dedicated LKL section; lkl_bins added to §5.0 timestamp scope. |
| 2026-09-20 | W3 review (Nick Q1–Q3 + edge) | **W3 v2 LOCKED.** Fire at 60-min window entry, 5-min floor, one brief per task (idempotent), re-brief only if due shifts ≥15 min (logged). Poll 5 min, delivery SLA ≤2 min. Empty touchpoints → "no recent touchpoints — call fresh" (no fabrication). pre_call_briefs table added (§2.8). D9. |
| 2026-09-20 | W4 review + global notification | **W4 v2 LOCKED.** Canonical CRM names: leads, customers, touchpoints (opportunities=V1.1). W4 writes customers (if promoting) + touchpoints (always). Session_status lifecycle (active/partial/done/abandoned). Extraction validation → exceptions_queue (+ SMS alert to Sandra). Sandra notification channels locked: Twilio SMS primary, ntfy secondary for non-urgent only. CRM naming drift killed (§7-6 → RESOLVED). W16 delivery method + iOS WebKit constraints recorded (parked). D10–D12. |
| 2026-09-20 | W5 + W6 superseded + W16 updated | **W5 v2 LOCKED.** Tiered SLA: ≤15s → <1s, 16–60s → <3s, >60s → rejected. SLA measured clip-end to browser. Fail visible on Whisper down. **W6 Superseded.** Lead scoring now real-time via W2. Retry muddle moot. **W16 spec stub updated.** Google Cloud Speech-to-Text (streaming, diarized, custom vocab). Every 30s → OpenRouter scripts. On Done → structured extraction → leads + touchpoints + crm_sessions pipeline. Cost ~$16/mo peak. w16.tazacateringphoenix.com via Cloudflare tunnel (parked). D13. |
| 2026-09-20 | W9 review (Q1–Q2) | **W9 v2 LOCKED.** 6-hour scheduled pull = V1.0 primary sync (webhook = V1.1 extension point stub). Soft-delete only: `is_active` BOOLEAN NOT NULL DEFAULT TRUE, `last_synced_at` TIMESTAMPTZ added to menu_items. 2 consecutive sync failures → Twilio SMS to Nick (system/ops alert). D14. |
| 2026-09-20 | W10 superseded + Square detection pattern + dedicated inbox | **W10 Superseded** — replaced by Taza Calendar Web App (`calendar.tazacateringphoenix.com`, reads/writes `events` table). W16 = sole Google Cloud dependency. **D16: Square event detection pattern** — email-then-fetch from dedicated monitoring inbox (Nick to set up). Sender `invoicing@messaging.squareup.com`, subject parse, body extraction, one targeted Square API call. **D1 updated**: dedicated inbox replaces `hello@` as poll target. `source_type` added to processed_email_ledger. |
| 2026-09-20 | PROD-30 spec stub (V1.1) | **PROD-30 direction confirmed (Nick).** Taza Invoice & Payment Orchestration System — own invoicing via Helcim→Stripe→Square failover routing. ~$2,700+/yr savings. V1.1, parked. Tables: `invoice_line_items`, `payment_attempts`, `invoice_links` added to §2.7. D17. |
| 2026-09-20 | W2 review (Nick answers Q1–Q5) | W2 v2 LOCKED. Category = deterministic thresholds on profit_score (5/4→Hot, 3→Warm, 2→Low, 1→Pass; one-level AI override w/ written red_flags reason only). Rubric → ~/repo/config/lead_scoring_rubric.md, git-versioned, rubric_version = commit hash on lead. Fail-to-Low + scoring_ai_unavailable flag. Re-score triggers defined; score_history JSONB (append-only). Handoff: W2 tags only; W6/W12/W13 route. Leads table gets scoring fields. |
| 2026-09-25 | Nick directive (mURS review) | **D18 LOCKED — Square attrs = 11 (6 visible + 5 hidden).** "12/7-visible" retired; §2.6 corrected. CAT-001 export still says 12 (flagged for mURS pass 1). |
| 2026-09-25 | Nick directive (mURS review) | **D19 LOCKED — deposit = fixed dollar.** `deposit_basis_cents` frozen at first publish; % is form-only default (50%). §2.7 updated. |
| 2026-09-25 | Live DB inspection (Cortex) | Four-DB inventory added (§2.9). NocoDB already pointed at tazaos (MIGRATION-001 step 4 mostly done; steps 1/2/3/5 open). WireGuard refs in security.md/health.md flagged for retirement. |
| 2026-09-30 | Nick decision (Pass 1, W11) | **D21 LOCKED — W11 folded into PROD-22.** `changelog` = alert queue only (W12 writes, W13 reads). Raw before/after history lives in `audit_log` (PROD-22). W11 becomes a read-only changelog view over `audit_log` — removes the duplicated raw-diff capture path. |

## 0.1 Two numbering systems — do not conflate

- **D1–D23 (no dash)** = THIS file's living decisions. Authoritative.
- **D-XXX (dash + 3 digits)** = legacy Notion decision IDs scattered through the
  cluster FRS prose (D-004, D-019, D-021, D-025, D-060, D-061...). Unmapped,
  frozen with Notion. They are NOT this file's D-numbers. When a spec says
  "Implements D-019", it does NOT mean the D19 deposit decision above.
  See `urs/alias-map.tsv` class `legacy-decision-ref`.

## Status legend

- **LOCKED** — decided explicitly by Nick in this review cycle; normative.
- **DRAFT** — drafted from cluster specs; awaiting that spec's review turn for confirmation.
- **TBD** — open item (tracked in §7); not safe to implement.

---

## 1. Global decisions already applied (2026-09)

- **D6 — Lead scoring is deterministic-threshold-first (W2 v2, LOCKED).** profit_score (1–5) is the semantic input; category is the deterministic output: 5/4→Hot, 3→Warm, 2→Low, 1→Pass. AI may adjust a category by **at most one level** with an explicit red_flags entry + written reason — never a silent override. Thresholds live in the rubric config (`~/repo/config/lead_scoring_rubric.md`), never hardcoded. Rubric is Nick-only-edited, git-versioned; `rubric_version` = commit hash of the rubric file at scoring time, embedded per score.
- **D7 — Scoring failure fails safe (W2 v2, LOCKED).** AI unavailable → category=Low + `scoring_ai_unavailable=true`. Low is safe: it doesn't suppress Sandra's attention, it just doesn't escalate; the flag puts it in manual review instead of letting a moderate-looking default masquerade as confident.
- **D8 — W2 tags; others route (W2 v2, LOCKED).** W2 sets category on the lead and fires the Hot SMS (Sandra Ping Policy iv) — nothing else. Downstream: Warm = *eligible* for the W6 morning digest (W6 decides rank, top-5 only); Low/Pass = eligible for weekly review (W12/W13 route). W2 has no direct touch on digest or weekly-review queues.


- **D1 — External events arrive by email, not webhook/API, for V1.0.** One monitoring loop polls a dedicated monitoring inbox (Nick to set up — name TBD; Gmail API, 1–2 min), classifies every message, and fans out. This inbox receives ONLY automated emails from Square and Wix — all other senders blocked. No human reads this inbox; mail can be archived/deleted after processing. Classes: `FORM` (Wix intake/contact-us), `DIRECT` (free-form customer email), `AUTO` (out-of-office/bounce/loop — zero side effects), `SQUARE_PAYMENT` (Square deposit/payment confirmation), `SQUARE_UPDATE` (Square invoice updated, no payment event), `SQUARE_MENU_CHANGE` (Square catalog change). External webhooks/API are V1.1 extension points (stubbed + documented hook locations). Internal service-to-service webhooks (NocoDB → W11, MicroTouch → W14) are unaffected.
- **D2 — Event "Confirmed" is set by the deposit email.** Parse SQUARE_PAYMENT email → order/invoice ID → event lookup → status = `CONFIRMED` → triggers W15 (timeline/BEO) then PROD-06 (task-chain generation). Unparseable email → exceptions queue → Sandra confirms manually. Refund **rescinds** Confirmed (~1/410 events); re-payment re-triggers. Each transition = one authorized W15 run (idempotent on invoice ID + email Message-ID).
- **D3 — kitchen_departure is two different quantities; split the name everywhere.**
  - `kitchen_exit_time` — ops-only, lives in the BEO, never customer-facing. `= crew_arrival − drive_time − pack_buffer`.
  - `venue_arrival_time` — Square Order Custom Attribute, customer-facing invoice. `= kitchen_exit_time + drive_time`.
  - Writer rule (one authoritative writer per lifecycle stage): **W7 estimates (or blank) at invoice draft; W15 authorizes at Confirmed (overwrites); nobody touches it after Event status = `IN_PROGRESS` (crew departed) — frozen.**
- **D4 — LOCKED: single store.** PostgreSQL is the migration target. The NocoDB/Postgres split accumulated by accident — never a deliberate architecture — and is **NOT permanent**. Everything collapses into tazaos PostgreSQL; NocoDB becomes a pure UI skin reconfigured to connect to tazaos as an external database (Settings → Connections). Deciding factor: simpler to maintain — one backup, one failure surface, no cross-store joins. Blocked by **MIGRATION-001** (§4); no V1.0 code before it.
- **D5 — Canonical store rule (all specs):**
  - One store: tazaos PostgreSQL, N100, 192.168.2.102:5432.
  - Connection string via env var per PROD-26 — never hardcoded anywhere.
  - NocoDB UI reads/writes tazaos **directly** — workflow code never touches the NocoDB API.
  - All workflows use direct PostgreSQL writes only.
  - Every prior "NocoDB table" reference in W/PROD specs = Postgres table behind the NocoDB skin from migration completion onward.
- **D6 — Lead scoring is deterministic-threshold-first (W2 v2, LOCKED).** profit_score (1–5) is the semantic input; category is the deterministic output: 5/4→Hot, 3→Warm, 2→Low, 1→Pass. The AI may adjust a category by **at most one level** with an explicit red_flags entry + written reason — never a silent override. Thresholds live in the rubric config (`~/repo/config/lead_scoring_rubric.md`), never hardcoded. Rubric is Nick-only-edited, git-versioned; `rubric_version` = git commit hash of the rubric at scoring time, embedded per score.
- **D7 — Scoring failure fails safe (W2 v2, LOCKED).** AI unavailable → category=Low + `scoring_ai_unavailable=true`. Low is safe: it doesn't suppress Sandra's attention, it just doesn't escalate; the flag routes to manual review instead of a moderate-looking default that lets mediocre leads masquerade as confident.
- **D8 — W2 tags; others route (W2 v2, LOCKED).** W2 sets category on the lead and fires the Hot SMS (Sandra Ping Policy iv) — nothing else. Downstream: Warm = *eligible* for the W6 morning digest (W6 decides rank, top-5 only); Low/Pass = eligible for weekly review (W12/W13 route). W2 never touches the digest or weekly-review queues directly.
- **D9 — Pre-call brief contract (W3 v2, LOCKED).** Fire on window entry (task enters 60-min window), floor of 5 min before due — never later, never sooner than needed. One brief per task (idempotent on task_id); re-brief only if due_time shifts ≥15 min, logged as re-brief with reason. Poll every 5 min; delivery SLA ≤2 min from detection. Empty touchpoints → "no recent touchpoints — call fresh" as middle paragraph — never fabricated context.

- **D10 — Sandra notification channels (global, all W-specs).** Primary: Twilio SMS for all time-sensitive notifications — HOT lead (W2), pre-call brief (W3), draft invoice ready (W7), CRM extraction failure (W4), any other actionable item. Secondary: ntfy push for non-urgent system alerts only (low-urgency exceptions flags). Nick stays on ntfy (as configured). Never use email-only for anything Sandra needs to act on. Any spec that currently says "ntfy to Sandra" → replace with "Twilio SMS to Sandra." "ntfy to Nick" stays as-is.

- **D11 — Canonical CRM table names (W4 v2, LOCKED, kills all drift).** Normalized set: `leads` (raw inbound — W1 creates), `customers` (qualified/active — promoted from leads after first booking or explicit qualification), `touchpoints` (interaction log, append-only — every call, session, email, note), `crm_sessions` (W4 conversation transcripts). `opportunities` = V1.1 deferred — V1.0 collapses opportunity tracking into leads/customers lifecycle. W4 writes to `customers` (if promoting) + `touchpoints` (always). W1 writes to `leads`. W2/W3 read from leads + touchpoints. Every prior "Accounts"/"Contacts"/"Opportunities" reference in W-specs → canonical names.

- **D12 — CRM session lifecycle + extraction (W4 v2, LOCKED).** Save every turn as it happens. Session status: `active` (in-progress), `partial` (tab close before Done), `done` (extracted), `abandoned` (24h inactivity). Never auto-extract on timeout or tab close — only explicit "Done." Extraction output validated against a schema; validation fails → raw transcript goes to exceptions_queue (+ SMS alert to Sandra), flagged for manual CRM entry. W4 never writes bad data to CRM tables. Raw transcript always preserved, regardless of extraction outcome.

- **D13 — W5 tiered SLA (LOCKED).** ≤15s audio → <1s, 16–60s audio → <3s, >60s → rejected at capture with "clip too long, please re-record." SLA measured clip-end to transcript in browser (includes Whisper API round-trip + network). Whisper API unavailable → fail visibly with "transcription unavailable, please type" — never a silent hang.

- **D14 — Square Menu Sync (W9 v2, LOCKED).** 6-hour scheduled pull is V1.0 primary sync; `catalog.version.updated` webhook is a V1.1 extension point stub (document hook location, do not wire in V1.0). Soft-delete only on deactivation: set `is_active = false` (keep row forever for historical invoice integrity); Square reactivates → next sync flips back to `true`. An item absent from Square response for 2 consecutive sync cycles triggers `is_active = false` (not on first miss — network blip protection). 2 consecutive full-sync failures → Twilio SMS to Nick (system/ops alert; never silent).

- **D15 — W10 Superseded.** Replaced by W10 v2: Taza Calendar Web App at `calendar.tazacateringphoenix.com` via Cloudflare tunnel. No Google Calendar, no OAuth, no sync — reads/writes the `events` table directly. Nick and Sandra add/edit events directly. W16 is now the sole Google Cloud dependency in V1.0.

- **D16 — Square event detection pattern (canonical, W15 + PROD-06).** V1.0 pattern = email-then-fetch via D1's dedicated inbox. Sender: `invoicing@messaging.squareup.com`. Subject parse: `#([A-Z0-9-]+)` extracts invoice number (e.g. `LH-DS-10032026` = initials + event type + date). Body contains: customer contact, event date, delivery time, venue address+zip, line items, total. Classify as `SQUARE_PAYMENT` (deposit received) or `SQUARE_UPDATE` (invoice changed) from subject. Extract body data + one targeted Square API call (`GET /v2/invoices/{invoice_id}`) for authoritative state. Route: payment → W15 + PROD-06 task chains; invoice published/updated → W7 approval check; items changed post-confirmation → flag Sandra. Square webhook = V1.1 extension point stub only.

- **D17 — PROD-30 direction confirmed (V1.1, parked).** Taza Invoice & Payment Orchestration System. Replaces Square invoicing partially (Square = last-resort fallback). Failover routing: Helcim (primary, ~2.5%) → Stripe (secondary, ~2.9%) → Square (fallback, ~3.3%). Own invoice generation + delivery via dedicated web app (`invoices.tazacateringphoenix.com`). Estimated savings ~$2,700+/yr at current volume. Not built until V1.0 review complete and MIGRATION-001 done.
- **D18 — Square Catalog attributes = 11, not 12 (LOCKED, Nick 2026-09-25).** 6 visible (Sandra-editable): serves_min, serves_max, pricing_unit, dietary_flags, allergen_notes, station_type. 5 hidden (API/RAG only): hot_hold_max_min, cold_hold_max_min, prep_advance_max_hr, quality_risk, default_pan_footprint. "12 (7 visible + 5 hidden)" is retired; the CAT-001 count discrepancy resolves to 11. §2.6 corrected.
- **D19 — Deposit = fixed dollar (LOCKED, Nick 2026-09-25).** `deposit_basis_cents` frozen at first publish. Sandra selects a % in the form (default 50%); the dollar amount is computed from the current subtotal at that moment; the DOLLAR figure is what locks. Later invoice changes never move the deposit. Reconciles PROD-08 ("fixed dollar") with the 50% default.
- **D21 — Changelog vs audit_log (LOCKED, Nick 2026-09-30).** W11 no longer writes its own raw before/after changelog — that duplicated PROD-22's `audit_log`. `audit_log` (PROD-22, append-only, trigger-fired) is the sole history-of-record. `changelog` becomes the **alert queue** (W12 writes, W13 reads). W11 becomes a read-only changelog view over `audit_log` for the key tables (Leads, Customers, Invoices, Tasks).

---

## 2. Object model

All tables carry `created_at` / `updated_at` per §5.0 (standing schema rule) — omitted from the per-table listings below for brevity; **normative**. Storage: tazaos PostgreSQL (D4), single store.

### 2.1 events — Event / gig records (DRAFT; lifecycle locked in D2; store = tazaos per D4)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| invoice/order ref | text | Square order ID extracted from deposit email; the join key into the email event |
| status | text enum | `PENDING → CONFIRMED → IN_PROGRESS → COMPLETE`; refund moves `CONFIRMED → PENDING` (rescind); `CANCELLED` on refund-final |
| confirmed_by | ref | SQUARE_PAYMENT email Message-ID / manual actor |
| confirmed_at | timestamptz | |
| venue_zip | text | drive-time lookup key (Phoenix-metro flat matrix) |
| drive_time_min | int | Medium confidence (zip lookup, no live traffic); V2-FEAT-006 solver replaces |
| kitchen_exit_time | timestamptz | **LOCKED name (D3)**. Ops-only; BEO artifact |
| venue_arrival_time | timestamptz | **LOCKED name (D3)**. = kitchen_exit_time + drive_time. **Postgres is the authority; the Square order attribute is a mirror** — W15 writes Postgres, syncs the attr, and the attr is frozen app-level at IN_PROGRESS |
| service_start / breakdown_complete | timestamptz | W15 timeline endpoints |
| pack_buffer_min / setup_buffer_min | int | configured via PROD-26 runtime config; values TBD with Nick (§7-2) |
| beo (payload) | jsonb | formatted BEO document |

Open: pack_rate coefficients for pack_start computation — deterministic lookup, values TBD (§7-3).

### 2.2 tasks — Task chains (PROD-01/PROD-02) (DRAFT)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| task_type | text | e.g. `follow-up call` (W1 creates exactly this type; W3 keys its trigger off it — LOCKED via W1 v2), plus task-verb-library verbs `Buy` / `Pull` / `FLAG` (PROD-05-V2) |
| status | text enum | Enumerated from specs; **confirm exact set in PROD-01 review** (§7-5): `LOCKED`, `PENDING`, `IN_PROGRESS`, `COMPLETED`, `PARTIAL_COMPLETE`, `BLOCKED`, + kanban display states (not-started/in-progress/done, KANBAN 3) |
| assigned_crew | ref crew | |
| due_time | timestamptz | W1 follow-up default: T+2 business hours, or next morning if captured after 4pm (LOCKED default) |
| parent_id | uuid FK tasks | single FK, linear chains in V1 (PROD-01); multi-dependency junction deferred to V2 |
| depends_on | ref | `LOCKED → PENDING` with `unlocked_at` on parent COMPLETED; recursive unlock max depth 5 |
| qty_target / qty_completed | numeric | PROD-02 partial-complete reconciliation: completed + residual = target exactly, at every step |
| lkl_bin_id | FK lkl_bins (bin master) | LKL completion gate (CLOSE 18): no location-changing task reaches Done without a valid bin; raw close capture lands in `lkl_records` (append-only) |
| close fields | refs | TaskCloseEvent surface (see §3) — closed_by_method, voice_transcript, verification_thumbnail_path etc. are null until close |
| notify_sent | bool | per-Lead dedupe of outbound SMS (W1 v2 Silent-failure rule) |

### 2.3 task_close_events — canonical close contract, append-only (PROD-38) (DRAFT)

Frozen dataclass fields: `task_id`, `crew_id`, `crew_pin_hash`, `close_kind` (7 variants), `close_method` (4 variants), `event_id`, `occurred_at`, + kind-specific optionals (`qty`, `unit`, `lkl_bin_id`, `lot_id`, `allergen_flag`, `equipment_id`, `voice_transcript`, `verification_thumbnail_path`).

- `close_kind` 7 variants: **LKL, EQUIPMENT_CLEANING, ALLERGEN_RECEIVING, VAN_LOAD, PORTION_CAPTURE, INVENTORY_LOT, STANDARD_COMPLETE** — the 7th, identified by Nick (2026-09-20) as the base case: a normal card close with no special capture, which all other kinds extend. Confirmed at PROD-38 review (§7-4).
- `close_method` 4 variants: `TAP`, `VOICE`, `CAMERA_VERIFIED`, `SUPERVISOR_OVERRIDE`.
- Router contract: validate → exactly one audit row → fan out to exactly the documented handlers per kind (7×7 cross-contamination matrix); unrecognized kind fails closed; idempotent on `event_id`; a downstream handler failure must never report "closed".

### 2.4 LKL — bin master & close-capture log (DRAFT; Nick-confirmed split — keep separate)

**`lkl_bins` — bin master reference (slowly changing):** authoritative master of physical locations; zone/unit/shelf segments composing `[Zone]-[Unit]-[Shelf]`; row added on rack reconfiguration — bins are referenced by FK, never reused in place for a different physical spot.

**`lkl_records` — append-only close-capture log (high frequency):** one row per LKL capture at task close; FK `lkl_records.lkl_bin_id → lkl_bins.id` (correct architecture per Nick 2026-09-20); the raw capture backing PROD-02 closures and task_close_events.

**Relationship:** bin master changes slowly, capture log grows fast — separate tables, never merged.

### 2.5 inventory — lots + transactions (PROD-36) (DRAFT)

Parent→child lot lineage across thaw/repack/portion/refreeze/consume/waste/overbuy; every transform decrements parent, creates child; closes fire as `close_kind=INVENTORY_LOT`. Lot transactions reconcile to a canonical ledger. CLOSE-2 (LKL) = WHERE; inventory = HOW MUCH / WHICH LOT.

### 2.6 catalog — menu + Tier-2 operational tables (W9 / PROD-09) (DRAFT)

- `menu_items` — canonical copy of Square Catering items + all 11 Catalog Intelligence custom attributes (6 visible + 5 hidden) via SearchCatalogItems (not SearchCatalogObjects — only that endpoint returns custom attribute values). Incremental via `catalog_version` cursor. **Store: tazaos PostgreSQL (D4 LOCKED) — W9/PROD-09's "NocoDB" wording superseded.** Columns: `id` (PK, generated), `square_id` (unique, constraint exists), `name`, `category`, `description`, `price_cents`, `allergens` (text[]), `prep_time_min`, `is_active` BOOLEAN NOT NULL DEFAULT TRUE (W9 v2 soft-delete — never DELETE from this table), `last_synced_at` TIMESTAMPTZ (records when Square last confirmed the item, distinct from `updated_at`).
- Tier-2 (PROD-09): `item_packing_profiles` (GN pan footprint/depth/fill qty per service mode), `item_components` (BOM explosion), `item_equipment` (occupancy), `procedure_link` (SOP). Deterministic retrieval only — LLM never computes geometry (ground rule).
- `pack_rate_config` — deterministic pack rates (min/unit) by item/service mode; lookup for W15 pack_start computation (open item §7-3). Named by Nick 2026-09-20.

- `ingredient_master` — canonical ingredient facts for shopping + BOM (PROD-05-V2 / CAT-003). One row per ingredient. **Schema defined 2026-10-01 (Nick "fix the ingredient master schema now").**
  - `id` (PK, generated)
  - `name` TEXT UNIQUE NOT NULL — canonical ingredient name
  - `category` TEXT — protein / produce / dairy / dry_good / frozen / spice / other
  - `vendor` TEXT — preferred vendor (vendor grouping + reliability tracking, PROD-05-V2/KIT-106)
  - `vendor_alt` TEXT — backup vendor
  - `unit` TEXT NOT NULL — lb / oz / each / cup / gal / count
  - `frost_risk` BOOLEAN NOT NULL DEFAULT FALSE — must stay chilled/frozen; pulled last within vendor group in-car (PROD-05-V2)
  - `safety_stock_qty` NUMERIC NOT NULL DEFAULT 0 — below this → FLAG task, never silent Buy
  - `thaw_lead_hours` NUMERIC — how far ahead dense frozen items must start thawing (prep planning)
  - `shelf_life_days` NUMERIC — perishability horizon for batching windows
  - `notes` TEXT
  - `created_at` / `updated_at` per §5.0
  - Populated from the RAG transfer (219 rows, `rag_operations_content` recipe/portion metadata) + Sandra's portion notes.


### 2.7 CRM / sales tables — MIGRATION-001 targets (DRAFT; schema derived from the NocoDB export)

- `leads` — W1 v2 extraction surface: name, email/tel, event type, event date, guest count, venue, budget signals; per-field confidence + FLAG columns (D-006); dedupe business key (normalized_sender_email, event_date, window default 30 days); `notify_sent` (SMS idempotency).
  - **Scoring fields (W2 v2, LOCKED):** `profit_score` INTEGER (1–5); `category` TEXT (`Hot|Warm|Low|Pass`); `scoring_ai_unavailable` BOOLEAN DEFAULT FALSE (fail-to-Low flag); `rubric_version` TEXT (git commit hash of rubric at scoring time); `score_history` JSONB append-only array — each entry carries profit_score, category, rubric_version, trigger, timestamp; standing score is the latest entry, never destroyed.
  - **Scoring fields (W2 v2, LOCKED):** `profit_score` INTEGER (1–5), `category` TEXT (`Hot|Warm|Low|Pass`), `scoring_ai_unavailable` BOOLEAN DEFAULT FALSE (fail-to-Low flag), `rubric_version` TEXT (git commit hash of rubric at scoring time), `score_history` JSONB (append-only array; each entry carries profit_score, category, rubric_version, trigger, timestamp — never overwritten).
- `crm_sessions` — W4 conversation transcripts + extracted JSON updates (schema from export). **Session status lifecycle (D12): `active`, `partial`, `done`, `abandoned**. FK `customer_id` to customers (nullable for anonymous).
- `customers` — qualified/active accounts; promoted from leads after first booking or explicit qualification. **Canonical names (D11): leads, customers, touchpoints; opportunities=V1.1 deferred.**
- `touchpoints` — append-only interaction log: `customer_id` (FK customers), `session_id` (FK crm_sessions, nullable), `type` TEXT (call, session, email, note), `summary` TEXT, `created_at` per §5.0.
- `invoices` — Square order/invoice ref; approval state (W7 draft → approved → published); `deposit_basis_cents` INTEGER (D19: fixed dollar, locked at first publish — Sandra picks % (default 50%) in the form, the dollar is computed from the current subtotal, and that DOLLAR locks; later invoice changes never move it); venue_arrival_time mirror (authority lives on `events`). **PROD-30 V1.1 target**: replaced by own invoice generation (Square = fallback).
- `invoice_line_items` — **PROD-30 V1.1:** line items per invoice: `invoice_id` FK, `description`, `qty`, `unit_price_cents`, `total_cents`, `source_type` TEXT (square|manual|custom).
- `payment_attempts` — **PROD-30 V1.1:** append-only attempt log: `invoice_id` FK, `processor` TEXT (helcim|stripe|square), `amount_cents`, `status` TEXT (success|failed|pending|timeout), `error` TEXT, `attempted_at` TIMESTAMPTZ.
- `invoice_links` — **PROD-30 V1.1:** unique per-invoice customer link: `invoice_id` FK, `token` UUID UNIQUE, `expires_at` TIMESTAMPTZ (90 days), `used_at` TIMESTAMPTZ (nullable, set on payment page visit).
- `communications` — outbound comms log (W13).
- `changelog` — **alert queue only** (W12 writes alerts, W13 reads them). Raw before/after history lives in `audit_log` (PROD-22, trigger-fired). W11 is a read-only changelog view over `audit_log` (D21).

### 2.8 system infrastructure (DRAFT)

- `system_events` — append-only event bus topic log (PROD-20 `emit()`/`emit_failure()`), consumers subscribe by topic. Foundational; Required=YES.
- `audit_log` — append-only every canonical write: actor, table, old/new, timestamp, correlation_id. No canonical write without a corresponding audit row (PROD-22). Fired by trigger on every write via the DB access layer (PROD-27).
- `exceptions_queue` — PROD-23 "FLAG, don't guess" as a real routing mechanism; persist-before-notify (EXCEPT 5).
- Inbox staging tables (PROD-21) — raw external inputs (email classes, Square emails) stage append-only before promotion; invalid rows route to exceptions_queue, never silently accepted.
- `processed_email_ledger` — **NEW from W1 v2 (LOCKED shape):** `message_id` PK (source dedupe), `mailbox_class` TEXT (FORM|DIRECT|AUTO|SQUARE_PAYMENT|SQUARE_UPDATE|SQUARE_MENU_CHANGE), `source_type` TEXT (LEAD_INQUIRY|SQUARE_PAYMENT|SQUARE_UPDATE|SQUARE_MENU_CHANGE|AUTO_REPLY — deduplicated from mailbox_class after classification), `received_at`, `processing_state`, refs to created lead/event/invoice, `notify_sent` flags. Authoritative skip-criterion; cosmetic Gmail label only. **Store: tazaos PostgreSQL (D4 LOCKED).**
- `pre_call_briefs` — append-only log of brief deliveries: `task_id` (FK tasks), `sent_at`, `rubric_version` (from rubric file), `is_rebrief` BOOLEAN DEFAULT FALSE, `rebrief_reason` TEXT (null if not a re-brief), `content_preview` TEXT (first 200 chars for audit), `trigger_event` TEXT (`'window_entry'`, `'re_brief'`). One row per brief sent — never overwritten. The idempotency check (W3 v2) skips if a brief exists for `task_id` and no re-brief triggered.

### 2.9 Database instances — live inventory (2026-09-25, Cortex via shell on n100)

| Database | Size | Role | Notes |
|---|---|---|---|
| `tazaos` | 238 MB | **Canonical store (D4/D5)** | Live: menu_items (434), square_catalog_items (355), square_catalog_sync_log (13), system_metrics (1.25M), crew (6). Empty scaffolding: events (0), task_cards (0), inventory (0), van_loadout_items (0), prep_completions (0). NocoDB internal `nc_*` tables (170+) in `public` — reconciliation target for MIGRATION-001 step 5. |
| `taza_os` | 8.7 MB | LangGraph checkpointer | `checkpoint_blobs/writes/migrations/checkpoints` — agent orchestration state, NOT business data. |
| `taza_memory` | 8.7 MB | taza-brain shared memory | `shared_memory` (21 rows: id, ts, author, topic, body, tags) — agent handoff/decision log, NOT business data. |
| `postgres` | 8.5 MB | Default cluster DB | Ignore. |

Roles: `postgres`, `taza`, `taza_mem`, plus one legacy role (retired project). `tazaos` (no underscore) ≠ `taza_os` (underscore) — never confuse the two in specs or connection strings.

---

## 3. Status machines (normative)

### Event lifecycle (LOCKED via D2)
```
PENDING ──deposit email parsed──▶ CONFIRMED ──crew departed──▶ IN_PROGRESS ──▶ COMPLETE
   ▲                                  │
   └──────── refund rescinds ──────────┘      (~1/410 events)
```
- W15 runs once per CONFIRMED transition; refund→re-payment re-runs authorized.
- venue_arrival_time writable only from draft→IN_PROGRESS; frozen after.

### Task lifecycle (DRAFT — exact state set to confirm in PROD-01 review, §7-5)
```
LOCKED ──depends_on satisfied──▶ PENDING ──assigned/started──▶ IN_PROGRESS
IN_PROGRESS ──close (LKL gate ok, qty==target)──▶ COMPLETED
IN_PROGRESS ──close (qty < target, LKL ok)──▶ PARTIAL_COMPLETE
   └─ auto-spawns exactly one URGENT prep task + one BLOCKED residual task; completed+residual == target; idempotent on replay
COMPLETED on parent ──▶ recursive unlock of children (depth ≤ 5)
```
- All transitions deterministic, LLM-free (D-025). No LLM arithmetic anywhere.

---

## 4. Migration plan — MIGRATION-001 (BLOCKING PREREQUISITE; no V1.0 code before it)

**Decision (Nick, 2026-09-20):** collapse everything into tazaos PostgreSQL. NocoDB becomes a pure UI skin over tazaos via external-database connection (Settings → Connections).

| # | Step | Guard |
|---|------|-------|
| 1 | Export NocoDB tables: Leads, Customers/Accounts, Invoices, Events, Communications, Changelog | Complete export; no truncated rows |
| 2 | Design + create proper schemas in tazaos PostgreSQL (object model §2) | DB-001: every canonical object gets a table; no ad-hoc columns; **every migrated table receives `created_at` + `updated_at` per §5.0** |
| 3 | Import data | NULL vs NOT NULL per DB-001 EDGE-3; constraint check on every table |
| 4 | Reconfigure NocoDB as external DB client of tazaos (Settings → Connections) | NocoDB views (DB-002) + roles (DB-003) preserved on the skin |
| 5 | Reconciliation pass | No tazaos tables/columns outside canonical model (DB-001 NEGATIVE-5 / PROD-18 recon flag) |

Every W/PROD spec's "NocoDB table" reference = Postgres table behind the NocoDB skin from migration completion onward. Cross-store joins: moot — there is no second store.

**Timestamps at migration:** `created_at`/`updated_at` added to all migrated tables at migration time (§5.0); backfilled from NocoDB createdAt/updatedAt where present, else migration timestamp.

---

## 5. Schema & integrity standards

### 5.0 Standing schema rule — `created_at` / `updated_at` on EVERY table

No table ships — existing or future, including any table added after this rule — without both columns:

- `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW() — set once on insert, never updated.
- `updated_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW() — updated automatically on every row change via trigger.

Reusable trigger function:

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

Applied to every table:

```sql
CREATE TRIGGER trg_set_updated_at
BEFORE UPDATE ON <table_name>
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

Tables in scope (at time of writing): leads, customers, invoices, invoice_line_items, payment_attempts, invoice_links, events, tasks, task_close_events, inventory_lots, inventory_transactions, lkl_bins, lkl_records, menu_items, pre_call_briefs, system_events, audit_log, exceptions_queue, crm_sessions, communications, changelog, pack_rate_config — and any new table going forward.

Rationale (Nick, 2026-09-20): development review (sort NocoDB by updated_at to see what changed), production troubleshooting (staleness detection, audit, URS-HEALTH-005 fail-visible principle applied to data).


---

- **Task unlock trigger:** AFTER UPDATE on tasks SET status=COMPLETED → recursive `LOCKED→PENDING` with `unlocked_at`, depth ≤ 5 (PROD-01).
- **LKL gate:** no location-changing task closes Done without a valid bin `[Zone]-[Unit]-[Shelf]` against the bin master (PROD-02/CLOSE 18). Missing bin → close rejected entirely; no auto-spawn on top of a rejected close.
- **PARTIAL_COMPLETE auto-spawn:** exactly one URGENT + one BLOCKED pair, idempotent on replay (`event_id`), partial success must surface as error, parent completion % must reconcile.
- **Overshoot rejection:** qty_completed > qty_target → specific validation error, never clamped.
- **Audit gate (PROD-27):** ALLOWED_TABLES allowlist; parameterized queries only; audit trigger on every canonical write; no raw connections outside the access layer.
- **Close router (PROD-38):** no module writes LKL/inventory/label/allergen tables outside TaskCloseRouter dispatch (CI-checkable).
- **Email dedupe (W1 v2):** source key Message-ID; business key normalized sender email + event date (± tolerance) within window (default 30 days); WON/LOST hit → flag, no silent merge.
- **Event confirm idempotency (D2):** one W15 run per CONFIRMED transition, keyed on invoice ID + email Message-ID.

---

## 6. Storage & access config (PROD-26/PROD-27)

- All endpoints/ports/credentials via env at startup; missing required env = startup error, not runtime exception. D-061 build rule (OLLAMA_BASE_URL and all service addresses env-var).
- Connection pooling per INFRA 1; connection string via PROD-26.
- Reconciles legacy `OLLAMA_BASE_URL` naming.
- **Canonical store (D5):** tazaos PostgreSQL, N100, 192.168.2.102:5432. Connection string via env var (PROD-26), never hardcoded. One store, one backup, one failure surface.
- **Google Cloud credentials (W16 only — V1.0).** W10 superseded (no longer uses Google Calendar). `GOOGLE_APPLICATION_CREDENTIALS` env var per PROD-26 for W16 (Speech-to-Text streaming, diarized, custom vocabulary).

---

## 7. Open items tracker

| # | Item | Depends on | Owner |
|---|------|-----------|-------|
| 1 | **MIGRATION-001** — export NocoDB → tazaos schemas → import → NocoDB skin (§4, 5 steps). **Blocks all V1.0 code** | — | Nick |
| 2 | pack_buffer / setup_buffer default values | W15 review | Nick |
| 3 | pack_rate_config table — coefficients/values (deterministic lookup) | W15/W9 review | Nick |
| 4 | `close_kind` 7th variant = **STANDARD_COMPLETE** (Nick-identified 2026-09-20) — confirm at PROD-38 review that no other kind is missing | PROD-38 review | Nick |
| 5 | Exact task status enum + trigger semantics | PROD-01 review | Nick |
| 6 | **RESOLVED (D11)** — Canonical CRM table names locked: leads, customers, touchpoints; opportunities=V1.1 deferred. | — | Nick |
| 7 | **RESOLVED (D14)** — W9 item deactivation = soft-delete `is_active` only, never DELETE. | — | Nick |
| 8 | Drive-time matrix source + refresh ownership | W15 review | Nick |
| 9 | W15 v1 "SMART 23/25" — which 2 criteria were unmet | Nick | Nick |
| 10 | **Object-model tables not yet created in tazaos** (§2.1–2.8): tasks, task_close_events, lkl_bins, lkl_records, audit_log, system_events, exceptions_queue, leads, customers, touchpoints, crm_sessions, invoices, processed_email_ledger, pre_call_briefs, item_components, item_packing_profiles, item_equipment, procedure_link, pack_rate_config, inventory_lots, inventory_transactions, communications, changelog. Build later — mURS review first (Nick 2026-09-25) | MIGRATION-001 | Nick |
| 11 | Duplicate `master_urs`: public (278) + NocoDB base schema `pckp5o6vpkbml4e` (278); stray `nc_*` tables in public schema. Reconcile at MIGRATION-001 step 5 | MIGRATION-001 | Nick |
| 12 | WireGuard references in `security.md` + `health.md` to retire — Tailscale-only (Nick 2026-09-25) | — | Nick |
| 13 | CAT-001 export still says "12 attributes (7 visible + 5 hidden)"; D18 says 11 (6+5). Correct the corpus row in mURS pass 1 | — | Nick |

---

## 8. Ground rules (binding for all downstream code)

1. No slop. Every function single-responsibility.
2. Every edge case handled explicitly.
3. No silent failures — anything that can't complete goes to exceptions_queue, loudly.
4. **No LLM arithmetic or geometry** — LLM narrates; deterministic code computes. D-025.