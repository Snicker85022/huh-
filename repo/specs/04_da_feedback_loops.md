# Devil's Advocate Feedback Loops

No change to either loop's logic or round-cap for VNC/browser/LangGraph/ntfy scope.
One addition: flagged deadlocks now have a concrete delivery mechanism.

Two related but distinct loops. The first runs before execution, when DA raises a
concern about the Driver's plan. The second only runs after execution, and only if the
first loop ended in a genuine, unresolved deadlock.

Both loops are explicitly collaborative and Socratic/Bayesian, not purely adversarial -
the goal is the best solution both parties can reach, not DA "winning." If both sides
genuinely update on each other's evidence, true deadlocks should be rare. Both loops are
capped at 2 rounds; a decision must be reached and acted on after that, with the
disagreement logged rather than silently dropped.

## Loop 1 - pre-execution concern resolution

```
round = 0
while True:
    da_raises_concern()
    well_founded = coder_and_da_discuss()  # Socratic: coder explains reasoning
    # Criterion: a concern is well-founded iff it is STRUCTURAL -- it would still bite if
    # the other side had perfect knowledge. A concern that dissolves once the homework is
    # done was an information gap, not a design flaw; resolve it by doing the homework.
    if not well_founded:
        log("concern_resolved", justification=coder_reasoning)
        break  # proceed to execution
    mitigation = agree_on_mitigation()
    # mitigation must be one of: minimize_risk_before, add_testing_after, or BOTH.
    # This is an inclusive choice, situation-dependent -- never treat it as either/or.
    round += 1
    if round >= 2:
        nature = classify_disagreement(transcript)  # "structural" | "epistemic_asymmetry"
        log("deadlock", flagged_for_review=True, mitigation_attempted=mitigation, nature=nature)
        if nature == "structural":
            escalate_to_nick(urgency="pause")  # Nick's thumb decides; do not proceed past Nick's gate
            break  # proceed to the NEXT gate -- for a Band-1 item that is still Nick's approval
        break  # epistemic_asymmetry: forced decision, Verifier flag, inform-level ntfy -- never silent
    # otherwise loop again with the revised plan
```

Key rules:
- "Well-founded" is determined by the coder's justification actually holding up under
  Socratic questioning, not by assertion. Operational criterion: a concern is well-founded
  iff it is structural - it would still bite if the other side had perfect knowledge (all
  homework done, all evidence in hand). A concern that dissolves once the homework is done
  was an information gap, not a design flaw; resolve it by doing the homework, don't
  escalate it.
- Loop 1 resolves BEFORE the Band-1 gate. "Proceed to execution anyway" on deadlock means
  proceed to the NEXT gate - for a Band-1 item, that is still Nick's approval. It never
  means straight to execution.
- A logged resolution (well_founded = False) must cite the specific evidence that changed
  the mind - a fact, a command output, a re-derived number. A resolution with zero new
  evidence in the transcript is auto-flagged low-weight to the Verifier.
- Deadlock classifications are auditable: an epistemic_asymmetry classification is valid
  only if the transcript shows the evidence (the homework). Otherwise it defaults to
  structural. The Verifier checks classifications on its re-execution pass.
- Mitigation choice is genuinely three-way: minimize risk before proceeding, add testing
  after, or both - pick whichever fits the specific situation. Do not hardcode this as a
  binary choice.
- A deadlock that proceeds anyway must be flagged for the Verifier, not silently
  dropped. The unresolved objection is real information; losing it defeats much of the
  point of having DA in the first place. Attach it to the plan as an explicit
  "verifier: check this specifically" note. A logged deadlock also fires an ntfy
  notification to Nick (same mechanism as 01's Band 1/2 actions, see 06) - a flagged,
  unresolved objection that's proceeding anyway is exactly the kind of thing Nick should
  know about in real time, not discover later reading a log.

## Loop 2 - post-execution deadlock re-analysis

Only runs if Loop 1 ended in a logged deadlock. Triggered once Executor/Verifier results
are in.

```
round = 0
while True:
    da_and_coder_reanalyze(actual_results)
    conclusive = disprove_or_validate(original_concern)
    if conclusive:
        log_lessons_learned(status="settled", outcome=conclusive_result,
                             confidence_weight="high")
        break
    round += 1
    if round >= 2:
        log_lessons_learned(status="forced_call", outcome=best_available_judgment,
                             confidence_weight="low",
                             note="revisit if this pattern recurs")
        break
```

Key rule on confidence weighting: a settled lessons-learned entry (concern actually
disproved or validated against real results) may update the precedent table's S/O/D
anchors with real conviction. A forced-call entry (still unresolved, just a judgment
call on record) must be logged with lower confidence weight and an explicit note to
revisit if the same pattern recurs - it must not be treated as equally strong evidence
as a settled outcome.

## Function signatures

```python
def resolve_concern(concern, max_rounds=2):
    """Returns {'status': 'resolved'|'deadlock', 'rounds_used': int,
    'nature': 'structural'|'epistemic_asymmetry'|None, 'evidence': str|None, ...}
    'nature' is set only when status='deadlock'. 'evidence' is required when
    status='resolved'."""

def reanalyze_deadlock(deadlock_record, results, max_rounds=2):
    """Only called when resolve_concern returned status='deadlock'.
    Returns {'status': 'settled'|'forced_call', 'confidence_weight': 'high'|'low', ...}
    and writes a lessons_learned row to the KB either way."""
```
