# README-FIRST — Taza OS

Read this first, then the live map, then the databases. Never the old markdown.

**This is the only markdown file allowed in the factory.** The product stack may hold any file
type it likes — markdown included. The factory is what builds and operates the system; the
product is what actually runs for Mom's Table.

Last updated: 2026-10-15. Supersedes every earlier handoff document; those live in
`archive/session-handoffs/` and are historical only.

## The front door

The map is machine-written every hour (cron :05) — it cannot drift from reality:

| | |
|---|---|
| LAN | `http://192.168.2.107:8095/architecture` |
| tunnel | `https://pm.tazacateringphoenix.com/architecture` |
| raw facts | `/architecture.json` |

The rules door (read-only, whitelist — it serves only these three files):

| | |
|---|---|
| LAN | `http://192.168.2.107:8099/README-FIRST.md` · `/roles.json` · `/architecture.json` |
| tunnel | `https://rules.tazacateringphoenix.com/README-FIRST.md` · `/roles.json` · `/architecture.json` |

The index door — what is IN the repo, as one lookup instead of a search:

| | |
|---|---|
| file | `/home/taza/repo/factory/index/index.tsv` · `index.json` |
| rebuilt | hourly (`spec-index-build.timer`) |

A broad `find *.py` in the one repo returns 1,378 paths. Nobody reads that, so they guess. The
index says what each real source file is for, in the author's own words, and excludes the
`.venv` / `__pycache__` noise that buries it. **Read the index before searching.**

Cards are coloured by what a thing **is**: PRODUCT (runs for Mom's Table) · FACTORY (builds or
operates it) · FROZEN (archive) · FACTORY · not ours (third-party) · HOST (plumbing) · THE ONE
REPO. The whole classification is one file, and this is where `roles.json` lives:
`/home/taza/repo/factory/arch/roles.json`. Red = one thing with two owners; each row names the
action that closes it.

## The loop — how every piece of work happens

1. Examine or research **one feature** — product or factory. Nothing is written yet.
2. Get AI advice.
3. **Nick decides.** The decision is his alone.
4. The AI he is talking to must have a shell MCP — a standalone chat, or a team in the fusion
   stack. One of them **records the decision in the decisions database** — there is only one
   decision log. Then every spec the decision touches is changed to match it, including split
   decisions ("build x, y, z; wait on p, q, r; dependency B is not live yet, put a placeholder
   there").
5. The AI **records those spec changes, then builds what Nick asked for against the specs** —
   honouring his intention and his own language.
6. Nick and the AI run AC/VM testing. If Nick approves —
7. the AI records a **build record inside the spec database, and nowhere else.** What was
   specified and what was actually built now sit in one place, side by side.
8. The AI records a **change record inside the decisions database, and nowhere else.** It says
   which lines of the URS spec were changed, and what the diffs were.
9. The AI **recommends** updating the primary git repo. If Nick approves, the affected repo(s)
   are committed and pushed, and that is logged.

No step writes a file anywhere except the two databases and, at step 9, the repo. No step
creates markdown. That is what keeps "what I asked for" and "what got built" provable.

## Where things go

| the thing | where it lives |
|---|---|
| **product** — anything running for Mom's Table | n100 (`192.168.2.102`) and `product/n100/` in the one repo |
| **factory** — anything that builds or operates the product | `factory/` in the one repo; it may run on either box |
| a **prototype** | on gflip (`192.168.2.107`); moves to n100 once it is wired and automated |
| a **systemd unit** or a **cron line** | into the repo beside its owner (`product/<host>/systemd/`, `factory/systemd/`) |
| a **secret** | never in the repo, not for a moment |
| the **one repo** | `huh-` at `/home/taza/repo`. `/opt/taza` is a fork to archive |

## The two development databases

Both live in the estate's only Postgres — on n100 (`taza-server`, `192.168.2.102:5432`). gflip has
no Postgres server of its own; it reaches this one over the LAN.

| database | what it is | what goes in it |
|---|---|---|
| `spec` | the **spec database** — schema `spec` + `intake`. The URS is `spec.taza_os_user_requirement_specifications`. | the specs — and every build record (step 7) |
| `decisions` | the **decisions database** — the change-management system | every decision (step 4) and every change record (step 8) |

`dev_pipeline` is transitional — being split into those two — and retires once nothing points at it.

Derived mirrors exist and are **not** authorities — never cite one as spec truth:

| mirror | rebuilt | note |
|---|---|---|
| `factory/spec-export/specs.csv` | on every change | copies the spec database. The database is the authority. |
| `urs/tables/*.tsv`, `export/murs_specs.csv` | by hand, from `master-urs.md` | a DIFFERENT source (markdown). These drift. Noise — do not use. |

`factory/team-log/` holds the team's **proposals and their history** — a proposal is not a
spec and is never binding; once a row is approved it goes into the database above, and after
that the database is the record. The folder also holds receipts (`LOADED-*.sql`) of rows
actually written: **those are historical, never run them.** For any spec, query the database.

## How to behave

1. Read this file, then the map, then the databases. Never the old markdown.
2. **Never touch:** `~/librechat` (files, `.env`, yaml, compose, containers); `mcp_shell.py` /
   `mcp_shell.service` / the shell MCP you are running in; `pg_hba.conf`; the live cloudflared
   tunnels. **Never restart gflip's cloudflared synchronously — it carries the chat session.**
3. **Copy, don't move,** until the new path is verified working. Never `rm` — retire means stop +
   disable + archive copy.
4. Never invent a table or a column. Never create markdown in the factory.
5. "Idle", "active" and exit 0 are not proof — prove the outcome (paper in the tray, HTTP 200,
   hash match, row count).
6. After ONE failed attempt: stop, read the docs, retry. Never retry-loop.
7. One bounded action per step: `STEP / CMD / EXPECT / GOT / VERDICT / NEXT`.

## The lists — five of them

| governs | file |
|---|---|
| what may be committed from the one repo | `/home/taza/repo/.gitignore` |
| what may be committed from n100's home | `n100:/home/taza/.gitignore` |
| the ten "never" rules | `decisions_log` — doctrine lives in the database |
| what LibreChat may fetch | `/home/taza/librechat/librechat.yaml` → `allowedDomains`, `allowedAddresses` |
| what the shell MCP refuses to run | `mcp_shell.py` — a write verb AND a system path in the same command |

The long-form factory doctrine (postgres rules, gherkin conventions, boot sequence, open items)
lives in `factory/docs/doctrine.html` — HTML, not markdown, so the one-markdown rule still holds.
Everything else about the system is on the map; this file only orients you.
