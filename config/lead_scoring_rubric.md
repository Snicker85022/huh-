# Lead Scoring Rubric (W2 v2 — D6/D7/D8 LOCKED)

profit_score (1–5) → category via deterministic thresholds:

  5 → Hot
  4 → Hot
  3 → Warm
  2 → Low
  1 → Pass

AI override: at most ONE level up or down, with a written red_flags reason —
never a silent override. AI unavailable → category = Low + scoring_ai_unavailable=true.

Rubric is Nick-only-edited and git-versioned; rubric_version = commit hash of this
file at scoring time, embedded on each lead. This file is the canonical rubric;
workflow code reads it from this path (D6).

DRAFT — create by Cortex from postgres-spec.md D6/D7/D8; needs Nick sign-off.
