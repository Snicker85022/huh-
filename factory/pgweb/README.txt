FACTORY VIEWERS — read-only windows onto the databases that ARE the record
==========================================================================

WHY (D139, D140 / 2026-10-16)
  Nick asked to view the SPEC database and the DECISIONS changelog in a browser. He could
  not. The only viewer was nocodb.tazacateringphoenix.com, pointed at tazaos, and pg_hba.conf
  granted the docker bridge access to tazaos and dev_pipeline only — so spec and decisions
  were unreachable from any viewer at all.

  So each database that matters got its own viewer, and the URL says which one it serves.

WHAT RUNS
  pgweb-spec        8082 -> the spec database       specs.tazacateringphoenix.com
  pgweb-decisions   8083 -> the decisions database  decisions.tazacateringphoenix.com

  They run ON n100 (192.168.2.102). The tunnel runs on gflip and reaches n100 by LAN IP,
  which is why the tunnel targets 192.168.2.102:8082 / :8083 and not localhost.

READ-ONLY, BY ROLE
  Both connect as `viewer_ro` — not a superuser, no CREATE, SELECT only. Verified
  2026-10-16: UPDATE, DELETE and CREATE TABLE are all refused ("cannot execute ... in a
  read-only transaction"). A viewer cannot alter a spec or a decision. That is the whole
  point: the spec database is the sole source of truth (README-FIRST), so its viewer must
  not be able to change it.

  The password is read from the environment at run time and is NEVER stored in this file:
      export PGWEB_RO_PASSWORD="$(cat /home/taza/viewer_ro.cred)"
      docker compose up -d
  viewer_ro.cred is mode 600 on n100 and is not in the repo.

WHY pg_hba.conf WAS EDITED (D140)
  Nick challenged the assumption that pg_hba.conf is untouchable, and he was right to.
  The doctrine says two things: §5.2 lists it under "Never touch" (a caution — a bad line
  locks out every connection), and §5.8 gives the PROCEDURE: "never edit it without a
  backup and a RELOAD (not a restart), so a bad line fails without being applied."
  §5.8 is a procedure, not a prohibition. Four lines were added, each edit preceded by a
  timestamped backup and followed by a RELOAD.

  Two subnet ranges are granted because two kinds of container exist:
      172.17.0.0/16   docker0 — the two older, hand-run viewers
      172.18.0.0/16   compose's own bridge (pgweb_default)
  Docker refuses a user-defined network overlapping docker0, so a second range was narrower
  than fighting the compose default.

HOW TO RUN IT (on n100)
  scp factory/pgweb/docker-compose.yml taza@192.168.2.102:/home/taza/pgweb/
  ssh taza@192.168.2.102
  cd /home/taza/pgweb
  export PGWEB_RO_PASSWORD="$(cat /home/taza/viewer_ro.cred)"
  sudo -E docker compose up -d

A FAULT THIS FIXES, AND ONE IT DOES NOT
  The two older viewers (pgweb -> tazaos, pgweb-dev-pipeline -> dev_pipeline) were started
  by hand with `docker run`. Nothing declared them; they survive a box restart only via
  restart=unless-stopped. THIS file declares the two new ones. The old two still deserve a
  decision of their own — as does the nocodb.* alias, which is now doubly misleading
  (NocoDB retired 2026-10-04 by D37, and the name points at tazaos).
