dev_pipeline — ONE-TIME ARCHIVE, NOT AUTHORITATIVE

Frozen at decision D113, 2026-10-14 16:40:07 -07. Last spec-side write 2026-10-04.
This database was deprecated and then dropped on 2026-10-19 under ticket T-0059.

IT IS NOT THE TRUTH. The authoritative databases are:
    n100:5432/spec       schema spec       taza_os_user_requirement_specifications
    n100:5432/decisions  schema decisions  decisions_log, build_log, change_record

This archive exists only so the data is not lost. Restoring it would reintroduce a
stale copy of the spec and decision log, which is the exact failure T-0059 removed.

Contents: dev_pipeline_20261019.dump (pg_dump -Fc, 21 tables, 972,552 bytes)
Restore with: pg_restore -d <newdb> dev_pipeline_20261019.dump
