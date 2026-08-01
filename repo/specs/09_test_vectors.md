# Test Vectors - Acceptance Oracle

Verifier runs every row before signing off on any implementation. Scope-change note:
only the "Executor subtype selection" section is new; no other row's expected value
changed.

## R, band, and overlay flags

Raw computed R (before the required rounding fix), 4 decimal places, resulting band and
flags after applying `round(r, 6)`.

| S | O | D | R | Band | Conundrum | Out-of-control |
|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3.0000 | 2 | False | True |
| 1 | 5 | 1 | 1.3077 | 4 | False | False |
| 5 | 1 | 1 | 1.7100 | 4 | False | False |
| 1 | 1 | 5 | 2.2361 | 3 | False | False |
| 5 | 1 | 5 | 3.8236 | 2 | True | False |
| 4 | 2 | 5 | 3.9842 | 2 | True | False |
| 5 | 5 | 5 | 5.0000 | 1 | True | False |
| 2 | 5 | 4 | 3.2951 | 2 | True (D=4, SxO=10>9) | False |
| 5 | 2 | 4 | 3.8388 | 2 | True (D=4, SxO=10>9) | False |
| 3 | 4 | 4 | 3.6342 | 2 | True (D=4, SxO=12>9) | True |
| 3 | 3 | 4 | 3.4641 | 2 | False (SxO=9, not >9 - boundary correctly excluded) | True |
| 2 | 3 | 4 | 3.0262 | 2 | False | False (S=2 breaks the "all in 3-4" condition) |
| 2 | 2 | 2 | 2.0000 | 3 | False | False |

## Boundary cases - floating point (verify these first)

| S | O | D | Raw float | Rounded | Band |
|---|---|---|---|---|---|
| 2 | 2 | 2 | `2.0000000000000004` | `2.0` | 3 |
| 3 | 3 | 3 | `2.9999999999999996` | `3.0` | 2 - breaks without rounding |
| 4 | 4 | 4 | `4.0` | `4.0` | 1 |
| 5 | 5 | 5 | `4.999999999999999` | `5.0` | 1 |

An implementation that omits `round(r, 6)` before comparison misclassifies `S=O=D=3` as
Band 3 instead of Band 2. Single most important row to check first.

## Aggregate Batch Risk (ABR)

| Batch contents | Chained (3+ steps)? | ABR | Outcome |
|---|---|---|---|
| Any number of items with R <= 2.0 | No | 0 | `ok` |
| One item, R = 3.0 | No | 1.0 | `ok` |
| Fourteen items, each R = 3.0 | No | 14.0 | `ok` |
| One item, R = 5.0 | No | 9.0 | `ok` |
| Two items, each R = 5.0 | No | 18.0 | `reject` |
| One item R = 5.0 + one item R = 4.0 | No | 13.0 | `near_ceiling` |
| One item R = 5.0 + one item R = 4.0 | Yes | 19.5 | `reject` (13.0 x 1.5) |
| Three items, R = 3.0 each, chained | Yes | 4.5 | `ok` (3 x 1.0 x 1.5) |

## Executor subtype selection (route(), per 03's tool_access update)

| tool_access | Expected `executor_subtypes` |
|---|---|
| `"aider"` | `["Executor-Aider"]` |
| `"browser"` | `["Executor-Browser"]` |
| `"both"` | `["Executor-Aider", "Executor-Browser"]` |
| `"gui"` (or any value outside aider/browser/both) | raises `ValueError`, checked before ABR is even computed |

Combined with existing ABR rows:

| item_scores | chained | tool_access | Expected result |
|---|---|---|---|
| `[3.0]` | False | `"aider"` | `proceed=True`, `executor_subtypes=["Executor-Aider"]`, `abr=1.0`, `outcome="ok"` |
| `[5.0, 5.0]` | False | `"both"` | `proceed=False`, `reason="abr_ceiling_exceeded"`. `executor_subtypes` must NOT appear in this response - function returns before reaching that line. Check for the key's absence, not just an empty/null value. |

## Dispatch design

| scope_ok | sequencing_ok | efficiency_ok | unambiguous_ok | approved | failures |
|---|---|---|---|---|---|
| True | True | True | True | True | `[]` |
| False | True | True | True | False | `["scope"]` |
| True | False | False | True | False | `["sequencing", "efficiency"]` |
| True | True | True | False | False | `["ambiguity"]` |

## DA loop round-capping

| Scenario | Expected result |
|---|---|
| Concern raised, coder justifies successfully on round 1 | `status='resolved'`, `rounds_used=1` |
| Concern raised, mitigation agreed round 1, resolved round 2 | `status='resolved'`, `rounds_used=2` |
| Concern raised, mitigation agreed round 1 AND round 2, still unresolved | `status='deadlock'`, `rounds_used=2`, flagged for Verifier, ntfy fired |
| Post-execution re-analysis: conclusive on round 1 | `status='settled'`, `confidence_weight='high'` |
| Post-execution re-analysis: still inconclusive after round 2 | `status='forced_call'`, `confidence_weight='low'`, note to revisit if recurs |
