# llama-gflip inference: graceful degradation runbook (2026-08-01)

## Architecture
- Qwen3-30B-A3B Q4_K_M served by llama-server on gflip (192.168.2.107) :8080.
- Primary: GPU via AMDVLK 2025.Q2.1 (-ngl 99). RADV/Mesa hangs MoE kernels -> AMDVLK fixed it (52.2 pp / 17.5 tg t/s).
- Fallback: CPU (-ngl 0, -t 16) with CPU governor boosted to performance (40.2 / 8.8 t/s).
- State: /var/lib/taza/llama-mode (mode=GPU|CPU|DOWN, reason, needs_root_cause)
- Log: /var/log/taza/llama-failover.log
- Notice for Nick/AI: /home/taza/.taza-ai-notice (exists only when NOT on GPU)
- Status page: http://192.168.2.107:8088/ (auto-refresh 15s) + /status.json

## Failover chain (llama-watchdog.timer, every 60s)
1. Healthy -> reset fail counter.
2. Unhealthy -> restart attempt; after 3 consecutive unhealthy checks:
   - GPU -> switch to CPU (drop-in failover-cpu.conf overrides ExecStart to -ngl 0),
     governor -> performance, state=CPU, notify.
   - CPU also unhealthy -> stop service, state=DOWN, notify urgent.
3. Daily 04:15 recovery timer: tries GPU once; success -> GPU + restore governor + clear notice;
   failure -> back to CPU.
4. Manual: /usr/local/bin/llama-failover.sh {status|cpu|gpu|down|recover}

## Notifications (ntfy, self-hosted on n100:2586)
- Client config: /etc/taza/ntfy.conf (canonical: repo/scripts/taza-ntfy.conf)
  NTFY_URL=http://192.168.2.102:2586  NTFY_TOPIC=taza-llama-alerts
- Server: ntfy v2.26.3 on n100 (repo/scripts/ntfy.service + ntfy-server.yml), port 2586.
- Phone: ntfy app -> settings -> add server http://192.168.2.102:2586 -> subscribe taza-llama-alerts.
  (LAN-only for now; off-LAN later via public domain reverse proxy.)
- Priorities: GPU->CPU high/warning; DOWN urgent/skull; recovery ok default/check.
- Public ntfy.sh free tier hit daily quota (429) -> do NOT revert to it.

## Zee panel (Taza OS Health Dashboard, n100:9000)
- Patched dashboard.py (backup: dashboard.py.bak-20260801):
  * get_gflip() fetches gflip :8080 health/props/models + :8088/status.json
  * main page Services panel row "gflip 30B :8080 <MODE>" (mode badge green/amber/red)
  * /system AI Engines row
  * top banner: gflip.mode==CPU -> amber alert line; DOWN -> red alert line
- If "zee panel" is a different display, point a browser/kiosk at http://192.168.2.107:8088/ (self-contained status page).

## Rules & ops
- NEVER run a second all-GPU 17GB load while the server is up (OOM history -> now cgroup-contained).
- Bench tools hang at exit on AMDVLK (vkDeviceWaitIdle): kill by PID; watchdog reaps stale llama-bench.
- Session ritual (AI on gflip): read /var/lib/taza/llama-mode + .taza-ai-notice first;
  if needs_root_cause=1, tell Nick + investigate before restoring GPU.
- After any reboot: everything persists (systemd units+drop-ins, dpkg amdvlk,
  /etc/environment VK_ICD_FILENAMES, sysctl swappiness=10, journald 1G cap, timers).
- Memory cage: MemoryHigh=23G / MemoryMax=26G. GPU healthy: `curl http://127.0.0.1:8080/health`.
