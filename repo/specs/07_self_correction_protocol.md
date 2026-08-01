# Self-Correction Protocol

Four standing triggers. Each has a concrete, checkable condition - implement the
condition-check, leave wording to the instruction layer.

## 1. Before asserting a capability

Before any agent states "X can do Y" or "I can do Y", check the Domain Capability Matrix
(03) for that model/role/domain_scope combination:

```python
def can_assert_capability(model, role, domain_scope, max_age_days=None) -> bool:
    row = capability_matrix.lookup(model, role, domain_scope)
    if row is None or row.evidence_count == 0:
        return False
    if max_age_days is not None and row.age_days() > max_age_days:
        return False
    return row.taza_confidence >= 0.6  # threshold to be tuned with real evidence
```

If False: respond "I need to verify that," then dispatch a check. Never assert and
hope.

Probation: the first use of any capability runs under Band-1-style supervision by
definition -- the smoke test IS the evidence. The row is logged status='probation' and
auto-graduates after N=3 verified outcomes; Nick does not have to track which
capabilities are still on probation. For Executor-Browser, the first browser-use+VNC run
is a supervised test by definition, not an assertion of readiness.

## 2. Diagnose before retry

On any dispatch failure, do not retry the same approach with different wording.

```python
def handle_dispatch_failure(error) -> dict:
    root_cause = identify_root_cause(error)          # read the ACTUAL error
    missing_capability = check_capability_gap(root_cause)
    if missing_capability:
        verify_capability_exists(missing_capability)  # don't assume either way
    new_method = choose_different_method(root_cause)  # must differ from the failed attempt
    return {"root_cause": root_cause, "new_method": new_method}
```

## 3. Same-session correction

When an agent was wrong about something, the correction lands in the record (KB, git,
decision_log, wake-up file - whichever holds the wrong fact) in the same session it was
found. Show Nick the exact edit inline before or alongside writing it.

```python
def correct_record(source_of_truth, wrong_fact, correction, evidence) -> None:
    """Writes the correction to the same store the wrong fact came from.
    Preserve the original text for history (mark superseded, don't delete) -
    see 08's Design Decisions section for a worked example."""
```

## 4. Never fabricate verification evidence

Every claim of "this worked" must be backed by literal, freshly-captured command output
pasted into the report - not a description of output, not a remembered value from an
earlier step, not an inference from "the command didn't error." If the executor did not
run something and see its output this turn, say so instead of guessing.

```python
def verify_dispatch_claim(claim: str, fresh_capture: str | None) -> dict:
    """fresh_capture must be literal output of a command run THIS turn -- a PID from
    pgrep, a status from systemctl is-active, a row count from a live query, a
    screenshot/VNC frame (see 06). A remembered or prior-turn value does not count."""
    if fresh_capture is None:
        return {"accepted": False, "reason": "no_fresh_capture_provided"}
    return {"accepted": True, "evidence": fresh_capture}

Blinding (see 03): the Verifier re-runs the acceptance check itself, own execution, own
fresh capture. The Executor's report is an audit artifact, not evidence -- reading it
primes the Verifier toward confirmation. Where the Executor's report is the only record,
treat it as a claim to re-test, never as verification.
```

Two specific failure shapes to check for:
- Chained commands (`A && B && C`) can fail partway without an obvious error at the
  failure point - the visible symptom can show up later, at an unrelated step. Check
  each step's actual exit status individually; don't assume the whole chain ran.
- Cross-machine timestamp comparisons need each host's clock zone confirmed first, not
  assumed. Machines in the same fleet are not guaranteed to share a timezone.
