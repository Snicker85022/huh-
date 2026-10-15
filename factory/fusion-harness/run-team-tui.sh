#!/bin/bash
cd /home/taza/repo/factory/fusion-harness
export HOME=/home/taza
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export TERM=xterm-256color
# HARD MODEL GUARD — the same pre-approved cheap models as run-tui.sh.
# The TEAM stack is composed only from models inside this list.
export FH_ALLOWED_MODELS="openrouter/deepseek/deepseek-v4-pro,openrouter/deepseek/deepseek-v4-flash,openrouter/z-ai/glm-5.3-flash,openrouter/cohere/north-mini-code:free,openrouter/poolside/laguna-s-2.1:free"
# Nick's CODING HELPERS TEAM: architect · code-expert · red team · spec-validator(+AC/VM) · documentarian
exec just fh-team
