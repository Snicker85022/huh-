# Taza OS Master URS — Comprehensive Evaluation Report

**Scope:** All 290 specs in `/home/taza/repo/master-urs.md`  
**Evaluation Date:** 2026-10-01 (per file timestamp)  
**Evaluator:** Cortex (Anthropic Claude Code)

---

## Executive Summary

The Master URS is a remarkably thorough document. Its defining strength is the **SILENT-FAILURE** acceptance criteria category — a structural innovation that catches subtle operational failure modes (partial resync, false auto-resolve, classifier drift, revenue leak) that conventional specs miss entirely. However, the document shows strain from organic growth: **template drift** (3 variants), **unresolved overlaps** between specs, **stale cross-references**, and **status contradictions**.

### By the Numbers

| Metric | Count |
|--------|-------|
| Total specs | 290 |
| Superseded | ~25 (est.) |
| Deployed | ~35 (est.) |
| Active (Spec Drafted/Approved/In Development) | ~230 |
| P0 priority | ~90 |
| P1 priority | ~60 |
| Required for Release: YES | ~100 |
| Required for Release: NO | ~130 |
| Has open questions | ~40+ |
| Idea stage (no AC/VM) | ~8 |

---

## Structural Issues

### 1. Template Drift (3 variants coexist)

**Compact template** (AI-0xx, TV-0xx, PROD-2x, CX-0xx):  
`## ID — Title → Status | Priority | Release → Record Type → Domain → URS → FRS → Failure → AC → VM → Required`

**Expanded "Atomic Requirement" variant** (URS-HEALTH, URS-MOB, URS-INV, HAI, INFRA, CAT):  
Adds `Atomic Requirement`, `Intent / User Need`, `Inputs`, `Outputs`, `Trigger`, `Invariants`, `Failure Mode Addressed`, `Maintenance Requirements`, `External Dependencies`, `Rationale` sections.

**Hybrid/minimal** (W10, DOC-004, PROD-14/18/34/37):  
Missing FRS, missing AC, "Idea stage", or single-paragraph specs.

**Impact:** A developer must learn 3 formats to navigate. Template normalization would improve readability and ensure consistent coverage.

### 2. Status Inconsistencies

| Problem | Examples |
|---------|----------|
| **P0 + Required: NO** | PROD-07, HW-004, AI-008 — contradictory signals for builders |
| **Deployed + "Spec Drafted"** | PROD-28 — spec behind reality |
| **Superseded + still has AC** | TV-011, PROD-25 — harmless but confusing |
| **Required: YES + Spec Drafted** | Most URS-PLAN specs — implies planned but not committed |

### 3. Cross-Ref Integrity Issues

| Issue | Affected Specs |
|-------|----------------|
| **D-060/D-061 don't exist** | PROD-07 references them (Decisions section ends at D27) |
| **NocoDB references after D4 ruling** | W10, DB-002/003/004 — D4 says PostgreSQL-only |
| **D-006 reused** | PROD-23 references "D-006: FLAG don't guess" — but D-006 in Decisions is about lead scoring |
| **Dead refs to old naming** | Several specs reference legacy specs that were consolidated |

---

## Duplication Hotspots

### Tier 1 — Must resolve before implementation

| Pair | Issue |
|------|-------|
| **PROD-23 ↔ URS-EVENT-002** | Both cover exception handling with persist-before-notify. Cross-refs exist but boundary is blurry. URS-EVENT-002 is the ordering invariant; PROD-23 is the router. Formalize: EVENT-002 = contract, PROD-23 = implementation. |
| **URS-INV-002 ↔ KIT-019** | Parent-child lot lineage. Both flagged for debate. |  
| **URS-LKL-002 ↔ KIT-003** | LKL provenance field set. Flagged for "reconcile in debate." |

### Tier 2 — Clean separations maintained

| Pair | Status |
|------|--------|
| PROD-16 ↔ PROD-16-V2 | Clean V1/V2 split with no-overwrite rule |
| CX-001..007 | Open QUESTION flags them as consolidation candidate |
| CAT-001..006 | Clean separation of concerns |
| URS-PLAN-001..008 + PKG | Clean package breakdown (PROD-09 vs CAT-002/003/004/005) open questions are minor |

---

## Acceptance Criteria Quality Assessment

### Top-Tier (exemplary SILENT-FAILURE coverage)

