# NPU DOE Phase 2 — Primitive baselines: NPU vs CPU vs iGPU

Date: 2026-08-25. Machine: gflip (Ryzen 9 PRO 8945HS, XDNA1 NPU, Radeon 780M, 64GB DDR5).
Driver: MAINLINE amdxdna 0.7.0 (kernel 7.0.0-30) — no staging driver, no DKMS (revert doc: npu_driver_revert.md).
NPU stack: XRT 2.26.0 (built from amd/xdna-driver, base debs + built SHIM libs only), IRON/mlir-aie v1.3.4 wheel, llvm-aie 22, firmware 1.5.5.391.
Small model for CPU/iGPU: Qwen2.5-0.5B-Instruct Q4_K_M (630.17 M params, 462.96 MiB), llama-bench.

## 2.1 Small-model inference throughput (0.5B class) — t/s, latency

| Device | pp512 (t/s) | tg128 (t/s) | latency ms/tok (decode) |
|--------|------------|------------|------------------------|
| CPU (8 thr, CPU-only build) | 983.53 ± 1.72 | 129.67 ± 0.03 | 7.71 |
| iGPU 780M (Vulkan, -ngl 99) | 4504.75 ± 13.08 | 152.19 ± 0.28 | 6.57 |
| NPU (XDNA1) | — | — | — |

**NPU row is not measurable end-to-end: there is NO whole-model LLM runtime for XDNA1 on
Linux** (open-xdna FAQ: no ggml XDNA backend; FastFlowLM/Lemonade are XDNA2-only). The real
NPU datapoints instead (all measured this session, mainline driver):

- 512³ int16 matmul: **87.13 GFLOPS**, 3.08 ms/op (PASS, verified vs NumPy).
- 2-layer MLP forward (2 × 512³ matmuls): **PASS, bit-exact** (max abs diff 0) — "a model
  forward pass on the NPU" at kernel level.
- Projected best-case decode (CLEARLY LABELED, not measured): 630M params ≈ 1.26 GFLOP/tok at
  87 GFLOPS → ~14.5 ms/tok ≈ **69 t/s IF purely matmul-bound with zero dispatch overhead and a
  runtime existed**. The 270 µs/kernel dispatch overhead (2.2) and int16-vs-Q4 efficiency make
  the real ceiling far lower. Even the optimistic projection is below both CPU (129.7) and
  iGPU (152.2). **The NPU loses small-model t/s by ~2× or more, even in the best case.**

## 2.2 Kernel invocation overhead — the "constant-cost trap" (NPU)

passthrough kernel, 4096-byte payload, 50 iters:

```
NPU time     (avg/min/max us): 113.6 / 99.7 / 128.2
End-to-end   (avg/min/max us): 269.6 / 205.2 / 372.9
```

~270 µs end-to-end per trivial kernel = host → NPU dispatch + DMA + return, before any useful
work. For real decode-sized ops (small matvecs) this dispatch dominates: consistent with the
literature's mobile-NPU "constant-cost trap", measured on THIS hardware.

## 2.3 Vision / embedding (three-way, where examples exist)

| Pipeline | NPU | CPU | iGPU |
|----------|-----|-----|------|
| edge-detect 512×512 (rgba2gray→filter2D→threshold→gray2rgba→addWeighted) | **PASS** bit-near-exact (L1 0.96); full python run 7.28 s wall (dominated by host/RT setup, not kernel) | numpy reference 17.54 ms/frame | — |
| full multimodal vision (Ornith mmproj, 1045-tok image prompt, from Piece-2 DOE on this machine) | — | — | ~132 pp t/s, ~23 gen t/s (measured) |

NPU runs the CNN vision pipeline its silicon was built for (bit-exact vs reference), but at
base 512×512 it does not beat CPU on wall time when host setup is included — the open-xdna
"offload, not speed" conclusion, corroborated on our machine.

## Power (RAPL package-0; ~15-18s sustained workloads, sudo)

| Workload | pkg W | core W | rest W | Δpkg vs idle |
|----------|------:|------:|------:|-------------:|
| idle | 4.71 | 0.10 | 4.61 | — |
| NPU 512³ matmul loop | 25.67 | 0.17 | 25.50 | **+20.96** |
| CPU llama-bench | 46.10 | 4.03 | 42.07 | +41.39 |
| iGPU 780M llama-bench | 49.24 | 0.06 | 49.18 | +44.53 |

CAVEATS (important, do not over-read):
- **No NPU-specific RAPL domain.** "NPU" column = package delta over idle (NPU + DRAM + fabric).
  The NPU loop's +21 W is an UPPER BOUND on the NPU die; the 512³ host-DMA loop also drives
  DRAM/fabric. (open-xdna measured +2.9 W on a different 8845HS box at a much higher idle
  baseline — our absolute deltas differ; treat magnitude as machine-specific.)
- The RAPL **core domain under-reads on this APU** (4 W core during an 8-thread CPU load) —
  the core/rest split is NOT a reliable device attribution; the package total is the solid
  number. Don't quote per-domain splits as device power.
- iGPU sample ran concurrent with production Ornith on the same 780M (brief contention; Ornith
  health checked OK afterward, GTT cap unchanged 50 GiB).

## Verdict (data-only, no summary beyond the phases yet)

- NPU **loses** small-model t/s decisively (no runtime + slower kernel + dispatch trap).
- NPU **ties/loses** vision on wall time at base size (wins only on offload/low-power semantics).
- NPU **loses** power-per-work for dense matmul at package level (+21 W vs idle), contrary to
  the "~6.6 W floor" narrative on our machine — the floor only holds for light/periodic NPU
  use, not a sustained matmul loop. To be re-checked under Phase 4 concurrency.
