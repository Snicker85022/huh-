# Taza OS URS — INFRA cluster
_Exported: 2026-09-19 21:35 | 9 rows_
_Source: Notion Master URS & Specification Registry_

---
## INFRA-001 — Ubuntu Host Baseline
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As the system owner, I need a stable, reproducible host environment so deployments and recovery are predictable.

**Atomic Requirement:**  
The host shall boot Ubuntu 22.04 LTS, retain its assigned LAN identity, update successfully, and expose the Intel graphics device.

**Functional Requirement Specification:**  
The N100 shall run the canonical Ubuntu 22.04 LTS host baseline with deterministic LAN addressing and verified Intel graphics support.

**Acceptance Criteria:**  
NORMAL:
1. N100 runs Ubuntu 22.04 LTS with deterministic (static/reserved) LAN addressing and verified working Intel graphics support.

EDGE:
2. A reboot (planned or power-loss recovery) brings the N100 back up on the exact same LAN address every time — not DHCP-reassigned to a different IP.
3. An OS update/patch cycle doesn't silently change graphics driver behavior in a way that breaks anything dependent on it (if applicable — flag for recon if graphics dependency exists beyond display output).

NEGATIVE:
4. A fresh install/rebuild (e.g. during a DR drill, [[SPEC:OPS-003]]) reproduces this exact baseline reliably from documented steps, not tribal knowledge.

SILENT FAILURE:
5. LAN address 'drifting' due to a DHCP reservation being lost (router reset, misconfiguration) would silently break every hardcoded-IP reference across the system — verify addressing is actually static/reserved at the network level, not just 'usually comes up the same' by DHCP luck.
6. Intel graphics support degrading after a kernel/driver update is a real regression risk — verify there's a smoke test for graphics functionality after any OS-level update, not assumed permanently fine.

**Verification Method:**  
1) Baseline verification: confirm Ubuntu 22.04 LTS, static LAN address, graphics support all present and correct. 2) Reboot test: multiple reboot cycles, confirm the N100 returns to the exact same LAN address every time. 3) Rebuild-reproducibility test: as part of a DR drill ([[SPEC:OPS-003]]), confirm this baseline is reproducible from documentation alone. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Ubuntu-Host-Baseline-7109dc5443fb4a648249830c6a4cca49_

---
## INFRA-002 — Core Services and Automation Runtime
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As the system owner, I need every core service and automation to recover automatically so operations do not depend on manual restarts.

**Atomic Requirement:**  
All core services and scheduled Python automations and/or RUST programs shall start automatically after host reboot and expose healthy status.

**Functional Requirement Specification:**  
The environment shall run NocoDB, PostgreSQL, Open WebUI, and Python-and/or-Rust automation jobs with systemd-managed startup and restart behavior.

**Acceptance Criteria:**  
NORMAL:
1. NocoDB, PostgreSQL, Open WebUI, and Python/Rust automation jobs all run under systemd with defined startup order and automatic restart on crash.

EDGE:
2. A reboot brings all four services back up in the correct dependency order (e.g. PostgreSQL before NocoDB/automation that depends on it) — not a race where a dependent service starts before its dependency is ready.
3. A service crash-looping (fails, restarts, fails again rapidly) is caught by systemd's restart-limit backoff, not left in an infinite rapid-restart loop consuming resources.

NEGATIVE:
4. A service that fails to start at all (bad config, missing dependency) is visibly flagged, not silently absent with everything else appearing to run fine.

SILENT FAILURE:
5. One of the four services silently dying and NOT being restarted (systemd restart policy misconfigured for that unit) would leave a critical gap — verify actual crash-and-recover behavior is tested per service, not just assumed from the systemd unit file existing.
6. Services 'running' per systemd status but actually unresponsive/hung (process alive, not functioning) must be distinguished from truly healthy — verify health checks go beyond process-exists to actual functional response.

