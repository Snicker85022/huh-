"""Risk Engine - deterministic risk scoring per Taza OS specs 01 + 02.

Function bodies verbatim from specs/01_risk_engine_core.md and
specs/02_batch_aggregate_risk.md (post-debate ruling, committed HEAD):

- band_of(r): single source of truth for all band thresholds (2.0/3.0/4.0).
- score(s, o, d): R = S^(1/3) * O^(1/6) * D^(1/2), rounded to 6dp before band
  thresholds (floating-point trap, spec 01).
- aggregate_batch_risk(item_scores, chained): ABR = sum(max(0, R_i - 2)^2),
  x1.5 when chained (3+ interdependent steps); reject > 14.99, near_ceiling
  12.0-14.99, ok < 12.0 (spec 02).
"""

def band_of(r: float) -> int:
    """Band from an already-rounded R value. Single source of truth for all band
    thresholds (2.0 / 3.0 / 4.0) -- score() and role_routing's route() both call this so
    the thresholds can never drift apart. r must be round(r_raw, 6) before calling."""
    if r >= 4.0:
        return 1
    if r >= 3.0:
        return 2
    if r >= 2.0:
        return 3
    return 4

def score(s: int, o: int, d: int) -> dict:
    """s, o, d each in 1..5. Returns R, band, color, research_tier, both overlay flags."""
    if not (1 <= s <= 5 and 1 <= o <= 5 and 1 <= d <= 5):
        raise ValueError(f"S, O, D must each be in 1..5, got S={s} O={o} D={d}")
    r_raw = s ** (1/3) * o ** (1/6) * d ** (1/2)
    r = round(r_raw, 6)  # required -- see floating-point trap above
    band = band_of(r)  # single source of truth -- see band_of() above
    color = {1: "red", 2: "coral", 3: "amber", 4: "green"}[band]
    research_tier = band
    conundrum = (d == 5 and s >= 4) or (d == 4 and s * o > 9)
    out_of_control = s in (3, 4) and o in (3, 4) and d in (3, 4)
    return {
        "r": r, "band": band, "color": color, "research_tier": research_tier,
        "conundrum": conundrum, "out_of_control": out_of_control,
    }

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
