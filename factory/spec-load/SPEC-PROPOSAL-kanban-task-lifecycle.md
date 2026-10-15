# SPEC-PROPOSAL: Kanban Task Lifecycle — Close Contract & Bus Publication

**Proposed by:** deep (ARCHITECT) — integration pass over the flash (CODE EXPERT) draft
**Date:** 2026-10-15
**Status:** PROPOSAL ONLY — no database written, nothing registered, nothing built

---

## 0. Corrections to the flash draft (by evidence, not by confidence)

F1. flash set `entity_table = task_cards` for the close topic and claimed it "enables
    referential integrity check." It does not. `validate_event()` hardcodes the lookup column:
    `EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE square_invoice_id = $1)', t.entity_table)`
    (public.validate_event, tazaos). `task_cards` has no `square_invoice_id` column, so every
    insert would raise "column square_invoice_id does not exist" — a crash, not a clean reject.
    The topic must leave `entity_table` NULL until the intercom generalizes that check.

F2. flash said "task_cards remains the authoritative state store." It is not. Nothing writes it:
    `grep -rn "task_cards"` across the repo and live kitchen returns only the doctrine mention.
    Its 10 rows (ids 31-40) have titles that do not match the live deck (ids 101-128). It is
    orphaned legacy. The live state is `deck.json` + in-browser memory.

F3. flash used `record_type = Spec Package` and `priority = P1`. The five live URS-KANBAN rows
    are all `Atomic Requirement`, and 001/002/003/005 are P0. Nick's brief calls the game
    "load-bearing." Correct values: `Atomic Requirement`, P0, required_for_release=YES.

F4. flash's payload keys mix names (`card_id`, `invoice_number`). They must align to PROD-38's
    frozen dataclass field names: `task_id`, `close_kind`, `close_method`, `crew_id` — plus
    `invoice` for traceability. See the row below.

F5. flash's `owner_module = kanban` and `entity_type = task_card` are invented. No kanban
    topic, owner_module, or entity_type exists in `event_topics` (verified: 0 rows match
    kanban/task/card). These are Nick's decisions, proposed below, not facts.

F6. flash's `allowed_from_states = ["hand","table"]` is wrong. A card must be on the table to
    close (it is dragged hand→table first, `playCard()` sets `zone="table"`). from_state must
    be `{table}` only.

---

## 1. PROPOSED SPEC ROW

- **spec_id:** `URS-KANBAN-006` — next free id in the URS-KANBAN series (001-005 exist).
- **name:** Kanban task lifecycle, canonical close contract, and bus publication
- **status:** Spec Drafted (propose only)
- **priority:** P0
- **release:** V1.0
- **record_type:** Atomic Requirement
- **domain:** Production Core
- **determinism_class:** D
- **required_for_release:** YES

### user_requirement
Need: closing any card — confirm/prep/cook/portion/pack/stage/deliver/flag — behaves the same
underneath: one canonical TaskCloseEvent through one router, exactly one committed event on the
intercom, traceable back to its gig/invoice. No card kind gets bespoke persistence; no close is
invisible to the LG TV display, scoring, or any future consumer.

### functional_requirement
The kanban app (`server_kanban.py`, port 9003) shall implement PROD-38: one frozen
`TaskCloseEvent` dataclass and one `TaskCloseRouter`. All 8 deck `_kind` values route through
that single router; no per-kind POST endpoint and no bespoke front-end close path remain.
The router (a) validates the close, (b) writes the app's state exactly once, and (c) emits
exactly one `task.closed` event to `public.system_events` in the SAME transaction as the state
write, so a failed close emits nothing and a retry emits no duplicate. The event payload carries
`task_id`, `close_kind`, `close_method`, `crew_id`, `invoice`. The app shall register its topics
in `public.event_topics` and shall refuse to start if they are not registered (fail closed).

### ac_normal
1. Close a card of any of the 8 kinds → exactly one `task.closed` row in `system_events` with
   the required payload keys, and no duplicate write on the state store.
2. Prep/portion close also carries kind-specific fields (leftover_qty, leftover_unit, location,
   photo_path) inside the event payload — no separate table write is required.

### ac_edge
3. Same close retried with the same `correlation_id` → no second `system_events` row, no
   duplicated consumer effect (consumer de-dups on `correlation_id`).
4. Two cards closed concurrently → both commit, both publish, no interleaving corruption.

### ac_negative
5. Close with no/insufficient PIN → rejected before any write; no event emitted.
6. Close a card already `done` → rejected by the state machine; `validate_event()` rejects
   `task.closed` because `to_state=done` is not reachable from `from_state=done`.