**Verification Method:**  
1) Boot-order test: full reboot, confirm all four services come up in correct dependency order with no race failures. 2) Crash-recovery test: kill each service's process individually, confirm systemd restarts it automatically. 3) Crash-loop test: force repeated rapid failures, confirm systemd's backoff/restart-limit engages rather than infinite rapid restart. 4) Functional health check: confirm each service is verified by an actual functional probe (e.g. a real query/request), not just process-alive status. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Core-Services-and-Automation-Runtime-9156f65ab98c4be589aae2222d505e35_

---
## INFRA-003 — Native llama.cpp Inference Service
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As an operator, I need dependable local inference with known performance and thermal limits so AI assistance remains available and predictable.

**Atomic Requirement:**  
The inference service shall start automatically, expose its API, meet the V1 throughput floor, and remain within the approved thermal envelope.

**Functional Requirement Specification:**  
The system shall run llama.cpp server as a native systemd service,

**Acceptance Criteria:**  
NORMAL:
1. llama.cpp runs as a native systemd service (not a wrapper/container adding overhead), starts on boot, restarts on crash.

EDGE:
2. Service survives a model reload/swap (if the pluggable-backend architecture from [[SPEC:PROD-10]] requires this) without requiring a full service restart, or if it does require a restart, that's documented and handled gracefully.
3. Concurrent requests during the CPU-pinned tier system ([[SPEC:PROD-10]]) are correctly isolated — this service's behavior under real concurrent tiered load, not just single-request benchmarks.

NEGATIVE:
4. Service failing to start (bad model path, port conflict) is visibly logged/alerted, not silently absent while dependent features fail mysteriously.

SILENT FAILURE:
5. Since V1.0 is cloud-first ([[SPEC:PROD-10]] decision) and this local llama.cpp service becomes the future-pluggable-local path rather than the V1.0 default, verify this row's Target Release / Implementation Status reflects that — don't let a debate agent build this as a load-bearing V1.0 dependency when it's actually the aspirational local-swap-in path.
6. A hung (unresponsive but process-alive) llama.cpp service must be distinguishable from a healthy one via the health dashboard, not just systemd's process-alive check.

**Verification Method:**  
1) Service test: confirm systemd unit starts on boot, restarts on crash, logs failures visibly. 2) Load test: concurrent requests under the tiered CPU-pinning model, confirm correct isolation. 3) Functional health check: confirm the health dashboard distinguishes a hung service from a genuinely responsive one, not just process-alive. 4) Scope check: confirm this row is correctly scoped as the local-model path (not V1.0-required, per the [[SPEC:PROD-10]] cloud-first decision) before it goes to debate, so it isn't built as a false V1.0 dependency. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Native-llama-cpp-Inference-Service-f08149c7d508477789b2730bf19053bf_

---
## INFRA-004 — CPU Throttle and Restore Controls
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As the system owner, I need safe, reversible CPU operating modes so heavy work cannot silently destabilize production services.

**Atomic Requirement:**  
Throttle and restore commands shall apply the intended CPU state, be safe to repeat, and restore the canonical state after constrained work.

**Functional Requirement Specification:**  
The environment shall provide idempotent throttle and restore controls for CPU governor and active-thread settings.

**Acceptance Criteria:**  
NORMAL:
1. Throttle control reduces CPU governor/active-thread settings on command; restore control returns them to normal on command — both idempotent (repeated calls produce the same end state, no cumulative drift).

EDGE:
2. Throttle called while already throttled is a no-op that doesn't over-throttle or error; restore called while already normal is a no-op that doesn't error.
3. Throttle/restore correctly interacts with the overnight-analysis CPU-throttle window ([[SPEC:W6]]/[[SPEC:W6]]) — verify the actual consumer of this control behaves correctly, not just the control mechanism in isolation.

