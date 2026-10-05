# README-FIRST — Taza OS

**Read this file first, then run the boot query, then read the database. Do not read the
old markdown. Do not create new markdown.**

Last updated: 2026-10-04. Supersedes every earlier handoff document; those live in
`archive/session-handoffs/` and are historical only.

---

## 0. Why this file exists at all — and how to treat it

Nick hates markdown. This is the single sanctioned exception: one orientation file so a
cold agent does not have to guess.

**This is a LIVING FILE (D44). Every time you touch it, read it for anything now out of
date and REPLACE it. Never append. Never leave a stale line because it is inconvenient to
check.**

- It is **not** part of the development or production stack. It is an aid to the agent.
- It **points at** the system; it does not describe it. Anything factual belongs in the
  database, referenced from here.
- If a section here starts duplicating something the database already records, **delete
  the section** rather than maintain two copies.
- The exception holds **only while there is exactly one such file.** If a second
  orientation file ever appears, this exception is broken and one of them must go.
- Correct staleness **in the session that discovers it**, not later.

Two things this file has already had to correct, as examples of how wrong it can get:
"murs_specs" was renamed and "mers_dev" never existed under its final name; and the
viewer Nick calls PGAdmin is pgweb on a `nocodb.*` hostname.

---

## 1. The loop

Nick runs a **spec-driven** operation. There is exactly one loop:

```
DECIDE  ->  decisions_log  ->  spec  ->  CODE
         (change mgmt)     (normative)  (derived)
```

- **`decisions_log`** — the change-management system. Everything is proposed, debated,
  decided and logged here. Nothing changes without a row.
- **`spec`** — the normative description of what the system must do. **If it is in here,
  it is required.** Each spec points back at the decision that created it.
- **Code is generated from the spec.** Never the reverse.

There is no third store. Do not create one.

### The two failure modes that destroy this system

1. **Putting an unevaluated idea into the spec.** The spec's only real property is that
   everything in it is required. Once that is untrue, neither a human nor an agent can
   trust it as a contract.
2. **Putting an undecided idea into `decisions_log`.** Every row must be something that
   was decided, or the log stops answering the one question it exists to answer: *has
   this been decided?*

Ideas live in `intake` until they exit as a spec delta, a decision, an
`already_satisfied` disposition, or a rejection with a recorded reason.

---

## 2. Where everything lives

**Server:** n100 = `192.168.2.102` (`ssh taza@192.168.2.102`). PostgreSQL 14.

| database | size | what it is |
|---|---|---|
| **`dev_pipeline`** | ~14 MB | **the development pipeline.** Spec + decisions + intake. |
| **`tazaos`** | ~250 MB | **production runtime.** Apps, invoice mirrors, operational data. |
| `taza_os_langgraph_checkpoints` | ~9 MB | LangGraph checkpoints only. Nothing to do with "Taza OS". |
| `taza_memory` | ~9 MB | unused; 0 tables, 11 functions. Not deleted (unknown consumer). |

### `dev_pipeline`

| schema | contents |
|---|---|
| `spec` | `taza_os_user_requirement_specifications` (291 rows, one per spec), `master_urs` (legacy import), `specs`, `acceptance_criteria`, `verification_methods`, `seam_stamps`, `seam-stamps`, `seam-open`, `branches`, `domain_rules`, `foundational_table`, `foundational_column`, `spec_decision_link`, `v_boot` |
| `decisions` | `decisions_log` (**the** decision log), `change_record` (every change, FK-linked to its decision) |
| `intake` | `source`, `candidate`, `candidate_spec`, `alternative` — the idea funnel |

### `tazaos` (production)

Live: `square_catalog_items` (355), `square_catalog_sync_log`, `square_invoices` (329),
`square_invoice_sync_log`, `invoices_with_deposit` (305), plus `events`, `menu_items`,
`crew`, `inventory`, `task_cards`, `state_machines`, and the rest of the operational set.

**13 design-time tables in `tazaos` are FROZEN** (D37) and carry a `FROZEN` table comment
naming their live counterpart in `dev_pipeline`. They are stale pre-split copies.
**Never edit them.** Cutover — dropping them — is still pending.

### Roles and viewers

