# Pass 1 — Per-Cluster Audit Prompt Template

Read-only: read/grep/find only. Do NOT edit files.

Read: /home/taza/repo/notion-export/clusters/<CLUSTER>.md

Canonical ID convention (D20): cite specs by their final ID. Map for this cluster:
<ID MAP>

For EACH spec row, produce one line per finding in this fixed schema:

<ID> | <CLASS> | <FIELD> | <SEVERITY> | <finding> | <evidence-quote>

CLASS ∈ {GAP, AMBIGUITY, UNTESTABLE, UNDEFINED, CONTRADICTION, ALIAS, ENHANCEMENT}
SEVERITY ∈ {BLOCKER, MAJOR, MINOR}

- GAP: required field missing/empty (trigger, inputs, outputs, failure behavior, acceptance criteria, verification method)
- AMBIGUITY: a statement with two defensible readings
- UNTESTABLE: an acceptance criterion or verification method that cannot be verified as written
- UNDEFINED: a term used but never defined in this spec or the lexicon
- CONTRADICTION: conflicts with another spec (cite both IDs)
- ALIAS: a legacy reference (CLOSE N, SHOP N, INVOICE N, CATALOG N, PACK N) → propose its canonical ID
- ENHANCEMENT: optional improvement, clearly labeled as such

Per spec, also propose:
- determinism class: D / KG / EXT / EXT-EMAIL / HUM / INF (one-line justification if INF)
- runtime host: N100 / gflip / either

End with: the 3 most build-blocking findings in this cluster.
