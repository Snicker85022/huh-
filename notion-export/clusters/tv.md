# Taza OS URS — TV cluster
_Exported: 2026-09-19 21:35 | 9 rows_
_Source: Notion Master URS & Specification Registry_

---
## TV-001 — Wake-on-LAN + auto dashboard launch
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: all kitchen TVs wake at 6am to their assigned dashboard via WoL, sleep at 11pm, zero manual remote use.

**Functional Requirement Specification:**  
Wake-on-LAN + auto dashboard launch: N100 wakes all three TVs at 6:00 AM via WoL, opens each to its assigned dashboard URL via ADB after a boot delay, and sleeps them at 11:00 PM. Zero manual remote interaction required for the daily cycle.

**Failure Behavior:**  
Fallback: manual remote power-on each morning.

**Acceptance Criteria:**  
NORMAL:
1. At 6:00 AM, all three TVs wake via WoL and open to their assigned dashboard URL after boot delay, with zero manual remote interaction.
2. At 11:00 PM, all three TVs sleep automatically.

EDGE:
3. A TV that's already awake at 6:00 AM (didn't fully sleep the prior night) still ends up on the correct dashboard URL, not left on whatever it was showing.
4. Boot delay is long enough that the ADB dashboard-open command never fires before the TV's OS is actually ready to receive it — verify against slowest real observed boot time, not best-case.

NEGATIVE:
5. A TV that fails to wake via WoL (network issue, TV powered off at the wall) is detectable — doesn't fail silently with no signal that the daily cycle didn't complete for that TV.

SILENT FAILURE:
6. WoL packet sent successfully but the TV doesn't actually wake (missed) must not be indistinguishable from 'working correctly' — needs a way to confirm actual wake state, not just packet-sent confirmation.
7. ADB dashboard-launch command sent but silently fails (TV awake, wrong app in foreground) must be caught — verify there's a check that the correct URL is actually displaying, not just that the command was issued.

**Verification Method:**  
1) Scheduled-job tests: WoL fires at 6:00 AM, sleep fires at 11:00 PM, across multiple real days not just one. 2) Failure-detection test: simulate a TV that doesn't wake, confirm this is detected and alerted rather than silent. 3) State-verification test: after ADB dashboard-launch, confirm (via screenshot capture or DOM check) the correct URL is actually foregrounded, not just that the command was sent. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Wake-on-LAN-auto-dashboard-launch-3cfe152fc1998109bf76d3eab8b9cc3a_

---
## TV-002 — Network presence monitoring
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: SMS alert naming the specific TV if it goes unreachable for 5 min, auto-resolving on recovery.

**Functional Requirement Specification:**  
Network presence monitoring: N100 pings each TV IP every 60 seconds. If a TV is unreachable for >5 consecutive pings (5 minutes), an SMS alert fires naming the TV. Alert auto-resolves when ping resumes. Prevents silent display failures during active events.

**Failure Behavior:**  
Fallback: manual visual check each morning.

**Acceptance Criteria:**  
NORMAL:
1. TV unreachable for 5 consecutive pings (5 min) → SMS alert fires naming the specific TV.
2. Ping resumes → alert auto-resolves.

EDGE:
3. A TV that flaps (goes down for 4 pings, comes back, goes down again) does not fire a false-negative — verify the consecutive-ping counter resets correctly and doesn't accidentally suppress a real outage.
4. Two or three TVs going down simultaneously (e.g. shared network segment failure) sends distinct, identifiable alerts for each, not one ambiguous alert.

NEGATIVE:
5. A single missed ping (not 5 consecutive) does not fire a false alarm.

SILENT FAILURE:
6. If the SMS delivery itself fails (Twilio down, bad number), the outage must not go unreported — verify a fallback or at minimum a logged failure Nick can find, not silent non-delivery.
7. Auto-resolve firing incorrectly (TV still actually down, ping happens to succeed once due to a fluke) would mask a real ongoing problem — verify auto-resolve requires sustained recovery, not a single successful ping.

**Verification Method:**  
1) Unit tests: 5-consecutive-miss triggers alert, single miss does not, ping-resume auto-resolves. 2) Flap test: simulate intermittent connectivity, confirm the counter logic doesn't mask or falsely suppress a real outage. 3) Multi-TV-failure test: simultaneous outage on 2-3 TVs produces distinct per-TV alerts. 4) Delivery-failure test: simulate SMS send failure, confirm the outage is still logged/discoverable. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Network-presence-monitoring-3cfe152fc199814e8a64cd6fb0fbdbf1_