NEGATIVE:
4. A throttle command issued but never followed by a restore command (bug, crash mid-window) leaves the system permanently throttled — verify there's a safety timeout or a way to detect and recover from a stuck-throttled state.

SILENT FAILURE:
5. A restore command that silently fails to actually take effect (system still throttled, control reports success) would degrade real-time performance (voice path, etc.) without an obvious cause — verify restore is confirmed by an actual measured performance check, not just a command-issued signal.
6. Concurrent throttle/restore calls (race condition, e.g. two different callers) must resolve to a defined, correct end state, not an undefined race.

**Verification Method:**  
1) Idempotency tests: repeated throttle calls, repeated restore calls, confirm stable end state both times. 2) Stuck-state test: simulate a crash between throttle and restore, confirm a timeout/recovery mechanism returns the system to normal. 3) Real-consumer integration test: run the actual overnight-analysis throttle window ([[SPEC:W6]]) and confirm real-time voice-path performance is unaffected outside that window. 4) Verified-restore test: confirm restore is checked against actual measured CPU behavior, not just command-success. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/CPU-Throttle-and-Restore-Controls-eb667331de7f4c0ba9f7b6b9dc814200_

---
## INFRA-005 — Self-Owned Remote Access and Reverse Proxy
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As the system owner, I need secure remote access that I control so critical Taza services remain reachable

**Atomic Requirement:**  
Approved remote services shall be reachable over HTTPS through the VPS while the N100 exposes no direct public inbound service ports.

**Functional Requirement Specification:**  
The system shall expose only approved services for remote access through an encrypted, authenticated tunnel with zero public inbound ports on the N100 (see [[SPEC:SEC-002]]).

**Acceptance Criteria:**  
NORMAL:
1. Only approved services are exposed for remote access, all via the encrypted authenticated tunnel (Tailscale, per [[SPEC:SEC-002]]) — zero public inbound ports.

EDGE:
2. A new service added later is remote-accessible only if explicitly approved and routed through the tunnel — nothing is exposed by default.

NEGATIVE:
3. An approved service's reverse-proxy rule scoped incorrectly (too broad) is caught — verify each exposed service's actual accessible surface matches its documented approval, not more.

SILENT FAILURE:
4. This row's own Design Spec was flagged as still needing authoring (per earlier recon) — verify the actual Tailscale ACL/reverse-proxy config has been documented to match what's live, not left as an undocumented tribal-knowledge setup.
5. A reverse-proxy misconfiguration exposing an internal-only service (e.g. the health dashboard) beyond its intended scope must be caught by the same audit as [[SPEC:SEC-004]], not treated as a separate unchecked surface.

**Verification Method:**  
1) Access-surface audit: enumerate every service reachable via the tunnel, confirm each is on the approved list and no more. 2) Config documentation check: confirm the actual live Tailscale ACL / reverse-proxy rules are documented, closing the previously-flagged authoring gap. 3) Cross-check against [[SPEC:SEC-004]]'s firewall audit for consistency. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
Design Spec (actual Tailscale config/ACLs) still needs authoring.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Self-Owned-Remote-Access-and-Reverse-Proxy-bec7c8b23aeb4039ace7057a9c18a6eb_

---
## INFRA-006 — Protected Environment Configuration
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As the system owner, I need secrets and environment settings centralized and protected so services are reproducible without leaking credentials.

**Atomic Requirement:**  
Every required service shall load its approved configuration from the protected environment file without exposing secrets in source control or logs.

**Functional Requirement Specification:**  
The environment shall maintain required service credentials and configuration in /opt/taza/.env with restricted access and exclusion from Git.

**Acceptance Criteria:**  
NORMAL:
1. All service credentials/config live in /opt/taza/.env, readable only by authorized processes/users, and .env is git-ignored.

EDGE:
2. A fresh clone of the repo contains zero credentials — confirm history is also clean (no credential ever committed then removed, which would still leak via git history).

