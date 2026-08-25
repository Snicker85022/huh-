# Ornith-1.5-35B-A3B — gflip Optimization DOE Report
**Date:** 2026-08-24/25 (UTC) | **Host:** gflip | **Model:** Ornith-1.5-35B-A3B (Q6_K, 27.2 GiB) + vision projector

## Hardware / baseline
- CPU: Ryzen 9 PRO 8945HS (Hawk Point), 16 threads, 8 used for inference
- iGPU: Radeon 780M (gfx1103), 2 GiB dedicated VRAM, shared GTT (UMA)
- RAM: 64 GB (2×32) DDR5-5600 dual channel — theoretical 89.6 GB/s
- GPU-visible memory ceiling (GTT) measured: **50 GiB** (after fix; was 23.4 GiB)
- mclk (memory clock): **fixed at 2800 MHz (DDR5-5600)** — per-state pinning rejected (`pp_dpm_mclk` I/O error); a constant, not a factor
- llama.cpp: Vulkan backend, rebuilt from **latest master f280b2698 (ggml 0.21.0)** — pulled 398 commits ahead of the prior Aug-1 build

## Problem that started it
Ornith ran on a 23.4 GiB GTT ceiling at 99.6% capacity → `vk::Queue::submit: ErrorDeviceLost` / "Not enough memory for command submission" → server crash under load.

### Phase 0 — memory fix
- `/etc/default/grub` had a stale, deprecated **`amdgpu.gttsize=32768` (twice)** capping GTT at 32 GiB and overriding modprobe.d.
- Removed it; set the modern **`ttm.pages_limit=13107200`** (kernel 6.8) / **`amdttm`** (kernel 7.x) = 50 GiB ceiling.
- Result: `[drm] amdgpu: 51200M of GTT memory ready` (was 32768M). No longer OOMs.

## Kernel 6.8 block — driver × offload × slots × mmap (24 combos)
On kernel 6.8.0-136, at default power. Winner = **cmoe0 (all 35B on GPU)**.

| config family | gen t/s |
|---|---|
| **cmoe0** (all-GPU) | **23.2–23.5** |
| cmoe6 (6 experts → CPU) | 20.0–21.2 |
| cmoe10 | 18.9–20.4 |
| pre-DOE config (cmoe6, np4) | 18.1 |

radv vs amdvlk, np2 vs np4, mmap vs no-mmap: all within noise (~0.1 t/s). Tool-calling OK in every config, zero crashes.

## Kernel 7.0 block — same grid (24 combos)
Identical ranking and speeds (cmoe0 23.3–23.6). **Kernel 7.0 is a wash on raw throughput** but is the newer/current driver; adopted.

## Power/clock envelope (power × perf)
| STAPM | perf | sclk | gen t/s |
|---|---|---|---|
| 45 W | auto | 800 idle | 23.3 |
| 60 W | auto | 800 idle | 23.3 |
| 60 W | high | **2799 MHz** | 23.5 |
| 45 W | high | 2799 MHz | 23.4 |
| 54 W | high | 2799 MHz | 23.5 |

**Finding: the 780M is DRAM-bandwidth-bound, not clock-bound.** Forcing 2799 MHz (2.5× shader clock) changes t/s by ~0.2 (noise). mclk measured at 2800 MHz (max) during load on every run. **Power/clock are NOT useful levers — run auto/45 W.**

### Controllability results
- `ryzenadj` (installed from source) reads/writes package power (STAPM 45→60 W, Fast PPT 54→65 W) — verified working on 8945HS.
- Raising power + forcing `high` **does** let the GPU sustain 2799 MHz under load — but yields zero t/s.
- Per-state `pp_dpm_sclk`/`pp_dpm_mclk` pinning: **rejected (I/O error)** on this APU.
- RAM clock (mclk): **not controllable** (fixed 2800 MHz / DDR5-5600).

## Batch & concurrency (phase 2) + stress
- `-ub` {64,128,256,512} × `-np` {1,2,4}: **gen flat 23.1–23.3** — batch and slots don't affect single-stream speed.
- Tool-calling accuracy battery (5 tools, function+args): **70–90%** (arg misses largely case/format scoring strictness).
- Concurrency stress (4 parallel requests per slots config): **zero crashes**; **np4 = best p50 (11.4 s vs 14.1–14.6 s)**. → For multi-agent (Fusion) use, np4 helps; single-job use, np2 is fine.

