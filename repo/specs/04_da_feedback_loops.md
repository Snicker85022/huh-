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
    if not well_founded:
        log("concern_resolved", justification=coder_reasoning)
        break  # proceed to execution
    mitigation = agree_on_mitigation()
    # mitigation must be one of: minimize_risk_before, add_testing_after, or BOTH.
    # This is an inclusive choice, situation-dependent -- never treat it as either/or.
    round += 1
    if round >= 2:
        log("deadlock", flagged_for_review=True, mitigation_attempted=mitigation)
        break  # proceed to execution ANYWAY -- forced decision, not blocked indefinitely
    # otherwise loop again with the revised plan
```

Key rules:
- "Well-founded" is determined by the coder's justification actually holding up under
  Socratic questioning, not by assertion.
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
    """Returns {'status': 'resolved'|'deadlock', 'rounds_used': int, ...}"""

def reanalyze_deadlock(deadlock_record, results, max_rounds=2):
    """Only called when resolve_concern returned status='deadlock'.
    Returns {'status': 'settled'|'forced_call', 'confidence_weight': 'high'|'low', ...}
    and writes a lessons_learned row to the KB either way."""
```