| role | notes |
|---|---|
| `taza` | the working role. Can write `tazaos` and `dev_pipeline`. |
| `viewer_ro` | **read-only by construction** (D32): SELECT-only on `public` + `intake`, `default_transaction_read_only=on` pinned at role level. Password at `/home/taza/viewer_ro.cred` (chmod 600). |
| `postgres` | superuser. Needed for `pg_dump`, `pg_hba` edits, role creation. |

| viewer | port | targets |
|---|---|---|
| `pgweb` | 8080 | `tazaos` |
| `pgweb-dev-pipeline` | 8081 | `dev_pipeline` |

**⚠️ Naming trap.** What Nick calls "PGAdmin" is actually **pgweb**, served at
`nocodb.tazacateringphoenix.com`. There is no PGAdmin installed anywhere. pgweb has
**zero authentication** — Nick has explicitly accepted that until the system operates.

### Tunnels — two separate cloudflared instances, different domains

| machine | domain | fronts |
|---|---|---|
| n100 | `*.tazabistro.com` | `terminal` (:7682) only. n8n + nocodb retired. |
| gflip | `*.tazacateringphoenix.com` | `fusion`, `pm`, **`chat` (:3080 — the LibreChat Nick talks to the agent through)**, `nocodb` (→ n100:8080 pgweb) |

**Restarting gflip's cloudflared kills the chat session.** Any gflip ingress change must
be scheduled detached, after the agent's reply lands.

### Scheduled jobs

| timer | cadence |
|---|---|
| `square-invoice-sync.timer` | **every 30 minutes** |
| `square-catalog-sync.timer` | Sundays 03:03 |
| `square-menu-sync.timer` | Sundays 03:00 |

All three: `User=taza`, `EnvironmentFile=/etc/taza/secrets` (Square credentials live
there, **not** in `/home/taza/.env`).

---

## 3. The cascade standard

**Nick's rule: every change to the system description goes through a decision first.**

The order is not optional:

1. **Record the decision** in `decisions_log` — *before* touching anything
2. **Apply the change**
3. **Record it** in `change_record`, with a **foreign key** to `decisions_log.branch_id`
4. If spec content moved, **recompute the hash**

`change_record.branch_id` is a real FK. A change record cannot reference a decision that
does not exist — the engine enforces it. This caught an error the first time it was tried.

**The link direction on specs:** `spec_decision_link(spec_id, branch_id)` — a spec points
at the **branch** that caused it, not the decision id, because one decision can have
several branches (D29.A / D29.B / D29.C).

---

## 4. The content hash

```
canon = spec_id | branch_id | functional_requirement | ac_normal | ac_edge |
        ac_negative | ac_silent_failure | ac_challenge | verification_methods |
        atomic_requirement | intent_user_need | inputs | outputs |
        trigger_condition | invariants | out_of_scope | maintenance_requirements |
        external_dependencies | rationale | failure_mode_addressed

version_id = sha256(canon)[:16]
```

**20 fields.** Recipe lives in `tools/stage-deterministic.py` and is reproduced in
`decisions_log` D36 and D41.

- `implementation_status` is **deliberately excluded** — it is work tracking, and a status
  flip must not bump 291 versions (D41).
- **Changing any hashed field means recomputing all 291** and logging it. Before extending
  the canon, first prove you can reproduce the existing values — the D36 change did that
  and got 291/291 before touching anything.
- A hand-edit that changes hashed content without recomputing breaks the integrity check.

---

## 5. Handoff rules — what NOT to do

1. **Never invent a table or column.** Emit `NEEDS-SCHEMA: <what is missing>` and stop.
   Schema changes go through a decision (PD-009).
2. **Never create a markdown store.** The database is the record (PD-016).
3. **Never write to `tazaos` design-time tables.** They are frozen (D37).
4. **Never assume which database you want.** `dev_pipeline` = spec/decisions.
   `tazaos` = production. Check before acting.
5. **Never trust a count without breaking it down.** See §6.
6. **Never report success before validating.** The invoice bug was declared working and
   wasn't.
7. **Never restart gflip's cloudflared synchronously** — it carries the chat session.
8. **Never edit `pg_hba.conf` without a backup and a RELOAD** (not a restart), so a bad
   line fails without being applied.
