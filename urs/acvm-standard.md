# D22 — Acceptance Criteria & Verification Method standard (Nick, 2026-09-30)

Every spec must carry AC + VM. No fluff. Nick is the reviewer.

## Acceptance Criteria — five mandatory classes

1. NORMAL — the happy path, stated as a binary, testable condition.
2. EDGE — boundary cases specific to this spec (empty input, boundary values,
   first/last item, network blip, reactivation, cap limits).
3. NEGATIVE — the spec must fail correctly: wrong endpoint, missing dependency,
   overshoot, invalid input → blocked or rejected, never silent.
4. SILENT-FAILURE — the failure mode that would otherwise go unnoticed:
   one item silently missing data, a field quietly dropped, a write that half-succeeds.
5. CHALLENGE — at least one real stress/real-world test: kill a dependency mid-run,
   feed adversarial input, a deliberately empty record, an unusual real case.

## Verification Method — evidence required, not assertions

Every VM line must name the evidence artifact that will be captured:

- live query (psql/SQL + result screenshot)
- code-search (command + output, e.g. grep SearchCatalogObjects → zero hits)
- screenshot (UI state, dashboard, phone SMS)
- photo (physical: labels, van load, kitchen screen)
- observation log (timestamped note of a hands-on run)
- hands-on test (Nick or Sandra performs the action; result documented)

Standing rule (from CAT-001, now universal): "Nick will test manually. Verification
is by 100% inspection and hands-on interaction where user intent must be verified.
Proof (screenshots, reports, photos) is captured and documented."

## Style by determinism class

- D (deterministic): AC asserts exact outputs for given inputs; VM = query + code-search.
- KG (knowledge-graph): AC asserts the graph resolves correctly; VM = fixture data + query.
- EXT / EXT-EMAIL: AC asserts the external failure mode + fallback; VM = kill the
  dependency and observe; for email, assert delay + parse-failure behavior.
- HUM: AC asserts the human decision gate; VM = observation log of the review.
- INF (AI inference): AC asserts no fabrication (confidence labels honest, missing →
  blank not guessed); VM = adversarial-input battery + delta review + code-search
  proving the LLM never does arithmetic/geometry.
