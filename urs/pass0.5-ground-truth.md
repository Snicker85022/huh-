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