9. **Never run `pg_dump` as `taza`** for a whole database — the role does not own every
   table. Use `postgres`. And `postgres` cannot write into the 700 permissions backup dir;
   dump to `/tmp` then move.
10. **Never renumber the PD- doctrine ids** — `README-FIRST` and other records reference
    them. Doctrine lives in `decisions_log` alongside the D- decisions.

---

## 6. Facts Nick tends to forget — remind him

- **"PGAdmin" is pgweb**, served on a hostname called `nocodb.*`. Both names are wrong.
- **NocoDB is retired** (D37). Its 144 metadata tables were dropped. Do not resurrect.
- **The `decisions` table no longer exists.** Decisions and the decision log are **one
  table** (D34). Doctrine is rows in it too (D40).
- **`tazaos` still holds stale copies of the spec and decisions.** The live ones are in
  `dev_pipeline` (D37).
- **Square owns invoices in V1** (D42). PROD-30's "replacing Square invoicing" is a
  **V2.0** target. Both tracks run in parallel; Square is the fallback until Taza's own
  system is proven for months.
- **Deposit rule: ANY amount counts.** Not 50%. Estimates rise after the deposit, so the
  percentage is meaningless — the fact that a deposit exists is the signal (Nick,
  2026-10-04).
- **Cancelled invoices are not leads.** A `CANCELED` invoice is dead paperwork.
- **The CRM app does not exist yet**, so Track A's invoice-drafting workflow cannot be
  tested end to end. Only the Square ingestion is live.
- **Estimates are deliberately NOT ingested.** Square's "Pending — Estimates" is a
  separate object and the invoices API cannot see it. Nick's ruling: not worth pulling.
- **The Payments API WORKS with the token we already have** — tested 2026-10-04, HTTP 200.
  35 completed payments in the previous 30 days summed to **$44,925.68**, matching Nick's
  Square app exactly. **So no new payment key is needed.** What has NOT happened yet is
  the ingestion itself: no payment-level rows are stored, so "when did money arrive" is
  still unanswerable from the database. 19 of 90 payments failed over 90 days — 21%.

---

## 7. Boot sequence

```sql
-- the single entry point
select * from spec.v_boot;

-- the doctrine, now rows in the decision log
select branch_id, branch_title, body
from decisions.decisions_log
where branch_id like 'PD-%' order by branch_id;

-- the open idea queue
select candidate_id, title, status from intake.candidate
where status not in ('rejected','already_satisfied','promoted');

-- recent changes and what drove them
select c.change_id, c.branch_id, c.change_type, c.object_ref, d.branch_title
from decisions.change_record c join decisions.decisions_log d using (branch_id)
order by c.change_id desc limit 20;
```

---

## 8. Current state — 2026-10-04

**66 decisions · 12 change records · 291 specs · 329 Square invoices mirrored**

**Live:** Square invoice ingestion every 30 min (`square_invoices` → `invoices_with_deposit`
→ `v_invoices_awaiting_final_payment`). Verified against Nick's Square app: outstanding
$49,462.20 — exact match to the cent.

**Built but not cut over:** `dev_pipeline` holds the live spec and decisions; `tazaos`
still holds frozen copies.

**Not built:** the CRM app, the invoice-drafting web form, the two-person approval
workflow, the Square push, and the entire Track B Taza-invoiced system.

---

## 9. PENDING DECISIONS — what Nick still has to rule on

Each of these is live in `decisions_log` with status `proposed`. Read the full rationale
there before asking him; he asked for enough context to decide without re-deriving it.

### D47 — what key joins an invoice to an event? **blocking the Kanban spine**

**The problem.** Nick says invoice data is the spine Mom's Kanban and other apps consume.
`PROD-06` turns a deposit into tasks. Both need to know *which event* an invoice belongs to.
**That link is impossible today.**

**Why.** The real `public.events` table is `id(integer), name, client, event_date,
start_time, end_time, guest_count, venue, status, allergen_flags, notes` — and has **zero
rows**. The registry claims it is `id(uuid), invoice_order_ref, customer_id, venue_name,
venue_arrival_time, tables_count, linens_tier, kitchen_departure_time`. **The registry is
wrong** — the column we planned to join on, `invoice_order_ref`, does not exist. Our own
registry describes a table that isn't there, which puts PD-012 in violation by our own
registry.

