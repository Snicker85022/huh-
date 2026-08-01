# Taza OS Backlog

## [2026-08-01 Nick] Reduce daily ntfy notification noise (many are noise)
- Context: ntfy.sh/taza-ops hit free-tier daily quota today (429 on ALL topics from the
  LAN). Cutting message volume reduces quota pressure and phone fatigue.
- Likely noise sources:
  * cc-watcher.sh on n100 pushes RUNNING + COMPLETE on EVERY dispatch -> consider
    COMPLETE-only, failure-only, or a digest.
  * gflip-relay relay.env has NTFY_TOPIC slot (empty at deploy) -> if enabled later,
    same per-dispatch pattern; decide the policy first.
  * llama-failover (gflip) pushes ONLY on mode changes (GPU<->CPU<->DOWN) -> not
    noise, keep as-is.
- Open decision (2026-08-01, from GPU failover work): ntfy.sh paid plan vs promote
  self-hosted n100:2586 to primary vs keep fallback chain. See
  specs/llama-gflip-failover.md "Notifications".

## [2026-08-01 logged] Spec gaps found on word-for-word review (risk_engine build)
- GAP a: specs/03 capability_matrix schema table is missing a `status` column
  (probation/graduated) that specs/07 references directly. Needs a one-line
  schema addition to 03 at some point.
- GAP b: specs/07 self-correction protocol has 4 triggers; the 5th
  (self-diagnostic on suspected impairment) discussed earlier was never drafted
  into 07 - spec 11's session-start ritual may already cover this. Decision
  needed: add a 5th trigger to 07, or treat spec 11 as sufficient coverage.