### ac_silent_failure
7. The state write succeeds but the `system_events` INSERT fails (dead connection) → whole
   transaction rolls back; caller gets an error; the card is NOT done. No half-close.
8. `validate_event()` rejects the emit (bad payload/state) → the transaction rolls back; the
   card is NOT done. Rejections land in `event_rejects` (quarantine), never silently dropped.

### ac_challenge
9. 20 cards closed in rapid succession during service transition → all 20 committed and
   published; `system_events.id` monotonic; no reject rows for `task.closed`.

### ac_block
10. `task.closed` is not in `event_topics` → the server refuses to start (startup pre-flight),
    so no close can be attempted against a missing topic.
11. `entity_table` is left NULL for these topics because the intercom referential check is
    hardcoded to `square_invoice_id` (see DEF-3). Attempting `entity_table=task_cards` is a
    build error.

### verification_methods
VM1 AUTO: per-close_kind (8) unit test emits a well-formed event with all required payload keys.
VM2 AUTO: integration test — POST close → one `system_events` row + state committed atomically.
VM3 AUTO: idempotency — same `correlation_id` retried → single row everywhere.
VM4 AUTO: state machine — closing a done card → HTTP 409, zero row changes.
VM5 AUTO: startup gate — with topic unregistered, server refuses to start.
VM6 NICK: live close on the board → event visible in `system_events` via psql, payload correct.

**Counts:** vm_count=6, vm_auto_count=5, vm_nick_count=1

### failure_behavior
A close that fails at any step (validate, state write, emit) rolls back entirely: the card is
not done and no event exists. The server fails closed at startup if its topics are unregistered.
Bus rejections are quarantined in `event_rejects`, never dropped silently.

### dependency_notes
- PROD-38 (TaskCloseEvent + TaskCloseRouter) is the contract this implements; neither the
  dataclass nor the router exists in code today.
- PROD-20 + URS-EVENT-001: the bus, `validate_event()`, `block_event_mutation()`, and the
  `event_topics` registry are live and verified.
- URS-KANBAN-001 (hand/table/done) is enforced client-side only; there is no server-side
  state machine today.
- URS-KANBAN-002 (accountable handoff) is NOT implemented: the board has no crew login
  (taza-card-table.html:640) and `confirmLay()` checks only `if(!pending||pinBuf.length<4) return;`
  (taza-card-table.html:992) — any 4 digits close a card. `crew_member` is hardcoded "Crew".
- URS-KANBAN-005 (commit-then-emit, exactly one correlated event) is the core this row makes
  buildable.

### consumes
PROD-38, PROD-20, URS-EVENT-001, URS-KANBAN-001, URS-KANBAN-002, URS-KANBAN-005

### consumed_by
checklist display (checklist_app.py → DEBT-007/PROD-20), SSB-001/SSB-003/KIT-007 (TV display
and staleness). Scoring has NO spec_id today — DEFICIT, see DEF-9.

### open_questions
See section 6.

---

## 2. TOPIC REGISTRATIONS (proposed — none exist today)

Verified: `event_topics` holds 10 topics (event.created, invoice.*, order.captured,
ops.printer_state, test.ping) and ZERO kanban/task/card topics.

### Topic 1 — `task.closed` (canonical close)

| key | value | justification |
|---|---|---|
| topic | `task.closed` | past-tense verb matching `invoice.paid` / `order.captured`; matches Nick's "close" language and PROD-38's "TaskCloseEvent" |
| owner_module | `taza-kanban` (PROPOSED) | matches systemd unit `taza-kanban.service`; existing owner_modules are unit/app names (checklist-app, order_ingest, square_invoice_sync, printer_selfheal) |
| entity_type | `task` (PROPOSED) | matches PROD-38 field `task_id` and "TaskCloseEvent" |
| is_strict | `true` | a close is a commit; a foreign module claiming to close a task must be rejected |
| require_correlation | `true` | URS-EVENT-001; also the de-dup key for retry/replay |
| payload_required | `["task_id","close_kind","close_method","crew_id","invoice"]` | PROD-38 frozen fields + `invoice` for the traceability seam |
| allowed_from_states | `{table}` | a card must be on the table to close (hand→table happens first) |
| allowed_to_states | `{done}` | the only terminal state |
| must_transition | `true` | `task.closed` is always a table→done transition |
| entity_table | NULL | intercom referential check is hardcoded to `square_invoice_id`; cannot point at `task_cards` (DEF-3) |

