# Taza OS URS — UI cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## UI-001 — CRM Session PWA
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As a user logging a CRM session, I need a simple mobile-friendly app with a customer dropdown, chat, a record button, and an end-session button so that I can log a session quickly from whatever device I'm on.

**Functional Requirement Specification:**  
CRM Session PWA (port 3001): customer dropdown, chat, Record mic, End Session; mobile-responsive.

**Failure Behavior:**  
Fallback: Sandra types notes in NocoDB.

**Acceptance Criteria:**  
NOTE: this row is flagged for recon (possible duplicate of SCREEN-10/CRM 2, same PWA on port 3001) — resolve before debate builds against both in parallel.

NORMAL:
1. PWA provides customer dropdown, chat, Record mic, End Session, mobile-responsive.

EDGE:
2. Customer dropdown with a large customer list remains fast/searchable, not a slow unfiltered scroll.
3. Record mic mid-session, then End Session without an explicit stop — recording state is handled gracefully (auto-stopped and included, or clearly discarded), not left in an undefined state.

NEGATIVE:
4. End Session with no customer selected is blocked with a clear prompt, not allowed to submit an orphaned session.

SILENT FAILURE:
5. End Session appearing to succeed in the UI while the backend extraction/write (W4/CRM 3) actually fails must not be possible — verify End Session's success state is gated on confirmed backend completion, not just the UI action being tapped.

**Verification Method:**  
1) Recon step (precondition): confirm with Nick and against the live gflip/N100 service on port 3001 whether this row or SCREEN-10 is authoritative before further build work. 2) Unit tests: customer selection required before End Session, mic record/stop handling. 3) Backend-confirmation test: force the CRM 3 extraction/write to fail, confirm End Session does not report false success. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
RECON NEEDED: UI-001 and SCREEN-10 (CRM 2) both describe the same CRM Session PWA (port 3001). Recon team: (a) check the live gflip/N100 service on port 3001 to confirm which spec matches deployed reality; (b) confirm with Nick whether UI-001 is safe to deprecate in favor of SCREEN-10, or whether the two cover genuinely distinct scope worth keeping separate.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/CRM-Session-PWA-3cfe152fc199818a9f9ee89fc61b0e61_

---
## UI-002 — Invoice Form PWA
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As a user creating an invoice, I need a single mobile-responsive form covering Customer, Event, Timing, Dispatch, SKUs, Payment, Title, and Future sections so that I can enter a full invoice in one place without switching tools.

**Functional Requirement Specification:**  
Invoice Form PWA (port 3002): 8 sections — Customer, Event, Timing, Dispatch, SKUs, Payment, Title, Future; mobile-responsive.

**Failure Behavior:**  
Fallback: Manual Square invoice.

**Acceptance Criteria:**  
NOTE: this row is flagged for recon (possible duplicate of SCREEN-09/INVOICE 3, same PWA on port 3002) — AC below applies if recon confirms this row stands; resolve the recon flag before debate builds against this in parallel with SCREEN-09.

NORMAL:
1. All 8 sections (Customer, Event, Timing, Dispatch, SKUs, Payment, Title, Future) render and are usable on a mobile-responsive layout.

EDGE:
2. Form usable one-handed on a phone in the field (matches the mobile-first pattern established elsewhere, e.g. CRM 14) — not just responsive in a desktop-browser-resized sense.
3. Partially completed form (some sections filled, not submitted) persists on accidental navigation away/app backgrounding, not lost.

NEGATIVE:
4. Required fields across the 8 sections block submission with specific per-field errors, not a generic 'form invalid' message.

SILENT FAILURE:
5. A section that silently fails to save (network blip during multi-step form fill) must not let the user believe the whole form saved when only part did.

**Verification Method:**  
1) Recon step (precondition): confirm with Nick and against the live gflip/N100 service on port 3002 whether this row or SCREEN-09 is authoritative before further build work. 2) Unit tests per section: field validation, required-field errors. 3) Persistence test: partial fill, background/reopen, confirm no data loss. 4) Mobile usability test: one-handed real-device test, not just responsive breakpoints. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
RECON NEEDED: UI-002 and SCREEN-09 (INVOICE 3) both describe the same Invoice Form PWA (port 3002). Recon team: (a) check the live gflip/N100 service on port 3002 to confirm which spec matches deployed reality; (b) confirm with Nick whether UI-002 is safe to deprecate in favor of SCREEN-09, or whether the two cover genuinely distinct scope worth keeping separate.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Invoice-Form-PWA-3cfe152fc19981b08550dfc0567646e9_

---
## UI-003 — TV kiosk auto-boot views
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As a crew member glancing at the kitchen TVs, I need TV 1 showing the event calendar and TV 2 showing the team kanban board, both booting straight into those views with no manual browser steps, so that the information is just there when the screen powers on.

**Functional Requirement Specification:**  
TV 1 kiosk shows the event calendar; TV 2 kiosk shows the team kanban board; both auto-boot with no manual browser action needed.