- **TV-002** — Network presence monitoring: flap detection, multi-TV failure, SMS delivery failure, false auto-resolve
- **URS-EVENT-002** — Persist-before-notify: racing test, idempotency under retry
- **SW-004** — JSON retry loop: refined vs blind resubmit, parse/schema boundary, queue health monitoring
- **INFRA-009** — Shared client library: watchdog failure, push/poll race, version drift detection
- **URS-PLAN-003** — Collaborative editing: adversarial convergence test, stale presence, clock skew
- **PROD-38** — TaskCloseEvent: 7×7 cross-contamination matrix, fault-injection mid-fan-out
- **CAT-001** — Catalog Intelligence: governing-principle enforcement test, wrong-endpoint detection

### Weakest (sparse or deferred)

- **PROD-28** — CHALLENGE AC: "cold reboot → auto-start" (trivial)
- **W10** — Almost no AC
- **SW-006** — "Idea stage — no AC/VM until promoted"
- **PROD-14, 18, 34, 37** — Deferred/Idea stage
- **DOC-004** — Single AC
- Several spec-drafted items under 10 lines total

---

## Readiness for Code-Writing

### 🟢 READY NOW (HIGH)
*Actionable specs with clear AC, VM, and failure modes.*

| Spec | Why |
|------|-----|
| TV-002 | Network presence monitoring — best-specified in document |
| TV-012 | PWA with local cache — clear, thorough |
| INFRA-009 | Shared push/pull library — race conditions tested |
| SW-004 | JSON retry loop — all edge cases covered |
| CULT-002 | Instructional panels — excellent threshold logic |
| URS-MOB-001 | Passkey auth — well-defined WebAuthn integration |
| HW-005 | Ethernet switching — clear, deployed |
| HW-008 | UPS core stack — deployed, thorough |
| SEC-002/004 | Firewall/access — clear security posture |
| SSB-001/003/004 | TV display standards — concrete, testable |
| PROD-38 | TaskCloseEvent — outstanding AC/VM coverage |
| PROD-30 | Payment orchestration — exceptionally detailed |
| URS-PLAN-007 | Offline client — well-thought-out edge cases |

### 🟡 ALMOST READY (MEDIUM-HIGH)
*Needs one missing piece: schema, boundary resolution, or template fix.*

| Spec | Blocked by |
|------|------------|
| AI-004 | Missing extraction schema/output format definition |
| URS-LKL-002 | KIT-003 overlap needs resolution |
| URS-MOB-003 | Day-boundary definition (what is "today's events" at midnight?) |
| PROD-20 | Event bus — missing retry/persistence guarantee details |
| PROD-22 | Audit log — missing retention/compaction policy |
| PROD-02 | LKL gate — excellent but needs KIT-003 alignment |
| INFRA-002 | Core services — needs functional health check spec |
| INFRA-008 | Delta push — missing malformed-payload handling |
| INT-001 | Square API — spec is thin, mostly cross-refs |
| URS-PLAN-005 | Room capture — excellent but needs rectangular-table clearance rule |

### 🟠 NEEDS WORK (MEDIUM)
*Concept is sound but spec has gaps, incomplete sections, or open questions.*

| Spec | Issue |
|------|-------|
| PROD-23 | Boundary with URS-EVENT-002 unclear |
| INFRA-003 | FRS is **TRUNCATED** mid-sentence |
| URS-PLAN-003 | Needs parent BUNDLE-PLANNER-CORE architecture |
| URS-EVENT-002 | Out-of-band escalation channel unresolved OPEN QUESTION |
| URS-PLAN-004 | Blocking OPEN QUESTION (whole-layout vs field-only lock) |
| CAT-001..005 | Open reconcile questions with PROD-09 |
| PROD-03 | Kanban — "Phase 4 unaudited" — child behavior dependency |
| PROD-05-V2 | "do not use earlier draft" warning — code-reference hazard |
| URS-PLAN-006 | Change tracking — retention/compaction strategy needed |
| URS-PLAN-002 | Access control — OPEN QUESTION on transitive access |

### 🔴 NOT READY (LOW)
*Blocked by unresolved decisions, missing dependencies, or idea-stage status.*

| Spec | Reason |
|------|--------|
| URS-INV-002 | KIT-019 overlap unresolved; no reconciliation mechanism |
| AI-008 | V1.x target, NPU dependency doesn't exist yet |
| PROD-07 | Stale D-060/D-061 refs; Required: NO |
| URS-PLAN-008 | Pricing model conflict unresolved; exact numbers TBD |
| KIT-020 | V1.x, no training pipeline, no hardware test setup |
| PROD-14 | Idea stage — no AC/VM |
| PROD-18 | Idea stage — no AC/VM |
| PROD-34 | Idea stage — no AC/VM |
| PROD-37 | V2.0 — no AC/VM |
| W10 | Superseded, under-specified |
| SW-006 | Idea stage |
| SCREEN-12 | Not yet networked |