**What's already live regardless:** `invoice_number` is parsed into `customer_code`,
`service_code` and `event_date_derived`. **261 of 329 invoices carry a usable event date**
— so the Kanban has a real date per invoice today. That is not a substitute for the link.

### Other open items needing a ruling

| # | the question | why it matters |
|---|---|---|
| 1 | **Backup retention** — 14 days is my default, unreviewed | determines how far back a point-in-time restore can reach |
| 2 | **Alert delivery** — `ops_alert` exists but nothing reads it | a failed sync currently writes a row nobody sees; PROD-25 (Notifier) is specified, not built |
| 3 | **`PROD-06` says webhooks, we built polling** | Nick's stated intent is *both*: polling now, webhooks + email API later as redundancy. Confirm and amend PROD-06. |
| 4 | **Do we store payment-level rows?** | the API works but nothing is ingested; needed for refunds, partial payments, cash-arrival dates |
| 5 | **Track B payment stack** — Helcim primary, then what? | named as "a fallback stack" but the providers are undecided |
| 6 | **The `tazaos` cutover** — when do the frozen design-time copies actually get dropped? | until then drift is possible and the duplication is confusing |
| 7 | **Item 10** — archive `master-urs.md`? | one reconciliation run decides it; frees the last big markdown |
| 8 | **Item 7** — the 52 `urs/*.md` files | ~12 are real findings worth queueing; the rest are prompts, applied drafts or superseded |
| 9 | **Formal mirrors** — 1,164 cells, `[KG]` is the longest today | PD-013 makes Nick the sole approver; needs a batched review process, not one pass |
| 10 | **`events` registry is wrong** | partially D47, but the registry fix is its own change |

---

## 10. SPEC AUTHORING CONVENTIONS — how Nick wants acceptance criteria and verification methods written

These two rules apply to every spec written or rewritten from 2026-10-04 onward. They are
authoring standards, not suggestions. Apply them to any AC or VM you touch, and to every
new spec.

### 10.1 Acceptance criteria are written in GHERKIN

Given / When / Then. Not prose. Every AC class - normal, edge, negative, silent-failure,
challenge - is expressed as a scenario.

WHY IT MATTERS: a Gherkin scenario is already a test. `Given` is the fixture, `When` is the
action, `Then` is the assertion. It maps directly onto a runnable test without a human
translating prose into code first, which is the step where meaning is lost. It also makes
the AC falsifiable at a glance: if you cannot write the `Then` as an observable outcome,
the requirement was not testable and that is a defect in the requirement, not in the test.

WRITTEN WRONG (current state of most of the corpus):

    ac_normal: The system sends a pre-call brief before the task is due.

WRITTEN RIGHT:

    Scenario: A brief fires inside the task window
      Given a task with due_time 14:00 and an unbroken 60-minute window before it
        And the brief has not already been sent for this task_id
       When the poller runs at 13:10
       Then exactly one brief is sent for that task_id
        And it is sent no later than due_time minus 5 minutes
        And it is never sent earlier than due_time minus 60 minutes

NOTE the shape: one scenario per AC class, concrete values not placeholders, and a `Then`
that names something measurable. "Sent" is not measurable; "exactly one brief for that
task_id" is.

### 10.2 Verification methods use LOGICALLY DESCRIPTIVE NAMES

In any formal expression - `vm_formal`, `ac_formal`, `domain_rules.formal`, invariants,
guards - every identifier must be the REAL field or entity name, spelled out. Never a
placeholder, never an abbreviation, never `x` and `y`.

This is already PD-012 (formal logic references only real fields). This rule extends it: a
real field must also be written at FULL LENGTH so a reader knows what it means without a
legend.

WRITTEN WRONG:

    x >= y * 0.25
    SELECT count(*) FROM t WHERE c1 > 5

WRITTEN RIGHT:

    deposit_paid_cents >= total_cents * 0.25
    SELECT count(*) FROM public.invoices_with_deposit WHERE is_outstanding

