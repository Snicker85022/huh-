# Taza OS URS — HARDWARE cluster
_Exported: 2026-09-19 21:35 | 9 rows_
_Source: Notion Master URS & Specification Registry_

---
## HW-001 — N100 Core Server
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As an operator, I need a correctly sized and installed local server so Taza OS has a reliable always-on brain.

**Atomic Requirement:**  
The N100 host shall power on, pass BIOS POST, detect its NVMe and Intel iGPU, and expose approximately 30GB usable RAM.

**Functional Requirement Specification:**  
The system’s core automations shall run on an Intel N100 mini-PC with 32GB RAM and 512GB NVMe, installed, powered, and VESA-mounted.

**Acceptance Criteria:**  
NORMAL:
1. Intel N100 mini-PC (32GB RAM, 512GB NVMe) installed, powered, and VESA-mounted, running the core automations.

EDGE:
2. Under the heaviest realistic concurrent load (inference + WS broadcast + NocoDB + Postgres all active at once, e.g. during event prep), the hardware doesn't hit resource ceilings that degrade any single service.
3. VESA mount physically secures the unit against normal kitchen vibration/movement — not just resting in place.

NEGATIVE:
4. Disk usage approaching 512GB capacity is alerted before it causes a failure, not discovered when a write fails.

SILENT FAILURE:
5. RAM or disk pressure causing gradual performance degradation (not a hard crash) would look like 'the system got slow' rather than an identifiable resource issue — verify resource usage is monitored and visible on the health dashboard (HEALTH 1), not just assumed adequate from spec sheet numbers.
6. NVMe wear/health degrading over time (SSD write endurance) is a real long-term risk for a system doing frequent DB writes — flag for periodic SMART-health monitoring, not a one-time install check.

**Verification Method:**  
1) Hardware bring-up: confirm install, power, VESA mount security. 2) Load test: run realistic peak concurrent workload (inference + broadcasts + DB), confirm no resource-starvation degradation of any service. 3) Resource-monitoring integration: confirm RAM/disk/CPU are visible on the health dashboard with alerting thresholds, not silent. 4) Disk-capacity alert test: simulate approaching capacity, confirm an alert fires before failure. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/N100-Core-Server-d06b1dea7acd4b74ab3c69f568d1b9ae_

---
## HW-002 — 21.5-inch Industrial Touchscreen
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As kitchen staff, we need a large responsive touch surface for reliable at-a-glance interaction.

**Atomic Requirement:**  
The 21.5-inch touchscreen shall boot, obtain a wired network address, open Chrome, and respond to touch quickly

**Functional Requirement Specification:**  
The system shall provide a mounted 21.5-inch RK3288 Android touchscreen with wired Ethernet connectivity.

**Acceptance Criteria:**  
NORMAL:
1. 21.5-inch RK3288 Android touchscreen mounted, powered, and connected via wired Ethernet.

EDGE:
2. Touch input is accurate across the full screen surface, including edges/corners where physical mounts can sometimes distort touch registration.
3. Screen remains responsive under the actual multi-tab usage pattern documented elsewhere (5 tabs: kanban, health, gamemaster, board-master, LKL ref — DISPLAY 5) without degraded performance.

NEGATIVE:
4. A touch-input dead zone (physical defect or mounting stress) is caught by a full-surface test pattern, not just a casual tap-around.

SILENT FAILURE:
5. Touch responsiveness degrading gradually over time (wear, heat) would be easy to miss without a periodic re-check — flag for periodic spot-check, not just an install-time pass.
6. Ethernet link dropping intermittently (not a hard disconnect) could look like 'the touchscreen is just slow' rather than a network issue — verify there's a way to distinguish touch-hardware lag from network lag when troubleshooting.