NEGATIVE:
3. A non-root/non-service user on the N100 cannot read .env's contents via normal file permissions.
4. Attempting to commit .env (accidental git add -f) is caught — verify a pre-commit hook or equivalent guard exists, not just reliance on .gitignore discipline.

SILENT FAILURE:
5. A credential rotated in .env but a service still running with the old cached value in memory would silently keep working on stale creds — verify services actually reload on .env change or require restart, and that this is documented.
6. File permissions on .env drifting (e.g. a deploy script accidentally chmod 644) must be checkable/auditable, not just correct at initial setup.

**Verification Method:**  
1) Permission audit: confirm .env file permissions restrict read access to authorized users/processes only. 2) Git-history scan: confirm no credential has ever been committed, including in prior commits. 3) Guard test: attempt to force-add .env, confirm it's blocked. 4) Rotation test: change a credential, confirm the dependent service either reloads it or the restart requirement is documented and followed. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Protected-Environment-Configuration-077954afa8134cc8805277966f92c7bd_

---
## INFRA-007 — Dedicated WebSocket broadcast server
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: when something changes in the kitchen, every screen (TVs and touchscreens) updates live, without the piece that pushes updates competing with the AI/automation workload for resources.

**Functional Requirement Specification:**  
Dedicated WebSocket broadcast server: lightweight Node.js Docker container on N100, separate from the automation layer. Automation POSTs state change notifications to the WS server via HTTP; WS server manages all client connections and broadcasts to all 6 surfaces (3 TVs + 3 touchscreens). Classifies priority, checks CPU load, builds delta payload, broadcasts TVs then touchscreens per priority timing. CRITICAL alerts bypass all checks.

**Failure Behavior:**  
Fallback: direct WebSocket without dedicated broadcast server (less stable under load).

**Acceptance Criteria:**  
NORMAL:
1. WS server runs as a separate Node.js Docker container, receives state-change POSTs from automation, and broadcasts to all 6 surfaces (3 TVs + 3 touchscreens).
2. CRITICAL alerts bypass priority/CPU-load checks and broadcast immediately.

EDGE:
3. Under high CPU load, non-critical broadcasts are deprioritized/delayed as designed, but CRITICAL alerts still get through with no delay — verify the bypass actually holds under real load, not just in an idle test.
4. A surface that's mid-reconnect when a broadcast fires receives it on reconnect (via gap-recovery/full-state), not permanently missing that update.

NEGATIVE:
5. The WS server crashing does not silently take down the automation layer with it — confirm they're actually decoupled as designed (automation POSTs, doesn't depend on WS server's internal state).

SILENT FAILURE:
6. A broadcast that's sent by the WS server but not received by one or more surfaces (network blip, but not a full disconnect) must be discoverable — verify delivery confirmation or the gap-detection mechanism ([[SPEC:INFRA-009]]) actually catches this case.
7. Priority misclassification (something that should be CRITICAL gets classified as normal priority and delayed under load) would be a dangerous silent failure for time-sensitive alerts — verify the classification logic is tested against real alert types, not just the mechanism.

**Verification Method:**  
1) Broadcast test: trigger a state change, confirm all 6 surfaces receive it correctly. 2) Load test: generate high CPU load, confirm CRITICAL alerts still bypass all checks and deliver immediately while non-critical broadcasts are appropriately deprioritized. 3) Decoupling test: kill the WS server process, confirm automation layer continues operating independently. 4) Classification-accuracy test: verify each real alert type in the system classifies to the correct priority tier. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Dedicated-WebSocket-broadcast-server-3cfe152fc19981c18df0e78686762cfe_

---
## INFRA-008 — Delta push protocol
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: screen updates stay fast and light — send only what changed, not the whole state every time — while still being able to recover the full picture if a device falls behind.

**Functional Requirement Specification:**  
Delta push protocol: WS server builds version-numbered delta payloads containing only changed fields (target 100-300 bytes vs ~2-3KB full state). Full state snapshot always available at a REST endpoint for gap recovery.

