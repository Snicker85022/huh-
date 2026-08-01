# Dispatch Design Checklist

Rule: dispatches must be right-sized. No bundling unrelated work. No fragmenting one
coherent change into wasteful pieces. No wasted tokens/time.

## Checks (all must pass; four for an unharnessed executor, three otherwise)

1. Scope right-sized. Not bundled, not fragmented.
2. Sequencing sound. Step order correct. (Distinct from 02's chained-steps ABR
   multiplier, which flags risk, not order.)
3. Token/time efficient. No redundant work, no re-fetched context, no duplicate setup.
4. Unharnessed executor only: no step requires interpretation. Every instruction is a
   literal command, a literal file to read, or a literal value to write - never "figure
   out X." If satisfying the dispatch requires the executor to guess anything, the
   dispatch is not ready; tighten it or split off a recon step first. See 07 for why
   this check exists.

Check 4 is independent of checks 1-3: a dispatch can pass all three and still fail 4 on
one vague instruction.

## Outcome

- All required checks pass: approved, proceed.
- Any fail: redesign before dispatch (scope, order, batching, or ambiguity). Loop back
  to the Driver. Do not proceed on a known-bad shape.

## Function signature

```python
def check_dispatch_design(scope_ok: bool, sequencing_ok: bool, efficiency_ok: bool,
                           unambiguous_ok: bool = True) -> dict:
    """unambiguous_ok defaults True for harnessed executors (check 4 doesn't apply).
    Pass it explicitly, computed, whenever the target executor is unharnessed."""
    passed = scope_ok and sequencing_ok and efficiency_ok and unambiguous_ok
    failures = [name for name, ok in [
        ("scope", scope_ok), ("sequencing", sequencing_ok),
        ("efficiency", efficiency_ok), ("ambiguity", unambiguous_ok),
    ] if not ok]
    return {"approved": passed, "failures": failures}
```

Note: all four booleans are judgment calls (Driver/DA), not derived from 01/02. Low
risk (Band 4, low ABR) does not auto-pass this check.
