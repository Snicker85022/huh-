# Ornith-1.5-35B-A3B — Complete gflip DOE Report
- Host: gflip | Model: Ornith-1.5-35B-A3B Q6_K (27.2 GiB) + vision projector (mmproj)
- CPU: Ryzen 9 PRO 8945HS (Hawk Point) | iGPU: Radeon 780M (gfx1103) | RAM: 64 GB (2x32) DDR5-5600 dual channel (89.6 GB/s)
- llama.cpp Vulkan. Builds: prior Aug-1 (786148e9d), final master f280b2698 (ggml 0.21.0, +398 commits)
- Kernels tested: 6.8.0-136 GA, 7.0.0-30 HWE
- GTT ceiling: 23.4 GiB (pre-fix) -> 50 GiB (post-fix)
- All speeds in tokens/sec. Default sampling unless noted.

## A. Pre-session DOE (kernel 6.8, 24 GiB GTT cap) — 2026-08-23
### A1. Driver / flash-attn / threads (results-final.csv)
| run | driver | cmoe | flash | threads | pp t/s | gen t/s | status |
|---|---|---|---|---|---|---|---|
| control x3 | radv | on | auto | 0 | 28.8/33.9/33.9 | 13.24/13.22/13.23 | ok |
| driver-radv | radv | on | auto | 0 | 33.47 | 13.22 | ok |
| driver-amdvlk | amdvlk | on | auto | 0 | 34.14 | 12.20 | ok |
| fa off, t8 | radv | on | off | 8 | 33.36 | 13.18 | ok |
| fa on, t8 | radv | on | on | 8 | 33.50 | 13.25 | ok |
| fa on, t16 | radv | on | on | 16 | 33.72 | 11.21 | ok |
| cpu-only (ngl=0) | radv | off | off | 16 | 21.99 | 12.21 | ok |
| cmoe off (all-GPU) | radv | off | on | 8 | - | - | **FAIL rc=-6 (OOM, 24GiB cap)** |

### A2. Context / batch / ncmoe / burst (results-v2.csv)
| run | type | pp t/s | gen t/s | agg t/s | ttft p50 | ttft p95 | status |
|---|---|---|---|---|---|---|---|
| control | single | 25.55 | 13.24 | | | | ok |
| ctx32k | single | 24.82 | 13.25 | | | | ok |
| batch4k | single | 26.22 | 13.26 | | | | ok |
| tb8 | single | 26.30 | 13.24 | | | | ok |
| ncmoe10 | single | 47.85 | 20.03 | | | | ok |
| np1-burst | burst | | | 10.14 | 21968 | 40896 | ok |
| np4-burst | burst | | | 21.08 | 6127 | 6321 | ok |
| np8-burst | burst | | | 21.06 | 6093 | 6286 | ok |

### A3. n_cpu_moe sweep (ncmoe_sweep.csv)
| N (experts to CPU) | pp t/s | gen t/s | status |
|---|---|---|---|
| (none) | 23.30 | 13.26 | ok |
| 5 | - | - | FAIL (OOM under 24GiB cap) |
| 10 | 49.65 / 41.38 | 20.23 / 20.27 | ok |
| 15 | 35.54 | 19.07 | ok |
| 20 | 36.92 | 18.12 | ok |
| 25 | 32.70 | 16.21 | ok |

### A4. n_cpu_moe fine (ncmoe_fine.csv)
| N | pp t/s | gen t/s |
|---|---|---|
| 8 | 48.72 | 20.75 |
| 9 | 46.26 | 20.46 |
| 10 | 50.49 | 20.22 |
| 11 | 49.53 | 20.00 |
| 12 | 37.86 | 19.82 |
### A5. n_cpu_moe edge (ncmoe_edge.csv): N=6 -> 50.1 pp / 21.11 gen; N=7 -> 49.86 / 20.89
### A6. n_cpu_moe 6 x3 replicates (ncmoe_rep6.csv): gen 21.17 / 21.13 / 21.11

## B. Phase 0 — memory ceiling fix
- Root cause of crashes: 35B model at 99.6% of 23.4 GiB GTT; `vk::Queue::submit: ErrorDeviceLost` / "Not enough memory for command submission".
- `/etc/default/grub` contained deprecated `amdgpu.gttsize=32768` twice (cmdline overrides modprobe.d; caps GTT at 32 GiB).
- Fix: removed gttsize; set `ttm.pages_limit=13107200` (kernel 6.8) / `amdttm` (7.x) = 50 GiB.
- Result: `[drm] amdgpu: 51200M of GTT memory ready`. mclk constant at 2800 MHz (DDR5-5600); per-state `pp_dpm_mclk` pinning rejected (I/O error) -> memory clock is fixed, not a factor.

