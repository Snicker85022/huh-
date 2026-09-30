# Taza OS URS — DATABASE cluster
_Exported: 2026-09-19 21:35 | 4 rows_
_Source: Notion Master URS & Specification Registry_

---
## DB-001 — PostgreSQL DDL from canonical schema definitions
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: PostgreSQL built from canonical schema — every object/field/relationship queryable, no drift from the schema doc.

**Functional Requirement Specification:**  
PostgreSQL DDL derived from the canonical Data Schemas & Field Maps definitions — every Object Type gets a table, columns match, FKs resolve, indexes created.

**Failure Behavior:**  
Fallback: manual DDL correction.

**Acceptance Criteria:**  
NORMAL:
1. Every Object Type in the canonical Data Schemas & Field Maps has a corresponding PostgreSQL table with matching columns.
2. All foreign keys resolve correctly; all documented indexes exist.

EDGE:
3. An Object Type with an optional/nullable field is correctly nullable in the DDL, not accidentally NOT NULL (or vice versa for required fields).
4. A schema update (new field added to canonical definitions) has a defined migration path, not requiring a manual out-of-band DB edit each time.

NEGATIVE:
5. A table/column that exists in Postgres but has drifted from the canonical schema definition (added ad hoc, not reflected back in the source-of-truth doc) is detectable — this is exactly the PROD-18 'some elements already populated directly in Postgres' recon flag; verify a reconciliation pass catches this.

SILENT FAILURE:
6. A foreign key that's technically present but points to the wrong table/column (typo, copy-paste error) would silently allow bad data linkage — verify FK correctness is spot-checked against actual relationships, not just 'a constraint exists.'
7. Missing indexes on frequently-queried columns would silently degrade performance without an explicit error — verify indexes match actual query patterns, not just the documented list.

**Verification Method:**  
1) Schema-diff test: automated comparison of canonical Data Schema definitions against live Postgres schema, flagging any drift in either direction. 2) FK-integrity test: verify each foreign key references the correct table/column, spot-checked against real relationships. 3) Reconciliation pass: address the PROD-18 flag — confirm no Postgres tables/columns exist outside what canonical schema defines, or update canonical schema to match reality. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/PostgreSQL-DDL-from-canonical-schema-definitions-3cfe152fc199814f9083f31b2407c0ee_

---
## DB-002 — NocoDB schema + core views imported
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: NocoDB pre-imported with core views (Lead Scores, CRM Sessions, Customer Opps, Voice Notes, Comms, Invoices), working on any device.

**Functional Requirement Specification:**  
NocoDB schema imported with views: Lead Scores, CRM Sessions, Customer Opps, Voice Notes, Comms, Invoices. All views load with correct column types; data entry works on all devices.

**Failure Behavior:**  
Fallback: rebuild NocoDB from DDL.

**Acceptance Criteria:**  
All views load; column types match; data entry works on all devices

**Verification Method:**
1. [AUTO] Views: all 6 views (Lead Scores, CRM Sessions, Customer Opps, Voice Notes, Comms, Invoices) load with correct column types. Evidence: screenshot + schema query.
2. [NICK] Live: Sandra enters data from laptop and phone. Evidence: observation log.
3. [AUTO] Fallback: DDL rebuild reproduces the schema cleanly. Evidence: rebuild test log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/NocoDB-schema-core-views-imported-3cfe152fc19981d29537fd2c429f51dc_

---
## DB-003 — NocoDB user roles (Nick/Sandra/Edgar)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: Nick (admin), Sandra (editor), Edgar (editor, limited tables) each have their own role-scoped NocoDB login.

**Functional Requirement Specification:**  
NocoDB user roles: Nick (admin), Sandra (editor), Edgar (editor, limited tables). Each logs in and sees only the tables their role allows.

**Failure Behavior:**  
Fallback: single admin account (temp).

**Acceptance Criteria:**  
Each user logs in; table visibility matches role spec

**Verification Method:**
1. [AUTO] Role matrix: each role sees exactly its allowed tables (Nick=admin, Sandra=editor, Edgar=editor-limited). Evidence: per-role login test log.
2. [NICK] Live: Nick logs in as each of the three roles and verifies visibility. Evidence: observation log + screenshots.
3. [AUTO] Fallback: single admin account still works. Evidence: log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/NocoDB-user-roles-Nick-Sandra-Edgar-3cfe152fc19981169accc851b3e0f434_

---
## DB-004 — NocoDB accessible from all operating devices
**Status:**  | **Priority:** P3 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
System Infrastructure

**User Requirement Statement:**  
Need: Nick/Sandra/Edgar can reach NocoDB from laptop and phone. Full NocoDB view on z33 only among on-site screens. MicroTouch 1/2 and 21.5" touchscreen do not get NocoDB.

**Functional Requirement Specification:**  
NocoDB reachable with working touch input from laptop and phone for Nick, Sandra, Edgar, and from z33 (full view). Kitchen floor devices (MicroTouch 1/2, 21.5" touchscreen) are NOT NocoDB clients — they run KANBAN 1/DISPLAY 1/HEALTH 1/HEALTH 2 surfaces only.

**Acceptance Criteria:**  
NocoDB loads on all device types; touch works on touchscreens

**Open Questions:**  
Per-role NocoDB permissions not yet defined: Edgar full write vs. view-only on sensitive tables? Sandra all-tables or event/recipe-only?

**Verification Method:**
1. [NICK] Live: Nick/Sandra/Edgar each open NocoDB on laptop + phone. Evidence: screenshots.
2. [AUTO] z33: full NocoDB view loads. Evidence: screenshot.
3. [AUTO] Exclusion: MicroTouch 1/2 and 21.5" do NOT load NocoDB — kanban/display surfaces only. Evidence: config check.
4. [NICK] Live: touch input works on z33. Evidence: observation log.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/NocoDB-accessible-from-all-operating-devices-3cfe152fc199814a88d5c7b9d6cc52de_