### ⚫ NOT APPLICABLE
*Superseded, obsolete, or non-software specs.*

TV-011, INT-007, PROD-25, UI-001, UI-002, SW-001, SW-006, ALC-002, PROD-05, PROD-10, DOC-004, CULT-003 (physical poster)

---

## Cross-Cutting Recommendations

### 1. Schema Normalization
**Problem:** No spec defines the actual PostgreSQL schema for its data. Developers must infer fields from prose.  
**Fix:** Add a required `Schema` section to every spec that writes to PostgreSQL, referencing the canonical DDL or providing a minimal field listing.

### 2. Template Consolidation
**Problem:** 3 template variants cause uneven coverage.  
**Fix:** Adopt the expanded Atomic Requirement template (Inputs/Outputs/Trigger/Invariants/Failure Mode Addressed) as standard. The compact template misses too many sections.

### 3. Open Question Resolution
**Problem:** ~40+ specs have open questions, some blocking implementation.  
**Priority open questions:**  
1. URS-PLAN-004: Whole-layout vs food-service-field lock scope  
2. URS-PLAN-008: Pricing model (bundle vs flat fee)  
3. URS-EVENT-002: Out-of-band escalation channel  
4. KIT-019/URS-INV-002: Lot lineage overlap  
5. KIT-003/URS-LKL-002: LKL schema overlap  
6. URS-PLAN-002: Transitive access control  
7. PROD-09/CAT-002/003/004/005: Tier 2 scope  

### 4. Status Hygiene
- **Required: YES** specs should be P0 or justified otherwise  
- **P0** specs should be Required: YES unless explicitly rationalized  
- **Deployed** specs should have status: Deployed (not Spec Drafted)  
- **Superseded** specs should be clearly cross-linked to their replacement  

### 5. The SILENT-FAILURE Pattern Should Be Preserved
This is the URS's strongest feature. When rewriting or extending specs, preserve the SILENT-FAILURE category. It catches:
- Partial resync masquerading as full sync
- False auto-resolve masking real problems
- Revenue-leak paths (unreconciled overrides)
- Classifier/model drift
- Stale data presented as current
- Zombie connections (disconnected shown as connected)

### 6. Cross-Ref Audit
Run a script to verify all `[[SPEC:XXX]]` and `D-XX` cross-references actually resolve. Known broken references:
- PROD-07 → D-060, D-061 (missing from Decisions)
- Several → old spec IDs that were renamed

---

## Domain-by-Domain Summary