## C. Kernel 6.8 block — driver x offload x slots x mmap (24 combos + baseline)
Columns: combo | pp1 | gen1(short) | gen2(tool) | pp3 | gen3(long) | GTT used/hd (GiB)
| combo | pp1 | gen1 | gen2 | pp3 | gen3 | GTT used/hd |
|---|---|---|---|---|---|---|
| BASELINE (pre-DOE: cmoe6 np4) | 64.4 | 18.1 | 12.3 | 86.0 | 12.4 | 0.0/50.0 |
| amdvlk/cmoe0/np4/mmap1 | 43.0 | 23.5 | 23.7 | 176.1 | 23.3 | 27.2/22.8 |
| amdvlk/cmoe0/np2/mmap1 | 43.0 | 23.5 | 23.6 | 174.9 | 23.1 | 27.0/23.0 |
| amdvlk/cmoe0/np4/mmap0 | 43.0 | 23.5 | 23.7 | 175.1 | 23.2 | 26.8/23.2 |
| amdvlk/cmoe0/np2/mmap0 | 43.1 | 23.4 | 23.7 | 174.6 | 23.2 | 26.6/23.4 |
| radv/cmoe0/np4/mmap1 | 63.1 | 23.5 | 23.8 | 235.7 | 23.2 | 27.2/22.8 |
| radv/cmoe0/np2/mmap1 | 42.6 | 23.4 | 23.6 | 210.7 | 23.2 | 27.0/23.0 |
| radv/cmoe0/np4/mmap0 | 63.4 | 23.4 | 23.8 | 235.4 | 23.2 | 26.8/23.2 |
| radv/cmoe0/np2/mmap0 | 42.3 | 23.2 | 23.7 | 210.1 | 23.2 | 26.6/23.4 |
| amdvlk/cmoe6/np4/mmap1 | 40.6 | 20.3 | 20.4 | 164.2 | 19.9 | 27.4/22.6 |
| amdvlk/cmoe6/np2/mmap1 | 40.6 | 20.3 | 20.5 | 165.6 | 20.0 | 27.5/22.5 |
| amdvlk/cmoe6/np4/mmap0 | 40.6 | 20.3 | 20.6 | 151.2 | 20.0 | 23.5/26.5 |
| amdvlk/cmoe6/np2/mmap0 | 40.8 | 20.3 | 20.5 | 150.2 | 20.0 | 23.5/26.5 |
| radv/cmoe6/np4/mmap1 | 60.7 | 21.1 | 21.2 | 219.3 | 20.7 | 27.4/22.6 |
| radv/cmoe6/np2/mmap1 | 42.5 | 21.2 | 21.4 | 203.6 | 21.0 | 27.4/22.6 |
| radv/cmoe6/np4/mmap0 | 29.3 | 20.0 | 21.1 | 173.8 | 20.7 | 23.4/26.6 |
| radv/cmoe6/np2/mmap0 | 29.9 | 20.2 | 21.1 | 170.3 | 20.8 | 23.5/26.5 |
| amdvlk/cmoe10/np4/mmap1 | 39.1 | 19.4 | 19.6 | 163.0 | 19.1 | 27.6/22.4 |
| amdvlk/cmoe10/np2/mmap1 | 39.2 | 19.4 | 19.5 | 162.6 | 19.1 | 27.3/22.7 |
| amdvlk/cmoe10/np4/mmap0 | 39.2 | 19.4 | 19.6 | 141.7 | 19.2 | 21.1/28.9 |
| amdvlk/cmoe10/np2/mmap0 | 39.4 | 19.4 | 19.6 | 140.4 | 19.2 | 20.9/29.1 |
| radv/cmoe10/np4/mmap1 | 59.6 | 20.3 | 20.5 | 214.9 | 20.1 | 27.6/22.4 |
| radv/cmoe10/np2/mmap1 | 41.7 | 20.4 | 20.6 | 198.0 | 20.2 | 27.3/22.7 |
| radv/cmoe10/np4/mmap0 | 31.8 | 18.9 | 20.2 | 169.6 | 19.8 | 21.1/28.9 |
| radv/cmoe10/np2/mmap0 | 25.9 | 19.0 | 20.2 | 152.8 | 19.9 | 20.9/29.1 |
All 24 combos: tool_ok=1, crashed=0.

