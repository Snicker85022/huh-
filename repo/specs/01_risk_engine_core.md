# Risk Engine - Core Scoring

No math/threshold change for VNC/browser/LangGraph/ntfy scope. One addition: escalation
actions below now fire via ntfy, not Notion.

## Inputs

Three axes, integer 1-5, per proposed action/item:

| Axis | Meaning | 1 (low) | 3 (medium) | 5 (high) |
|---|---|---|---|---|
| S - Severity | Consequence if wrong | Cosmetic, isolated, reversible | Touches shared infra, moderate reversal effort | Production/customer-facing, architectural lock-in, cross-system cascade, irreversible |
| O - Occurrence | Likelihood we're wrong | KB-FACT / verified this session | INFERRED, 60-85% confidence, or stale | UNVERIFIED, no KB entry, or contradicts known fact |
| D - Detection | Time to notice if wrong | Fails loudly/immediately | Surfaces within session or days | Silent, compounding, found only downstream |

Elicited by the agent, or looked up from the precedent table (see 03) if a matching
problem type has calibrated values. Confirmed with Nick until the precedent table has
enough evidence to stand alone.

## Composite score R

R = S^(1/3) * O^(1/6) * D^(1/2)

- Exponents sum to 1 -> R always in [1, 5] for S, O, D each in [1, 5]. No rescaling.
- Weight order: D > S > O (doubling D moves R ~1.41x, S ~1.26x, O ~1.12x). Deliberate.
- Implement with math.pow / **, not integer approximations. See 09 for exact floats.

## Escalation bands

| Band | Color | R range | Action |
|---|---|---|---|
| 1 | Red | R >= 4.0 | Pause for Nick. No proceed without explicit approval. |
| 2 | Coral | 3.0 <= R < 4.0 | Inform Nick, then proceed. |
| 3 | Amber | 2.0 <= R < 3.0 | Proceed with caution; flag the risk; report later. |
| 4 | Green | R < 2.0 | Proceed; report later. |

Notification: Band 1/2 actions fire via ntfy (see 06), not Notion. Band assignment
itself is unaffected - table above is the complete rule.

No separate "Consequence x Cost-if-wrong" axis pair. Consequence folds into Severity;
Cost-if-wrong is an output of Severity x Detection interacting, not an independent
input. Do not add a second scoring pass.

## Overlay flags

Run in addition to band assignment. Never change the band. Add mandatory work on top.

### Conundrum flag

conundrum = (D == 5 and S >= 4) or (D == 4 and S * O > 9)

Action: dual-track mitigation - reduce S AND improve D. Both required, not either/or.

Every combination satisfying this computes to R >= 3.0 (exhaustive check across the
valid S/O/D space, done at design time) -> always Band 1 or 2 -> always inside 03's
DA-engagement range (top two bands only). If the R formula ever changes, re-verify this
property and 03's DA-engagement rule together.

### Out-of-control flag

out_of_control = S in (3,4) and O in (3,4) and D in (3,4)

All three axes simultaneously mediocre. Not a severity escalation - a process-debt
flag: medium-frequent + medium-hard-to-detect + medium-hard-to-recover, usually means
tribal-knowledge dependency or bad detection tooling. Action: open a process-debt
ticket - at least one of: eliminate root cause, build a mitigation plan, add real
detection instrumentation. Mirrors the existing Six Sigma ladder (200/15/5 ppm).

## Research-investment tiers

| R range | Tier | Action |
|---|---|---|
| R < 2.0 | 1 | Skip formal research. Bayesian KB update still fires (see 03). |
| 2.0 <= R < 3.0 | 2 | Quick KB check only. |
| 3.0 <= R < 4.0 | 3 | Read manual + search forums before proposing. |
| R >= 4.0 | 4 | Full research + explicit KB contradiction check. |

## Function signature

Floating-point trap, confirmed during spec verification: S=O=D=3 is mathematically
R=3.0 (Band 2), but `3**(1/3) * 3**(1/6) * 3**(1/2)` evaluates to
`2.9999999999999996` in IEEE 754 double - one ULP under 3.0. Naive `r >= 3.0`
misclassifies it as Band 3. Same happens at S=O=D=5 (`4.999999999999999` - harmless
there, still far above 4.0). Fix: `round(r, 6)` before any threshold comparison.
Required, not optional.

```python
def score(s: int, o: int, d: int) -> dict:
    """s, o, d each in 1..5. Returns R, band, color, research_tier, both overlay flags."""
    if not (1 <= s <= 5 and 1 <= o <= 5 and 1 <= d <= 5):
        raise ValueError(f"S, O, D must each be in 1..5, got S={s} O={o} D={d}")
    r_raw = s ** (1/3) * o ** (1/6) * d ** (1/2)
    r = round(r_raw, 6)  # required -- see floating-point trap above
    band = 1 if r >= 4.0 else 2 if r >= 3.0 else 3 if r >= 2.0 else 4
    color = {1: "red", 2: "coral", 3: "amber", 4: "green"}[band]
    research_tier = band
    conundrum = (d == 5 and s >= 4) or (d == 4 and s * o > 9)
    out_of_control = s in (3, 4) and o in (3, 4) and d in (3, 4)
    return {
        "r": r, "band": band, "color": color, "research_tier": research_tier,
        "conundrum": conundrum, "out_of_control": out_of_control,
    }
```

Raise, don't clamp, on out-of-range S/O/D. See 09 for the boundary cases the Verifier
checks first.
