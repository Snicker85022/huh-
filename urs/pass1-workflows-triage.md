# Pass 1 Triage — workflows.md pilot (54 findings, 14 specs)

Source: fusion Main (deepseek-v4-flash) audit of workflows.md, 2026-09-30.
Triage: Cortex, cross-referenced against docs/postgres-spec.md (living D-decisions).

## Meta-finding 1: corpus is 6 decisions behind the living doc

The auditor flagged these as open. They are already LOCKED in postgres-spec.md:

| Finding | Already decided | Resolution |
|---|---|---|
| W1 trigger "Gmail-only vs +Wix webhook" | D1 | V1.0 = email only; webhook is V1.1 stub. Fix Trigger/Inputs text. |
| W5 "<1 second transcription" ambiguity | D13 | Tiered: ≤15s→<1s, 16-60s→<3s, >60s→reject. Fix SLA text. |
| W2 "Nick's scoring rubric" undefined | D6 | Rubric → ~/repo/config/lead_scoring_rubric.md, git-versioned. **BUT FILE DOES NOT EXIST** (see meta-finding 3). |
| W3 timing "T-60s delivery" | D9 | Fire at 60-min window entry, 5-min floor, ≤2min SLA. Fix text. |
| W6 Nightly Deep Analysis | Superseded | Lead scoring now real-time via W2. Mark Superseded. |
| W10 Google Calendar Sync | D15 | Superseded by calendar web app. Mark Superseded. |
| W9 "12 attrs (7+5)" | D18 | 11 attrs (6 visible + 5 hidden). Fix text. |

## Meta-finding 2: universal AC/VM gap

13 of 14 specs lack Acceptance Criteria; 13 lack Verification Method. Every single
workflow spec. This is where "code writes itself" lives or dies.

## Meta-finding 3: one decision artifact is missing

D6 says the lead-scoring rubric lives at ~/repo/config/lead_scoring_rubric.md.
That directory/file does not exist. The decision was recorded; the artifact wasn't.

## Genuinely new — needs Nick (see chat questions)

- W11: FRS lists "Invoices", Trigger lists "Customer Events" — which is canonical?
- W3: "3-paragraph ≤300 chars" self-contradictory (AI-007 says "who/last interaction/angle <300 chars")
- W4: model selection rule ("cheapest capable") + backup provider undefined
- W13: input "digest from W6" dangles since W6 superseded; does W13 survive?
- W6: is the morning DIGEST dead, or only the scoring half? Digest may need new home.

## Already-tracked open items (no new question)

- W15 drive-time matrix location → postgres-spec.md §7 item 8
- W15 SMART 23/25 unmet criteria → §7 item 9

## Cross-cluster refs (resolve when we audit the target clusters)

- W7 → CX-001..CX-007 (cx.md) — verify content covers output format
- W4 → SCREEN-10 port 3001 (screens.md) — verify surface defined
- W14 → command_registry.json (AI-008) — verify schema specified
- W15 → V2-FEAT-006 → PROD-16-V2 (already in dangling-ref list)