### 6.8 summary (mean short-gen t/s)
| family | mean gen1 | range |
|---|---|---|
| cmoe0 (all-GPU) | 23.4 | 23.2-23.5 |
| cmoe6 | 20.5 | 20.0-21.2 |
| cmoe10 | 19.5 | 18.9-20.4 |
| baseline (old) | 18.1 | - |

## D. Kernel 7.0 block — same 24-combo grid
Columns: combo | pp1 | gen1 | gen2 | pp3 | gen3 | GTT used/hd | busy% | sclk | mclk
| combo | gen1 | gen2 | gen3 | GTT used/hd | busy% |
|---|---|---|---|---|---|
| amdvlk/cmoe0/np4/mmap1 | 23.4 | 23.6 | 23.1 | 27.2/22.8 | 98 |
| amdvlk/cmoe0/np2/mmap1 | 23.3 | 23.5 | 23.0 | 27.0/23.0 | 98 |
| amdvlk/cmoe0/np4/mmap0 | 23.4 | 23.6 | 23.1 | 26.8/23.2 | 98 |
| amdvlk/cmoe0/np2/mmap0 | 23.3 | 23.5 | 23.0 | 26.6/23.4 | 97 |
| radv/cmoe0/np4/mmap1 | 23.6 | 23.8 | 23.3 | 27.2/22.8 | 98 |
| radv/cmoe0/np2/mmap1 | 23.4 | 23.6 | 23.2 | 27.0/23.0 | 97 |
| radv/cmoe0/np4/mmap0 | 23.5 | 23.8 | 23.2 | 26.8/23.2 | 98 |
| radv/cmoe0/np2/mmap0 | 23.4 | 23.7 | 23.2 | 26.6/23.4 | 98 |
| amdvlk/cmoe6/np4/mmap1 | 20.4 | 20.6 | 20.0 | 27.4/22.6 | 89 |
| amdvlk/cmoe6/np2/mmap1 | 20.3 | 20.5 | 20.0 | 27.5/22.5 | 89 |
| amdvlk/cmoe6/np4/mmap0 | 20.4 | 20.5 | 20.0 | 23.5/26.5 | 89 |
| amdvlk/cmoe6/np2/mmap0 | 20.3 | 20.6 | 20.1 | 23.5/26.5 | 89 |
| radv/cmoe6/np4/mmap1 | 21.3 | 21.5 | 21.0 | 27.4/22.6 | 88 |
| radv/cmoe6/np2/mmap1 | 21.2 | 21.2 | 20.9 | 27.4/22.6 | 88 |
| radv/cmoe6/np4/mmap0 | 21.1 | 21.5 | 21.1 | 23.4/26.6 | 88 |
| radv/cmoe6/np2/mmap0 | 20.3 | 21.2 | 20.9 | 23.5/26.5 | 88 |
| amdvlk/cmoe10/np4/mmap1 | 19.4 | 19.5 | 19.1 | 27.6/22.4 | 83 |
| amdvlk/cmoe10/np2/mmap1 | 19.4 | 19.6 | 19.1 | 27.3/22.7 | 83 |
| amdvlk/cmoe10/np4/mmap0 | 19.4 | 19.6 | 19.2 | 21.1/28.9 | 83 |
| amdvlk/cmoe10/np2/mmap0 | 19.4 | 19.6 | 19.2 | 20.9/29.1 | 83 |
| radv/cmoe10/np4/mmap1 | 20.3 | 20.5 | 20.1 | 27.6/22.4 | 84 |
| radv/cmoe10/np2/mmap1 | 20.4 | 20.6 | 20.2 | 27.3/22.7 | 83 |
| radv/cmoe10/np4/mmap0 | 18.9 | 20.1 | 19.8 | 21.1/28.9 | 83 |
| radv/cmoe10/np2/mmap0 | 20.5 | 20.6 | 20.3 | 20.9/29.1 | 83 |
All 24: tool_ok=1, crashed=0. mclk peak = 2800 MHz on every run.