**Failure Behavior:**  
Fallback: full state push on every change (20x larger, still functional).

**Acceptance Criteria:**  
NORMAL:
1. WS server builds version-numbered delta payloads containing only changed fields, targeting 100-300 bytes vs. ~2-3KB full state.
2. A full state snapshot is always available at a REST endpoint for gap recovery.

EDGE:
3. A change touching most/all fields (rare but possible) still produces a correct delta, even if it approaches full-state size — the format doesn't break down at the edge of 'mostly everything changed.'
4. Rapid sequential changes to the same field (last-write-wins scenario) produce a correct final delta reflecting the true final value, not an intermediate one.

NEGATIVE:
5. A client requesting the REST snapshot endpoint with a stale/invalid version number still receives a usable full state, not an error that leaves it stuck.

SILENT FAILURE:
6. Version-number gaps (a client missed delta #47, next received is #49) must be detectable client-side so gap-recovery via REST is actually triggered — verify this detection works, not just that the REST endpoint exists in theory.
7. A delta payload that's malformed or corrupted in transit must not be silently applied as a partial/wrong state update — verify validation before application.

**Verification Method:**  
1) Payload-size test: confirm typical deltas fall in the 100-300 byte target range against real state changes. 2) Gap-detection test: simulate a missed version number, confirm the client detects the gap and pulls the REST full-state snapshot. 3) Malformed-payload test: inject a corrupted delta, confirm it's rejected rather than partially applied. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Delta-push-protocol-3cfe152fc19981369139cf80cd5945ba_

---
## INFRA-009 — Shared push/pull hybrid client library
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: every screen in the kitchen fleet handles a dropped connection and reconnects the same reliable way — one shared piece of code, not six different implementations that could each fail differently.

**Functional Requirement Specification:**  
Shared push/pull hybrid client library: one JavaScript module deployed to all 6 surfaces, handling WebSocket connection with backoff reconnection, delta application, version continuity tracking, gap detection, polling fallback watchdog (pull full state if no push in 10s), and seamless return to push on reconnect.

**Failure Behavior:**  
Fallback: per-device polling implementation (no shared library, higher maintenance).

**Acceptance Criteria:**  
NORMAL:
1. The one shared client module handles WS connection with backoff reconnection, delta application, version tracking, gap detection, and polling-fallback watchdog (pull full state if no push in 10s), across all 6 surfaces.

EDGE:
2. Backoff reconnection behaves correctly across a range of outage durations (seconds to many minutes) — doesn't hammer the server with rapid retries nor wait excessively long after a brief drop.
3. A device that reconnects after being fully offline (not just WS-disconnected, actually powered off) correctly re-syncs to current state via the same library path, not a different code path that could diverge in behavior.

NEGATIVE:
4. A surface running an outdated version of this shared library (missed a deploy) is detectable — all 6 surfaces should be verifiably on the same version, not silently drifting.

SILENT FAILURE:
5. The 10s polling-fallback watchdog itself failing to trigger (bug in the watchdog logic) would leave a surface silently stuck with no push AND no fallback poll — verify the watchdog is tested as its own failure mode, not just assumed to work because it's documented.
6. 'Seamless return to push on reconnect' must not create a race where both polling and push are simultaneously active and double-applying updates — verify the handoff is clean.

**Verification Method:**  
1) Unit tests: backoff reconnection timing, gap detection, watchdog fallback trigger at 10s. 2) Cross-surface consistency test: confirm all 6 surfaces run the same library version and behave identically under the same simulated outage. 3) Race-condition test: force a push-arrives-during-poll-fallback scenario, confirm no double-application of updates. 4) Version-drift check: establish a way to verify all surfaces are on current library version. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Shared-push-pull-hybrid-client-library-3cfe152fc19981e7a24dd0dee1a8a37f_
