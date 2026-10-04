# Change Log — mURS / Taza OS pipeline

## 2026-10-04 — Read-only production viewer role (`viewer_ro`)

**Decision:** D32, recorded in `decisions_log` (`tazaos`, n100).

**Why.** Browsing production used the shared `taza` account — the existing PGAdmin
connection in `~/pgadmin-servers.json` (host `172.17.0.1`, user `taza`) — which
carries full write and DDL privilege on `tazaos`, including `murs_specs` and
`decisions_log`. Nick's stated fear was that an agent operating inside Taza OS
could corrupt a live production database. Nick approved a read-only viewer role
on 2026-10-04.

**What changed.** Created Postgres role `viewer_ro`:

- `SELECT` only, on all tables in schemas `public` and `intake` (188 tables)
- `default_transaction_read_only = on`, pinned at role level so the guard
  survives any client — this is the actual enforcement
- `statement_timeout = 60s`
- not superuser, no `createdb`, no `createrole`
- verified after creation: **zero** non-`SELECT` privileges granted

**Not changed.** App writes and migrations continue under separate privileged
roles. No data was modified. No tables or columns were added or dropped.

**Open items.**
- PGAdmin connection must be repointed from `taza` to `viewer_ro`. Credential
  at `/home/taza/viewer_ro.cred` on n100 (chmod 600, not echoed here).
- `pg_hba.conf` has no line permitting `viewer_ro` over TCP from any host, so a
  `pg_hba` entry is required once the PGAdmin host is known.
- Full `pg_dump` of `tazaos` must run as `postgres`: `taza` does not own
  `public.checkpoint_migrations`.

**Artifacts.**
- `/home/taza/backups/globals_pre_viewer_ro_20261004.sql` — roles before the change
- `/home/taza/backups/tazaos_20261004.dump` — full database dump
