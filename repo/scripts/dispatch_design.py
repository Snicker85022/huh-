"""Dispatch design checklist (spec 05).

check_dispatch_design() verbatim from specs/05_dispatch_design_checklist.md.
Four judgment-call gates (scope/sequencing/efficiency/ambiguity) - not derived
from 01/02; low risk does not auto-pass this check.
"""

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
