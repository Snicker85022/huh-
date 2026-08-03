# Session Handoff — 2026-08-03 (Claude Code / Cortex)

## What changed today
1. **Chat participants renamed** (hub display names): qwen30b->SwiftServe, qwen15b->Eggplant, deepseek->Dee.
   - participants.json senders updated; legacy-name dedup added; @mention works with both old and new names.
2. **Eggplant guaranteed window** in chat bridge turn-taking (participant.py):
   - PRIMARY_TIMEOUT=90s (secondaries take floor if SwiftServe silent).
   - EGGPLANT_WINDOW=120s (Dee yields to Eggplant's turn).
3. **Executor rewire (Claude cost -> local)**:
   - NEW /home/taza/cc-aider-exec.sh (gflip): aider + SwiftServe (:8080) default; deepseek tier -> DeepSeek API.
   - NEW /home/taza/cc-aider-exec-n100.sh (n100): aider + Eggplant (:8081) default; deepseek tier.
   - cc-run-gflip.sh + cc-run.sh now invoke the helper, NOT the claude CLI.
   - aider 0.86.2 installed on n100. aider-local alias model label fixed (qwen3-30b-a3b).
   - PROOF: commit ae5a25c by SwiftServe <swiftserve@tazacateringphoenix.com> (rewire-test file).
4. **Notion FROZEN (manual-only by Nick)**:
   - gflip: cc-watcher-gflip.service stopped+disabled (mask failed - unit file exists; disabled is enough).
   - n100: cc-watcher.service, cc-watcher-gflip.service, notion-auth-check.{service,timer} stopped+disabled.
   - KEPT (Notion-free): aider-watcher-n100.service (/opt/taza/inbox queue), ntfy-ack-watcher.service, chat bridges.
   - LibreChat "Taza OS Brain" agent (6a65c0a9ff9eaf322c4c940d): Notion tools (queryKB/createPage/getPage) stripped; keeps tavily + run_command shell-exec.
5. **Identity rule**: CLAUDE.md written (home + repo). Cortex = Claude Code. Never impersonate other agents.

## Standing orders
- SwiftServe leads. Eggplant + Dee assist. Claude Code only enters when Nick summons it (@Cortex).
- All Notion data import/export: Nick, manually. Agents do not touch Notion.

## Files
- Bridges: /home/taza/chat-bridges/ (participant.py v3+patches, participants.json)
- Executors: /home/taza/cc-aider-exec.sh, /home/taza/cc-aider-exec-n100.sh
- Backups: participant.py.bak-*, cc-run*.bak-*, participants.json.bak-* (same dirs)
