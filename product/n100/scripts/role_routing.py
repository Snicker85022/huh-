"""Role routing and model selection (spec 03).

route() verbatim from specs/03_role_routing_and_model_selection.md. Calls
risk_engine.aggregate_batch_risk / band_of for every decision point (spec 00
Layer 1: routing code never reimplements the math).
"""

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
