# Role Routing and Model Selection

## The four roles

| Role | Who (currently) | Engages when | Job |
|---|---|---|---|
| Driver | DeepSeek V4 Flash | Every batch, always | Plans, designs, sequences the batch - locked architecture decision (Postgres+Git migration, 2026-07-26): DeepSeek is the primary dev brain, not Claude Code. |
| Devil's Advocate (DA) | Claude Chat | When any item in the batch has individual Band 1/2, OR the batch ABR outcome is near_ceiling (02) -- the near-ceiling "mandatory second look" has no other owner | Adversarially/collaboratively reviews the Driver's plan before Executor touches it. Covers research-risk proposals (source trust, contradiction-checking) and execution-risk proposals (code/batch/sequencing). Standing instruction for every review: any item with D=5 requires a detection-instrumentation or explicit-visibility component in its mitigation -- the D-half of the Conundrum action, applied even where the full dual-track doesn't fire (S < 4). See 04 for the feedback loop. |
| Executor | Local model, one of two subtypes (below) | Every batch that clears the DA gate (or every batch, if DA wasn't triggered) | Writes/runs the change. |
| Verifier | Local model, separate session from Executor - non-negotiable | Every batch, always | Tests, verifies against acceptance criteria, documents. Must never share context with Executor - that's what makes it an independent check rather than the same reasoning validating itself. Blinding: the Verifier re-runs the acceptance check itself, own execution, own fresh capture; the Executor's report is an audit artifact, not evidence. Reading the Executor's pasted output primes the Verifier -- verification from narrative is confirmation, not checking (see 07). |

### Executor subtypes

Two subtypes, distinguished by which tool the task requires:

| Subtype | Tooling | Handles |
|---|---|---|
| Executor-Aider | Shell/file access on gflip or N100 | Code edits, file work, config - anything reachable via shell/filesystem. |
| Executor-Browser | browser-use + VNC | Web/UI tasks - anything where the correct outcome can only be confirmed by a rendered page (see 08's Web Apps / UI domain). |

A task's `tool_access` (`aider` / `browser` / `both`) determines which subtype(s)
engage. When `both`, the two subtypes run in parallel on the same item - not
sequential, and a different kind of pairing than the `chained` flag in 02, which governs
sequencing between batch items, not between the two subtypes handling one item. A batch
mixing `aider`-only and `browser`-only items should generally fail 05's scope check
(dissimilar work) before it gets this far - `tool_access` is assumed uniform across a
well-scoped batch, not decided per-item.

## Routing sequence

1. Item scores computed (01), batch aggregate risk computed (02).
2. If ABR outcome is `reject`, batch is rescoped/split, does not proceed.
3. Driver plans the batch (always) and declares the batch's `tool_access`
   (`aider` / `browser` / `both`).
4. DA gate check: does any item have Band 1/2, or is the batch ABR outcome near_ceiling?
   Yes -> DA reviews the plan (04's pre-execution loop runs here; the near-ceiling second
   look has no other owner). No -> skip straight to Executor.
5. Executor subtype(s) selected from `tool_access` (table above). Executor runs.
   Verifier runs, separate session, always.
6. Bayesian KB update fires regardless of outcome (see below).

## Decision-QA sweep (Driver recurring duty)

After every 3 completed decisions (count-based, not calendar -- adjust if the
signal-to-noise ratio is too low), the Driver sweeps decision_log and appends to the
`decision_qa` table in Postgres (taza_os):

- band-predicted vs Verifier-verified outcome deltas, per decision
- structural deadlocks per N decisions, per 04's nature classification
- elicitation deltas (re-elicitation disagreements per N, per axis)
- per-decider rate series: engine-only decisions vs Nick-override decisions, accuracy
  over a sliding window -- Nick gets the same calibration feedback the models get, privately
- Nick's override rate (reversals of the engine per N decisions): rising = trust erosion in
  the engine's inputs, a process-debt signal; falling = the loop is working

Any rate crossing its threshold opens a process-debt ticket per 01's out-of-control
mechanism (eliminate root cause / mitigation plan / add detection instrumentation). This
sweep is the scheduled reader of the audit trail; nothing reads the trail if this doesn't
run.

## Domain Capability Matrix

Living table, not a static config. Answers "which model is actually good at this
specific domain/tool scope" - separate from the risk score, because a low-risk task in
an unfamiliar domain still needs the model that knows that domain, and a high-risk task
in a well-trodden domain doesn't automatically need the largest model.

### Schema (Postgres table `capability_matrix`)

| Column | Type | Notes |
|---|---|---|
| `model` | text | e.g. `deepseek-v4-flash`, `phi-4-14b-q4km` |
| `role` | text | Driver / Executor-Aider / Executor-Browser / Verifier / DA |
| `domain_scope` | text | e.g. "ER605 Playwright automation", "systemd config", "Notion API" |
| `tool_access` | text | `aider` / `browser` / `both` - which subtype(s) this row's model supports for this domain_scope. Meaningful for local Executor rows; `n/a` for Driver/DA rows that don't touch tools directly. |
| `taza_confidence` | float | Bayesian posterior, 0-1. Starts low for any new row. |
| `evidence_count` | int | Number of real dispatch outcomes this is based on. Starts at 0. |
| `last_updated` | timestamp | |
| `notable_failures` | text | Free text or linked failure_mode rows |
| `external_reference` | text | Public benchmarks etc - prior information only, never treated as Taza-verified evidence. Keep structurally separate from `taza_confidence` so nobody confuses a public benchmark with a real verified dispatch outcome. |

### Update rule

Every dispatch outcome updates the row's `taza_confidence` (Bayesian posterior: success
nudges up with a ceiling so one success can't overclaim certainty; failure drops it
sharply, can demote it) and increments `evidence_count`. Same update mechanism used for
the precedent table (S/O/D anchors) - one mechanism, multiple fact types.

### Seed rows (as of this spec - evidence_count starts at 0 for all)

| model | role | domain_scope | tool_access | taza_confidence | evidence_count | external_reference |
|---|---|---|---|---|---|---|
| deepseek-v4-flash | Driver | Batch/sequence planning, general coding-agent tasks | n/a | low (unseeded) | 0 | 96.7% AIME 2026 (independent eval); DeepSeek positions it coding/agent-focused - prior only |
| phi-4-14b-q4km | Executor-Aider / Verifier | TBD | aider | low (unseeded) | 0 | none |
| qwen3-14b | Executor-Aider / Verifier (night) | TBD | aider | low (unseeded) | 0 | none |

New specialist models or new roles on existing models onboard by adding a row here at
the same low-confidence/zero-evidence start - no separate onboarding mechanism. They
earn trust the same way everything else does: real outcomes. No Executor-Browser row is
seeded yet; add one (`tool_access: browser`) the first time a browser-use+VNC
model/config actually runs against this architecture.

## Function signature

```python
def route(item_scores: list[float], chained: bool, tool_access: str) -> dict:
    from risk_engine import aggregate_batch_risk, band_of  # single module per 00; band thresholds live in 01
    if tool_access not in ("aider", "browser", "both"):
        raise ValueError(f"tool_access must be one of aider/browser/both, got {tool_access!r}")
    abr_result = aggregate_batch_risk(item_scores, chained)
    if abr_result["outcome"] == "reject":
        return {"proceed": False, "reason": "abr_ceiling_exceeded", **abr_result}
    da_required = (abr_result["outcome"] == "near_ceiling") or any(band_of(r) in (1, 2) for r in item_scores)
    executor_subtypes = (
        ["Executor-Aider"] if tool_access == "aider"
        else ["Executor-Browser"] if tool_access == "browser"
        else ["Executor-Aider", "Executor-Browser"]  # both, run in parallel on the item
    )
    return {
        "proceed": True,
        "da_required": da_required,
        "near_ceiling": abr_result["outcome"] == "near_ceiling",
        "executor_subtypes": executor_subtypes,
        **abr_result,
    }
```
