# Taza OS Risk Engine — Specification Set

This is the implementation spec for the deterministic risk-scoring, routing, and
process-discipline layer of Taza OS / HPWT. It was designed collaboratively across an
extended design session and is now ready to be coded. Read this file first — it explains
how the other files fit together and where each piece of logic should physically live.

## File index

| File | Covers |
|---|---|
| `01_risk_engine_core.md` | S/O/D scoring, the composite score R, the four risk bands, the Conundrum and Out-of-Control overlay flags, the research-investment tiers |
| `02_batch_aggregate_risk.md` | Aggregate Batch Risk (ABR) formula, ceiling, near-ceiling warning band |
| `03_role_routing_and_model_selection.md` | Driver / Devil's Advocate / Executor (Aider / Browser subtypes) / Verifier roles, when each engages, the Domain Capability Matrix |
| `04_da_feedback_loops.md` | The pre-execution Socratic concern-resolution loop and the post-execution deadlock re-analysis loop, both capped at 2 rounds |
| `05_dispatch_design_checklist.md` | Scope, sequencing, and token-efficiency gate for any proposed batch of work |
| `06_output_interaction_rules.md` | Artifact-vs-inline rule, session-type formatting, mobile-first output requirement, human-notification channel |
| `07_self_correction_protocol.md` | Capability-assertion check, diagnose-before-retry, same-session correction, anti-fabrication rules for unharnessed local executors |
| `08_domain_policies.md` | How the above mechanisms apply specifically to Design Decisions, Hardware, Configuration, Software & AI Models, Network Topology, and Web Apps / UI |
| `09_test_vectors.md` | Concrete input/output pairs for every formula and threshold — this is the acceptance-test oracle |

## Why this is split into layers (read this before writing any code)

Three layers, each with a different reason for existing, and each implemented differently:

**1. Risk Engine — deterministic code.** Everything in files 01–07 is arithmetic and
table lookups. It must be actual version-controlled, unit-tested code (Python, per the
locked Postgres+Git migration), never text an LLM re-derives from memory each session.
Two different model instances, or the same model on two different days, must produce
the identical R, band, ABR, and routing decision for the same inputs. This is the
concrete expression of Taza OS's own "deterministic-first, not LLM-first" principle.

**2. Precedent / fact tables — data, not code.** The S/O/D anchors for specific problem
types, the decision log, and the Domain Capability Matrix all grow over time via Bayesian
updating (see `03` and `09`). They are queryable data, living in Postgres (structured,
frequently-queried facts) or the git repo's `kb/` tree (narrative, documentation-style
facts — see `08` for the Software & AI Models policy on this split). They must never be
hardcoded into the Risk Engine module itself, because they change on a completely
different cadence than the math does. **Postgres now also holds the LangGraph
checkpoint tables** (confirmed live on N100, `taza_os` database) — this is the
coordination/state layer, distinct from `decision_log` / `capability_matrix` /
`precedent_table` but living in the same instance.

**3. Instruction layer — thin, and the only LLM-interpreted part.** Every agent (the
Driver, the Devil's Advocate, the Executor subtypes, the Verifier, and any specialist
model added later) needs the same short briefing: *elicit-or-look-up S/O/D for a new
situation, call the Risk Engine, follow its output; check the Capability Matrix before
asserting a capability; the specifics of software/hardware/config/network facts live in
the repo and Postgres, not in your own memory.* This is deliberately small. It should
not contain any formula, threshold, or number that appears in files 01–09 — if it does,
that number can drift out of sync with the actual code.

**4. Orchestration — LangGraph, sitting on top of layers 1–3, not replacing them.** The
locked HPWT loop (propose → KB gauntlet → confidence gate → optional DA review → Nick
approval → dual execute → verify → KB update) is implemented as a LangGraph state graph,
checkpointed to the Postgres `taza_os` database via `PostgresSaver`. Each stage is a
node; the confidence check is a conditional edge; Nick's approval is a human-in-the-loop
interrupt; the two Executor subtypes are parallel branches when a task needs both. The
graph calls into Layer 1 functions (`score()`, `aggregate_batch_risk()`, `route()`) for
every decision point — it does not reimplement or approximate that math itself. Human
notification at Band 1/2 decision points (the "Pause for Nick" / "Inform Nick" actions in
`01`) fires via **ntfy**, not a Notion write — see `06`. This replaces the earlier
Notion-inbox-polling coordination pattern entirely for local AIs; Notion is retained only
for Claude Code, which is cloud-hosted and not "truly local."

## Suggested repo layout

```
/opt/taza/repo/
  scripts/
    risk_engine.py         # files 01, 02 — pure functions, fully unit tested
    role_routing.py        # file 03 — reads risk_engine output + capability_matrix table
    dispatch_design.py     # file 05
    hpwt_graph.py           # LangGraph state graph — orchestration layer (§4 above),
                             # calls risk_engine.py / role_routing.py, never duplicates
                             # their logic; PostgresSaver checkpointer against taza_os
    notify.py               # thin ntfy wrapper used by hpwt_graph.py at Band 1/2 nodes
  specs/
    00_overview_and_architecture.md   # this file and its siblings — committed as
    01..09_*.md                        # reference docs once the harness passes tests
  kb/
    architecture/          # decision_log entries, superseded/locked history
    hardware/               # durable specs; recheck only on scope change
    software/               # perishable — verify claims against git commits (file 08)
    network/                # perishable — freshness windows per file 08
  DECISIONS.md              # human-readable mirror of decision_log
```

Postgres tables referenced throughout this spec (`decision_log`, `capability_matrix`,
`precedent_table`, plus the LangGraph checkpoint tables) all live in the `taza_os`
database on N100, per the locked Postgres+Git migration plan (2026-07-26); see
`03_role_routing_and_model_selection.md` and `08_domain_policies.md` for the specific
columns each needs.

## Deployment plan for building this

1. This spec set (you're reading it).
2. `09_test_vectors.md` — the acceptance-test oracle, authored independently of the
   implementation, from worked examples already hand-verified during design.
3. Implementation, one bounded script at a time, against this spec — local Qwen model(s)
   on gflip are the executors; see `05` and the per-script dispatch prompts for the exact
   scoping discipline. Build order: `risk_engine.py` (01+02) → `role_routing.py` (03) →
   `dispatch_design.py` (05) → `notify.py` → `hpwt_graph.py` (wires the above into the
   LangGraph orchestration described in Layer 4 above; requires `risk_engine.py`,
   `role_routing.py`, and `dispatch_design.py` already passing their own tests first).
4. Independent Verifier (separate session from whoever implements) runs the test
   vectors, and specifically audits every boundary value in `09` — that's where
   off-by-one and floating-point rounding errors hide.
5. This build itself should run through the Escalation Gate defined in
   `01_risk_engine_core.md` — checkpoints at spec-complete, tests-complete, and
   implementation pass/fail, not a single handoff at the end.

**Working with an unharnessed local executor.** The executor building this (Qwen Coder
on gflip, currently no agent scaffolding beyond a raw shell tool) has no built-in
guardrails against guessing, fabricating command output, or silently skipping steps in a
chained command. `05` and `07` now carry explicit rules for this. The practical
consequence for anyone writing a dispatch prompt: smaller, more literal, more
independently-verifiable steps than you'd give a harnessed agent — even if that means
more dispatches and a slower night. See `07` for the specific anti-fabrication protocol.
