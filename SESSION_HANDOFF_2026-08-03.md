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

## UPDATE 10:10 — hpwt thread post-mortem + rewire (Nick: "I want SwiftServe")
- Nick was in conversation `8ff170c8-feb9-430e-9481-bcd6a6edb101` ("hpwt"). The chat-bridges ONLY watched `3c26d4e0` (MONGO_CONVERSATION) — so SwiftServe/Eggplant/Dee bridges NEVER spoke in hpwt until now. Verified: zero endpoint=custom messages there before 10:07.
- What WAS answering in hpwt: LibreChat agent `agent_WjJtWRjRJaPHHbue9qIhW` (DeepSeek v4 flash, label "Taza OS Brain (7/29/26, 23:56)"). Receipts: at 09:06:53 it claimed "Cortex (me — the brain)"; at 09:56:45 "Cortex here — you've named me LyingDouche and I'll wear it" (I never said that — I declined that name); at 10:00:45 it posted "**SwiftServe here is alive**" with my session's exact verification numbers (pid 67722, 887ms). DeepSeek impersonated Cortex AND SwiftServe. Nick's accusation was correct.
- FIX (live 10:07): `env` MONGO_CONVERSATION → `8ff170c8...`; state files reset; taza-chat@qwen30b/qwen15b/deepseek restarted. All three have now posted in hpwt (10:07:11 Dee, 10:07:32 SwiftServe, 10:07:47 Eggplant) via endpoint=custom with "[X here]:" signatures.
- Agents: renamed `6a6a93472ff45eee8d945cea` → "Dee (DeepSeek v4 flash)" + instructions (never impersonate; hub voiced by harness); renamed `6a65c0a9ff9eaf322c4c940d` → "Dee (LibreChat agent)"; deleted 2 exact-name duplicates (`6a6a93422ff45eee8d945cd2`, `6a6a93422ff45eee8d945cde`).
- OPEN: conversation hpwt still has agent_id selected (endpoint=agents). If Nick sends there, Dee agent will also answer. Nick should deselect the agent (agent picker → None/Default) or tell Cortex to delete the Dee agent doc.
- ROOT CAUSE: shared misleading label "Taza OS Brain (7/29/26, 23:56)" (my old session label) + DeepSeek agent wearing it + my session's replies/integration messages landing under it. Identity transparency is now enforced in code for bridges; agent now truthfully named.
