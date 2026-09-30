# Pass 0.5 — Ground-Truth Register

**Source:** Nick's operational narration + Q&A, 2026-09-25. These are authoritative decisions;
they override the frozen Notion export where they disagree.

## DB architecture (RESOLVED — see docs/database-architecture-2026-09-25.md)

- Single store of record = `tazaos` PostgreSQL on n100 (D4/D5 LOCKED 2026-09-20).
- NocoDB = UI skin over tazaos. "NocoDB table" in specs = Postgres table. (Live env confirms.)
- `taza_os` = LangGraph checkpointer (agent state, not business data).
- `taza_memory` = shared_memory log (brain memory, not business data).
- Mom's Table task core NOT wired: task_cards=0 rows, events=0 rows. Schema exists; wiring is the work.

## Nick's decisions (2026-09-25)

1. **RAM:** gflip = 64 GB dual-channel DDR5-5600. n100 = 32 GB single-channel DDR4.
2. **Deposit:** FIXED DOLLAR (PROD-08 correct). `deposit_basis_cents` frozen at first publish.
   Mechanism: Sandra picks a % (default 50%) in the form; dollar amount computed from the
   current subtotal; the DOLLAR figure is what locks. Later invoice changes do not move the deposit.
3. **W7 trigger:** manual "Create AI Draft" click (V1 primary) + auto status path documented.
   Task chains are PROD-06's job (deposit-triggered), NOT W7's.
4. **W15:** NOT deployed. Prototype only; needs wiring + automation.
5. **Square attributes:** 11 for now (6 visible + 5 hidden). "12/7-visible" is wrong.
6. **Cloudflare tunnels:** KEEP. Harden near shipping. Cloudflare edge AI planned for planner app.
7. **WireGuard:** RETIRE all references.
8. **Mom's Table:** the task core to wire — cooks interact via MicroTouch MT1/MT2 + z33.

## Registry corrections queued (for Pass 1)

- W15 status: `Deployed` → `Prototype` (or `In Development`).
- CAT-001: "12 attributes (7 visible + 5 hidden)" → "11 attributes (6 visible + 5 hidden)".
- W7 trigger text: add manual-click primary path; reconcile export's "Lead status → Ready to Invoice".
- security.md / health.md: remove WireGuard references (Tailscale-only).
- prod.md PROD-08 deposit: keep fixed-dollar; add the 50%-default computation mechanism from decision 2.
- master_urs duplicate: `public` (278) vs NocoDB base schema `pckp5o6vpkbml4e` (278) — pick canonical.

## Pass 0.5 — spec-discovery artifacts (added 2026-09-29)

Nick: `tcl1-east.html`, `tcl2-west.html`, `taza-card-table.html`, `gamemaster.html`,
`van-loadout.html` are **static prototypes that never worked** — theme/brand/human-
readability mockups. Good enough for v1.0, to be improved later. Therefore they are
**design references, NOT operational reality**. The true operational ground truth is
Nick's narration (above), not these files.

## Pass 0.5 — alias-family finding (added 2026-09-29, per Claude review)

The legacy reference families — `CLOSE N`, `SHOP N`, `INVOICE N`, `CATALOG N`,
`PACK N` (e.g. CLOSE 1 = PROD-38 TaskCloseEvent, SHOP 1 = PROD-05-V2, PACK 2 =
PROD-16-V2) — appear **in FRS prose only**, never in Inputs/Outputs. The Pass 0
edge graph therefore **misses this entire reference class**. These are not in the
identity matrix as edges; they are prose-level cross-references requiring semantic
mapping. **Flag as a Pass 1 per-cluster audit target**: each cluster audit must
extract every `CLOSE/SHOP/INVOICE/CATALOG/PACK N` mention and propose its canonical
spec ID.

## D20 — Canonical naming scheme (design LOCKED 2026-09-29; execute after Pass 1)

Four mechanical rules, applied to 287 specs → 113 renamed, 174 unchanged, 0 collisions:

| Rule | Before → After | Count |
|---|---|---|
| Drop `URS-` prefix | URS-KIT-101 → KIT-101, URS-CRM-007 → CRM-007 | 83 |
| Drop `REQ-` prefix | REQ-CI-001 → CI-001, REQ-TELE-001 → TELE-001 | 5 |
| Legacy kit family | KIT-001…KIT-023 → KITL-001…KITL-023 (bin master, kit-legacy) | 13 |
| SCREEN zero-pad | SCREEN-01 → SCREEN-001 (3-digit, matches CAT-001 style) | 12 |

**Rationale:** prose already uses short forms (Pass 0 found 19 short-form tokens resolving to URS- prefixed IDs). `URS-` carries no information the cluster code lacks. KITL eliminates the KIT-001-vs-KIT-101 semantic collision.

**Timing: design now, execute after Pass 1 as mechanical Pass 1.5.** Pass 1's job is producing the *semantic* alias map (CLOSE N, SHOP N, INVOICE N, CATALOG N, PACK N → canonical). Renaming before that would destroy the drift evidence and leave prose aliases broken. Execute = one mechanical script (headers + CSV + prose aliases) in one commit; corpus untouched until then.

**Deferred to Pass 1 (semantic, NOT mechanical):**
- `V1.0-IG` (Input Grammar) — needs a real cluster home; do NOT guess AI-009
- entire `uncategorized` cluster (CRM-*, CALL-*, SYS-INTENT-001) — needs homes
- CLOSE/SHOP/INVOICE/CATALOG/PACK N → canonical mapping (Pass 1 discovery)

**Numbering gaps are Pass 1 findings, not rename targets:** INT-002, LABEL-002, TV-008/009/010, PROD-30/31/32/33/35 missing. Do not renumber; flag.

Map artifact: `urs/canonical-id-map.tsv` (287 rows, source_id → final_id).

## D21 — Changelog vs audit_log (Nick 2026-09-30, Pass 1)

W11's raw before/after capture duplicated PROD-22's `audit_log`. Resolution (option B):
- `audit_log` (PROD-22, trigger-fired, append-only) = sole history-of-record.
- `changelog` = alert queue only (W12 writes alerts, W13 reads).
- W11 = read-only changelog view over `audit_log` for Leads/Customers/Invoices/Tasks.

## D22 — AC/VM drafting standard (Nick 2026-09-30)

Cortex drafts AC/VM for all specs. Mandatory: normal + edge + negative +
silent-failure + challenge-test classes. VM must name the evidence artifact
(query/screenshot/photo/observation log/code-search/hands-on). Nick is reviewer.
Standard in `urs/acvm-standard.md`.