### 7.0 summary (mean short-gen t/s): cmoe0 23.4 | cmoe6 20.7 | cmoe10 19.6
### Kernel comparison: cmoe0 23.4 vs 23.4; cmoe6 20.5 vs 20.7; cmoe10 19.5 vs 19.6. No material difference.

## E. Power/clock envelope (results_env_k7.csv) — base radv/cmoe0/np2/mmap0
| STAPM W | perf | measured sclk | gen1 t/s | gen3 t/s | gpu_busy% | gpu_pwr W |
|---|---|---|---|---|---|---|
| 45 | auto | state0 800MHz (idle) | 23.3 | 23.1 | 97 | 13.6 |
| 60 | auto | state0 | 23.3 | 23.1 | 98 | 15.3 |
| 60 | high | state2 2799MHz | 23.5 | 23.3 | 98 | 16.4 |
| 45 | high | state2 2799MHz | 23.4 | 21.5 | 91 | 14.0 |
| 54 | high | state2 2799MHz | 23.5 | 23.2 | 98 | 15.9 |
FINDING: sclk 2799 vs ~1100 under load changes gen t/s by <=0.2 (noise). mclk measured at 2800 MHz during load on all runs. Throughput is DRAM-bandwidth-bound.

## F. Power/clock controllability
- `ryzenadj` (built from source) reads/writes package power on 8945HS: STAPM 45->60W, Fast PPT 54->65W (verified readback).
- With raised power + perf=high, GPU sustains 2799 MHz at 96% busy under load (measured live). Zero t/s gain.
- `pp_dpm_sclk` / `pp_dpm_mclk` per-state pinning: rejected (I/O error) on this APU.
- mclk fixed at 2800 MHz (DDR5-5600); not controllable in software.
- `power_dpm_force_performance_level`: auto/high/low writable; high caps sclk at 2799 but SMU still manages under load at default power.

## G. Batch & concurrency grid (phase 2, 12 runs) + quality
| config | gen1 | tool fn/arg | tool acc% | excel score | excel /min | busy% | pwr W | mclk |
|---|---|---|---|---|---|---|---|---|
| np1/ub64 | 23.1 | 5/4 | 90 | 4 | 7.5 | 99 | 44.9 | 2800 |
| np1/ub128 | 23.1 | 5/3 | 80 | 1 | 1.9 | 99 | 44.3 | 2800 |
| np1/ub256 | 23.1 | 5/3 | 80 | 0 | 0.0 | 98 | 43.8 | 2800 |
| np1/ub512 | 23.1 | 4/3 | 70 | 3 | 5.6 | 97 | 44.0 | 2800 |
| np2/ub64 | 23.2 | 4/3 | 70 | 2 | 3.8 | 99 | 44.6 | 2800 |
| np2/ub128 | 23.1 | 5/4 | 90 | 0 | 0.0 | 99 | 44.3 | 2800 |
| np2/ub256 | 23.1 | 5/4 | 90 | 2 | 3.7 | 98 | 43.9 | 2800 |
| np2/ub512 | 23.1 | 5/4 | 90 | 4 | 7.5 | 97 | 44.0 | 2800 |
| np4/ub64 | 23.3 | 5/3 | 80 | 2 | 4.0 | 99 | 44.8 | 2800 |
| np4/ub128 | 23.2 | 5/4 | 90 | 2 | 4.0 | 99 | 44.7 | 2800 |
| np4/ub256 | 23.3 | 4/3 | 70 | 0 | 0.0 | 99 | 44.7 | 2800 |
| np4/ub512 | 23.3 | 4/3 | 70 | 2 | 4.0 | 99 | 44.7 | 2800 |
gen1 range 23.1-23.3 (no effect from -ub or -np). Tool acc 70-90% (arg misses = case/format strictness). All crashed=0.

## H. Concurrency stress (results_stress_k7_v2.csv) — 4 parallel requests
| slots | ok/4 | crashed | p50 ms | p95 ms | ms/token |
|---|---|---|---|---|---|
| 1 | 4/4 | 0 | 14142 | 18853 | 122.8 |
| 2 | 4/4 | 0 | 14628 | 14629 | 114.1 |
| 4 | 4/4 | 0 | 11407 | 11407 | 118.5 |
np4 lowest p50 (11407 ms). Latencies include fresh-model-load warmup; compare relatively. Zero crashes at all slot counts.

