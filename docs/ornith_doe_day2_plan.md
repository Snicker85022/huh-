# Ornith-1.5 gflip — Day-2 DOE Plan (2026-08-25/26)

Goal: find remaining throughput, verify speculative decoding on this bandwidth-bound iGPU,
and lock a production config that balances speed with a 98%/36-month thermal-lifetime target.

Production baseline (live): radv / cmoe0 / -np 4 / -c 32768 / temp 0.2 / top_p 0.95 / top_k 20 /
--mmproj vision / default 45W envelope / Tctl cap 70C / GTT 50GiB. Q6_K gen ~23.5 t/s.

## Block 1 — NPU draft model for speculative decoding (highest priority, per Nick)
Premise: main model is DRAM-bandwidth-bound (89.6 GB/s). A draft model running on the AMD
XDNA NPU does NOT compete for that bus -> speculative decoding could finally beat the wall.
Steps / feasibility gates (honest, in order):
1. Bring up the NPU: load amdxdna driver (kernel 7.0.0-30 ships it? verify), /dev/accel/accel0,
   /sys/class/accel. Install Ryzen AI stack (ONNX Runtime + Vitis AI EP / amdnpu) + rocminfo.
2. Get a SMALL draft model on the NPU: export a ~0.6-1.5B INT8 model to ONNX (Qwen3-0.6B,
   LFM-1.2B, or Ornith's own MTP head) and benchmark NPU t/s (the NPU is ~16 TOPS; small-model
   gen t/s is the open question — target >= main-model t/s at 1 draft token, i.e. > 23 t/s).
3. INTEGRATION gate: llama.cpp has no native NPU backend. Determine the draft transport:
   a. llama.cpp --model-draft requires a GGUF in the same process (runs on iGPU = same bus =
      the known loss). Not the NPU path.
   b. Check if this llama.cpp build supports a REMOTE draft server / custom draft source
      (server draft via HTTP?). If not, we need a small bridge: an OpenAI-compatible draft
      endpoint (Ryzen AI stack serving the ONNX model) + a llama.cpp draft plugin if one exists.
   c. If no clean integration exists, document it as infeasible THIS build and keep the NPU
      experiment as a standalone benchmark (still valuable data).
4. If integration works: measure end-to-end gen t/s with draft-max {2,4,8}, acceptance rate,
   and confirm MTP/np/mmproj restrictions in this build.

## Block 2 — MTP merge + single-slot re-test (fallback if Block 1 is infeasible)
- The two MTP ggufs (Q8_0 + embd) each failed alone as a draft (missing token_embd.weight /
  output_norm.weight). They are split parts -> merge OR reconvert from /home/taza/models/mtp-draft
  (HF dir, model-mtp.safetensors) via convert_hf_to_gguf.py into ONE complete draft gguf.
- Run a SECOND instance: --spec-draft-model <merged> --spec-draft-n-max {3,6}, -np 1, NO --mmproj
  (model card: MTP incompatible with -np>1 and --mmproj).
- Compare vs no-draft single-stream on the same port. Prior A/B was a LOSS (12.7 vs 13.2) on the
  old build/cap — low expectation; close it out with a current number.

## Block 3 — Cold-cache long-context (running now, results_longctx_cold_k7.csv)
- Unique SALT per prompt defeats llama.cpp KV prefix cache -> TRUE cold prompt-eval per length
  (4K-32K x3) = what the per-task scheduler actually pays. Reports real pp_tps + wall + retrieval.

## Block 4 — Production concurrency
- -np 4 applied (stress data: p50 11.4s vs 14.1s at 4-parallel). Validate with a 4-request burst
  on the production instance + confirm no crash + temp stays under cap.

## Block 5 — Quant tradeoff (bandwidth math)
- Q6_K ceiling ~28-32 t/s realistic. Test Q5_K_M (allowed, >= Q5): fewer bytes/token -> expect
  +12-18% gen. Also re-run tool battery + QA at Q5. Do NOT go below Q5 (Nick constraint).

## Block 6 — Sampling DOE, task-representative battery
- Replace the 8 generic QA tasks with N real batch-job-shaped tasks (write endpoint / parse a
  task report / fix a config / produce task-report JSON). 27-cell temp/top_p/top_k grid rerun.
  temp=0.2 is a working default only until this lands.

## Block 7 — Grammar-constrained task-report output
- Server-level --grammar-file for the scheduler's fixed task-report JSON contract (tool-call
  grammar is already automatic; general-output grammar is not). Test correctness + speed impact.

## Block 8 — Thermal / longevity soak
- Sustained load at Tctl cap 70C for ~1h; record steady-state temps (GPU/CPU), confirm gen speed
  unaffected, verify fan/firmware holds temps. Rationale: 36-month, 23.5h/day-for-1-month then
  6h/day duty; Tctl 70C ceiling is far below 95C max and gives large silicon-lifetime margin.

## Housekeeping / already done
- Removed broken spec-test drop-in (crashed on MTP draft load) — production restored.
- Tool-call scorer normalized (case/whitespace) — re-run battery for true accuracy.
- Thermal cap oneshot (ornith-thermal.service) + default 45W envelope.
- ryzenadj pp-boost is DEPRIORITIZED (raises temps; conflicts with the thermal policy).
