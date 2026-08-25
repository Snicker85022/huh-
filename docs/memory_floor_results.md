# Ornith-1.5 Memory Floor (Piece 2) — Results & Safety Ceiling

Date: 2026-08-25. Method: runtime TTM pages_limit (/sys/module/ttm/parameters/pages_limit —
the same knob that sets the 50 GiB production GTT, writable at runtime with sudo). Per cap:
fresh service load + realistic mixed batch (8 text/coding/tool tasks + 4 vision tasks incl.
two real app screenshots), production sampling (temp 0.2 / top_p 0.95 / top_k 20).
Full per-task data: doe/results_memory_floor.csv. Runner: doe/memory_floor.py.

| GTT cap  | load time | gtt_used after load | batch | gen t/s |
|----------|-----------|---------------------|-------|---------|
| 50 GiB   | 0.0s*     | 26.87 GiB           | 12/12 | 23.1    |
| 47 GiB   | 6.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 44 GiB   | 5.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 40 GiB   | 5.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 36 GiB   | 5.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 30 GiB   | 5.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 28 GiB   | 5.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 27 GiB   | 5.0s      | 26.83 GiB           | 12/12 | 23.1    |
| 26 GiB   | 13.2s     | 26.82 GiB           | 0/12  | 0.1  <- FAILURE POINT |

*50 GiB row = server already loaded (no restart). All other rows = fresh load under the cap.

## Findings
- Ornith's real GTT footprint (production config, -np 4, 32768 ctx, vision): ~26.8 GiB.
- Any ceiling above the footprint behaves IDENTICALLY. Confirms the allocator is dynamic:
  unused ceiling is simply unused; lowering the cap costs nothing until it bites.
- 26 GiB (just under the footprint): the model still LOADS (part of gtt_used is reclaimable
  page-cache-backed weights, so TTM squeezes it in) but generation collapses to ~0.1 t/s
  thrash — one request took 190.3s vs the normal 1.2s. Degradation, not a clean error.
- Load time grows 5.0s -> 13.2s right at the edge.

## Safety ceiling (for the Fusion harness)
- Absolute edge: 27 GiB works, 26 GiB thrashes.
- Recommended minimum GTT ceiling: **36 GiB** (~1.34x the 26.83 GiB footprint) — headroom
  for KV growth, vision buffers, framebuffer/kernel GTT consumers, concurrency spikes.
- Conservative option: 39 GiB (~1.45x).
- Live production cap stays 50 GiB (untouched). 36/39 GiB is a SIZING FLOOR for the harness,
  not a reason to lower the live ceiling.

## Operational notes
- pages_limit is the enforced ceiling; amdgpu still reports mem_info_gtt_total = 50 GiB.
- The harness must ALWAYS restore pages_limit = 13107200 (50 GiB) after any capped run —
  use a finally-style restore (a stalled run left the cap at 26 GiB on the live server once).
- Memory exhaustion manifests as THRASH/hang (~0.1 t/s), not a clean allocation error —
  the scheduler's hard-stop must not assume a graceful failure from memory pressure.
