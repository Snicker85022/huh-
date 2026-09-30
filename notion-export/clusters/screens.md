# Taza OS URS — SCREENS cluster
_Exported: 2026-09-19 21:35 | 12 rows_
_Source: Notion Master URS & Specification Registry_

---
## SCREEN-01 — Mom's Table Kanban Board (taza-card-table.html, MT1/MT2)
**Status:** Deployed | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Production Core

**User Requirement Statement:**  
The on-screen kanban card board crew tap to run and close tasks — realizes the Mom's Table kanban ([[SPEC:PROD-03]]).

**Functional Requirement Specification:**  
Live kitchen kanban on MT1 (East) and MT2 (West). Three-state card flow, per-card signals, PIN-gated close, Short Stop, Mom's Table game/brand layer. Reads ?board=East/West (default West).

**Dependency Notes:**  
IMPLEMENTS: [[SPEC:URS-KANBAN-001]]..005 (state/close/signals/short-stop/publish), URS-KIT-METHOD-* (Taza Method cards), [[SPEC:PROD-12]] (PIN). Parent feature KANBAN 1.

**Verification Method:**
1. [NICK] Live: crew taps a card through all three states on MT1. Evidence: screenshot.
2. [AUTO] PIN gate: close without PIN is rejected. Evidence: test log.
3. [AUTO] Board param: ?board=East vs West loads the correct board. Evidence: screenshots.
4. [NICK] Brand: Mom's Table game/brand layer renders (gold, game state). Evidence: screenshot.

**Acceptance Criteria:**
NORMAL: MT1 (East) and MT2 (West) render the kanban board; three-state card flow works; cards tap-to-close with PIN gate.
EDGE: ?board=East/West renders the correct board; no param defaults to West.
NEGATIVE: Close attempt without PIN → rejected.
SILENT-FAILURE: Board stops updating mid-service → caught by TV watchdog ([[SPEC:TV-007]]), never a silently frozen board.
CHALLENGE: 50+ open cards → board stays responsive and per-card signals remain readable.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Mom-s-Table-Kanban-Board-taza-card-table-html-MT1-MT2-3cfe152fc19981caa50cf27c4e3528c2_

---
## SCREEN-02 — TCL East Situational Display (tcl1-east.html)
**Status:** Deployed | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Event Execution

**User Requirement Statement:**  
East wall situational-awareness display — realizes [[SPEC:URS-DISP-003]].

**Functional Requirement Specification:**  
TCL East 75": event timeline, situational status, allergen board. Fetches /situational.json + /inventory.json from N100; glanceable per SSB standards.

**Dependency Notes:**  
IMPLEMENTS: DISPLAY 23 (East situational awareness by mode), [[SPEC:SSB-001]]..007 (glanceable shared board). Parent feature DISPLAY 1.

**Verification Method:**
1. [NICK] Live: Nick reads the East display from across the kitchen. Evidence: photo + observation log.
2. [AUTO] Data: /situational.json + /inventory.json fetch confirmed from N100. Evidence: curl + log.
3. [AUTO] Watchdog: kill the page → auto-reloads. Evidence: log.
4. [NICK] Allergen: allergen flag → red on the board. Evidence: screenshot.

**Acceptance Criteria:**
NORMAL: TCL East renders event timeline + situational status + allergen board from /situational.json + /inventory.json.
EDGE: JSON fetch fails → display shows a stale/error state, never a blank wall.
NEGATIVE: Allergen board silently missing → impossible: allergen population forces a visible red state.
SILENT-FAILURE: Display goes blank mid-event → caught by TV watchdog ([[SPEC:TV-007]]).
CHALLENGE: Full event day with a long timeline → glanceable in <3s from across the kitchen.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/TCL-East-Situational-Display-tcl1-east-html-3cfe152fc19981b1a84fc2e3671b5fd0_

---
## SCREEN-03 — TCL West Prep Display (tcl2-west.html)
**Status:** Deployed | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Event Execution

**User Requirement Statement:**  
West wall prep-execution display — realizes [[SPEC:URS-DISP-004]].

**Functional Requirement Specification:**  
TCL West 75": prep-station checklist/progress. Fetches /situational.json from N100; glanceable per SSB standards.