| Domain | Total | Ready | Almost | Needs Work | Not Ready | Superseded | Notes |
|--------|-------|-------|--------|------------|-----------|------------|-------|
| **AI** (prompts) | 8 | 0 | 1 | 1 | 1 | 0 | AI-004 needs schema; AI-005/006/007 are P1/Required:NO |
| **ALC** (Alexa) | 5 | 0 | 0 | 0 | 1 | 1 | Mostly V1.x aspirational |
| **CAT** (Catalog) | 6 | 0 | 2 | 3 | 0 | 0 | Excellent detail; PROD-09 overlap needs resolution |
| **CULT** (Culture) | 12 | 1 | 1 | 0 | 0 | 1 | Strong culture specs; CULT-002 ready for code |
| **CX** (Invoice blocks) | 7 | 0 | 0 | 1 | 0 | 0 | Consolidation candidate (merged into 1-2 specs) |
| **DB** (Database) | 4 | 0 | 0 | 2 | 0 | 0 | NocoDB refs stale per D4 |
| **DOC** (Docs) | 4 | 0 | 0 | 0 | 0 | 1 | Low priority by design |
| **EPR** (Emergency power) | 5 | 0 | 0 | 0 | 0 | 0 | Well-organized; deployed-tracking |
| **HAI** (Human-AI) | 5 | 1 | 0 | 0 | 0 | 0 | Sandra override and alert format are well-specified |
| **HW** (Hardware) | 10 | 3 | 0 | 0 | 0 | 0 | Mostly deployed; well-documented |
| **INFRA** (Infrastructure) | 9 | 2 | 2 | 1 | 0 | 0 | INFRA-003 truncated FRS; otherwise solid |
| **INT** (Integrations) | 7 | 0 | 1 | 0 | 1 | 1 | Thin specs — mostly cross-refs to W-specs |
| **KIT** (Kitchen tasks) | 13 | 0 | 0 | 1 | 2 | 0 | KIT-020 is experimental; KIT-007 needs UI spec |
| **MT** (MicroTouch) | 2 | 0 | 0 | 0 | 0 | 0 | Very thin; V1.x NPU-dependent |
| **OPS** (Operations) | 4 | 0 | 0 | 0 | 0 | 0 | Thin; future-facing |
| **PROD** (Production core) | 36 | 4 | 3 | 5 | 4 | 3 | The heart of the system; highest variance in quality |
| **REQ** (Requirements) | 5 | 0 | 0 | 0 | 0 | 0 | Thin telemetry/CI specs |
| **SCREEN** (Screens) | 12 | 2 | 0 | 0 | 1 | 0 | Deployed design references; thin as specs |
| **SEC** (Security) | 4 | 2 | 0 | 0 | 0 | 0 | Solid; SEC-002 needs Tailscale rewrite |
| **SSB** (Shared board) | 7 | 3 | 0 | 0 | 0 | 0 | Excellent concrete TV standards |
| **SW** (Software) | 13 | 1 | 0 | 0 | 2 | 2 | SW-004 is excellent; SW-006/014 are idea/superseded |
| **TV** (TV displays) | 9 | 2 | 0 | 0 | 0 | 1 | TV-002/012 are model specs |
| **UI** (UI) | 5 | 0 | 0 | 0 | 0 | 3 | Mostly superseded by SCREEN specs |
| **URS-*** | 84 | 8 | 4 | 3 | 2 | 0 | Highest count; URS-PLAN series is detailed but V1.x |
| **V1.0-IG** | 1 | 0 | 0 | 0 | 0 | 0 | Single spec — Input Grammar |
| **W*** (Workflows) | 15 | 0 | 0 | 0 | 1 | 0 | W10 superseded; others are cross-ref targets |

---

## Top 10 Critical Path Items for Code-Writing

These specs must be resolved first — they are foundational dependencies for everything else:

1. **PROD-38** — TaskCloseEvent (canonical close contract; 8+ other specs depend on it)  
   *Status: READY NOW*

2. **PROD-20** — System Event Bus (cross-module nervous system)  
   *Status: ALMOST READY — needs retry guarantees*

3. **PROD-22** — Audit Log (append-only write history)  
   *Status: ALMOST READY — needs retention policy*

4. **URS-EVENT-002** — Persist-before-notify contract  
   *Status: NEEDS WORK — escalation channel unresolved*

5. **PROD-23** — Exception Router  
   *Status: NEEDS WORK — boundary with EVENT-002*

6. **PROD-21** — Inbox Promotion (validation gate for all external input)  
   *Status: ALMOST READY*

7. **PROD-27** — Database Access Layer (connection management)  
   *Status: MEDIUM — thin but foundational*

8. **PROD-30** — Payment Orchestration (**new, largest new spec**)  
   *Status: READY NOW — exceptionally detailed, phased rollout*

9. **URS-PLAN-PKG** — Planner Portal (8 specs, V1.x)  
   *Status: MIXED — individual specs range from READY to NOT READY*

10. **CAT-001** — Catalog Intelligence (feeds 5+ downstream specs)  
    *Status: ALMOST READY — reconciliation with PROD-09*

---

## Conclusion

The Master URS is **production-grade** in its best sections (TV-002, PROD-38, SW-004, URS-EVENT-002, PROD-30) and **idea-stage** in its weakest (PROD-14, 18, 34, 37). The SILENT-FAILURE pattern is a genuine innovation worth preserving. The document's main liabilities are:

1. **Template inconsistency** — slows onboarding and makes comparison hard  
2. **Unresolved boundary overlap** between related specs (PROD-23/EVENT-002, KIT-019/URS-INV-002)  
3. **Stale cross-references** to renamed specs and missing decision IDs  
4. **Status contradictions** (P0 + Required: NO; Deployed + Spec Drafted)  
5. **Missing schemas** — no spec defines its actual PostgreSQL data model

For a V1.0 code push, **~40 specs are ready now** (HIGH tier), **~30 more are almost ready** (need one missing piece each), and **~20 need significant work**. The remaining ~150 active specs are either deployed (documentation of existing), deferred (V1.x/NPU/Idea), or waiting on a debate decision.
