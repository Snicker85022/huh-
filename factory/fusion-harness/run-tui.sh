#!/bin/bash
# fusion.tazacateringphoenix.com  ->  localhost:7684  ->  THIS script.
# Serves Nick's CODING HELPERS TEAM in PLAIN-ENGLISH TEAM MODE: he types normal English,
# every member answers in its lane, the architect fuses ONE reply back. No /fh-* needed.
# The cheap5 debate stack is still available on demand:
#   just fh-stack .pi/fusion-harness/model-stack-cheap5.yaml
# Archived original: /home/taza/archive/fusion-tui-cheap5-20261015/run-tui.sh.bak
cd /home/taza/repo/factory/fusion-harness
export HOME=/home/taza
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export TERM=xterm-256color
# HARD MODEL GUARD — only these pre-approved cheap models may ever run.
# No claude-fable-5, no kimi-k3, no gemini, no gpt-5.x. Ever.
export FH_ALLOWED_MODELS="openrouter/deepseek/deepseek-v4-pro,openrouter/deepseek/deepseek-v4-flash,openrouter/qwen/qwen3-235b-a22b-2507,openrouter/z-ai/glm-5.3-flash,openrouter/cohere/north-mini-code:free,openrouter/poolside/laguna-s-2.1:free"
# pi does NOT read .env itself — it reads env vars. Without this the harness dies with
# "no configured authentication for openrouter/..." on every slot.
if [ -z "$OPENROUTER_API_KEY" ] && [ -f .env ]; then
  export OPENROUTER_API_KEY="$(grep -oP '(?<=OPENROUTER_API_KEY=)\S+' .env | head -1)"
fi
# Plain-English team mode ON. Just talk. (Turn off in-session with /fh-team-mode off.)
exec just fh-team --fh-team-mode on