**Dependency Notes:**  
IMPLEMENTS: DISPLAY 24 (West prep execution by mode), [[SPEC:SSB-001]]..007. Parent feature DISPLAY 1.

**Verification Method:**
1. [NICK] Live: Edgar reads the West prep display from across the kitchen. Evidence: photo + observation log.
2. [AUTO] Data: /situational.json fetch confirmed. Evidence: curl + log.
3. [AUTO] Watchdog: kill the page → auto-reloads. Evidence: log.

**Acceptance Criteria:**
NORMAL: TCL West renders prep-station checklist/progress from /situational.json.
EDGE: JSON fetch fails → stale/error state, never blank.
SILENT-FAILURE: Display freezes mid-prep → caught by TV watchdog ([[SPEC:TV-007]]).
CHALLENGE: Heavy prep day with many stations → still glanceable per SSB standards.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/TCL-West-Prep-Display-tcl2-west-html-3cfe152fc19981c7bf80d97d73977d78_

---
## SCREEN-04 — Van Loadout Scoreboard (van-loadout.html, Insignia/Alexa TV)
**Status:** Deployed | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Event Execution

**User Requirement Statement:**  
Van loadout readiness display — realizes [[SPEC:URS-DISP-005]].

**Functional Requirement Specification:**  
Insignia Fire TV: departure/loadout status by van/category. Fetches /van-loadout.json from N100. Handles ~6% right-edge dead zone via CSS var. Same physical TV runs Alexa skill ([[SPEC:ALC-001]]..006).

**Dependency Notes:**  
IMPLEMENTS: DISPLAY 25 (Van Scoreboard loadout readiness by mode), [[SPEC:URS-KIT-103]] (van-load departure checklist). Parent feature DISPLAY 1. Note: same physical TV runs the Alexa skill (ALC family).

**Verification Method:**
1. [NICK] Live: Edgar reads the scoreboard during an actual load. Evidence: photo.
2. [AUTO] Dead zone: content avoids the right-edge 6%. Evidence: screenshot + measurement.
3. [AUTO] Data: /van-loadout.json fetch confirmed. Evidence: curl + log.
4. [NICK] Coexist: Alexa skill still works on the same TV. Evidence: observation log.

**Acceptance Criteria:**
NORMAL: Insignia Fire TV shows departure/loadout status by van and category from /van-loadout.json.
EDGE: ~6% right-edge dead zone handled via CSS var — content stays out of it.
NEGATIVE: Alexa skill on the same physical TV conflicts with the scoreboard → impossible: both coexist.
SILENT-FAILURE: Scoreboard blank before departure → caught (departure-blocking surface).
CHALLENGE: Full van loadout across two vans → every category visible at a glance.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Van-Loadout-Scoreboard-van-loadout-html-Insignia-Alexa-TV-3cfe152fc19981f7949cfb2d1876b6bb_

---
## SCREEN-05 — z33 Gamemaster Display (z33-gamemaster.html)
**Status:** Deployed | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Event Execution

**User Requirement Statement:**  
Gamemaster/scoreboard view of Mom's Table game state on z33.

