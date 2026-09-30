# Taza OS URS — LABEL cluster
_Exported: 2026-09-19 21:35 | 5 rows_
_Source: Notion Master URS & Specification Registry_

---
## URS-LABEL-001 — Type A label contains internal pedigree essentials
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every internal label shows item, qty, event, batch, prep date, crew, use-by, and storage location — all pulled from the system, never handwritten.

**Atomic Requirement:**  
An internal Type A label shall contain item, quantity, event/customer, batch or lot, prep date, crew identity, use-by, and storage location in human-readable or QR-linked form.

**Functional Requirement Specification:**  
An internal Type A label shall contain in human-readable or QR-linked form: item, quantity, event/customer, batch or lot identifier, prep date, responsible crew identity, use-by date/time, and storage location. All fields shall be sourced from the canonical lot record — no manual re-entry. The label is crew-facing and internal only (Type B customer label is V2.0, URS-LABEL-002).

**Inputs:**  
Canonical lot record ([[SPEC:URS-INV-003]]): item, qty, event/customer, batch/lot ID, prep date, crew identity (PIN resolved to name), use-by, bin/location.

**Outputs:**  
A fully-populated Type A ZPL label payload with all required fields and a scannable QR.

**Trigger:**  
Crew confirms a label proposal ([[SPEC:URS-LABEL-006]] / [[SPEC:URS-INV-004]]).

**Invariants:**  
All required fields sourced from canonical data; no manual re-entry on the label path; Type A is internal-only (never exposed to customers as a primary label).

**Failure Behavior:**  
A label missing any required field is blocked (no partial label prints). A QR that can't be generated blocks the print rather than printing a broken code.

**Failure Mode Addressed:**  
A label that arrives at the line missing critical info (who made it, when, use-by, what event) — the 'mystery container' problem during multi-event weeks.

**Acceptance Criteria:**  
A generated Type A test label contains every required field and scans to the matching lot record.

**Verification Method:**  
Printed-label inspection and QR resolution test.

**Maintenance Requirements:**  
Keep the field list aligned with the lot record schema ([[SPEC:URS-INV-003]]); verify all fields populate correctly when new item types are added.

**Dependency Notes:**  
Content sourced from the lot record (CLOSE 8) + kanban close (LABEL 7 confirm step). QR resolves via LABEL 4. Print path via LABEL 6 (Ethernet ZPL). CROSS-REF: KIT-018 label-on-close. Part of BUNDLE-SMART-LABELS. Parent LABEL 1. Type B (customer) = URS-LABEL-002 V2.0.

**External Dependencies:**  
Zebra TLP 2844-Z; 4x1 stock.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Type-A-label-contains-internal-pedigree-essentials-f9780eb51af84d42acdb940c05124609_

---
## URS-LABEL-003 — Label QR resolves to canonical batch details
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: QR always resolves to the right batch, even after detail updates, with a clear explanation if the batch is unknown — never silence or wrong info.

**Atomic Requirement:**  
Each label QR shall resolve by immutable batch identifier to current canonical pedigree and applicable care information.