**Verification Method:**  
1) Hardware bring-up: confirm mount, power, and wired network connectivity. 2) Full-surface touch test: systematic tap-pattern across the entire screen, including edges, confirm no dead zones. 3) Real-usage load test: run the actual 5-tab z33 configuration and confirm sustained responsiveness. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/21-5-inch-Industrial-Touchscreen-769d64563d9b40c09c0fa2f4319cbc96_

---
## HW-003 — Dual MicroTouch Kitchen Displays
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As kitchen staff, we need two dedicated touch displays so simultaneous production work stays visible and actionable.

**Atomic Requirement:**  
Both MicroTouch displays shall boot Android 13, expose the confirmed MT8390 NPU stack, obtain Ethernet connectivity, and provide responsive touch interaction.

**Functional Requirement Specification:**  
The system shall provide two MicroTouch M1-156IC-AA2 15.6-inch Android 13 displays with MT8390 NPU capability and wired ethernet networking.

**Acceptance Criteria:**  
NORMAL:
1. Both MicroTouch M1-156IC-AA2 displays are installed, powered, running Android 13, and reachable over wired Ethernet.
2. Both displays' MT8390 NPU is confirmed accessible (not just present in hardware spec) for the capabilities that depend on it (NPU cluster).

EDGE:
3. One display losing Ethernet link does not affect the other's operation — confirm they're independently networked, not daisy-chained through a single point of failure.

NEGATIVE:
4. A display that boots but fails to get a DHCP/static lease is detectable, not silently invisible to the rest of the system.

SILENT FAILURE:
5. NPU hardware present but inaccessible via software (driver/permission issue) would silently break every NPU-dependent spec — verify NPU accessibility is confirmed via an actual on-device test, not assumed from the datasheet.
6. Touch input degrading (some screen regions unresponsive) over time/wear is a real physical-hardware risk — flag as requiring periodic physical spot-check, not just an install-time pass.

**Verification Method:**  
1) Hardware bring-up test: both displays power on, boot Android 13, obtain network address. 2) NPU accessibility test: run a real NeuroPilot SDK call against each display's MT8390, confirm actual accessibility, not just hardware presence. 3) Independence test: disconnect one display's Ethernet, confirm the other is unaffected. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Dual-MicroTouch-Kitchen-Displays-3acf3ae8f407417ca9d2c3509204c23e_

---
## HW-004 — Kitchen Display TV Cluster (2×75" TCL ops + 55" Fire TV + 50" onboarding)
**Status:** Deployed | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: large wall displays readable across the kitchen showing NOW / NEXT / PREP, plus a separate onboarding screen that doesn't tie up an operational display.

**Atomic Requirement:**  
Both 75-inch TVs shall continuously display their assigned operational content without flicker, dropout, or unplanned sleep.

**Functional Requirement Specification:**  
The kitchen display fleet shall provide 3 role-differentiated operational surfaces (NOW/NEXT/PREP-ALERTS) readable across the kitchen, plus one dedicated crew-onboarding display that never displaces an operational dashboard. All units run on Ethernet, pulling dashboard content from the N100 over LAN, with no auto-sleep during operating hours.

**Inputs:**  
N100-served dashboard HTML/SSE/WebSocket pushes over LAN; for the 55" Fire TV, the ALC cache endpoint + Alexa skill.

**Outputs:**  
Glanceable operational dashboards (NOW/NEXT/PREP-ALERTS) on the operational cluster; spoken Alexa alerts + cache answers on the Fire TV; full-screen onboarding panels on the 50".

**Failure Behavior:**  
TV offline → network-presence monitor (TV-002) sends SMS naming the screen. N100 serving failure → each TV falls back to local page (TV-004). 50" onboarding is non-critical.

**Out of Scope:**  
TV-001 (WoL/auto-boot), TV-002 (presence monitoring), TV-003/011 (voice nav), TV-004 (fallback), SSB-001..007 (dashboard content), ALC-001..006 (Alexa), SCREEN-12/CULT-002 (crew-training content). HW-004 = physical display fleet only.

