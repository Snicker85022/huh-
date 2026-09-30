# Taza OS URS — EMERGENCY-PRINT cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## EPR-001 — Emergency print path
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: if power goes out, the kitchen still gets a printed copy of what's left to do — no dependency on screens or network.

**Functional Requirement Specification:**  
Emergency print path. The N100 must be able to print the current operational truth (remaining packout items + open tasks) to the owned Star TSP143IIIU (USB) thermal printer during a power outage. Image path: StarTSPImage → native Star Graphic Mode raster → /dev/usb/lp1 directly (CUPS installed for LAN reachability only, not the image path — lp/lpr produces incorrect scaling). Print templates designed for 80mm width (~42 ch/line; checkbox per van/category; auto-cut).

**Acceptance Criteria:**
NORMAL: N100 prints current ops truth (remaining packout + open tasks) to the Star TSP143IIIU via /dev/usb/lp1 during a power outage.
EDGE: 80mm template, ~42 ch/line, checkbox per van/category, auto-cut.
NEGATIVE: lp/lpr used as the image path → BLOCKED (incorrect scaling; native Star Graphic Mode only).
SILENT-FAILURE: printer offline at the moment of outage → caught by event-start pre-flight print check.
CHALLENGE: pull power during an active-event dataset → full packet prints within the UPS runtime window.
**Verification Method:**
1. [AUTO] Path: prints via /dev/usb/lp1 native Graphic Mode, not lp/lpr. Evidence: code-search + test print.
2. [AUTO] Template: output at 80mm, correct scaling. Evidence: test print photo + measurement.
3. [AUTO] Pre-flight: printer-online check at event start. Evidence: log.
4. [NICK] Live: Nick pulls power during an active event → packet prints. Evidence: photo + observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Emergency-print-path-3cfe152fc199811c867afe4d366c99e8_

---
## EPR-002 — Phased screen-shed procedure
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: when power fails, crew finishes what's already cooking safely, gets the printed status, and the important stuff stays powered — no scramble, no guessing what to do.

**Functional Requirement Specification:**  
Phased screen-shed procedure. On outage: (1) finish in-progress cooking/packing task safely (~8 min); (2) print ops truth from N100; (3) shed TVs; (4) preserve N100 + ER605 + switch + z33 + one MicroTouch as long as feasible. Convenience Wi-Fi AP unplugged at T+0 (phone keeps broadcasting if needed).

**Acceptance Criteria:**
NORMAL: on outage: (1) finish in-progress cooking/packing ~8min, (2) print ops truth, (3) shed TVs, (4) preserve N100+ER605+switch+z33+one MicroTouch.
EDGE: convenience Wi-Fi AP unplugged at T+0.
NEGATIVE: crew scrambles or guesses the sequence → impossible (printed procedure at station).
SILENT-FAILURE: procedure missing or outdated → caught by periodic outage drill.
CHALLENGE: full outage drill → crew follows all four phases without prompting.
**Verification Method:**
1. [NICK] Live: outage drill → crew completes all 4 phases in order. Evidence: observation log + photos.
2. [AUTO] Procedure: printed checklist present at the station. Evidence: photo.
3. [NICK] Cadence: quarterly drill logged. Evidence: log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Phased-screen-shed-procedure-3cfe152fc19981f5b456cbe93d2077f2_

---
## EPR-003 — N100-priority power
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: whatever else goes dark in an outage, the brain (N100 + router + switch) stays up longest — everything else depends on it.

**Functional Requirement Specification:**  
N100-priority power, two-UPS allocation (Nick 2026-10-01). UPS 1 (existing APC BE600M1): N100 + ER605 router + 8-port switch — the 'brain', longest runtime. UPS 2 (new APC BE600M1): Alexa TV (Insignia), TCL1 (East), MT1 (East), 5-port switch — smart-dimming + graceful shutdown, ~65 min runtime. West Wall (MT2 + West Google TV) accepts no backup power ([[SPEC:EPR-004]]).

**Acceptance Criteria:**
NORMAL: N100 + ER605 + 8-port switch stay powered longest on UPS.
EDGE: other devices may go dark.
NEGATIVE: UPS capacity spent on screens before the brain → BLOCKED.
SILENT-FAILURE: UPS sizing TBD → tracked as open item, never silently ignored.
CHALLENGE: real outage → brain verifiably stays up longest.
**Verification Method:**
1. [AUTO] Wiring: N100+ER605+switch on UPS; TVs not. Evidence: config + photo.
2. [AUTO] Runtime: apcaccess shows UPS runtime estimate. Evidence: query.
3. [NICK] Live: outage drill → brain stays up longest. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/N100-priority-power-3cfe152fc19981e089a9e25facd2a4b8_

---
## EPR-004 — West Wall MicroTouch + West Google TV accept no backup power
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: don't overspend on backup power for screens that can afford to go dark during a rare outage.

**Functional Requirement Specification:**  
West Wall MicroTouch + West Google TV are accepted to go dark with no backup power during an outage. Do not spec UPS capacity for them. Rationale: rare event; avoid over-buying UPS units.

**Acceptance Criteria:**
NORMAL: West Wall MicroTouch + West Google TV go dark on outage; no UPS capacity specced for them.
NEGATIVE: UPS budgeted for West screens → violates the cost guard.
SILENT-FAILURE: someone later specs UPS for them → caught by [[SPEC:EPR-007]] allocation-map review.
CHALLENGE: outage → West dark, East/core up, no panic.
**Verification Method:**
1. [AUTO] Allocation: [[SPEC:EPR-007]] map shows no West-screen UPS. Evidence: config.
2. [NICK] Live: outage drill → West dark, core up. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/West-Wall-MicroTouch-West-Google-TV-accept-no-backup-power-3cfe152fc19981e5863afa19fbb9a0db_

---
## EPR-007 — Final UPS allocation map
**Status:**  | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: a final, settled answer for which device is backed up by which UPS — not an open question during an actual outage.

**Functional Requirement Specification:**  
Final UPS allocation map (LOCKED, Nick 2026-10-01): UPS 1 = N100 + ER605 + 8-port switch (longest). UPS 2 (new BE600M1) = Alexa TV + TCL1 + MT1 + 5-port switch. West Wall (MT2 + West Google TV) = no backup. Graceful-shutdown sequence on power loss: all screens drop to minimum backlight; TCL1 soft-shuts-down 10 min after the emergency print prints; Alexa TV stays up until UPS reaches 25% capacity then soft-shuts-down; MT1 + 5-port switch stay up till the bitter end. Estimated UPS-2 runtime ~65 min.

**Acceptance Criteria:**
NORMAL: settled device→UPS allocation map (which devices on the two 600VA APCs vs a possible third/stronger unit).
NEGATIVE: ambiguous allocation during an outage → eliminated by the written map.
SILENT-FAILURE: map drifts from physical wiring → caught by periodic audit.
CHALLENGE: Nick follows the map during a real outage without hesitation.
**Verification Method:**
1. [AUTO] Map: settled allocation document exists. Evidence: file.
2. [NICK] Live: Nick verifies the map matches physical wiring. Evidence: photo + observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Final-UPS-allocation-map-3cfe152fc1998124807cf28bbb812c8e_
