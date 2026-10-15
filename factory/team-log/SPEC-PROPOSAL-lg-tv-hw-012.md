SPEC PROPOSAL: HW-012 — LG webOS TV (kitchen checklist display, hardware + control surface)
================================================================================

Proposed: 2026-10-15 / deep (ARCHITECT — spec_id, dependencies, integration)
Purpose:  PROPOSE ONLY. Nothing written to any database.
Scope:    THIS ROW IS THE DEVICE. The checklist-display feature is a separate
          spec (proposed URS-DISP-007, team-log/SPEC-PROPOSAL-checklist-on-lg-tv.md)
          which will CONSUME this row. No content/layout/staleness/status-feed
          decisions belong here.

================================================================================
SPEC-ID DECISION
================================================================================

spec_id: HW-012

Why (verified against the LIVE spec table, 2026-10-15):
  - HW family runs HW-001..HW-011. HW-012 is the next free id.
  - No existing row names LG, webOS, or OLED (0 rows). No duplicate.
  - House style: HW-004 (TV cluster) gives domain/record_type/determinism_class/
    priority/release; HW-010/HW-011 give the hw_* column style.

Verified facts (probed from n100 on 2026-10-15; treated as given, not re-derived):
  - Model: "[LG] webOS TV OLED55B7A" (TV's own UPnP friendlyName); 55-inch OLED;
    model year 2022; OS webOS 22 (webOS 7.0).
  - Wired: 192.168.2.127, MAC 78:5d:c8:00:82:0b (Ethernet PRIMARY). Wi-Fi:
    192.168.2.137 (fallback ONLY).
  - Control: SSAP (lge-com:service:webos-second-screen) over WebSocket, port 3000,
    HTTP/1.1 101 upgrade. Same protocol as the LG phone app.
  - Auth: one paired client-key, accepted on-screen by Nick. Key file lives at
    /home/taza/repo/secrets/lg_tv.json ON N100 (verified present, mode 0600),
    never in the repo and never in this spec row.
  - Verified capabilities: listLaunchPoints (30 apps); getForegroundAppInfo -> appId;
    system.launcher/launch com.webos.app.browser with params.target=URL (returnValue:true,
    Nick saw the page); tvpower/power/getPowerState -> state=Active.
  - Proven heal: getForegroundAppInfo -> if appId != com.webos.app.browser, re-issue
    system.launcher/launch. This is the ONLY heal; do not spec turnOnScreen.

================================================================================
FULL ROW
================================================================================

spec_id:              HW-012
name:                 LG webOS TV OLED55B7A (kitchen checklist display)
record_type:          Atomic Requirement
domain:               System Infrastructure
determinism_class:    HUM
required_for_release: NO          (proposed; see Q1)
priority:             P1
release:              V1.0
status:               Spec Drafted

----------------------------------------------------------------------
user_requirement:
Need: a dedicated kitchen display panel — an LG webOS OLED TV — that the system
can reach and control over the LAN without anyone touching it, so the checklist
(and later displays) can be shown on it remotely.

----------------------------------------------------------------------
functional_requirement:
DEVICE IDENTITY: LG webOS TV OLED55B7A, 55-inch OLED (from model number), model
year 2022, OS webOS 22 (webOS 7.0). FriendlyName "[LG] webOS TV OLED55B7A".

PLACEMENT / ROLE: the dedicated kitchen checklist display panel. Wired Ethernet
192.168.2.127 (MAC 78:5d:c8:00:82:0b) is the PRIMARY path; Wi-Fi 192.168.2.137
is fallback ONLY, and running on Wi-Fi must raise an alert (never silent).

CONTROL SURFACE: SSAP (lge-com:service:webos-second-screen) over WebSocket on
TCP 3000 (HTTP/1.1 101 upgrade). Authenticated by one paired client-key, issued
after an on-screen accept by Nick; key file /home/taza/repo/secrets/lg_tv.json
on n100 only. Never in the repo, never in this row.

VERIFIED WORKING (probe 2026-10-15):
  - Launch a page: ssap://system.launcher/launch {id:"com.webos.app.browser",
    params:{target:"<url>"}} -> returnValue:true. Nick saw the page appear.
  - Read foreground app: ssap://com.webos.applicationManager/getForegroundAppInfo
    -> {"appId":"com.webos.app.browser"}.
  - Power state: ssap://com.webos.service.tvpower/power/getPowerState ->
    {"state":"Active"}.
  - App inventory: ssap://com.webos.applicationManager/listLaunchPoints -> 30 apps.