## I. Full-factor screening (phase A, 14 runs) — kernel 7, new build
Center = radv/cmoe0/np2/ub512/b2048/t8/mmap1/fa1/c16384. Each factor varied low/high around center.
| run | gen1 | gen2 | tool fn/arg | tool acc% | excel /min | busy% | sclk | mclk |
|---|---|---|---|---|---|---|---|---|
| center-1 | 23.1 | 23.0 | 4/4 | 80 | 3.8 | 97 | 2799 | 2800 |
| center-2 | 23.1 | 23.0 | 5/5 | 100 | 1.9 | 97 | 2799 | 2800 |
| center-3 | 23.1 | 23.0 | 4/4 | 80 | 1.9 | 97 | 2799 | 2800 |
| driver-amdvlk | 23.1 | 22.9 | 5/5 | 100 | 1.9 | 97 | 2799 | 2800 |
| moe10 | 19.7 | 19.6 | 5/5 | 100 | 1.6 | 95 | 2799 | 2800 |
| np4 | 23.2 | 23.0 | 5/4 | 90 | 2.0 | 99 | 2799 | 2800 |
| ub128 | 23.2 | 23.1 | 5/5 | 100 | 1.9 | 99 | 2798 | 2800 |
| batch1024 | 23.1 | 23.0 | 5/5 | 100 | 1.9 | 97 | 2799 | 2800 |
| batch4096 | 23.1 | 23.0 | 5/5 | 100 | 5.6 | 97 | 2799 | 2800 |
| threads16 | 23.1 | 23.0 | 5/5 | 100 | 5.6 | 97 | 2799 | 2800 |
| mmap0 | 23.1 | 23.0 | 4/4 | 80 | 5.7 | 97 | 2799 | 2800 |
| fa0 | 23.1 | 22.9 | 5/5 | 100 | 1.8 | 97 | 2799 | 2800 |
| ctx8k | 23.3 | 23.1 | 5/4 | 90 | 2.0 | 99 | 2799 | 2800 |
| ctx32k | 23.2 | 23.0 | 5/5 | 100 | 1.9 | 97 | 2799 | 2800 |
Screening result: only `moe` (offload) affects gen speed (cmoe10=19.7 vs cmoe0=23.1, -15%). All other factors within noise. sclk 2799 and mclk 2800 on every run at default power. All crashed=0.

## J. Sampling DOE (phase C, 27 runs) — temp x top_p x top_k
QA = 8 deterministic tasks. Tool = 5-tool battery.
| temp | top_p | top_k | QA% | tool% | excel/min |
|---|---|---|---|---|---|
| 0.2 | 0.9 | 10 | 25 | 90 | 1.9 |
| 0.2 | 0.9 | 20 | 50 | 100 | 1.9 |
| 0.2 | 0.9 | 40 | 50 | 90 | 2.6 |
| 0.2 | 0.95 | 10 | 62 | 90 | 1.9 |
| 0.2 | 0.95 | 20 | 62 | 90 | 5.6 |
| 0.2 | 0.95 | 40 | 25 | 90 | 5.6 |
| 0.2 | 1.0 | 10 | 25 | 90 | 3.7 |
| 0.2 | 1.0 | 20 | 38 | 90 | 1.9 |
| 0.2 | 1.0 | 40 | 62 | 100 | 1.9 |
| 0.5 | 0.9 | 10 | 38 | 100 | 1.9 |
| 0.5 | 0.9 | 20 | 25 | 100 | 3.7 |
| 0.5 | 0.9 | 40 | 12 | 100 | 5.6 |
| 0.5 | 0.95 | 10 | 38 | 100 | 1.9 |
| 0.5 | 0.95 | 20 | 38 | 100 | 5.6 |
| 0.5 | 0.95 | 40 | 62 | 100 | 5.6 |
| 0.5 | 1.0 | 10 | 62 | 90 | 0.0 |
| 0.5 | 1.0 | 20 | 62 | 80 | 1.9 |
| 0.5 | 1.0 | 40 | 38 | 90 | 1.9 |
| 0.7 | 0.9 | 10 | 50 | 100 | 3.7 |
| 0.7 | 0.9 | 20 | 25 | 90 | 5.6 |
| 0.7 | 0.9 | 40 | 50 | 80 | 1.9 |
| 0.7 | 0.95 | 10 | 25 | 80 | 7.5 |
| 0.7 | 0.95 | 20 | 50 | 90 | 3.7 |
| 0.7 | 0.95 | 40 | 38 | 80 | 1.9 |
| 0.7 | 1.0 | 10 | 50 | 90 | 1.9 |
| 0.7 | 1.0 | 20 | 38 | 80 | 1.9 |
| 0.7 | 1.0 | 40 | 12 | 90 | 1.9 |
QA mean by temp: 0.2 = 44%, 0.5 = 42%, 0.7 = 37%. Tool mean by temp: 0.2 = 95%, 0.5 = 94%, 0.7 = 87%.
Best QA combos (62%): (0.2,0.95,10), (0.2,0.95,20), (0.2,1.0,40), (0.5,0.95,40), (0.5,1.0,10), (0.5,1.0,20).

