# Taza OS URS — OPS cluster
_Exported: 2026-09-19 21:35 | 4 rows_
_Source: Notion Master URS & Specification Registry_

---
## OPS-001 — PostgreSQL daily backup with tested restore
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: database backed up automatically every night with a real tested restore path.

**Functional Requirement Specification:**  
PostgreSQL backup: daily at 3am, 30-day retention, tested restore.

**Failure Behavior:**  
Fallback: manual pg_dump; Notion export (degraded).

**Acceptance Criteria:**  
NORMAL:
1. A backup runs daily at 3am, retained for 30 days.
2. A restore from a backup is tested and confirmed to actually work, not just that the backup file exists.

EDGE:
3. Restoring from a backup taken mid-write (transaction in progress at 3am) produces a consistent database, not a corrupted one.
4. Backups older than 30 days are actually purged — confirm retention cleanup runs, not just that new backups accumulate indefinitely.

NEGATIVE:
5. A backup job that fails (disk full, DB unreachable) is alerted, not silently skipped with no one aware the day's backup didn't happen.

SILENT FAILURE:
6. A backup file that exists but is corrupt/truncated (bad backup, not a missing one) is the classic silent-failure trap — verify the tested-restore step actually catches this, on a real recurring cadence, not just once at initial setup.
7. Restore procedure itself drifting out of date (schema changes since the restore script was written) must be caught by periodic re-testing, not assumed still-valid indefinitely.

**Verification Method:**  
1) Scheduled-job test: confirm the 3am backup runs and produces a valid file across multiple real days. 2) Restore-drill: periodically (documented cadence) actually restore a backup to a scratch environment and verify data integrity, not just file existence. 3) Retention test: confirm backups older than 30 days are purged. 4) Failure-alert test: simulate a backup failure (disk full), confirm an alert fires rather than silent skip. 5) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/PostgreSQL-daily-backup-with-tested-restore-3cfe152fc1998142a6bacb8e3610dade_

---
## OPS-002 — Health monitoring (services checked every 5min)
**Status:**  | **Priority:** P1 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: every service checked every 5min, alert naming the specific service if down more than 10min.

**Functional Requirement Specification:**  
Health monitoring: all services checked every 5 minutes; alert if down more than 10 minutes, identifying which service.

**Failure Behavior:**  
Fallback: manual docker ps daily.

**Acceptance Criteria:**  
Alert fires within 15min of failure; identifies which service

**Verification Method:**
1. [AUTO] Cadence: all services checked every 5 min. Evidence: log.
2. [AUTO] Alert: service down >10 min → alert within 15 min naming the service. Evidence: test kill + log.
3. [NICK] Live: Nick receives a health alert naming a specific service. Evidence: screenshot.

**Required for Release:**  
NO

_Notion: https://app.notion.com/p/Health-monitoring-services-checked-every-5min-3cfe152fc199810e8dfdef7f12fa9fb3_

---
## OPS-003 — Disaster recovery procedure (<4h rebuild)
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: documented, tested disaster-recovery procedure rebuilding the system from backups on spare hardware in under 4 hours.

**Functional Requirement Specification:**  
Disaster recovery: a documented procedure, tested on spare hardware, that rebuilds the system from backups in under 4 hours.

**Failure Behavior:**  
Fallback: rebuild from Notion + Square (degraded).

**Acceptance Criteria:**  
NORMAL:
1. A documented DR procedure exists.
2. That procedure, executed on spare hardware, rebuilds the full system from backups in under 4 hours.

EDGE:
3. The DR test rebuild produces a system that's actually functionally correct (services start, data is intact and queryable), not just 'the timer stopped under 4 hours' with a broken result.
4. The procedure is followable by someone other than the person who wrote it (a real test of whether it's actually documented well enough, not just tribal knowledge in Nick's head).

NEGATIVE:
5. A DR attempt that fails partway (missing dependency, wrong version) is caught and fixed in the procedure before being relied upon — not discovered for the first time during a real disaster.

SILENT FAILURE:
6. The procedure going stale (system architecture changes since it was last tested) is the biggest risk to a DR plan — verify there's a re-test cadence, not a single successful test that's then trusted indefinitely.
7. 'Rebuilds from backups' assumes the backups themselves are good — this DR test is only meaningful if it's run using the actual current backup artifacts (see OPS-001's tested-restore), not a hand-picked known-good snapshot.

**Verification Method:**  
1) Full DR drill: execute the documented procedure on spare hardware, using real current backups, timed end-to-end, confirm under 4 hours AND functional correctness of the rebuilt system. 2) Independent-operator test: have someone other than the procedure's author follow it, confirm it's actually sufficient documentation. 3) Recurring re-test cadence: schedule periodic DR drills (e.g. quarterly) so the procedure doesn't go stale against real system changes. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Disaster-recovery-procedure-4h-rebuild-3cfe152fc19981ad8f9edd280ec9c0ee_

---
## OPS-004 — Thermal management
**Status:**  | **Priority:** P0 | **Release:** V1.0

**Record Type:**  
Atomic Requirement

**Domain:**  
Operational Monitoring

**User Requirement Statement:**  
Need: server hardware kept within safe thermal limits (intake filter, clear airflow, idle <50°C, stress <75°C).

**Functional Requirement Specification:**  
Thermal: intake filter installed, airflow clear, idle temp under 50°C, stress temp under 75°C.

**Failure Behavior:**  
Fallback: USB fan; relocate the box.

**Acceptance Criteria:**  
NORMAL:
1. Intake filter installed, airflow path clear, idle temp stays under 50°C, stress temp stays under 75°C.

EDGE:
2. Sustained peak load (worst realistic case — heavy inference + multiple concurrent WS broadcasts) still stays under the 75°C stress ceiling, not just a synthetic benchmark load.
3. Ambient kitchen temperature on the hottest realistic day (summer, ovens running) is factored into the test — not just a cool testing-room measurement.

NEGATIVE:
4. A partially-blocked filter (dust buildup over time, not fully blocked) still keeps temps in range — verify there's margin, not a system tuned to just barely pass with a brand-new filter.

SILENT FAILURE:
5. Thermal throttling kicking in silently (CPU self-protects by slowing down) would degrade performance without an obvious error — verify temps are actively monitored (ties to the health dashboard) so a slow creep toward the ceiling is visible before it causes throttling, not discovered after the fact.
6. Filter degradation over months of kitchen grease/dust exposure is a real maintenance risk — flag as requiring a periodic physical inspection/replacement cadence, not a one-time install check.

**Verification Method:**  
1) Thermal test: idle and sustained-stress temperature readings under real kitchen ambient conditions (hottest realistic day), confirm both thresholds hold. 2) Monitoring-integration check: confirm live temp readings feed the health dashboard (HEALTH 1) so a creep toward the ceiling is visible before throttling occurs. 3) Maintenance-cadence: establish and document a periodic filter-inspection schedule. 4) Nick will test manually. Verification will be by 100% inspection and hands-on interaction, where user intent is verified to produce the desired output. Proof (screenshots, reports, etc.) will be captured and documented.

**Required for Release:**  
YES

_Notion: https://app.notion.com/p/Thermal-management-3cfe152fc19981c687e9c30f2269da70_