Notes:
- `task_id` = the card's stable deck id as TEXT (e.g. "101"), which is also `system_events.entity_id`.
- `crew_pin_hash` is a PROD-38 dataclass field but is NOT a payload key. The PIN hash stays in
  the app's private store; the bus carries `crew_id` only. (Q7.)

### Topic 2 — `task.started` (hand→table)

| key | value |
|---|---|
| topic | `task.started` |
| owner_module | `taza-kanban` (PROPOSED) |
| entity_type | `task` (PROPOSED) |
| is_strict | `true` |
| require_correlation | `true` |
| payload_required | `["task_id","invoice"]` |
| allowed_from_states | `{hand}` |
| allowed_to_states | `{table}` |
| must_transition | `true` |
| entity_table | NULL |

Exactly-once guarantee (URS-KANBAN-005): the bus is append-only (UPDATE/DELETE blocked by
`block_event_mutation()`) and `validate_event()` requires `correlation_id`. The router emits
once per commit inside the commit transaction; a failed commit emits nothing; a retry reuses the
same `correlation_id`, and consumers de-dup on it. Note: this is exactly-one-emission +
consumer-side idempotency, not a bus-level exactly-once delivery guarantee — URS-KANBAN-005's
"replay shall not duplicate consumer effects" is consumer idempotency keyed on `correlation_id`.

---

## 3. WHAT BECOMES OF `prep_completions` AND `task_cards`

Recommendation: **both become redundant for the bus-carrying design.**

- `task_cards` — orphaned. Nothing writes it (verified). Its 10 rows (ids 31-40) are stale and
  do not match the live deck (ids 101-128). Its `event_id INTEGER REFERENCES events(id)` points
  at the GIG table (events has 3 rows: ids 10-12), not the bus. Retire it. If Nick wants a
  server-side authoritative state store later, create a NEW table keyed by `entity_id TEXT`
  (deck card id) with `invoice TEXT` and `zone hand/table/done` — do not resurrect `task_cards`.
- `prep_completions` — 0 rows today. It is written only by `_pg_log_prep` with no `event_id`
  and no invoice. Its kind-specific detail (leftover_qty/unit, location, photo_path) belongs
  inside the `task.closed` payload as PROD-38's kind-specific optional fields. Retire the table;
  keep the `prep-photos/` files on disk and carry `photo_path` in the payload.

Bottom line: the bus (`system_events`) is the record; `deck.json` + in-browser state remains the
app's working state; a new private state table is optional and not required for bootstrap.

---

## 4. THE "STARTED" SIGNAL (hand→table)

**Spec it, not a placeholder.** `task.started` (Topic 2) is registered now and built in the same
bootstrap, because the LG TV staleness pulse is explicitly blocked on it and it is the same
transaction shape as close.

What is missing to build it: the front-end never tells the server about hand→table.
`playCard()` does it purely client-side:
`function playCard(id){ const c=cards.find(x=>x.id===id); if(!c)return; c.zone="table"; render();`
(taza-card-table.html:943). Building `task.started` needs a new POST from the drag handler.
Sequencing (build now vs follow-up) is Q6.

---

## 5. SEAMS

S1. `task_cards.event_id` is INTEGER → `events(id)`; the bus uses `entity_id TEXT`. These are
    two different concepts: the FK points at the GIG (events), while `entity_id` is the CARD
    identity. Do not bridge them. Bus `entity_id` = deck card id as TEXT. Recommendation: drop
    `task_cards` entirely (orphaned), which removes this seam. A future state table uses
    `entity_id TEXT` + `invoice TEXT`, no `events(id)` FK.

S2. Traceability to gig/invoice. `deck.json` carries `trace.invoice` on every card (verified),
    so `task.closed` payload carries `invoice`. BUT `deck.json` does NOT retain the source
    `order.captured` correlation_id/event id (the trace block has invoice/rule/guests/items/quote
    only). Full end-to-end correlation (card → order.captured bus event) requires `gig_deck.py`
    to stamp each card with its source event id/correlation_id at deck-build time. DEF-7.

S3. Who owns "gig is complete". Nothing computes it; no spec and no code. It is a derived
    consumer state (all cards of a gig in `done`). NOT this spec's job. Recommend a future
    aggregator/consumer, and a decision on whether "gig.completed" is a bus event and who owns
    it. DEF-9.

---

## 6. DEFICIT REGISTER (ordered — what must exist before bootstrap is buildable)

DEF-1. PROD-38 implementation absent. `TaskCloseEvent` dataclass and `TaskCloseRouter` exist
       nowhere in code. Unblocks: every close-path decision.