**Acceptance Criteria:**  
Each TV displays 1080p content for at least five minutes without dropout and remains awake during configured operating hours.

**Verification Method:**  
Confirm all 4 TVs mounted and (once the 50" is networked) reachable on LAN; each operational TV renders its assigned dashboard legibly from a primary work position (SSB-002 glanceability); Fire TV runs the Alexa skill; 50" loads the onboarding panel set.

**Maintenance Requirements:**  
Update DHCP reservations + maintain scripts when a TV is added/swapped; network the 50"; keep TV→role mapping documented so a swap doesn't silently move the Alexa role off the Fire TV.

**Open Questions:**  
Network the 50" onboarding display; TV self-heal scripts/timers still missing (per 08-22 hardening pass).

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Kitchen-Display-TV-Cluster-2-75-TCL-ops-55-Fire-TV-50-onboarding-26c4550075df4900a65225a277756f5b_

---
## HW-005 — Kitchen Ethernet Switching and Cabling
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
As an operator, I need deterministic wired connectivity so kitchen devices do not depend on unreliable wireless links.

**Atomic Requirement:**  
All connected kitchen devices shall have active gigabit switch links, local latency under 5 ms, and internet reachability under normal conditions.

**Functional Requirement Specification:**  
The system shall provide a TP-Link TL-SG105 gigabit switch and Cat6 cabling for the kitchen device network.

**Acceptance Criteria:**  
NORMAL:
1. TP-Link TL-SG105 gigabit switch installed with Cat6 cabling connecting all kitchen devices.

EDGE:
2. All ports actually negotiate gigabit link speed with connected devices, not silently falling back to 100Mbps due to a bad cable run or connector.
3. Cable runs are physically routed/secured to survive normal kitchen activity (foot traffic, cleaning, equipment movement) without disconnection.

NEGATIVE:
4. A port failure (switch hardware fault) is detectable rather than silently degrading one device's connectivity without explanation.

SILENT FAILURE:
5. A cable that's physically connected but degraded (partial wire damage) could produce intermittent packet loss without a hard disconnect — this looks like 'flaky app behavior' rather than an obvious network fault; verify there's a way to spot-check link quality, not just link-up/link-down.
6. Switch itself has no UPS backing per this row's own scope — confirm it's covered by the shared core-stack UPS (INFRA 9), not an accidental gap between specs.

**Verification Method:**  
1) Link-speed test: verify every port negotiates gigabit with its connected device. 2) Physical inspection: confirm cable routing is secured against kitchen wear-and-tear. 3) Cross-spec check: confirm the switch draws power from the UPS-backed circuit (INFRA 9), not an unprotected outlet. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Kitchen-Ethernet-Switching-and-Cabling-473c7e2f925945dab468c3b5d461c22a_

---
## HW-006 — On-Site Crew Display Tablets
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
As event crew, we need durable ambient displays that preserve client context and operational focus without constant verbal supervision.

**Atomic Requirement:**  
Both crew tablets shall run the configured event story and scanning-prompt loop for a four-hour event without sleeping or requiring network access.

**Functional Requirement Specification:**  
The system shall provide two Samsung Galaxy Tab A8 tablets in rugged cases running the crew-display PWA in full-screen mode with wake lock and offline capability.

**Acceptance Criteria:**  
Both tablets boot to full-screen display; event setup works; prompts auto-advance; wake lock prevents sleep for four hours; content is readable from six feet.

**Verification Method:**
1. [AUTO] Boot: both tablets boot to full-screen PWA. Evidence: screenshot.
2. [AUTO] Wake-lock: screen stays awake through a 4-hour simulated event. Evidence: device log.
3. [AUTO] Offline: prompts auto-advance with zero network. Evidence: airplane-mode test.
4. [NICK] Live: crew reads the display from six feet during a real event. Evidence: photo + observation log.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/On-Site-Crew-Display-Tablets-823d0e314cee462f978c9232881e8eaa_