**Functional Requirement Specification:**  
z33 (21.5" touchscreen) gamemaster view: live Mom's Table game state/scoreboard via SSE. z33 is NOT kiosk-locked; runs 5 tabs (kanban, health :9000, gamemaster, board-master, LKL ref) + ADB tab-supervisor.

**Dependency Notes:**  
IMPLEMENTS: the gamemaster/scoreboard aspect of KANBAN 1 (Mom's Table) surfaced ambiently per DISPLAY 1. Parent feature DISPLAY 1.

**Verification Method:**
1. [NICK] Live: Nick sees the scoreboard update on a card close. Evidence: screenshot.
2. [AUTO] SSE: live updates without refresh. Evidence: log.
3. [AUTO] Tab-supervisor: the 5 tabs stay correct over 8h. Evidence: log.
4. [NICK] Touch: gamemaster interactions respond on the 21.5" touchscreen. Evidence: observation log.

**Acceptance Criteria:**
NORMAL: z33 shows live Mom's Table game state/scoreboard via SSE.
EDGE: all 5 tabs (kanban, health, gamemaster, board-master, LKL) reachable; ADB tab-supervisor keeps them on-target.
NEGATIVE: z33 is intentionally NOT kiosk-locked, but tabs must not drift to junk pages.
SILENT-FAILURE: SSE drops → scoreboard goes stale; caught by tab-supervisor/health.
CHALLENGE: Full event → game state updates live with no manual refresh.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/z33-Gamemaster-Display-z33-gamemaster-html-3cfe152fc199815fa574e1ca6c0fc868_

---
## SCREEN-06 — System Health Dashboard (dashboard.py, :9000)
**Status:** Deployed | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
System health dashboard — realizes [[SPEC:URS-HEALTH-001]] / [[SPEC:PROD-28]].

**Functional Requirement Specification:**  
Health dashboard: CPU temp, RAM/disk, UPS (apcaccess), service states, AI-engine status, network presence, thermal history. Green-on-dark, ~30s auto-refresh. LAN + Tailscale.

**Dependency Notes:**  
IMPLEMENTS: HEALTH 5 (signal set), HEALTH 8 (survives reboot), HEALTH 9 (fail-visible). Parent feature HEALTH 1.

**Verification Method:**
1. [NICK] Live: Nick reads health on his phone via Tailscale. Evidence: screenshot.
2. [AUTO] UPS: apcaccess values match the dashboard readout. Evidence: query + screenshot.
3. [AUTO] Fail drill: kill a service → board goes red within 60s. Evidence: screenshot.
4. [AUTO] Refresh: data refreshes ≤30s. Evidence: log.

**Acceptance Criteria:**
NORMAL: :9000 shows CPU temp, RAM/disk, UPS (apcaccess), service states, AI-engine status, network presence, thermal history.
EDGE: green-on-dark, ~30s auto-refresh.
NEGATIVE: A service goes down → board shows a fail state, never a stale green.
SILENT-FAILURE: A service silently drops off the board → caught (fail-visible per [[SPEC:URS-HEALTH-003]]).
CHALLENGE: Reboot the N100 → dashboard returns with correct live state.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/System-Health-Dashboard-dashboard-py-9000-3cfe152fc19981f188f8eafe18b52db7_

---
## SCREEN-07 — Crew Service / Emergency Page (server_mini.py, :9001)
**Status:** Deployed | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Phone-accessible crew/emergency page when screens are down — realizes [[SPEC:URS-HEALTH-002]].

**Functional Requirement Specification:**  
Phone-friendly crew/emergency web app: /emergency (power-outage brief), /siteguide (everyday crew ref), /status (live UPS via apcaccess). Two-tab HTML, 18px font, designed for a 45yo cook in AZ sunlight. LAN + Tailscale.

**Dependency Notes:**  
IMPLEMENTS: HEALTH 6 (phone emergency access). Related to HEALTH 7 (emergency print). Parent feature HEALTH 2.

**Open Questions:**  
Nick wants this always-on (not emergency-only); taza-crew.service exists as a loose file, intentionally not installed pending URS rewrite.

**Verification Method:**
1. [NICK] Live: Nick loads /emergency on a phone in sunlight. Evidence: screenshot.
2. [AUTO] apcaccess: /status matches live UPS. Evidence: query.
3. [NICK] Tailscale: reachable off-LAN. Evidence: screenshot.

**Acceptance Criteria:**
NORMAL: /emergency, /siteguide, /status reachable on a phone; 18px font, sunlight-readable.
EDGE: reachable on LAN and via Tailscale when the wall screens are down.
NEGATIVE: Power outage → /emergency brief still reachable (UPS-backed N100).
SILENT-FAILURE: /status shows stale UPS → caught (apcaccess is live).
CHALLENGE: a 45-year-old cook reads it on a phone in AZ sunlight.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Crew-Service-Emergency-Page-server_mini-py-9001-3cfe152fc19981e79781fc4601f32dec_

---
## SCREEN-08 — Crew Event Display v1 (taza-crew-display.html, Galaxy Tab)
**Status:** Built (unverified live) | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Event Execution

**User Requirement Statement:**  
On-site crew tablet: client story + hospitality prompts — realizes [[SPEC:PROD-29]].

**Functional Requirement Specification:**  
Standalone offline HTML/PWA on Galaxy Tab A8: Mode 1 client-story reveal (pre-service), Mode 2 hospitality scanning prompts cycling event arc, Mode 3 wind-down. Wake Lock keeps screen awake; no network during events.

**Dependency Notes:**  
IMPLEMENTS: CREW 3 (offline PWA), CREW 4 (event setup), CREW 5 (client story before prompts), CREW 6 (cycle prompts + stay awake). V2: URS-CREW-005 (auto-populate). Parent feature CREW 1.

**Verification Method:**
1. [NICK] Live: crew runs a real event on the tablet. Evidence: observation log.
2. [AUTO] Offline: airplane-mode run → still works. Evidence: test log.
3. [AUTO] Wake Lock: screen stays awake through service. Evidence: device log.

**Acceptance Criteria:**
NORMAL: Galaxy Tab runs offline; Mode 1 client story, Mode 2 hospitality prompts cycling the event arc, Mode 3 wind-down.
EDGE: Wake Lock keeps the screen awake; zero network during events.
NEGATIVE: Power loss → resumes at the correct mode.
SILENT-FAILURE: Screen sleeps mid-service → caught (Wake Lock must stay active).
CHALLENGE: Full event on airplane mode → all three modes work.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Crew-Event-Display-v1-taza-crew-display-html-Galaxy-Tab-3cfe152fc1998147b199e892832343dc_

---
## SCREEN-09 — Invoice Form PWA (:3002)
**Status:** Approved | **Priority:** P2 | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Revenue - Custom Catering

**User Requirement Statement:**  
Invoice form Sandra fills to produce event invoices — realizes [[SPEC:UI-002]] / [[SPEC:PROD-07]].

**Functional Requirement Specification:**  
The staff invoice-form web app (mobile-responsive PWA, port 3002): 8 sections (Customer, Event, Timing, Dispatch, SKUs, Payment, Title, Future), auto-title generation, address autocomplete, deposit logic, and publish-to-Square. The form is the deterministic front-end for [[SPEC:W2]]/[[SPEC:PROD-07]] invoice generation (97% deterministic coverage target).

**Dependency Notes:**  
IMPLEMENTS: [[SPEC:SCREEN-09]] (Invoice Form PWA requirement), [[SPEC:CX-001]]..007 (invoice blocks), [[SPEC:CAT-002]] (reads catalog attributes). Feeds [[SPEC:W2]]/[[SPEC:PROD-07]]. Parent feature [[SPEC:PROD-07]].

**Verification Method:**
1. [NICK] Live: Sandra fills a real invoice on her phone. Evidence: screenshot.
2. [AUTO] Sections: all 8 present and responsive. Evidence: screenshot.
3. [AUTO] Deposit: fixed-dollar lock per D19 holds. Evidence: test log.
4. [NICK] Publish: Nick reviews and publishes to Square. Evidence: observation log.

**Acceptance Criteria:**
NORMAL: 8 sections render; auto-title generates; address autocomplete; deposit logic; publish-to-Square.
EDGE: mobile-responsive on a phone.
NEGATIVE: publish without Nick/Sandra approval → blocked ([[SPEC:W7]] approval task).
SILENT-FAILURE: A section silently missing → caught (all 8 required).
CHALLENGE: Full invoice from an empty form → 97% deterministic coverage target.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Invoice-Form-PWA-3002-3cfe152fc19981208929f8495c1dbca6_

---
## SCREEN-10 — CRM Session PWA (:3001)
**Status:** Approved | **Priority:**  | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Customer Intelligence

**User Requirement Statement:**  
CRM session screen for customer calls — realizes [[SPEC:UI-001]] / [[SPEC:W4]]/[[SPEC:W13]].

**Functional Requirement Specification:**  
The CRM session web app (mobile-responsive PWA, port 3001): customer dropdown, multi-turn chat with the AI-backed CRM assistant, Record (voice→Whisper), End Session (triggers JSON extraction + NocoDB write). The front-end for [[SPEC:W4]]/[[SPEC:W13]] CRM interview sessions.

**Dependency Notes:**  
IMPLEMENTS: [[SPEC:UI-001]] (CRM Session PWA requirement). Feeds/hosts [[SPEC:W4]] (CRM Interview Session) + [[SPEC:W13]] (consolidated CRM session) + [[SPEC:W5]] (voice input). No single PROD parent — tie to [[SPEC:W4]]/[[SPEC:W13]] in debate.

**Verification Method:**
1. [NICK] Live: Sandra runs a real customer call. Evidence: screenshot.
2. [AUTO] Voice: Record → Whisper transcript appears. Evidence: test log.
3. [AUTO] Extraction: End Session → JSON lands in canonical tables. Evidence: psql.
4. [NICK] Backup: primary AI down → backup provider takes over. Evidence: observation log.

**Acceptance Criteria:**
NORMAL: customer dropdown, multi-turn chat with the AI CRM assistant, Record (voice→Whisper), End Session → JSON extraction + write.
EDGE: mobile-responsive on a phone.
NEGATIVE: End Session with no usable data → no partial write.
SILENT-FAILURE: Transcript lost → caught (stored in crm_sessions).
CHALLENGE: Full customer call with voice notes → correct structured extraction.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/CRM-Session-PWA-3001-3cfe152fc19981508c1ac53654b46178_

---
## SCREEN-11 — Shopping Staff Web App
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Design Reference

**Domain:**  
Production Core

**User Requirement Statement:**  
Staff mobile shopping app with vendor-grouped list and check-off — realizes [[SPEC:PROD-05-V2]].

**Functional Requirement Specification:**  
The staff shopping web app (mobile): passkey auth, aggregated + vendor-grouped + frost-risk-first shopping list, check-off with substitution capture, one-source-of-truth updates with optimistic-update conflict recovery. The staff-facing front-end for [[SPEC:PROD-05-V2]]/[[SPEC:PROD-05-V2]].

**Dependency Notes:**  
IMPLEMENTS: [[SPEC:URS-MOB-001]]..005 (staff mobile surface), [[SPEC:PROD-05-V2]] (aggregated/vendor-grouped/frost-risk shopping), [[SPEC:URS-KIT-105]] (substitution capture at check-off). Parent feature [[SPEC:PROD-05-V2]].

**Verification Method:**
1. [NICK] Live: Sandra checks off on her phone. Evidence: screenshot.
2. [AUTO] Frost-risk: item sorts last within its vendor group. Evidence: test log.
3. [AUTO] Conflict: two devices → revert works. Evidence: test log.
4. [AUTO] Passkey: auth works. Evidence: log.

**Acceptance Criteria:**
NORMAL: passkey auth; aggregated vendor-grouped frost-risk-first list; check-off with substitution capture.
EDGE: offline → optimistic update; conflict recovery on reconnect.
NEGATIVE: conflict → revert, never silent overwrite.
SILENT-FAILURE: substitution not captured at check-off → caught ([[SPEC:URS-KIT-105]]).
CHALLENGE: two staff check off the same item simultaneously → conflict recovery works.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Shopping-Staff-Web-App-3cfe152fc199810691d5e355ae3d5702_

---
## SCREEN-12 — 50" Onboarding/Orientation Display (not yet networked)
**Status:** Idea | **Priority:** P2 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Event Execution

**User Requirement Statement:**  
Dedicated display for new-crew onboarding/orientation without tying up an operational screen.

**Functional Requirement Specification:**  
50" Ethernet smart TV (mounted, not yet networked) showing onboarding panels (TV-009 Crew Training SOP mode + KANBAN 12 instructional panels). Once networked, added to DHCP reservations + display self-heal automation.

**Dependency Notes:**  
Previously mis-referenced as SHOP 2 in DISPLAY 21 — corrected; SHOP 2 is the Shopping Staff Web App.

**Verification Method:**
1. [NICK] Live: new crew watches onboarding end-to-end. Evidence: observation log.
2. [AUTO] Network: DHCP reservation + self-heal added. Evidence: config diff.
3. [NICK] Content: TV-009 + KANBAN 12 panels correct. Evidence: screenshot.

**Acceptance Criteria:**
NORMAL: 50" TV shows onboarding panels (TV-009 crew training SOP + KANBAN 12 instructional panels).
EDGE: not yet networked — pending DHCP reservation + display self-heal automation.
SILENT-FAILURE: once networked, covered by TV watchdog ([[SPEC:TV-007]]).
CHALLENGE: onboard a new crew member end-to-end from one screen.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/50-Onboarding-Orientation-Display-not-yet-networked-3cfe152fc19981b6a451e8aa9a454c79_