## K. Vision (results_vision_k7.csv) — 10-task battery, generated images
| task | result | pp t/s | gen t/s | prompt_tok |
|---|---|---|---|---|
| red / blue / green | PASS x3 | 131.8-133.2 | 22.7-22.8 | 1045 |
| OCR "HELLO 780M" | PASS | 120.9 | 22.8 | 1069 |
| digit 7 | PASS | 132.5 | 22.8 | 1046 |
| count 3 circles | PASS | 118.1 | 22.8 | 1079 |
| count 5 squares | PASS | 121.2 | 22.8 | 1055 |
| circle vs square | PASS x2 | 131.9/119.9 | 22.8 | 1044/1073 |
| left-position red | PASS | 118.2 | 22.8 | 1081 |
VISION ACCURACY: 10/10 = 100%.
Resolution sweep (blue): 128/512/1024 px all = 1045 prompt_tok, pp ~132.8, gen 22.8. Image tokenization is flat regardless of resolution.
Memory probe (512px): GTT 26.35 GiB before and after; gpu_pwr 44.4 W; busy 93.7%; pp 133.4; gen 22.9; prompt_tok 1047.
Tool-calling with image: OK (described image + get_weather(city=Tokyo)).

## L. Long-context needle-in-a-haystack (results_longctx_k7_v2.csv) — planner-app spec
18 runs: length {4K,8K,12K,16K,24K,32K} x pos {early,mid,late}. Scorer: exact substring.
| length | early | mid | late | gen t/s |
|---|---|---|---|---|
| 4096 | PASS | PASS | PASS | 22.4 |
| 8192 | PASS | PASS | PASS | 22.3 |
| 12288 | PASS | 110->1.1* | PASS | 22.3 |
| 16384 | PASS | PASS | PASS | 22.3 |
| 24576 | PASS | PASS | PASS | 22.3 |
| 32768 | PASS | 110->1.1* | PASS | 22.3 |
*The mid-position needle asked "over-budget threshold RATIO"; spec states 110% = 1.1x. Model answered "1.1" (correct); scorer expected "110". Both flagged FAIL are this scorer false-negative -> effective 18/18.
Generation speed flat 22.3-22.4 t/s at every context length. Prompt-eval (cold) up to ~243 t/s at 4078-token 32K prompt; many rows served from KV cache (prompt_n=4).
Coding-consistency task (16K spec, write new endpoint following /api/v1 conventions): PASS, got `/api/v1/venues`, all 18 rows.

## M. Production configuration (applied 2026-08-25)
- llama-server: radv / --n-cpu-moe 0 (all-GPU) / -np 2 / -ub 512 / -b 2048 / -t 8 / -c 32768 / --flash-attn on / --temp 0.2 / --top-p 0.95 / --top-k 20 / --mmproj (vision)
- Power: default envelope (STAPM 45W / Fast PPT 54W / Slow 45W), perf level auto (no boost)
- GTT ceiling: 50 GiB
- LibreChat Ornith-1.5-35B addParams: temperature 0.2, top_p 0.95, top_k 20
- Smoke after apply: content PROD-OK, gen 23.1 t/s, slots n_ctx 16384 x2

## N. Result files (all in /home/taza/doe/)
results_phase1_k68.csv, results_phase1_k7.csv, results_env_k7.csv, results_phase2_k7.csv,
results_stress_k7_v2.csv, results_phaseA_k7.csv, results_phaseC_k7.csv, results_vision_k7.csv,
results_longctx_k7.csv, results_longctx_k7_v2.csv, results-final.csv, results-v2.csv,
ncmoe_sweep.csv, ncmoe_fine.csv, ncmoe_edge.csv, ncmoe_rep6.csv