---
## TV-003 — Google Home voice navigation (content switching)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: switch TV content via voice ("show tomorrow's event", "allergen board", "good morning", "end of day") — no remote or screen touch.

**Functional Requirement Specification:**  
Google Home voice navigation for content switching: all three TVs enrolled in Google Home with Routines configured to Taza operational vocabulary ("show tomorrow's event", "show tonight's crew", "show prep list", "allergen board", "good morning" wakes all three, "end of day" switches to summary then sleeps). Zero code required — Routines only.

**Failure Behavior:**  
Fallback: manual URL navigation via TV remote.

**Acceptance Criteria:**  
NORMAL:
1. Each documented voice command ("show tomorrow's event", "show tonight's crew", "show prep list", "allergen board") switches the correct TV(s) to the correct content.
2. "good morning" wakes all three TVs; "end of day" switches to summary then sleeps.

EDGE:
3. Commands issued while a TV is already showing the requested content are a harmless no-op, not an error or a jarring re-render.
4. Overlapping/near-simultaneous commands to different TVs (e.g. two crew members speaking to different Google Home devices at once) don't cross-wire and switch the wrong TV.

NEGATIVE:
5. An unrecognized phrase close to but not matching the defined vocabulary does not trigger the wrong command — verify near-miss phrases fail to match rather than fuzzy-matching to something unintended.

SILENT FAILURE:
6. A Routine that silently stops working (Google account issue, Routine accidentally edited/deleted) must be detectable — since this is 'zero code, Routines only,' there's no application-level error handling; verify there's still SOME way to notice it's broken (periodic manual check, or a monitoring proxy).
7. "end of day" firing the summary-then-sleep sequence but the sleep step silently failing (TV stuck on summary all night) should be caught by existing display monitoring (DISPLAY 15), not assumed to just work because this row says it should.

**Verification Method:**  
1) Manual voice test: speak each defined command phrase, confirm correct TV(s) and content switch. 2) Near-miss phrase test: speak close-but-wrong phrases, confirm no unintended command fires. 3) Concurrency test: near-simultaneous commands to different TVs, confirm no cross-wiring. 4) Periodic Routine-health check: since this has no code-level error handling, establish a recurring manual or monitored check that the Routines still exist and function (weekly, tied into an existing ops checklist). 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Google-Home-voice-navigation-content-switching-3cfe152fc19981599555f6c095308d3c_

---
## TV-004 — Emergency fallback static page
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TVs auto-load a local fallback page (last-known event details, allergens, emergency contacts) if N100 goes down — critical info stays visible.

**Functional Requirement Specification:**  
Emergency fallback static page: a static HTML file pushed to each TV's local storage via ADB, containing last-known event details, allergen protocols, and emergency contacts. A watchdog detects N100 serving failure and ADB-commands all TVs to load the local fallback, matching the Taza visual design system.

**Failure Behavior:**  
Fallback: blank TV screens during N100 outage (ops via phones).

**Acceptance Criteria:**  
NORMAL:
1. N100 serving failure detected → watchdog ADB-commands all TVs to load the local fallback page showing last-known event details, allergen protocols, and emergency contacts.

EDGE:
2. Fallback page content (event details, allergens, contacts) is actually current as of the last successful push before failure, not a permanently stale hardcoded snapshot from install time.
3. Multiple TVs failing over at slightly different times (staggered detection) all end up on the fallback consistently, not some on fallback and some stuck on a broken live view.

NEGATIVE:
4. A transient N100 blip (recovers within seconds) does not trigger a full failover-and-recovery cycle if that would be more disruptive than briefly stale live data — verify the failure threshold is deliberately tuned, not hair-trigger.

SILENT FAILURE:
5. The watchdog itself failing (not just N100) would mean no failover happens on a real outage — verify the watchdog's own health is monitored, this can't be a single point of failure with no backup signal.
6. Fallback page silently going stale (allergen protocol changed since last push, but TV stuck on old fallback for an extended real outage) is a food-safety risk — verify there's a maximum acceptable staleness or a way to detect and flag it.

**Verification Method:**  
1) Failover test: kill N100 serving, confirm watchdog detects and ADB-commands all TVs to fallback within the defined threshold. 2) Content-freshness test: confirm fallback content reflects the actual last-known-good state, not a stale install-time snapshot. 3) Watchdog-health test: simulate the watchdog process itself failing, confirm this is detectable (secondary monitoring or alert). 4) Multi-TV staggered-failure test. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Emergency-fallback-static-page-3cfe152fc19981568af8f1abf1ccf654_