The corpus already has near-correct examples in `domain_rules` - AND one that breaks this
rule, which is the more useful example because it is real:

    rule_id              | formal                                       | verdict
    RULE-BERRY-T36       | purchase_time <= event_time - 36h            | GOOD - real names
    RULE-BRIEF-900       | brief_char_count <= 900                      | GOOD - real name
    RULE-AUDIO-SLA       | (dur<=15 -> lat<1000ms) AND (...)            | BREAKS IT - dur and lat

`dur` and `lat` are abbreviations. A reader needs the surrounding row to decode them, and a
rename of `audio_clip_duration_s` would never find them. The correct form is:

    audio_clip_duration_s <= 15 -> transcription_latency_ms < 1000

Same constraint, no legend required, greppable, and it survives a field rename. THAT is the
target quality.

WHY IT MATTERS BEYOND TIDINESS: a placeholder cannot be executed, cannot be checked against
the schema, and cannot be searched for when the field it should have named gets renamed.
Descriptive names make formal logic greppable, verifiable against the registry, and
survivable across schema changes.

### 10.3 THE CONVERSION JOB THIS IMPLIES

Measured 2026-10-04: 291 specs, **1,308 acceptance criteria, 1,143 verification methods**,
and 11 domain rules. Essentially none of the ACs are Gherkin, and the VM formats are
inconsistent (`VM@1`, `VMn`, bare `psql - SELECT ...`, `[NICK] screenshot of ...`).

So this is not a style note - it is a corpus conversion. It belongs with the formal-mirror
work in section 9, because a Gherkin scenario is itself a formalization of the AC.

OPEN QUESTION FOR NICK, raised not decided: does GHERKIN REPLACE the FOL-style
`ac_formal` mirror, or sit alongside it? An argument for replace: two formal representations
of one AC will drift, and Gherkin is the one a test can actually run. An argument for
alongside: the FOL mirror can express invariants and negative constraints that do not
naturally fit a scenario. This needs ruling before the formalization batches start, because
it determines what the batches produce.

### 10.4 READABILITY IS A REQUIREMENT, NOT A PREFERENCE

**Meet or exceed current WCQG readability standards.**

Nick's instruction, 2026-10-04. Applies to everything written: acceptance criteria,
verification methods, spec prose, decision rationales, formal expressions, reports to Nick,
and this file.

PRACTICAL CONSEQUENCE for spec work: an AC or VM written at a reading level, sentence
length or vocabulary that a cook, a crew member or Sandra cannot follow on a phone in a
kitchen is a defective requirement, not a stylistic one. The corpus currently contains
run-on ACs of 200+ characters with multiple numbered clauses per sentence (see `PROD-02`,
`PROD-06`) - those fail this standard regardless of how accurate they are.

**OPEN ITEM, RECORDED VERBATIM RATHER THAN GUESSED:** the agent does not know what WCQG
expands to, and has not invented a meaning. The instruction is recorded exactly as given.
The first future session that has the definition should replace this paragraph with the
actual standard, its source, and how conformance is measured. Until then: write plain,
short, concrete sentences, one requirement per sentence, no jargon, active voice.

---

## 11. API CALL LOGGING — a requirement, and a gap

**Nick, 2026-10-04: log API calls, and log both timestamps — when the call was initiated and
when it was filled (completed).**

Purpose: latency is a business signal, not a curiosity. A Square call that normally takes
300 ms and starts taking 6 s is the first symptom of something about to break, and it is
invisible in a log that only records that the run finished.

**CURRENT STATE — a known gap, recorded rather than glossed:**

| what is logged today | where |
|---|---|
| run-level `started_at` / `finished_at` | `tazaos.square_invoice_sync_log` |
| one summary line per run (`seen= upserted= deposit_unpaid= pages=`) | journald |
| `occurred_at` on every published event | `tazaos.system_events` |

**What is NOT logged: individual API calls.** There is no table recording per-call
endpoint, initiation timestamp, completion timestamp, duration, HTTP status, or page
number. A run that took 4 seconds because one page was slow is indistinguishable from a run
that took 4 seconds because there were four normal pages.

