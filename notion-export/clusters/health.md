# Taza OS URS — HEALTH cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-HEALTH-001 — Health dashboard covers event-critical infrastructure
**Status:** Deployed | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: one glanceable screen shows whether the whole system is actually healthy right now (services, UPS/power, thermal, disk/memory, printer, backup freshness) — catch a problem in seconds, not during an event.

**Atomic Requirement:**  
The health dashboard shall display service state, UPS/power, CPU, memory, disk, printer readiness, backup freshness, and event-critical service readiness.

**Functional Requirement Specification:**  
The system shall serve a live health dashboard covering, at minimum: per-service state, UPS/power status, CPU temperature, memory, disk, thermal history, network presence of the display fleet, AI-engine (llama.cpp) status, printer readiness, and backup freshness. Each signal shall render with a timestamp and an explicit state; a signal that cannot be read shall show 'unknown/degraded', never 'healthy' (see HEALTH 9). The dashboard shall be reachable on the LAN and via the approved private remote path (Tailscale).

**Intent / User Need:**  
Turn 'is the system OK?' from a multi-command SSH investigation into a single glance, so failures are caught in minutes not weeks (directly motivated by the 2026-08-21 outage that went undetected for ~2 weeks).

**Inputs:**  
systemctl service states; apcaccess UPS telemetry; /sys thermal + psutil CPU/RAM/disk; ping/ADB presence of the display fleet; llama.cpp /health; printer/CUPS status; backup file mtimes.

**Outputs:**  
Rendered health dashboard (HTML, 30s auto-refresh) on LAN + Tailscale; the same signals available for URS-HEALTH-005 staleness logic and for alerting.

**Trigger:**  
Continuous — page load + 30s poll loop while the service runs.

**Invariants:**  
Every configured signal is always shown (present-with-state), never silently omitted; an unreadable signal is degraded/unknown, never healthy (URS-HEALTH-005).

**Failure Behavior:**  
A failed signal read renders that tile as degraded/unknown with its last-known timestamp; the dashboard process itself is systemd-managed and restarts on failure (URS-HEALTH-004).

**Failure Mode Addressed:**  
Silent infrastructure failure that stays invisible until it hurts an event (the 08-21 dnsmasq outage that looked 'active' the whole time).

**Out of Scope:**  
PROD-25/ntfy (alerting).

**Acceptance Criteria:**  
Every configured signal appears with timestamp and state; unavailable signals are marked unknown rather than healthy.

**Verification Method:**  
Fault-injection and dashboard inspection.

**Maintenance Requirements:**  
Add a signal tile whenever a new critical service ships; keep the apcaccess/thermal parsers current with hardware changes; verify the 30s poll doesn't contend with inference on the N100.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Health-dashboard-covers-event-critical-infrastructure-eb3c169bcde24277a2eae1c626e79278_

---
## URS-HEALTH-002 — Emergency status remains accessible from a phone
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: a simple emergency/crew page reachable on a phone when normal kitchen screens or the network are down — essential operating info, never locked out by a display/UI failure.

**Atomic Requirement:**  
A phone-friendly emergency page shall remain reachable through the approved private/admin network path when normal operational interfaces are degraded.

**Functional Requirement Specification:**  
The system shall serve a phone-friendly emergency/crew page that remains reachable through the approved private admin path (Tailscale) when normal operational interfaces are degraded. It shall present the essential crew/emergency operating information in a large-text, sunlight-readable layout, and shall deny unauthorized public access.

**Intent / User Need:**  
Guarantee a degraded-mode information lifeline on the device everyone already has (their phone), so a screen/UI failure never leaves the kitchen blind.

**Inputs:**  
N100-served HTML; live UPS telemetry via apcaccess for /status; the configured essential crew/emergency content.

**Outputs:**  
Phone-rendered /emergency, /siteguide, /status pages over LAN + Tailscale.

**Trigger:**  
On-demand (crew opens the page); always-live service.

**Invariants:**  
Reachable only via LAN or authenticated Tailscale — never exposed to the public internet (SEC alignment); the page does not depend on the main operational UI being up.

**Failure Behavior:**  
systemd-managed, restarts on failure (URS-HEALTH-004). If the N100 itself is down, this path is unavailable by definition — the emergency PRINT path (URS-HEALTH-003) is the deeper fallback.