---
## TV-005 — TTS audio alerts via TV speakers
**Status:**  | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: high-priority alerts (allergen, departure, timer) spoken through nearest TV speakers via TTS — Sandra hears it even when not looking at any screen.

**Functional Requirement Specification:**  
TTS audio alerts via TV speakers: an ADB shell TTS command fires on the nearest TV for high-priority alerts — allergen field populated (immediate, highest priority), departure countdown, and configurable timer completion. Audio supplements the visual dashboard alert so Sandra hears it even when not looking at any screen.

**Acceptance Criteria:**  
TTS alert fires within 10s of trigger; audible at Sandra's primary work position under normal kitchen ambient noise; allergen alert fires on every population; departure alert fires at configured countdown

**Open Questions:**  
OVERLAP: same alert conditions (allergen/departure/timer) as ALEXA 4, both may fire on Insignia's speakers. Intentional redundancy or conflict? Reconcile in debate.

**Verification Method:**
1. [AUTO] Latency: trigger allergen flag → TTS fires ≤10s. Evidence: log timestamp.
2. [AUTO] Coverage: allergen population fires every time; departure countdown fires at configured time. Evidence: test log.
3. [NICK] Live: Sandra hears the alert at her primary work position under normal kitchen ambient noise. Evidence: observation log.
4. [NICK] Overlap: confirm TTS and Alexa ([[SPEC:ALC-004]]) both firing on the Insignia is not a conflict. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/TTS-audio-alerts-via-TV-speakers-3cfe152fc19981a7a19bd804bebc2c8f_

---
## TV-006 — Dynamic content mode switching
**Status:**  | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: each TV switches instantly between content modes (dashboard, QC ref, training SOP, ambient brand) driven by schedule, event state, or voice — no reload delay.

**Functional Requirement Specification:**  
Dynamic content mode switching: each TV serves multiple content modes — operational dashboard, QC reference library, crew training SOP, ambient brand display — switched by time-of-day schedule, event state change, or voice command. Mode definitions stored in NocoDB; switching is instant (URL navigation, no reload delay).

**Failure Behavior:**  
Fallback: manual URL navigation for mode changes.

**Acceptance Criteria:**  
Mode switches complete in <2s; schedule-based switching fires within 60s of trigger time; event-state switching fires within 30s of NocoDB write; ambient mode activates within 5 min of event close

**Verification Method:**
1. [AUTO] Latency: mode switch completes <2s. Evidence: timing log.
2. [AUTO] Schedule: fires within 60s of trigger time. Evidence: log.
3. [AUTO] Event-state: fires within 30s of the NocoDB write. Evidence: log.
4. [NICK] Live: Nick switches a mode by voice. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Dynamic-content-mode-switching-3cfe152fc19981759135e4e7e307139a_

---
## TV-007 — TV watchdog + Chrome auto-relaunch
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV browser watched + auto-relaunched on crash/background; health (CPU/mem/Chrome state/URL) reported to N100 every 60s.

**Functional Requirement Specification:**  
TV watchdog + Chrome auto-relaunch: a lightweight sideloaded APK monitors Chrome's process state every 30s and relaunches it to the last known URL if crashed or backgrounded. Reports TV health (CPU, memory, Chrome state, current URL) to N100 every 60s for viewing without touching the TVs.

**Failure Behavior:**  
Fallback: manual Chrome relaunch via ADB when [[SPEC:TV-002]] alerts.

**Acceptance Criteria:**  
Chrome crash on any TV triggers auto-relaunch within 45s; health reports visible in NocoDB with TV name/CPU/memory/state/URL/timestamp; APK survives TV reboot

**Verification Method:**
1. [AUTO] Crash drill: kill Chrome → auto-relaunch ≤45s. Evidence: log.
2. [AUTO] Health: NocoDB shows TV name/CPU/mem/state/URL/timestamp every 60s. Evidence: query.
3. [AUTO] Reboot: reboot the TV → APK survives and resumes. Evidence: log.
4. [NICK] Live: Nick reads TV health in NocoDB without touching the TV. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/TV-watchdog-Chrome-auto-relaunch-3cfe152fc199816e9971fc6675b39abb_

---
## TV-011 — Google Assistant Local Fulfillment
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV voice commands resolve locally on LAN <1s (fallback to cloud if N100 unreachable) — works without internet.

**Functional Requirement Specification:**  
Google Assistant Local Fulfillment: N100 registers as a local smart home fulfillment endpoint so voice commands to the TVs resolve directly on the LAN (<1s) instead of round-tripping to Google's cloud, with automatic fallback to cloud Routines (DISPLAY 16) if N100 is unreachable. Works without internet on LAN.

