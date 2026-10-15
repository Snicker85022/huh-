#!/bin/bash
# cheap smoke test of the model guard: only deepseek-v4-pro + deepseek-v4-flash approved.
# qwen3-coder-flash and ox-alpha are NOT approved → their child should be BLOCKED.
cd /home/taza/fusion-harness
export HOME=/home/taza
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
set -a; . ./.env; set +a
ALLOW="openrouter/deepseek/deepseek-v4-pro,openrouter/deepseek/deepseek-v4-flash"
timeout 120 pi -e extensions/fusion-harness/fusion-harness.ts \
  --fh-config .pi/fusion-harness/model-stack-cheap4.yaml \
  --fh-allow-models "$ALLOW" \
  -p '/fh-debate --rounds 1 Reply with exactly OK. Do NOT use tools, do NOT read any files.' \
  --session-dir /tmp/fh-guard-smoke
echo "smoke_exit=$?"