**What a compliant implementation looks like** — per call: `endpoint`, `method`,
`initiated_at`, `completed_at`, `duration_ms`, `http_status`, `attempt` (retry number),
`rows_returned`, `run_id`, and a `correlation_id` that ties every call in one run together
and ties the run to the events it published. The `correlation_id` is the important column:
without it a slow call cannot be joined to the downstream effect it caused.

**Applies to:** `square_invoice_sync` now, and every future service that calls anything
outside the machine. Add it to the build log's `does_not_do` for the sync.

---

## 12. AI OVERWATCH — feature draft. NICK WILL WRITE THE SPEC.

**Status: Nick's requirements, recorded verbatim in substance. He will spec this out. This
section is captured so the requirements are not lost and so the pieces it can stand on are
identified — it is NOT the specification, and the agent has not designed it.**

### What Nick asked for

A new AI agent that **lives in the system and watches everything that happens**, checks
whether what happens **conforms** to the specs, and looks both for **errors** and for
**ways to improve**.

- It **logs the chain of events**.
- Its logging must be designed **smartly enough that complex or compound failures, or
  plain weirdnesses in what the user experiences, can be UNWOUND** — traced back to a
  cause rather than guessed at.
- **Overwatch must have one or more AIs. At least one of those eyes must be a code
  specialist in Nick's type of code.**
- Overwatch **watches code execution** and **writes descriptive log entries**, each with a
  **unique identifier**.
- Overwatch **logs failure points at the point in time of failure** — not reconstructed
  later from inference.

### Why the compound-failure requirement is the hard part

A single failure is easy to log. **The interesting case is several things going wrong
together and producing a symptom that looks unrelated to any of them** — a display showing
the wrong event, a checklist that is short by two items, an invoice that is $40 off. To
unwind those you need to reconstruct *what was true at the moment it broke*, from a
sequence of timestamped, individually identified entries, not from whatever state the
system has drifted into by the time someone notices.

That is why "unique identifier" and "at the point in time of failure" are load-bearing
requirements rather than nice properties:
- the **unique id** is what lets one entry be referenced by another, so causality survives
- the **timestamp of the failure itself** is what lets you see the state as it was, because
  by the time you look, it is gone

### What already exists that Overwatch can stand on

| piece | what it gives |
|---|---|
| `tazaos.system_events` | the append-only chain. `correlation_id` links related events; `from_state`/`to_state` make causality explicit |
| `tazaos.emit_event()` | any writer can publish inside its own transaction, so an event cannot describe a write that rolled back |
| `tazaos.ops_alert` | the interim exception sink, with severity |
| `tazaos.backup_log`, `square_invoice_sync_log` | per-run health, with verification flags |
| `decisions.build_log` | what was built, what it does NOT do, and the command that proved it |
| `decisions.bootstrap_debt` | named deficits, with acceptable closure routes |
| the spec table + the decision log | the conformance reference Overwatch checks against |

### What is missing for it to exist

- An `audit_log` (PROD-22) — nothing currently records writes
- The exception router (PROD-23) and the notifier (PROD-25) — `ops_alert` is a stand-in
  with **nothing reading it**
- Per-call API timing (section 11)
- **A definition of conformance** — against which specs, checked how, and what happens on a
  miss. This is the piece that needs Nick's ruling most.
- **A decision on whether Overwatch may act** (file an alert, write a debt entry) or only
  observe and report. It changes the design fundamentally.

### OPEN QUESTIONS — for Nick to answer while writing the spec

1. **Conformance against what** — all 291 specs, or a nominated subset per module?
2. **May Overwatch act, or only observe?** Does it raise a debt entry itself, or only tell
   a human?
3. **What is "Nick's type of code"?** Which languages and stacks the code-specialist eye
   must actually know — this determines whether that eye can be a local model or must be a
   frontier one.
4. **How many eyes, and do they disagree?** If two eyes disagree on conformance, what is
   the tiebreak?
5. **Overwatch's own logging** — does it log to the same bus it watches? An observer writing
   to the thing it observes can create its own noise, and it needs to not watch itself into
   a loop.
6. **Cost** — Overwatch reading everything continuously is the largest inference load in the
   system. Triggered, sampled, or continuous?