---
## HW-007 — ER605 V2 Gateway Router (building MAC-binding solution)
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: the kitchen network actually comes up and stays up on this building's connection — a router that solves the building's networking quirk, with a fast recovery path when it reverts after a power blip.

**Functional Requirement Specification:**  
TP-Link Omada ER605 V2 gateway router NATs the entire Taza LAN behind a single WAN MAC, solving the building network's MAC-binding / single-DHCP-lease constraint (a plain switch presenting multiple MACs is rejected). Provides IP/MAC binding for a permanent N100 static IP (192.168.2.102), SPI firewall, DoS protection. Hard V1.0 dependency — without it the LAN does not come up. Known quirk: ER605 LAN IP can revert after a power cycle due to a Cox subnet conflict; daily config auto-backup to a dedicated FAT32 USB stick makes restore a ~30s touchscreen operation.

**Acceptance Criteria:**  
NORMAL:
1. ER605 V2 NATs the full Taza LAN behind a single WAN MAC, N100 holds a permanent static IP (192.168.2.102), SPI firewall + DoS protection active.

EDGE:
2. A power cycle that triggers the known Cox-subnet-conflict LAN-IP reversion is recovered from using the documented ~30s touchscreen restore, verified to actually work end-to-end, not just described.
3. Daily auto-backup of router config to the FAT32 USB stick actually succeeds and produces a restorable file — test a real restore from it, not just confirm the backup job runs.

NEGATIVE:
4. The building's MAC-binding/single-DHCP-lease constraint is confirmed still enforced by the building network as assumed — verify this hasn't changed, since the whole router choice depends on this constraint being real.

SILENT FAILURE:
5. LAN coming up on a different IP after a revert-and-manual-restore (human error during the 30s recovery) would silently break every hardcoded-IP reference in the system — verify recovery restores the EXACT expected IP, and there's a way to confirm this quickly.
6. This is called a 'Hard V1.0 dependency — without it the LAN does not come up' — verify there's a monitoring/alert path if the router itself fails or drops offline, since its failure is total, not partial.

**Verification Method:**  
1) Network test: confirm NAT, static IP binding, SPI firewall active. 2) Power-cycle recovery drill: physically power-cycle the router, trigger the known IP-reversion issue, execute the documented 30s touchscreen restore, confirm the LAN returns to the exact expected IP. 3) Backup-restore drill: restore router config from the FAT32 USB backup, confirm it actually works, not just that the backup file exists. 4) Router-failure alerting: confirm there's a monitoring signal if the router itself goes offline. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
Prior docs used informal HW-00X numbering that collides across documents; this HW-007 is the canonical registry ID for the router — not previously in the HW-001..006 series despite being a hard V1.0 dependency.

**Open Questions:**  
FLAGGED OUT OF DATE by Nick, specifics TBD. Confirm: ER605 V2 still live? Static IP/MAC-binding workaround, power-cycle/Cox quirk still accurate?

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/ER605-V2-Gateway-Router-building-MAC-binding-solution-3cfe152fc19981cba471d920cf527581_

---
## HW-008 — UPS for Core Stack (APC BE600M1, graceful-shutdown + emergency-print trigger)
**Status:** Deployed | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: a power outage doesn't take down the core system mid-service — enough runtime to shut down safely or trigger the emergency print, not just an abrupt kill.

**Functional Requirement Specification:**  
APC BE600M1 (600VA/330W) UPS on the core stack (N100 + ER605 + switch + z33 + printer) with USB monitoring to the N100 so apcupsd can (a) fire the emergency-print path on the ONBATTERY event and (b) initiate graceful shutdown on extended outage. In hand, QA-passed (serial 0B2606L08078). Lighter than the originally-spec'd 1500VA but adequate for the measured ~43W idle stack load (~30-40 min idle runtime). Replacement battery: APCRBC154.