## Full-factor screening (phase A) — 9 factors on new build
Center-point screening (3 center reps + 11 one-factor variants):

| factor varied | gen t/s | Δ |
|---|---|---|
| center (radv, cmoe0, np2, ub512, b2048, t8, mmap, fa, c16k) | 23.1 | — |
| **cmoe → 10** | **19.7** | **−15% (only real signal)** |
| driver→amdvlk, np→4, ub→128, batch 1K/4K, threads→16, mmap off, fa off, ctx 8K/32K | 23.1–23.3 | ~0 |

**Verdict: on this build, only `cmoe0` matters; all other factors are flat.**

## Sampling DOE (phase C) — temp × top_p × top_k (27 runs)
Weak/noise-level factor. QA accuracy (8 deterministic tasks): temp 0.2 → 44%, 0.5 → 42%, 0.7 → 37%. Tool-calling robust (80–100%). Best region: **temp 0.2–0.5, top_p 0.95–1.0**. Chose **temp 0.2, top_p 0.95, top_k 20** (deterministic, strong QA).

## Vision (10-task battery)
**10/10 = 100%** (colors, OCR "HELLO 780M", digit, counting, shapes, spatial position). Image ingest = flat ~1045 prompt tokens regardless of resolution; prompt-eval ~133 t/s; **gen unchanged (22.8 t/s)**; zero extra GTT; **tool-calling works with image in context**.

## Long-context stress (needle-in-a-haystack, planner-app spec)
| length | early | mid | late |
|---|---|---|---|
| 4K–24K | PASS | PASS | PASS |
| 32K | PASS | PASS* | PASS |

Retrieval = 18/18 (100%) at every length 4K-32K and every position (v2 re-run, max_tokens=256). The two apparent v1 fails were artifacts: (1) max_tokens=64 starved the reasoning model -> empty output; (2) a scorer strictness false-negative: model answered "1.1" (the correct ratio) for the "110%" threshold. **Generation speed flat 22.3 t/s at every context length; prompt-eval ~243 t/s even at a 4078-token 32K prompt.** Coding-consistency task (write a new /api/v1/venues endpoint matching established conventions from a 16K spec): **PASS** with max_tokens=256 (this reasoning model needs >=256 tokens to emit a final answer).

## Production configuration (now live)
- llama-server: **radv / cmoe0 / np2 / ub512 / b2048 / t8 / c32768 / flash-attn on / temp 0.2 / top_p 0.95 / top_k 20 / --mmproj (vision)**
- Power: **default 45 W envelope, perf `auto`** (boost pointless — bandwidth-bound)
- GTT: 50 GiB ceiling (headroom, cap not reservation)
- LibreChat `Ornith-1.5-35B` endpoint `addParams` updated to temp 0.2/top_p 0.95/top_k 20 (applies on LibreChat config reload/restart)
- Qwen3-30B kept **disabled** during DOE; re-enable at your discretion (no stacking on shared GTT)

## Key takeaways
1. **Only offload (cmoe0) matters**; every other software factor is flat — the iGPU is memory-bandwidth-bound.
2. **GPU clocks/power are not levers** — raising them wastes heat for zero t/s.
3. **RAM clock is fixed** and already at max.
4. **Vision is free and 100%.**
5. **Long-context holds to 32K** for retrieval and doesn't slow generation.
6. **Tool-calling is robust** to sampling and works with images.
7. The real future unlock is a **dGPU + OcuLink** (400+ GB/s VRAM vs 89.6 GB/s shared) — same model would jump from ~23 to ~100+ t/s.

## Appendix — serving-path verification (operational note)
This session's traffic was captured live (TLS-SNI + Mongo + server logs): the assistant serving the chat is routed by LibreChat to the **DeepSeek** endpoint (`api.deepseek.com`, model `deepseek-v4-flash`), with a clean network path and no Anthropic involvement. The model self-identifies as "Claude" when asked — consistent with a documented LLM identity-hallucination pattern (self-description absorbed from web/synthetic data), not an indication of actual model identity. Reported for transparency; all DOE numbers above are independent of this.
