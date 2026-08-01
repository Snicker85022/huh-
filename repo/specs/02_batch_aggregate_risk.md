# Batch Aggregate Risk (ABR)

Governs whether a set of items may be dispatched together as one batch. Separate
question from any individual item's band - a batch of low-risk items is fine regardless
of count; a batch containing two high-risk items should be structurally difficult to
construct.

## Formula

```
ABR = sum( max(0, R_i - 2) ** 2  for each item i in the batch )
if the batch has 3 or more chained/interdependent steps (a later step's correctness
depends on an earlier step's output):
    ABR = ABR * 1.5
```

The shift-by-2 baseline means items with R <= 2.0 (Band 4) contribute zero, no matter
how many are batched - this is what makes "lots of green stuff together" free. The
square is what makes combining risk expensive rather than merely additive.

## Ceiling and warning band

| ABR | Outcome |
|---|---|
| ABR > 14.99 | Reject. Batch must be rescoped or split. |
| 12.0 <= ABR <= 14.99 | Near-ceiling. Allowed, but triggers a mandatory second look even though it technically passes. |
| ABR < 12.0 | Batch shape is fine, proceed to role routing (03). |

## Reference behavior (see 09 for the full test-vector table)

| Contents | ABR | Outcome |
|---|---|---|
| Any number of R <= 2.0 items | 0 | Always allowed |
| One R = 3.0 item | 1 | Allowed |
| Fourteen R = 3.0 items | 14 | Near-ceiling - allowed, but triggers the mandatory second look (DA gate, 03) |
| One R = 5.0 item alone | 9 | Allowed |
| Two R = 5.0 items together | 18 | Rejected - two high-risk items must never share a batch |
| One R = 5.0 + one R = 4.0 item | 13 | Allowed, but near-ceiling - flag for manual look |

## Function signature

```python
def aggregate_batch_risk(item_scores: list[float], chained: bool) -> dict:
    """item_scores: list of R values (already computed via score() in 01).
    chained: True if the batch has >=3 interdependent steps."""
    abr = sum(max(0, r - 2) ** 2 for r in item_scores)
    if chained:
        abr *= 1.5
    outcome = (
        "reject" if abr > 14.99
        else "near_ceiling" if abr >= 12.0
        else "ok"
    )
    return {"abr": abr, "outcome": outcome}
```