**Acceptance Criteria:**  
NORMAL:
1. UPS holds the core stack (N100+ER605+switch+z33+printer) through a real power outage, USB-monitored so apcupsd fires the emergency-print path on ONBATTERY and initiates graceful shutdown on extended outage.

EDGE:
2. A very brief outage (power blips for 1-2 seconds) does not trigger a full emergency-print + shutdown sequence if that would be more disruptive than riding it out — verify thresholds are deliberately tuned.
3. Runtime under actual measured ~43W idle load matches the claimed 30-40 min window — verify with a real timed discharge test, not just the datasheet math.

NEGATIVE:
4. A UPS at reduced battery health (aging, not the tested-fresh unit) is caught by a periodic health check, not just trusted forever based on the initial QA pass.

SILENT FAILURE:
5. USB monitoring link between UPS and N100 failing (cable issue, driver issue) would mean apcupsd never sees the ONBATTERY event at all — verify this monitoring link itself is health-checked, since its failure defeats the entire UPS's software-triggered behaviors (though raw power backup still works).
6. Graceful shutdown triggering too late (battery nearly depleted before shutdown starts) would risk an unclean shutdown anyway — verify the extended-outage threshold leaves adequate margin under real measured runtime, not the optimistic datasheet number.

**Verification Method:**  
1) Real power-down test: pull wall power, confirm ONBATTERY event fires, emergency-print triggers, extended-outage graceful shutdown triggers with correct timing. 2) Runtime-measurement test: timed discharge test under actual measured idle load, confirm real runtime matches the 30-40 min claim. 3) USB-monitoring health check: verify the UPS→N100 monitoring link is itself checked periodically, not assumed permanently working. 4) Battery-health check: periodic UPS self-test/health check beyond the initial QA pass. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Dependency Notes:**  
Required by EPR-001..007 architecture. Prior docs numbered this hardware "HW-002" informally — collides with the registry's actual INFRA 3 (21.5" touchscreen); INFRA 9 is the canonical ID.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/UPS-for-Core-Stack-APC-BE600M1-graceful-shutdown-emergency-print-trigger-3cfe152fc19981fea69ad5fa36a6a5e2_

---
## HW-009 — Star TSP143IIIU Thermal Receipt Printer (emergency print hardware)
**Status:** Deployed | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: dedicated hardware that can physically print the emergency packout strip during a power loss, wired correctly so it actually works when needed.

**Functional Requirement Specification:**  
Star Micronics TSP143IIIU (TSP100III family) thermal receipt printer, USB-direct to the N100 (no LAN IP; occupies one of the N100's two USB ports). Prints the emergency ops-truth packout strip on power loss. IMPLEMENTATION CORRECTION (contractor brief v0.7.0): image printing uses the StarTSPImage library → native Star Graphic Mode raster → /dev/usb/lp1 directly. CUPS is installed and makes the queue LAN-reachable, but lp/lpr must NOT be used for the image path (produces incorrect scaling — confirmed wasted debugging). 576px-wide output, auto-cut. Confirmed working end-to-end with a real power-down test.

**Acceptance Criteria:**  
Emergency receipt prints from a single command on the N100 and when triggered by the apcupsd ONBATTERY hook; auto-cut fires; StarTSPImage path used, not lp/lpr.

**Dependency Notes:**  
HEALTH 10 corrected 2026-09-02 to match this row's printer path.

**Verification Method:**
1. [AUTO] Path: single command on N100 prints the emergency strip via StarTSPImage → /dev/usb/lp1, not lp/lpr. Evidence: test print + code-search.
2. [AUTO] Hook: apcupsd ONBATTERY hook triggers the print. Evidence: log.
3. [NICK] Live: Nick runs a real power-down test → receipt prints with auto-cut. Evidence: photo + observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Star-TSP143IIIU-Thermal-Receipt-Printer-emergency-print-hardware-3cfe152fc19981759cf8e0a67a2d0e9a_
