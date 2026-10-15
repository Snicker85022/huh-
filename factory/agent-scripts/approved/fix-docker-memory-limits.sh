#!/bin/bash
# Step C (Fix 1): per-container memory limits + Node heap cap for LibreChat.
#
# Why: docker-compose.yml has no memory/cpus limits anywhere, so a heavy agentic
# session can grow the LibreChat Node process to the whole host RAM (observed
# VmHWM 2.86 GB; host has 60 GB with no ceiling). Limits + a V8 heap cap make
# Node GC before the container is killed.
#
# Limits (approved): mongodb 1g, api 1g, meilisearch 512m, rag_api 512m,
# vectordb 512m, admin-panel 256m. Plus NODE_OPTIONS=--max-old-space-size=1536.
# Also caps mongod WiredTiger cache (currently 30.5 GB max, derived from host RAM)
# because an uncapped cache under a 1g container limit is an OOMKill trap.
#
# Usage:  fix-docker-memory-limits.sh            # dry run: show diff
#         fix-docker-memory-limits.sh --apply     # backup + patch + validate
#         fix-docker-memory-limits.sh --apply --skip-wiredtiger-cache
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/patch_compose_memory_limits.py" "$@"