**Failure Mode Addressed:**  
Total loss of operating info when the primary screens/UI degrade; being locked out of ops data during an incident.

**Acceptance Criteria:**  
NORMAL:
1. Emergency/crew page reachable via Tailscale even when normal operational interfaces are degraded, large-text/sunlight-readable, denies unauthorized public access.

EDGE:
2. Page is usable/legible on a phone in actual outdoor/bright-kitchen lighting conditions, not just tested indoors on a dim screen.
3. Page remains reachable even if the N100's normal application services are down, as long as the underlying Tailscale tunnel and this specific service are up — verify it doesn't share a failure dependency with the things it's meant to work around.

NEGATIVE:
4. An unauthenticated external request to reach this page is denied — confirm with an actual external attempt, not just trusting the Tailscale config.

SILENT FAILURE:
5. This page itself silently going down (its own service crashes) during the exact outage scenario it exists for would be the worst-case failure — verify its own uptime/health is monitored independently, ideally via a mechanism that doesn't depend on the same failure domain it's protecting against.
6. Content on this page (essential operating info) going stale during an extended outage (no updates flowing in) must be visibly marked as such, not presented as current.

**Verification Method:**  
1) Access test: reach the page via Tailscale from a phone, confirm large-text sunlight-readable rendering in real kitchen lighting. 2) Unauthorized-access test: attempt public access without Tailscale auth, confirm denial. 3) Degraded-mode test: simulate normal operational services being down, confirm this page remains reachable. 4) Independent-monitoring check: confirm this service's own health is tracked via a path that doesn't share the failure domain of what it's meant to work around. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Install/settle the always-on taza-crew.service version during the URS rewrite; keep crew phone numbers / site-guide content current; confirm Tailscale reachability after any network change.

**External Dependencies:**  
WireGuard/private admin path.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Emergency-status-remains-accessible-from-a-phone-199f512f56bd4538b773543da347c1bc_

---
## URS-HEALTH-003 — Emergency path prints essential operating packet
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: on power loss, the system automatically prints the essential 'what's happening tonight' packet on the receipt printer — keep running the event on paper.

**Atomic Requirement:**  
The emergency print path shall produce the current essential event and kitchen operating packet when normal screens or network-dependent workflows are unavailable.

**Functional Requirement Specification:**  
On a power-loss event, the system shall automatically print the current essential operating packet (remaining packout items, open tasks, allergen flags, crew contacts, event/gig blocks) to the owned thermal printer, without requiring the screens, network, or any manual action. The printed packet shall be readable, timestamped, and auto-cut.

**Intent / User Need:**  
A power-independent, screen-independent, network-independent operational-truth fallback — the kitchen runs on paper the instant power drops, no human intervention.

**Inputs:**  
apcupsd ONBATTERY event; current event/task/packout/allergen/crew data from PostgreSQL; UPS status.

**Outputs:**  
A printed 80mm thermal packout/ops-truth strip with dual QR codes, auto-cut, on power loss.

**Trigger:**  
apcupsd ONBATTERY hook fires on power loss (after 30s TIMELEFT stabilization).

**Invariants:**  
Prints via StarTSPImage direct-USB path only; fires automatically on ONBATTERY with no human action; UPS must hold the N100 + printer long enough to complete the job (HW-008).

**Failure Behavior:**  
If the DB read fails, print last-known/essential static content rather than nothing. Auto-cut confirms completion.

**Failure Mode Addressed:**  
Total operational blackout on power loss; dependence on screens/network that are themselves down during an outage.

**Out of Scope:**  
Ops-truth TEMPLATE design + richer Python trigger — a documented follow-on to 'make the printer print'.

**Acceptance Criteria:**  
NORMAL:
1. On power loss, the essential operating packet prints automatically, readable, timestamped, auto-cut, with no screen/network/manual dependency.

EDGE:
2. Timestamp on the printed packet reflects the actual outage/print moment, not a stale cached value from earlier.
3. Auto-cut functions correctly across the full print length regardless of content volume (short vs. long packet).

NEGATIVE:
4. A print job that fails partway (paper jam, mechanical fault) doesn't produce a silently truncated packet presented as complete — needs a way to distinguish a genuinely complete print from a failed one, even without network to report the failure.