NOT AVAILABLE (explicit constraints a later spec must not assume):
  - No ADB: port 5555 closed (webOS is not Android).
  - No Developer Mode: SSH 9922 closed, so ares-cli is unavailable.
  - CDP 9998 answers but lists NO targets (an inspector, not a launcher).
  - No wake-on-LAN endpoint over SSAP (404).
  - turnOnScreen/turnOffScreen EXIST (401, not 404) but the permission name is
    unknown (12 spellings tried, all 401). Do NOT spec a dependency on it; the
    proven heal is re-issuing the launch.
  - Screensaver dims the panel but does NOT kill the browser: content survives
    and getForegroundAppInfo still reports the browser. Nick disabled "turn off
    after 2 hours" and enabled "Mobile TV On" on the device.

----------------------------------------------------------------------
failure_behavior:
- TV unreachable or browser not foreground: detect via getForegroundAppInfo; heal
  by re-issuing system.launcher/launch. Never assume screen-wake.
- Active path is Wi-Fi (.137) instead of Ethernet (.127): raise an alert naming
  the fallback (fallback is fail-visible, never a silent state).
- Pairing lost (factory reset or cleared paired-client list): SSAP auth fails; the
  controller raises an alert naming the on-screen re-pair step rather than
  silently retrying a dead pairing.
- This device has NO local fallback page (TV-004 requires ADB); its outage surface
  is paper + kanban, and the consuming checklist spec owns that degradation.

----------------------------------------------------------------------
dependency_notes:
- DOES NOT inherit [[SPEC:TV-007]] (TV watchdog + Chrome auto-relaunch): TV-007 is
  the Android fleet via ADB. This panel is webOS with NO ADB. [[SPEC:TV-004]]
  (ADB-pushed local fallback) is also inapplicable.
- [[SPEC:TV-002]] (N100 pings each TV IP every 60s, alert after 5 misses) DOES apply
  at the network-presence level (it is just ICMP to the IP).
- Control surface == the LG phone app protocol (SSAP over WebSocket :3000).
- Consumes network: [[SPEC:HW-005]] (kitchen Ethernet switching/cabling) for the
  wired primary path.

----------------------------------------------------------------------
open_questions:
- Q-identity: friendlyName says OLED55B7A (an older LG panel name) while webOS 22
  implies a 2022 model. Confirm the model year on the device label.
- Q-reachability: is the reachability signal TV-002 ping alone, or ping + SSAP
  getPowerState/getForegroundAppInfo liveness, or both? (Proposed: both.)
- Q-wifi-alert: which channel should the Wi-Fi-fallback alert use (proposed: same
  ntfy "taza-ops" + health page as the consuming checklist spec)?
- Q-screen-wake: confirm turnOnScreen stays permanently out of scope (per the
  2026-10-15 decision recorded in lg_tv.json) or pursue the permission name later.
- Q-release: required_for_release NO vs YES (proposed NO — additive; paper + kanban
  stay the safety net).

----------------------------------------------------------------------
ac_normal:
SSAP over WebSocket :3000 from n100 proves control: launching com.webos.app.browser
with a target URL returns returnValue:true and Nick sees the page; getForegroundAppInfo
reports appId=com.webos.app.browser; getPowerState reports state=Active.

ac_edge:
Ethernet to 192.168.2.127 drops — the TV falls back to Wi-Fi (.137) and an alert fires
naming the fallback; when Ethernet returns, the controller uses the wired path again
with no manual step.

ac_negative:
Any dependency on ADB (5555), ares-cli / Developer Mode (9922), CDP-as-launcher (9998),
or SSAP turnOnScreen -> BLOCKED. These are proven unavailable on this device; re-issuing
the launch is the only heal.

ac_silent_failure:
Controller believes the page is up while the TV shows something else (launch silently
rejected, or foreground app changed) -> detected when getForegroundAppInfo returns
appId != com.webos.app.browser, then healed by re-issuing the launch.

ac_challenge:
After a factory reset or clearing the paired-client list, SSAP auth fails -> the
controller detects the auth failure and raises an alert naming the on-screen re-pair
step, never silently retrying a dead pairing.

