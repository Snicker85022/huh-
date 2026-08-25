# Ornith-1.5 Production Config (canonical, confirmed live 2026-08-25)

Source of truth: `/etc/systemd/system/ornith-1.5.service` (the systemd unit), NOT the DOE
report's "Production settings applied" section (that section was stale; corrected to -np 4).

Live confirmed command (via `ps` on the running service, 2026-08-25):
```
/home/taza/llama.cpp/build/bin/llama-server \
  -m /home/taza/models/Ornith-1.5-35B-Q6_K.gguf \
  --mmproj /home/taza/models/mmproj-Ornith-1.5-35B-BF16.gguf \
  --jinja --alias ornith-1.5-35b \
  --n-gpu-layers 99 --n-cpu-moe 0 --flash-attn on -t 8 -np 4 \
  -c 32768 --temp 0.2 --top-p 0.95 --top-k 20 --image-min-tokens 1024 \
  --host 0.0.0.0 --port 8082
```

- Backend: llama.cpp Vulkan, radv ICD (VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json)
- Model: Ornith-1.5-35B-Q6_K.gguf + mmproj (vision enabled)
- Parallel slots: **-np 4** (confirmed live; DOE report previously said -np 2 — that was stale)
- Context: -c 32768 => 8192 ctx/slot at -np 4
- GTT: 50 GiB (ttm pages_limit = 13107200); real footprint ~26.8 GiB (Piece 2 memory-floor)
- Measured: ~23.1-23.8 tok/s; mixed batch 12/12 (8 text + 4 vision)

DO NOT change this config as part of NPU testing.
