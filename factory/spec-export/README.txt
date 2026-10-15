SPEC EXPORT — mirrors spec.taza_os_user_requirement_specifications to CSV, live
================================================================================

THE RULE (Nick, 2026-10-15): "Any exported csv needs to update any time the database is
updated. It can't get stale." And it must mirror THE TABLE, not some older artifact.

WHAT THIS PRODUCES
  specs.csv        every column of spec.taza_os_user_requirement_specifications,
                   is_current rows, 291 rows x 65 columns as of 2026-10-15.
  specs.meta.json  provenance: table name, row count, the live column list, the
                   watermark (max updated_at + content hash), and when it was written.
  watch.log        one line per real change; an hourly heartbeat so a quiet watcher
                   is distinguishable from a dead one.

WHAT THIS IS NOT — read this before trusting any other CSV
  urs/tables/*.tsv and export/murs_specs.csv are produced by tools/murs-specs.py, which
  parses master-urs.md (a MARKDOWN FILE). That is a different source and it CAN and DOES
  disagree with Postgres. On 2026-10-15 those files were dated Oct 2-5, and
  urs/tables/specs.tsv found 1 "checklist" match where the live table had 9.
  This service reads ONLY the database. Do not confuse the two.

HOW IT STAYS CURRENT
  watch_specs.py polls a cheap watermark every 30s:
      count(*) + max(updated_at) + md5(string_agg(every row))
  and runs the full export only when that watermark moves. The table already carries a
  BEFORE UPDATE trigger (trg_murs_specs_updated -> set_updated_at()), so updated_at is
  maintained for us. We deliberately did NOT add a second trigger: a trigger that shells
  out to gflip would make every database write depend on gflip being up.
  Typical detection latency: one interval (30s).

HOW THE ROWS ARE TAKEN
  COPY (...) TO STDOUT WITH CSV HEADER, via ssh to taza@192.168.2.102.
  That is Postgres's own CSV writer, so the embedded newlines in 4 rows of text are
  quoted correctly. Do NOT rewrite this to split on tabs: a tab splitter silently shreds
  those rows into 14 bogus extras (303 "rows" for 291 specs) — that bug was hit and fixed
  on 2026-10-15.

SAFETY
  * Read-only against Postgres. SELECT / COPY TO STDOUT only. No writes, ever.
  * Writes exactly two files, both in this directory.
  * Atomic: temp file + fsync + os.replace(). A reader never sees a half-written CSV.
  * No secrets are written anywhere.
  * On repeated failure it backs off instead of spinning.

OPERATE
  systemctl status  spec-export-watch
  systemctl restart spec-export-watch
  tail -f /home/taza/repo/factory/spec-export/watch.log

  One-shot manual refresh (also rewrites if unchanged):
      python3 /home/taza/repo/factory/spec-export/export_specs.py --force
  Export every version, not just is_current:
      python3 /home/taza/repo/factory/spec-export/export_specs.py --all-versions

FILES
  export_specs.py     the exporter (one shot; exits 0 without writing when unchanged)
  watch_specs.py      the poller; runs under systemd as spec-export-watch.service
  specs.csv           the mirror
  specs.meta.json     provenance + watermark
  watch.log           service output