DEF-2. No registered topic. `event_topics` has 0 kanban/task/card rows; `validate_event()`
       rejects unknown topics as strict (`v_strict := true`). Unblocks: any publish at all.
DEF-3. Intercom referential check hardcoded: `square_invoice_id` (validate_event body). Unblocks:
       setting `entity_table` on non-invoice topics. Until generalized, entity_table must be NULL.
DEF-4. No bus writer in `server_kanban.py` — zero references to `system_events`; all writes are
       raw subprocess psql. Unblocks: emission and the commit-then-emit transaction.
DEF-5. Bespoke close paths confirmed (D1). Non-prep closes hit only
       `doneCards.push({who:c.who, title:c.title, icon:c.icon, cat:c.cat, urg:c.urg, lkl:c.lkl, base:PTS[c.urg], chain:chainBonus, demerit:0});`
       (taza-card-table.html:1010) with no fetch; only prep reaches
       `fetch("http://192.168.2.102:9003/api/prep-completion",{` (taza-card-table.html:1466).
       Unblocks: one canonical close path.
DEF-6. Close payload drops identity (D2 confirmed). `_pg_log_prep` INSERTs only
       `(card_id, card_title, crew_member, location, leftover_qty, leftover_unit, photo_path)`
       (server_kanban.py) — no `event_id`, no invoice, no `_kind`. The front-end POST body
       (taza-card-table.html:1457-1465) carries no invoice/_kind either. Unblocks: gig traceability.
DEF-7. `deck.json` lacks the source `order.captured` correlation_id (verified trace block).
       Unblocks: full card→order.captured correlation on the bus.
DEF-8. No hand→table server signal; `playCard()` is client-only (taza-card-table.html:943).
       Unblocks: `task.started`, LG TV staleness pulse, scoring duration.
DEF-9. "gig is complete" is unowned (no spec_id, no code). Scoring has no spec_id either.
       Unblocks: gig completion event and scoring consumer.
DEF-10. crew identity absent. No PIN verification; `confirmLay()` checks length only
        (taza-card-table.html:992); `crew_member` is hardcoded "Crew". Unblocks: real `crew_id`
        on the bus (URS-KANBAN-002).

---

## 7. BUILD ORDER (architect's DAG)

Level 0 (parallel, no mutual dependency): DEF-1 (TaskCloseEvent/Router) and DEF-3 (generalize
the intercom referential check) can proceed independently.
Level 1 (after DEF-2 + DEF-3): register the topics in `event_topics`.
Level 2 (after DEF-1 + DEF-4): build the bus writer + commit-then-emit transaction in
`server_kanban.py`.
Level 3 (after Level 2 + DEF-5): single `/api/task-close` endpoint; fold prep and non-prep paths
into it; add invoice/_kind to the payload (DEF-6).
Level 4 (parallel, after Level 3): DEF-7 (gig_deck stamps source correlation) and DEF-8
(task.started endpoint + front-end POST).
Not in this spec: DEF-9 (gig completion) and the full DEF-10 crew-login — both need their own
decisions/specs; DEF-10 is a hard prerequisite for real `crew_id` but the bus can carry
`crew_id="Crew"` as an honest placeholder until then.

---

## 8. OPEN QUESTIONS FOR NICK

Q1. Topic verb: `task.closed` (my proposal, matches "close") vs flash's `task.completed`.
Q2. owner_module: `taza-kanban` (systemd unit name) vs `kanban` vs `server_kanban`. I propose
    `taza-kanban`.
Q3. entity_type: `task` (matches PROD-38 `task_id`) vs `task_card`. I propose `task`.
Q4. Priority: P0 (load-bearing, matches the series) — flash said P1. Which?
Q5. Approve retiring both `task_cards` and `prep_completions` (both stale/orphaned, 0-10 rows),
    with the bus as the record — or keep one as a private store?
Q6. `task.started`: build now in the same bootstrap, or register-topic-only placeholder?
Q7. `crew_pin_hash`: keep it out of the bus payload (my rec — private store only), or publish?
Q8. PROD-38 says `close_kind [7 variants]` but the deck has 8 `_kind` values (confirm/prep/cook/
    portion/pack/stage/deliver/flag). Which is authoritative? PROD-38 does not enumerate its 7.
Q9. "gig is complete" and "scoring": confirm they stay OUT of this spec and get their own
    spec_ids/owners.
Q10. Transaction mechanism: add `psycopg2` (real BEGIN/COMMIT) vs subprocess psql (cannot do a
     reliable atomic multi-statement). I recommend psycopg2.