SILENT FAILURE:
5. See HEALTH 2 (PROD-11) — this row and that one describe the same real behavior; verify consistency and treat their acceptance criteria and test execution as one shared verification effort, not duplicated separately with potential drift.
6. Readability under real degraded conditions (thermal paper contrast, small text at 576px width) must be confirmed by an actual person reading a real printed sample, not assumed from the raw spec numbers.

**Verification Method:**  
1) Shared verification with HEALTH 2 (PROD-11) — same real power-down test, same printed artifact, evaluated against both rows' criteria together. 2) Readability check: Nick/Sandra physically read a real printed packet under kitchen lighting, confirm legibility. 3) Failure-mode test: interrupt the print job mid-print (simulate jam), confirm the failure is distinguishable from a complete print. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Keep the packout/ops-truth template current; verify the QR endpoints resolve (an earlier V1.0-Project-Plan item flagged QR codes returning 'site can't be reached' at ~67% — confirm resolved against the 07-07 working state); re-run a live power-down drill after any printer/UPS change.

**Open Questions:**  
Build the richer ops-truth template (follow-on).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Emergency-path-prints-essential-operating-packet-53846c10a2944aa2923bba08adbca2aa_

---
## URS-HEALTH-004 — Health and emergency services survive reboot
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: health-monitoring and emergency services come back on their own after any reboot/power event, and leave a visible record when something fails.

**Atomic Requirement:**  
Health-dashboard and emergency services shall be managed by systemd, start automatically after reboot, and expose observable failure logs.

**Functional Requirement Specification:**  
The health-dashboard and emergency services shall be systemd-managed, start automatically after a cold reboot with no manual action, and expose observable failure logs. A forced failure shall be recorded and visible (journalctl), and self-healing timers shall auto-restart a failed critical service.

**Intent / User Need:**  
Ensure the monitoring/emergency layer is self-restoring and self-reporting, so a reboot or crash never leaves the safety net down without anyone knowing.

**Inputs:**  
systemd unit definitions (Wants/After=network-online.target, Restart=on-failure); self-heal timer probes; journald logs.

**Outputs:**  
Services auto-healthy post-reboot; journalctl failure records; self-heal auto-restart actions.

**Trigger:**  
Boot; service failure; self-heal timer interval.

**Invariants:**  
Every critical service has a systemd unit that auto-starts on boot and restarts on failure; failures are logged and observable, never silent.

**Failure Behavior:**  
A crashed service is auto-restarted by systemd/self-heal timer within its interval; the event is recorded in journald. The 08-21 boot-order race (dnsmasq binding before enp1s0 had its IP) is permanently fixed via explicit listen-address + network-online.target ordering.

**Failure Mode Addressed:**  
Silent post-reboot service death; the specific dnsmasq boot-order bind failure that caused the 2-week undetected outage.

**Acceptance Criteria:**  
NORMAL:
1. Health-dashboard and emergency services are systemd-managed, start automatically after a cold reboot with no manual action, expose observable logs.
2. A forced failure is recorded and visible via journalctl; self-healing timers auto-restart a failed critical service.

EDGE:
3. A cold reboot triggered by an actual power-loss-then-restore (not a clean shutdown/reboot command) still results in correct automatic startup — verify against the messier real-world case, not just systemctl reboot.
4. A service that fails repeatedly (crash-loop) is caught by systemd's restart-limit rather than looping forever — same concern as INFRA 11, verify specifically for these critical health/emergency services given their outsized importance.

NEGATIVE:
5. A service that fails to start at all post-reboot (not just crashes after starting) is distinguishable in the logs from one that started and later crashed — different failure signatures should be diagnosable.

SILENT FAILURE:
6. Self-healing timers auto-restarting a service masks the underlying problem if it keeps happening repeatedly without anyone noticing the pattern — verify restart events themselves are visible/alertable in aggregate (e.g. 'this service has restarted 5 times today'), not just silently self-healed every time with no one the wiser.
7. journalctl logs being 'observable' in principle but never actually reviewed is equivalent to no logging for practical purposes — verify there's an actual review cadence or alerting tied to these logs, not just log-existence.

