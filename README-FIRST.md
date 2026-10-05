# README-FIRST — Taza OS spec-driven pipeline

**Read this file first. Then run the boot query. Then read the database, not the docs.**

Last updated: 2026-10-04.

---

## 1. What this system is

Nick runs a **spec-driven** operation. There is exactly one loop:

    DECIDE  ->  decisions_log  ->  murs_specs  ->  CODE
             (change mgmt)      (normative)     (generated)

- **`decisions_log`** — the change-management system. Every change to the system
  description is proposed, debated, decided and logged here. Nothing changes without a row.
- **`murs_specs`** — the normative description of what the system must do. If it is in
  here, it is **required**. Each spec points back at the decision that created it.
- **Code is generated from the specs.** Spec drives code. Never the reverse.

There is no third store. Do not create one. Do not create markdown handoff files.

## 2. Where it lives

| what | where |
|---|---|
| Server | n100, `192.168.2.102` (`ssh taza@192.168.2.102`) |
| Database | PostgreSQL `tazaos` |
| Schemas | `public` (spec + decisions + production data), `intake` (idea funnel) |
| Spec table | `public.murs_specs` — 291 rows, one per spec |
| Decision table | `public.decisions_log` — one row per decision-branch |
| Boot view | `public.v_boot` — the single entry point |
| Read-only role | `viewer_ro`; password at `/home/taza/viewer_ro.cred` (chmod 600) |
| Web viewer | `pgweb` container, port 8080, published behind cloudflared |

## 3. Your first three commands

    psql -d tazaos -c "select * from public.v_boot;"
    psql -d tazaos -c "select doctrine_id,title,rule from public.pipeline_doctrine where status='adopted' order by 1;"
    psql -d tazaos -c "select candidate_id,title,status from intake.candidate where status not in ('rejected','already_satisfied','promoted');"

## 4. Your role

You are a pipeline agent. You are **not** the decision-maker.

- **Read anything.** Reading is always allowed. Say "read-only" when you mean it.
- **Propose freely — into `intake`.** An outside idea (video, forum, vendor doc, search)
  becomes a row in `intake.candidate`. It does **not** go into `murs_specs` or
  `decisions_log` directly. See PD-002.
- **Write to `murs_specs` only after Nick has decided.** Sequence:
  Nick decides → a row appears in `decisions_log` → you change the spec → the spec
  points back at that decision row. That back-pointer *is* the audit trail.
- **Never change schema without a decision row first.** Production schema changes are
  decisions, not edits. See PD-009.
- **Never invent a table or column.** If something has no home, emit
  `NEEDS-SCHEMA: <exactly what is missing>` and stop.

## 5. The two failure modes to avoid

1. **Do not put an unevaluated idea into `murs_specs`.** That destroys the spec's only
   real property: everything in it is required. Once that is untrue, neither a human nor
   an agent can trust the spec as a contract.
2. **Do not put an undecided idea into `decisions_log`.** Every row must be something
   that was decided, or the log stops answering the one question it exists to answer:
   *has this been decided?*

Ideas live in `intake` until they exit as one of: a spec delta, a decision,
an `already_satisfied` disposition, or a rejection with a recorded reason.

## 6. Decisions you should read before proposing anything

| id | what it settled |
|---|---|
| **D31** | Two durable stores; pipeline doctrine lives in the DB, not a third file |
| **D32** | Read-only production viewer role (`viewer_ro`) |
| **D33** | **Supersedes D4.** The development pipeline gets its own database; production runtime stays separate |
| **D34** | `decisions` and `decisions_log` are one table |

Read them in full from `decisions_log`. Do not rely on this summary.

## 7. Known outlook — verify before assuming

**D33 is not yet executed.** The end state:

- **`mers_dev`** — the development pipeline database (spec + decisions + intake)
- **production runtime** — separate, eventually one database per app
- why: a shared runtime database is a back channel that bypasses the event bus
  (`PROD-20`), recreating the coupling the bus exists to prevent

Until the split lands, the spec and decision tables live inside `tazaos` alongside
production data. **Check `decisions_log` for D33's state before assuming which database
you are in.**

## 8. Things that are deliberately NOT here

- No Notion. Frozen since 2026-08-03.
- No NocoDB. Retired; its 144 metadata tables were dropped from `tazaos.public` on
  2026-10-04.
- No markdown handoff chain. Archived to `archive/session-handoffs/`.
