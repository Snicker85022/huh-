def score(s: int, o: int, d: int) -> dict:
    """s, o, d each in 1..5. Returns R, band, color, research_tier, both overlay flags."""
    if not (1 <= s <= 5 and 1 <= o <= 5 and 1 <= d <= 5):
        raise ValueError(f"S, O, D must each be in 1..5, got S={s} O={o} D={d}")
    r_raw = s ** (1/3) * o ** (1/6) * d ** (1/2)
    r = round(r_raw, 6)
    band = 1 if r >= 4.0 else 2 if r >= 3.0 else 3 if r >= 2.0 else 4
    color = {1: "red", 2: "coral", 3: "amber", 4: "green"}[band]
    research_tier = band
    conundrum = (d == 5 and s >= 4) or (d == 4 and s * o > 9)
    out_of_control = s in (3, 4) and o in (3, 4) and d in (3, 4)
    return {"r": r, "band": band, "color": color, "research_tier": research_tier, "conundrum": conundrum, "out_of_control": out_of_control}