**Verification Method:**  
1) Cold-boot test: actual power-loss-then-restore (not clean reboot), confirm health-dashboard and emergency services come up automatically. 2) Forced-failure test: kill each critical service, confirm journalctl records it and the self-healing timer restarts it. 3) Crash-loop test: force repeated rapid failures, confirm systemd's restart-limit engages. 4) Restart-frequency visibility test: confirm repeated self-heals on the same service are aggregately visible/alertable, not silently absorbed. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
Sweep any newly-added service for the same missing-Restart=on-failure / missing-listen-address class of bug; keep self-heal probes functional (real dig/health test, not just 'is the unit active'); extend self-heal automation to the display fleet (open).

**Open Questions:**  
Display-fleet self-heal scripts still missing (3 TVs).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Health-and-emergency-services-survive-reboot-c85ed1f872da4f97866ccc9a170c5a43_

---
## URS-HEALTH-005 — Stale or missing health data fails visibly
**Status:** In Development | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: a stale/missing/unreadable health signal shows unknown/degraded, never green — a false 'healthy' is worse than an honest 'unknown' (it's what hid the last outage).

**Atomic Requirement:**  
A stale, missing, or unreadable health signal shall display as unknown or degraded and shall never default to healthy.

**Functional Requirement Specification:**  
A stale, missing, or unreadable health signal shall render as 'unknown' or 'degraded' with a timestamp, and shall never default to 'healthy'. Each monitored signal shall have a staleness threshold; a read timeout or malformed value shall produce a timestamped degraded state and log an exception.

**Intent / User Need:**  
Make the monitoring layer trustworthy by making it fail loud — the whole point of a health dashboard is defeated if an unreadable signal reads green.

**Inputs:**  
Each monitored signal + its read timestamp + per-signal staleness threshold.

**Outputs:**  
A timestamped degraded/unknown state per stale-or-failed signal; a logged exception.

**Trigger:**  
Every poll cycle, per signal.

**Invariants:**  
No code path renders 'healthy' from an absent/stale/malformed read; every tile shows a timestamp.

**Failure Behavior:**  
Signal read fails or exceeds staleness threshold → tile = degraded/unknown + timestamp + exception logged. This IS the failure behavior (it's a fail-visible requirement).

**Failure Mode Addressed:**  
False-positive health (a dead thing reporting alive) — the exact 08-21 dnsmasq failure mode.

**Acceptance Criteria:**  
NORMAL:
1. A stale, missing, or unreadable health signal renders as 'unknown'/'degraded' with a timestamp — never defaults to 'healthy.'
2. Each monitored signal has a defined staleness threshold; exceeding it produces a timestamped degraded state and logs an exception.

EDGE:
3. A signal that recovers right at the staleness threshold boundary is handled deterministically (doesn't flicker between healthy/degraded on borderline timing).
4. A signal source that returns a malformed (not just missing) value is treated the same as a missing one — degraded, not a crash and not a false-healthy default from a parsing exception being swallowed.

NEGATIVE:
5. A monitoring code path that has a bug causing it to default to 'healthy' on any exception (a common anti-pattern: except: return healthy) is the specific failure mode this row exists to prevent — verify by code review AND by forcing every monitored signal's read path to throw, confirming none of them default to healthy.

SILENT FAILURE:
6. This row IS the silent-failure prevention mechanism for the whole health system — its own silent failure (this logic itself breaking) would be maximally dangerous since it would make every other health signal untrustworthy at once. Verify this logic has its own independent test coverage that's re-run on every change to any monitored signal's read path, not just tested once at initial build.
7. Logged exceptions from degraded-state detection must actually be reviewed/actionable, not just written to a log no one reads — verify these logs feed into an actual alert or review process.

**Verification Method:**  
1) Fault-injection test: force every individually monitored signal's read path to fail (timeout, malformed value, exception) one at a time, confirm each produces a timestamped degraded state and logged exception — never a healthy default. 2) Code-review gate: explicitly check for any except: return healthy-style anti-pattern across all health-signal code. 3) Boundary test: staleness threshold edge timing, confirm deterministic behavior. 4) Regression requirement: this test suite re-runs on any future change to a monitored signal's read path. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Maintenance Requirements:**  
When adding a signal, define its staleness threshold and its degraded-state rendering before shipping it; periodically fault-inject each signal class to confirm none silently defaults healthy.

**Open Questions:**  
Needs a fault-injection verification pass before this can be marked Verified — flagged as a verification gap, not assumed done.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Stale-or-missing-health-data-fails-visibly-91cabfadbd9c457891e26fdc6714ad3e_
