# NPU DOE Phase 3 + 4 — middleware candidates & concurrency (reframed per Phase 2 findings)

Date: 2026-08-25. Machine: gflip (Ryzen 9 PRO 8945HS, XDNA1 NPU on MAINLINE amdxdna 0.7.0, no
staging/DKMS; Radeon 780M; 64 GB). Small model for CPU/iGPU rows: Qwen2.5-0.5B-Instruct Q4_K_M.
Production Ornith: live service :8082, production config (verified), ~23.2 t/s, GTT 50 GiB.

## Phase 2 finding carried forward (kept explicit, not flattened)

**There is NO LLM runtime for XDNA1 on Linux at all** (no ggml/llama.cpp NPU backend;
FastFlowLM/Lemonade are XDNA2-only). That is a *capability gap*, not "NPU is slower". The 69 t/s
figure earlier was a theoretical matmul-throughput ceiling, never something that ran. This is why
the NPU column in Phases 3-4 is "infeasible / not applicable" rather than a slower number.

## Phase 3 — candidate middleware jobs (reframed: CPU + iGPU only)

The original "run tool-call validation and error-log distillation ON the NPU" is not executable:
no runtime exists to run them. Instead both jobs were run on CPU and iGPU for real baseline costs
(useful on their own, and the comparison point if a working XDNA1 LLM path ever appears).

### 3a. Tool-call / JSON validation — 40-item set (17 valid / 23 malformed), Qwen2.5-0.5B, temp 0

| Device | accuracy | lat_avg | lat_p50 |
|--------|---------|---------|---------|
| CPU | 19/40 = **0.475** | 55.8 ms | 40.0 ms |
| iGPU 780M | 20/40 = **0.500** | 38.0 ms | 29.0 ms |

At chance. The 0.5B class model cannot do this job (it rubber-stamps "YES"). Finding: the task is
cheap (30-56 ms/check) but needs a model ≥ 1.5B or a deterministic grammar validator (the harness
already uses llama.cpp's tool-grammar for real calls — this is the better tool for the job).

### 3b. Error-log distillation — 8 real traces from this session's logs, Qwen2.5-0.5B, graded by Ornith (1-5)

| Device | dist_wall_avg | quality (Ornith grade, 1-5) |
|--------|--------------|-----------------------------|
| CPU | 0.44 s/trace | (same model as iGPU) |
| iGPU 780M | 0.28 s/trace | mean **2.1** (7/8 graded) |

Grades: 1, 5, 1, 2, 4, 1, 1. The 5 was the self-explanatory cmake-version error (regurgitation
scored as fine). Observed quality: the 0.5B mostly regurgitates the error verbatim; it
hallucinated fixes on two (a Python code block for the TaskGroup error; "include <iostream>" for a
missing header). Grading note: Ornith-1.5 is a reasoning model — "reply with ONLY an integer"
repeatedly consumed the token budget in reasoning and never emitted the answer (1/8 ungradable
even at max_tokens=1024; 2/8 at 128). The harness MUST budget for reasoning tokens when asking
Ornith for short structured output.

### NPU column (both 3a and 3b)

**Infeasible — no XDNA1 LLM runtime exists.** Evidence from Phase 2: no ggml/llama.cpp NPU
backend; the only NPU primitives (512³ matmul 87 GFLOPS, passthrough dispatch ~270 µs end-to-end)
do not map to token-in/token-out middleware. Not a blank — a measured capability gap.

## Phase 4 — concurrency (reframed: does a RAW NPU compute loop degrade Ornith?)

10 identical 200-token generation tasks, production Ornith :8082, back-to-back. Stall timeout
120 s/task (Piece-2 lesson). GTT monitored (no GTT allocations by these loads → no thrash mode).

| condition | ok | gen_tps avg (min/max) | wall_total | stalls | Δ vs baseline |
|-----------|----|----------------------|-----------|--------|---------------|
| baseline (Ornith alone) | 10/10 | 23.17 (23.12-23.19) | 88.5 s | 0 | — |
| Ornith + **NPU** 512³ matmul loop | 10/10 | 22.87 (22.77-23.13) | 89.3 s | 0 | **-0.30 t/s (-1.3%)** |
| Ornith + **CPU** llama-bench loop (8 thr) | 10/10 | 17.97 (16.93-19.57) | 115.0 s | 0 | **-5.20 t/s (-22.4%)** |

GTT stable 26.87 GiB in all three; no stalls; production healthy after.

**Reading (the claim actually tested):** a RAW NPU compute loop running continuously degrades
Ornith only ~1.3% — the DRAM/fabric-contention hypothesis from Phase 2's power data is NOT
confirmed at this load intensity. A CPU background load degrades Ornith ~22%, far worse. So the
degradation is not NPU-specific; it is driven by whatever competes for CPU/DRAM, and the NPU loop
(off-core: core power +0.07 W during it) is a comparatively isolated background worker from
Ornith's perspective.

**Caveats (do not over-read):** the two background loads are NOT intensity-matched (CPU loop
drew ~41 W package vs NPU loop ~21 W). This is "NPU loop vs a heavier CPU loop", a strong but
not matched-intensity control. It answers "does a raw NPU loop hurt Ornith?" (barely) and "is it
NPU-specific or any load?" (any heavy load; CPU-type hurts much more). It does NOT claim anything
about "an NPU-hosted task" (none exists) nor about matched-power comparison.

## Operational notes

- Ornith-1.5 emits reasoning_content; short-answer prompts need a large max_tokens budget.
- Process hygiene: pkill/pgrep -f patterns that appear in your own command line match your own
  shell (hit twice this session, killed my shell). Use explicit PIDs or exclude $$.
- Driver state after all phases: still mainline (srcversion E4FC5AFFF53D21BC6AFDAE3), no DKMS.
