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