**Failure Behavior:**  
Fallback: Google Home cloud Routines only ([[SPEC:TV-003]], 2-4s, internet-dependent).

**Acceptance Criteria:**  
NORMAL:
1. Voice command to a TV resolves locally on the LAN in under 1 second when N100 is reachable.
2. N100 unreachable → automatic fallback to cloud Routines (DISPLAY 16), command still works (just not local-speed).

EDGE:
3. N100 goes down mid-command (command sent, then N100 drops before resolving) — command still completes via fallback, not lost.
4. N100 recovers — subsequent commands correctly resume using local fulfillment, not stuck on cloud fallback until a manual reset.

NEGATIVE:
5. A command issued with no internet AND N100 down (total connectivity loss) fails gracefully with no response, rather than hanging indefinitely or crashing the Google Home integration.

SILENT FAILURE:
6. Fallback to cloud Routines happening silently and consistently (N100 local fulfillment quietly broken but always falling back) would defeat the whole point of this row (sub-1s local resolution) without anyone noticing — verify there's a way to detect 'always falling back' as distinct from 'working locally, occasionally falling back.'
7. The <1s local-resolution claim must be verified under real LAN conditions during active kitchen use (network congestion from other traffic), not just an idle-network benchmark.

**Verification Method:**  
1) Latency test: measure actual local-fulfillment response time under real LAN conditions during simulated kitchen load. 2) Failover test: kill N100 mid-command and after, confirm fallback engages both times without losing the command. 3) Recovery test: restore N100, confirm subsequent commands resume local fulfillment rather than staying on cloud fallback. 4) Fallback-frequency monitoring: log which path (local vs. cloud) served each command, so a silently-always-falling-back state is detectable, not invisible. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Google-Assistant-Local-Fulfillment-3cfe152fc199818ab0cdfd6391809a47_

---
## TV-012 — TV dashboard PWA via self-owned domain
**Status:**  | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Need: TV dashboards as PWAs with local state caching — show last-known state during brief N100 outage instead of blank, auto-reconnect on recovery. Replaces need for [[SPEC:TV-007]] watchdog APK.

**Functional Requirement Specification:**  
TV dashboard PWA via self-owned domain: all three TV dashboards served as Progressive Web Apps in full-screen kiosk mode with local state caching (shows last-known state instead of a blank screen during an N100 outage), WebSocket push per INFRA 18, and automatic reconnection — replacing the need for the separate DISPLAY 18 watchdog APK, since the PWA handles its own resilience.

**Failure Behavior:**  
Fallback: ADB-launched Chrome tab per [[SPEC:TV-001]] (functional but no offline cache/PWA resilience).

**Acceptance Criteria:**  
NORMAL:
1. All three dashboards run as installed PWAs in full-screen kiosk mode, receiving WebSocket push updates and reflecting state changes live.
2. On N100 outage, each dashboard shows its last-known state instead of a blank/error screen.

EDGE:
3. Reconnection after a brief N100 blip (seconds) is seamless — no visible flash-to-blank before recovering.
4. Reconnection after an extended outage (minutes+) correctly reconciles to current state, not stuck replaying a stale cached state indefinitely.
5. A TV rebooted mid-outage relaunches into the PWA and correctly shows last-known-state on its own, without manual relaunch.

NEGATIVE:
6. A malformed or partial WebSocket push does not corrupt the locally cached last-known state — bad data in doesn't overwrite good cached data.

SILENT FAILURE:
7. A dashboard showing last-known state during an outage must be visibly marked as stale/disconnected — never presented identically to a live, current dashboard (crew needs to know it's not real-time).
8. Reconnection succeeding at the transport level but failing to actually resync full state (partial resync) must be detectable, not silently leave the dashboard subtly wrong.

**Verification Method:**  
1) Outage simulation: kill N100 connectivity, confirm dashboards show last-known state with a visible stale/disconnected indicator, not a blank screen and not an unmarked live-looking view. 2) Recovery test: restore connectivity after short and long outages, confirm full and correct resync in both cases. 3) Reboot-during-outage test: power-cycle a TV while N100 is down, confirm it self-recovers to last-known state on relaunch. 4) Malformed-payload test: inject a corrupt WebSocket push, confirm cached state is not corrupted. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/TV-dashboard-PWA-via-self-owned-domain-3cfe152fc1998131a20cfe3d0d1a3223_