**Failure Behavior:**  
Fallback: Manual browser open after reboot.

**Acceptance Criteria:**  
Both TVs show correct views within 60s of reboot; no auto-sleep

**Open Questions:**  
FLAGGED FOR RECON 2026-09-02 — likely stale pre-build draft, contradicted by the built system (KANBAN 2/DISPLAY 2/DISPLAY 3). Recon team: (a) check the live gflip/N100 TV services to confirm what's actually running; (b) ask Nick whether to deprecate outright or whether any element (e.g. an event-calendar view) is still wanted and should be re-specced against the real architecture.

**Verification Method:**
1. [AUTO] Boot: both TVs reach their kiosk view within 60s of reboot, no manual step. Evidence: reboot + log.
2. [NICK] Live: Nick confirms TV1=calendar, TV2=kanban after a real reboot. Evidence: screenshots.
3. [NICK] Recon: resolve the stale-draft flag — confirm against live services or deprecate (see Open Questions). Evidence: recon note.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/TV-kiosk-auto-boot-views-3cfe152fc199819196e5e2ee93a63193_

---
## UI-004 — 21.5" touchscreen bookmarks and kiosk config
**Status:**  | **Priority:** P3 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As a user of the 21.5" touchscreen, I need Chrome bookmarks set up for NocoDB, the CRM, and the Invoice Form, in portrait orientation with no Notion app installed, so that the device is configured for its intended kitchen-floor use and nothing extraneous is on it.

**Functional Requirement Specification:**  
21.5" touchscreen: Chrome bookmarks for NocoDB, CRM, and Invoice Form; portrait orientation; no Notion app installed.

**Failure Behavior:**  
Fallback: Phone via remote-access tunnel.

**Acceptance Criteria:**  
Chrome loads on boot; bookmarks work; touch targets ≥44px

**Open Questions:**  
FLAGGED FOR RECON 2026-09-02 — likely stale pre-build draft, contradicted by the built system (DISPLAY 5, z33 5-tab setup). Recon team: (a) check the live z33 device config to confirm what's actually running; (b) ask Nick whether to deprecate outright or preserve any still-wanted element as a separate, correctly-specced row.

**Verification Method:**
1. [AUTO] Config: Chrome bookmarks for NocoDB/CRM/Invoice Form present, portrait orientation, no Notion app. Evidence: device config.
2. [AUTO] Touch: touch targets ≥44px. Evidence: measurement.
3. [NICK] Recon: resolve the stale-draft flag — confirm against live z33 config or deprecate (see Open Questions). Evidence: recon note.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/21-5-touchscreen-bookmarks-and-kiosk-config-3cfe152fc199815e822cec32dc046a28_

---
## UI-005 — MicroTouch kiosk configuration
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
As a crew member using MicroTouch 1 or 2, I need the device to boot straight into NocoDB with the voice-feedback page reachable, and require a PIN to exit kiosk mode, so that the tablet stays locked to its intended function and can't be accidentally backed out of or reconfigured.

**Functional Requirement Specification:**  
MicroTouch 1+2: Fully Kiosk Browser with NocoDB loading on boot and the voice-feedback page accessible for W14; PIN required to exit kiosk mode.

**Failure Behavior:**  
Fallback: Chrome without kiosk lock.

**Acceptance Criteria:**  
NOTE: this row is flagged for recon (likely stale pre-build draft contradicting KANBAN 2's actual MT1/MT2 kanban-app behavior) — resolve before debate builds against it.

NORMAL:
1. MicroTouch 1+2 run Fully Kiosk Browser, load NocoDB on boot, expose the W14 voice-feedback page, and require a PIN to exit kiosk mode.

EDGE:
2. Kiosk PIN-exit is tested to actually prevent casual/accidental exit (e.g. multi-finger gesture, accidental long-press) while still allowing intentional authorized exit.

NEGATIVE:
3. An incorrect PIN attempt on kiosk-exit is rejected without revealing anything about the correct PIN (no partial feedback/lockout bypass).

SILENT FAILURE:
4. If this row's premise (NocoDB-on-boot) is actually stale and MT1/MT2 really run the kanban app per KANBAN 2, shipping this AC as-is would validate the wrong behavior — do not execute this verification until the recon flag is resolved.

**Verification Method:**  
1) Recon step (precondition): resolve against live MT1/MT2 kiosk config and Nick's confirmation before any test execution. 2) Once resolved: kiosk-exit PIN test (correct/incorrect), boot-behavior test matching whatever is confirmed as current reality. 3) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Open Questions:**  
FLAGGED FOR RECON 2026-09-02 — likely stale pre-build draft, contradicted by the built system (KANBAN 2, MT1/MT2 run the kanban app, not NocoDB-on-boot). Recon team: (a) check the live MT1/MT2 kiosk config to confirm what's actually running; (b) ask Nick whether to deprecate outright.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/MicroTouch-kiosk-configuration-3cfe152fc19981289f93f6e2746a6473_