ac_block:
(empty)

----------------------------------------------------------------------
verification_methods:
1) [AUTO] SSAP launch + read + power from n100 against 192.168.2.127:3000.
   Evidence: grep "SSAP_LAUNCH\|returnValue:true\|appId.*com.webos.app.browser\|\"state\":\"Active\"" /var/log/taza/lg-tv-control.log | tail -6
   (expect launch returnValue:true, appId=com.webos.app.browser, state=Active)
2) [AUTO] Control code has zero forbidden-dependency usage.
   Evidence: grep -rn "5555\|9922\|ares-cli\|devMode\|turnOnScreen" product/ --include="*.py" --include="*.sh" --include="*.ts" | grep -v "^[^:]*:[^:]*: *#"
   (expect zero hits in executable paths)
3) [AUTO] Wired-primary enforcement: .127 is primary; any active .137 raises an alert.
   Evidence: grep "LG_TV_WIFI_FALLBACK\|LG_TV_ACTIVE_IFACE" /var/log/taza/lg-tv-control.log | tail -3
   (expect .127 wired primary; .137 active -> alert line present)
4) [NICK] On-screen: Nick sees the launched page on the TV after a fresh launch.

vm_count:      4
vm_auto_count: 3
vm_nick_count: 1

----------------------------------------------------------------------
consumes:    HW-005
consumed_by: URS-DISP-007 (proposed — checklist-display spec consumes this device)

maintenance_requirements:
- Keep the paired client-key only at /home/taza/repo/secrets/lg_tv.json on n100;
  never commit it, never inline it.
- Factory reset or clearing the paired-client list breaks pairing -> re-pair
  on-screen and replace the key file.
- IPs are DHCP-reserved; if the reservation changes, update the controller's
  wired-primary config (and the Wi-Fi reservation if ever used).

external_dependencies:
- The LG SSAP service on the TV (webOS); no cloud dependency.
- n100 LAN reachability to 192.168.2.127:3000.

hw_make:           LG
hw_model:          OLED55B7A
hw_mpn:            OLED55B7A (no suffix verified; friendlyName is "webOS TV OLED55B7A")
hw_connectivity:   Ethernet RJ45 primary (192.168.2.127), Wi-Fi fallback only (192.168.2.137);
                   control via SSAP over WebSocket TCP 3000
hw_purchase_date:  (unverified — device pre-exists deployment records)
hw_purchase_source:(unverified)

================================================================================
SEAMS THIS ROW HANDS OFF (named now; a later spec consumes them)
================================================================================

S1 (device -> checklist-display spec): the consuming spec gets the device identity
   and the VERIFIED control surface only (launch / read-foreground / power-state /
   app-inventory) plus the hard constraints (no ADB / DevMode / CDP-as-launcher /
   screen-wake; Wi-Fi fallback must alert; re-issue launch is the sole heal). It
   gets NOTHING about content, layout, staleness thresholds, or status feeds.

S2 (reachability): how an app on n100 learns the TV is reachable, and what it does
   when it is not. Proposed split: TV-002 ping presence (network level, reusable)
   + SSAP getPowerState/getForegroundAppInfo liveness (control-surface level).
   When not reachable: alert, then re-issue launch on recovery.

S3 (Android/TV relationship): TV-007 (watchdog + Chrome auto-relaunch) and TV-004
   (ADB local fallback) are Android-via-ADB and do NOT apply to this webOS panel.
   Stated explicitly so nobody applies TV-007/004 to HW-012 by mistake. TV-002
   (ping presence) is the one TV-* spec that carries over.

================================================================================
OPEN QUESTIONS FOR NICK (decide, in impact order)
================================================================================
Q1: required_for_release — confirm NO (additive; paper + kanban stay the safety net)?
Q2: Reachability signal — ping alone (TV-002), SSAP liveness alone, or both (proposed)?
Q3: Wi-Fi-fallback alert channel — ntfy "taza-ops" + http://192.168.2.102:9000 health
    page (match the consuming checklist spec), or something else?
Q4: turnOnScreen — keep permanently out of scope (per the recorded decision), or
    authorize later research into the permission name?
Q5: Model year — accept "2022 / webOS 22" as given, or confirm the panel label first
    (friendlyName "OLED55B7A" is an older LG panel name)?