**Functional Requirement Specification:**  
Each label QR shall encode an immutable batch identifier that resolves to current canonical pedigree and applicable care information. The resolution shall be stable under batch data changes (the ID doesn't change; the hosted page updates). An unknown or retired batch shall return a safe explanatory state, never another batch's data or an unhandled error.

**Inputs:**  
Immutable batch/lot ID; the hosted endpoint serving current canonical lot data.

**Outputs:**  
A scannable QR code on the label that resolves to current canonical batch data or a safe explanatory fallback.

**Trigger:**  
Label generation (QR is baked in at print time); resolution on every QR scan.

**Invariants:**  
QR payload is immutable (encodes batch ID only, not the data itself); resolution is always to the correct batch or a safe fallback; no cross-batch contamination of data.

**Failure Behavior:**  
Unknown batch ID → safe explanatory page (never another batch's data). Retired/expired batch → explanatory state, not an error. The QR payload itself is immutable; only the hosted endpoint's content can change.

**Failure Mode Addressed:**  
A label that lies — scanning one item's QR and getting another batch's data — or a broken QR that returns nothing useful (the emergency print OPEN item: QR codes returning 'site can't be reached' at ~67%).

**Acceptance Criteria:**  
Scanning a label resolves the correct batch; unknown or retired batches return a safe explanatory state rather than another batch.

**Verification Method:**  
QR-to-record integration and negative tests.

**Maintenance Requirements:**  
Keep the hosted resolution endpoint live and reachable; handle batch retirement cleanly (don't 404, serve a safe state); verify QR resolution after any endpoint-routing change. OPEN: confirm the QR endpoint is reliably reachable post the 07-07 emergency-print fix (V1.0-Project-Plan P0 blocker).

**Dependency Notes:**  
The QR encodes the immutable batch/lot ID from CLOSE 6/CLOSE 8. The hosted resolution endpoint must return current canonical data for that ID. Unknown/retired batches return a safe explanatory state (never a wrong batch). Part of BUNDLE-SMART-LABELS. Parent LABEL 1.

**Open Questions:**  
QR endpoint reachability (V1.0-Project-Plan P0 item — "QR codes return site can't be reached" at ~67% — confirm resolved).

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Label-QR-resolves-to-canonical-batch-details-e188f03d7c3a4565b271bd4b582bd649_

---
## URS-LABEL-004 — FaviQR graphics use threshold-only monochrome conversion
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: every QR scans first time printed — threshold-only black/white conversion, never dithering (dithering at 203 DPI produces gray noise that breaks scans).

**Atomic Requirement:**  
FaviQR and label graphics shall use threshold-only black/white conversion and shall not use dithering.

**Functional Requirement Specification:**  
All FaviQR generation and label-graphic conversion shall apply threshold-only (binary) black/white conversion. Dithering is prohibited at any stage. The generated bitmap shall contain only pure-black (0) and pure-white (255) pixels. This is a hard constraint at 203 DPI on the Zebra printer — dithering produces gray pixels that become noise and cause scan failures.

**Inputs:**  
Any image or graphic destined for a ZPL label or QR code.

**Outputs:**  
Binary black/white-only bitmaps ready for ZPL embedding; QR codes that scan first time at 203 DPI.

**Trigger:**  
Any label or QR graphic generation step.

**Invariants:**  
Threshold-only conversion everywhere in the label/QR pipeline; no gray pixels in any generated bitmap; this constraint applies to ALL label graphics, not just QRs.

**Failure Behavior:**  
Any image-generation code path that produces gray/halftone pixels is rejected before print. A generated bitmap that fails the pixel-value test triggers a code error, not a print attempt.

**Failure Mode Addressed:**  
QR codes that look correct on screen but fail to scan when printed, because dithering introduces gray pixels that the 203-DPI Zebra printer renders as noise — confirmed the failure mode that drove this decision.

**Acceptance Criteria:**  
Generated bitmap contains only black and white values; printed QR scans successfully on the Zebra 203-DPI printer.

**Verification Method:**  
Pixel-value test plus physical first-scan test. Verified 2026-07-14 — test labels scanned first try after applying this rule.

**Maintenance Requirements:**  
Enforce this as a unit-test assertion (pixel-value check) on every label/QR generation code path; re-run the physical first-scan test after any image-processing library change.

**Dependency Notes:**  
This is a hard technical constraint on all label and QR generation code. Applies to every bitmap used in a ZPL label at 203 DPI. Locked in the KB Smart Label spec (2026-07-14). Part of BUNDLE-SMART-LABELS. Parent LABEL 1.

**External Dependencies:**  
Zebra TLP 2844-Z at 203 DPI.

**Rationale:**  
P0 — highest-priority label row; breaking it silently breaks every label's QR.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/FaviQR-graphics-use-threshold-only-monochrome-conversion-57c9935624994379bd4e6b600260ba22_

---
## URS-LABEL-005 — Production labels print through Ethernet ZPL only
**Status:** Spec Drafted | **Priority:** P0 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: labels print over Ethernet TCP, never USB — the USB port is physically occupied (AKiTiO dock).

**Atomic Requirement:**  
Production label output shall use raw ZPL over Ethernet TCP port 9100 and shall not depend on USB-B.

**Functional Requirement Specification:**  
Production label output shall send raw ZPL over a direct Ethernet TCP connection to the Zebra printer on port 9100. The print path shall not depend on USB-B, CUPS, or any print-driver layer. This is a hard constraint: the N100's spare USB port is physically occupied by the AKiTiO dock and is not available for printing.

**Inputs:**  
A complete ZPL payload + the Zebra printer's LAN IP.

**Outputs:**  
A raw ZPL job delivered over TCP port 9100 to the Zebra printer.

**Trigger:**  
A confirmed print request ([[SPEC:URS-LABEL-006]]).

**Invariants:**  
Print path is Ethernet TCP port 9100 only; no USB branch exists in the code; no CUPS or spool layer on the N100.

**Failure Behavior:**  
An attempt to print via USB — whether code error or misconfiguration — is a build bug, not a runtime fallback. The print path code shall not contain a USB branch. Ethernet unavailable → queue/flag per [[SPEC:URS-LABEL-006]].

**Failure Mode Addressed:**  
A label system that silently breaks after a hardware reshuffle (USB occupied by AKiTiO) because it was written against the USB path; or a print that requires a driver/spool layer that adds latency and failure surface.

**Acceptance Criteria:**  
A representative label prints over TCP 9100 after reboot; disconnecting USB has no effect on the print path.

**Verification Method:**  
Physical network-print test.

**Maintenance Requirements:**  
DHCP-reserve the Zebra printer's LAN IP; re-run the physical print test after any network change; ensure no future code change reintroduces a USB or CUPS code path.

**Dependency Notes:**  
Requires the Zebra printer to be Ethernet-connected to the kitchen LAN. USB port on the N100 that previously served the Zebra is now occupied by the AKiTiO dock — the USB path is physically gone. Port 9100 is the raw ZPL/TCP socket, no CUPS or driver layer. Print path proven 2026-07-14. Part of BUNDLE-SMART-LABELS. Parent LABEL 1.

**External Dependencies:**  
Printer network address must be verified before build; USB-B is unavailable.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Production-labels-print-through-Ethernet-ZPL-only-021710d65b1843d3b658f0a4287b7bb2_

---
## URS-LABEL-006 — Label printing is confirmable, logged, reprintable, and failure-safe
**Status:** Spec Drafted | **Priority:** P1 | **Release:** V1.x

**Record Type:**  
Atomic Requirement

**Domain:**  
Production Core

**User Requirement Statement:**  
Need: nothing prints without explicit approval, every attempt is logged, reprints are distinguishable from originals, and offline jobs queue rather than get lost.

**Atomic Requirement:**  
The label service shall require confirmation for automatic proposals, log every print attempt, support controlled reprints, and queue or flag jobs when the printer is unavailable.

**Functional Requirement Specification:**  
The label service shall (1) require explicit crew confirmation before printing any automatically-proposed label, (2) log every print attempt with timestamp, crew, lot, and outcome, (3) support controlled reprints as a linked, distinguishable record, and (4) queue or flag jobs when the printer is unavailable without losing the payload. Cancel prints nothing and creates no log entry; a successful confirm logs one attempt; a reprint creates a linked attempt distinct from the original.

**Inputs:**  
Crew confirm or cancel; the pre-populated label payload ([[SPEC:URS-LABEL-001]]); printer availability status.

**Outputs:**  
On confirm: one logged print attempt + one ZPL job to [[SPEC:URS-LABEL-005]]. On cancel: nothing. On offline: one queued/flagged exception with full payload preserved. On reprint: one linked log entry + one ZPL job.

**Trigger:**  
Crew confirms or cancels a label proposal ([[SPEC:URS-INV-004]] / [[SPEC:URS-LABEL-006]]); reprint request; printer-unavailability detection.

**Invariants:**  
No print without explicit confirmation; every print attempt (including failed) is logged; reprints are linked and distinct; offline printer never silently drops a job.

**Failure Behavior:**  
Cancel → no print, no log entry. Confirm → exactly one logged attempt. Printer unavailable → print job queued/flagged with the full payload preserved (no lost job); crew sees a visible exception, never a silent drop. Reprint → creates a distinct, linked log entry (never overwrites the original).

**Failure Mode Addressed:**  
Lost or phantom labels — a label nobody asked for (auto-print), a label that was supposed to print but didn't and nobody knows, or an accidental double-print from a reprint that can't be distinguished from the original.

**Acceptance Criteria:**  
Cancel prints nothing; confirm logs one attempt; reprint creates a linked attempt; offline printer produces a visible queued exception without losing payload.

**Verification Method:**  
Happy-path, reprint, retry, and offline-printer tests.

**Maintenance Requirements:**  
Keep the print-attempt log fields aligned with [[SPEC:PROD-22]] audit schema; verify queue persistence survives service restarts (a dropped queue means lost label jobs on reboot).

**Dependency Notes:**  
This is the service-layer contract wrapping LABEL 6 (print transport). Confirm step follows from CLOSE 9 (label proposal). Print attempts are logged to the audit trail ([[SPEC:PROD-22]]). Offline-printer exceptions route through EXCEPT 1 (Exception Router). Part of BUNDLE-SMART-LABELS. Parent LABEL 1.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Label-printing-is-confirmable-logged-reprintable-and-failure-safe-c4c278c5909c448bafef459bb65be0a2_
