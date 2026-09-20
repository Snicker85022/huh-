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
The on-screen kanban card board crew tap to run and close tasks — realizes the Mom's Table kanban (PROD-03).

**Functional Requirement Specification:**  
Live kitchen kanban on MT1 (East) and MT2 (West). Three-state card flow, per-card signals, PIN-gated close, Short Stop, Mom's Table game/brand layer. Reads ?board=East/West (default West).

**Dependency Notes:**  
IMPLEMENTS: URS-KANBAN-001..005 (state/close/signals/short-stop/publish), URS-KIT-METHOD-* (Taza Method cards), CLOSE 3 (PIN). Parent feature KANBAN 1.

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
East wall situational-awareness display — realizes URS-DISP-003.

**Functional Requirement Specification:**  
TCL East 75": event timeline, situational status, allergen board. Fetches /situational.json + /inventory.json from N100; glanceable per SSB standards.

**Dependency Notes:**  
IMPLEMENTS: DISPLAY 23 (East situational awareness by mode), SSB-001..007 (glanceable shared board). Parent feature DISPLAY 1.

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
West wall prep-execution display — realizes URS-DISP-004.

**Functional Requirement Specification:**  
TCL West 75": prep-station checklist/progress. Fetches /situational.json from N100; glanceable per SSB standards.

**Dependency Notes:**  
IMPLEMENTS: DISPLAY 24 (West prep execution by mode), SSB-001..007. Parent feature DISPLAY 1.

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
Van loadout readiness display — realizes URS-DISP-005.

**Functional Requirement Specification:**  
Insignia Fire TV: departure/loadout status by van/category. Fetches /van-loadout.json from N100. Handles ~6% right-edge dead zone via CSS var. Same physical TV runs Alexa skill (ALC-001..006).

**Dependency Notes:**  
IMPLEMENTS: DISPLAY 25 (Van Scoreboard loadout readiness by mode), CLOSE 15 (van-load departure checklist). Parent feature DISPLAY 1. Note: same physical TV runs the Alexa skill (ALC family).

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
System health dashboard — realizes URS-HEALTH-001 / PROD-28.

**Functional Requirement Specification:**  
Health dashboard: CPU temp, RAM/disk, UPS (apcaccess), service states, AI-engine status, network presence, thermal history. Green-on-dark, ~30s auto-refresh. LAN + Tailscale.

**Dependency Notes:**  
IMPLEMENTS: HEALTH 5 (signal set), HEALTH 8 (survives reboot), HEALTH 9 (fail-visible). Parent feature HEALTH 1.

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
Phone-accessible crew/emergency page when screens are down — realizes URS-HEALTH-002.

**Functional Requirement Specification:**  
Phone-friendly crew/emergency web app: /emergency (power-outage brief), /siteguide (everyday crew ref), /status (live UPS via apcaccess). Two-tab HTML, 18px font, designed for a 45yo cook in AZ sunlight. LAN + Tailscale.

**Verification Method:**  
Built.

**Dependency Notes:**  
IMPLEMENTS: HEALTH 6 (phone emergency access). Related to HEALTH 7 (emergency print). Parent feature HEALTH 2.

**Open Questions:**  
Nick wants this always-on (not emergency-only); taza-crew.service exists as a loose file, intentionally not installed pending URS rewrite.

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
On-site crew tablet: client story + hospitality prompts — realizes PROD-29.

**Functional Requirement Specification:**  
Standalone offline HTML/PWA on Galaxy Tab A8: Mode 1 client-story reveal (pre-service), Mode 2 hospitality scanning prompts cycling event arc, Mode 3 wind-down. Wake Lock keeps screen awake; no network during events.

**Verification Method:**  
Delivered 2026-06-20.

**Dependency Notes:**  
IMPLEMENTS: CREW 3 (offline PWA), CREW 4 (event setup), CREW 5 (client story before prompts), CREW 6 (cycle prompts + stay awake). V2: URS-CREW-005 (auto-populate). Parent feature CREW 1.

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
Invoice form Sandra fills to produce event invoices — realizes UI-002 / PROD-07.

**Functional Requirement Specification:**  
The staff invoice-form web app (mobile-responsive PWA, port 3002): 8 sections (Customer, Event, Timing, Dispatch, SKUs, Payment, Title, Future), auto-title generation, address autocomplete, deposit logic, and publish-to-Square. The form is the deterministic front-end for W2/INVOICE 13 invoice generation (97% deterministic coverage target).

**Verification Method:**  
Not yet built — listed in contractor brief as to-build.

**Dependency Notes:**  
IMPLEMENTS: INVOICE 12 (Invoice Form PWA requirement), CX-001..007 (invoice blocks), CATALOG 2 (reads catalog attributes). Feeds W2/INVOICE 13. Parent feature INVOICE 1.

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
CRM session screen for customer calls — realizes UI-001 / W4/W13.

**Functional Requirement Specification:**  
The CRM session web app (mobile-responsive PWA, port 3001): customer dropdown, multi-turn chat with the AI-backed CRM assistant, Record (voice→Whisper), End Session (triggers JSON extraction + NocoDB write). The front-end for W4/W13 CRM interview sessions.

**Verification Method:**  
Not yet built.

**Dependency Notes:**  
IMPLEMENTS: UI-001 (CRM Session PWA requirement). Feeds/hosts W4 (CRM Interview Session) + W13 (consolidated CRM session) + W5 (voice input). No single PROD parent — tie to W4/W13 in debate.

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
Staff mobile shopping app with vendor-grouped list and check-off — realizes PROD-05-V2.

**Functional Requirement Specification:**  
The staff shopping web app (mobile): passkey auth, aggregated + vendor-grouped + frost-risk-first shopping list, check-off with substitution capture, one-source-of-truth updates with optimistic-update conflict recovery. The staff-facing front-end for SHOP 11/SHOP 1.

**Verification Method:**  
Not yet built — v2 shopping logic fully spec'd (PROD-05-V2), app build unconfirmed.

**Dependency Notes:**  
IMPLEMENTS: URS-MOB-001..005 (staff mobile surface), SHOP 1 (aggregated/vendor-grouped/frost-risk shopping), SHOP 3 (substitution capture at check-off). Parent feature SHOP 11.

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

**Verification Method:**  
Not yet built. Hardware mounted, awaiting network connection (URS-DISP-PKG open item 4).

**Dependency Notes:**  
Previously mis-referenced as SHOP 2 in DISPLAY 21 — corrected; SHOP 2 is the Shopping Staff Web App.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/50-Onboarding-Orientation-Display-not-yet-networked-3cfe152fc19981b6a451e8aa9a454c79_
