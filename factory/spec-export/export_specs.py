#!/usr/bin/env python3
"""
export_specs.py — mirror spec.taza_os_user_requirement_specifications to CSV, live.

THE RULE (Nick, 2026-10-15): "Any exported csv needs to update any time the database is
updated. It can't get stale." And: it must mirror THE TABLE, not some older artifact.

WHAT THIS IS NOT: it is not tools/murs-specs.py. That tool parses master-urs.md (a markdown
file) into urs/tables/*.tsv. That is a different artifact from a different source and can
disagree with Postgres. This exporter reads ONLY the database.

HOW THE ROWS ARE TAKEN: `COPY (...) TO STDOUT WITH CSV HEADER`. That is Postgres's own CSV
writer, so embedded newlines, commas and quotes in the 65 text columns are quoted correctly.
A hand-rolled tab splitter is WRONG here -- 4 rows carry embedded newlines, which silently
shreds them into 14 extra bogus rows. Do not go back to splitting on tabs.

WHAT IT WRITES (both under this directory, nowhere else):
  specs.csv        the mirror
  specs.meta.json  provenance: table, row count, column list, watermark, content hash

ATOMIC: builds a temp file in this directory, fsyncs, then os.replace(). A reader can never
see a half-written CSV.

UNCHANGED => NO WRITE: it exits 0 without touching the file when the watermark is identical,
so a poller can run it every minute cheaply.

READ-ONLY against Postgres: SELECT only, via ssh to the estate host. Writes no secrets.
"""
import os, sys, csv, io, json, subprocess, tempfile, datetime, argparse

HERE     = os.path.dirname(os.path.abspath(__file__))
OUT_CSV  = os.path.join(HERE, "specs.csv")
OUT_META = os.path.join(HERE, "specs.meta.json")

DB_NAME    = os.environ.get("SPEC_DB_NAME", "spec")
DB_USER    = os.environ.get("SPEC_DB_USER", "taza")
SSH_TARGET = os.environ.get("SPEC_DB_SSH", "taza@192.168.2.102")
TABLE      = "spec.taza_os_user_requirement_specifications"
SCHEMA, TBL = TABLE.split(".")


def ssh_psql_copy(sql: str) -> str:
    """One COPY ... TO STDOUT WITH CSV HEADER, run on the estate host. Returns CSV text."""
    inner = f"\\copy ({sql}) to stdout with csv header"
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", SSH_TARGET,
         f"psql -d {DB_NAME} -U {DB_USER} -c {json.dumps(inner)}"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql COPY failed (rc={r.returncode}): {r.stderr.strip()[:400]}")
    return r.stdout


def ssh_psql_scalar(sql: str) -> str:
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", SSH_TARGET,
         f"psql -d {DB_NAME} -U {DB_USER} -At -c {json.dumps(sql)}"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed (rc={r.returncode}): {r.stderr.strip()[:400]}")
    return r.stdout.strip()


def live_columns() -> list[str]:
    """Every column of the live table, in table order — never a hardcoded list."""
    out = ssh_psql_scalar(
        "select string_agg(column_name, ',' order by ordinal_position) "
        "from information_schema.columns "
        f"where table_schema='{SCHEMA}' and table_name='{TBL}';")
    if not out:
        raise RuntimeError("could not read the live column list")
    return out.split(",")


def watermark(all_versions: bool) -> dict:
    where = "" if all_versions else "where is_current"
    out = ssh_psql_scalar(
        f"select count(*) || '|' || coalesce(max(updated_at)::text,'') || '|' || "
        f"coalesce(md5(string_agg(t::text, E'\\n' order by spec_id)),'') "
        f"from {TABLE} t {where};")
    rows, newest, h = (out.split("|") + ["", "", ""])[:3]
    return {"rows": int(rows or 0), "max_updated_at": newest, "hash": h}


def atomic_write(path: str, body: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-", suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_meta() -> dict:
    try:
        with open(OUT_META, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-versions", action="store_true", help="every row, not only is_current")
    ap.add_argument("--force", action="store_true", help="rewrite even if unchanged")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    say = (lambda *a: None) if args.quiet else (lambda *a: print(*a, flush=True))

    columns = live_columns()
    wm = watermark(args.all_versions)

    prev = read_meta()
    if (not args.force
            and prev.get("hash") == wm["hash"]
            and prev.get("columns") == columns
            and prev.get("all_versions", False) == args.all_versions):
        say(f"no change ({wm['rows']} rows, newest {wm['max_updated_at']}) — nothing written")
        return 0

    where = "" if args.all_versions else " where is_current"
    text = ssh_psql_copy(f"select * from {TABLE}{where} order by spec_id")

    # Validate Postgres's own CSV before trusting it, and get the true row count.
    parsed = list(csv.reader(io.StringIO(text)))
    if not parsed:
        raise RuntimeError("COPY returned nothing")
    header, body = parsed[0], parsed[1:]
    if header != columns:
        raise RuntimeError(f"header mismatch: COPY gave {len(header)} cols, table has {len(columns)}")
    if wm["rows"] and len(body) != wm["rows"]:
        raise RuntimeError(f"row count mismatch: COPY parsed {len(body)}, watermark says {wm['rows']}")
    ragged = [i for i, r in enumerate(body) if len(r) != len(columns)]
    if ragged:
        raise RuntimeError(f"ragged rows (bad quoting): {ragged[:5]}")

    atomic_write(OUT_CSV, text)
    with open(OUT_META, "w", encoding="utf-8") as fh:
        json.dump({
            "table": TABLE,
            "source": f"postgres {DB_NAME} @ {SSH_TARGET} via 'COPY ... TO STDOUT WITH CSV HEADER'",
            "authority": "THE DATABASE IS THE SOURCE OF TRUTH. This CSV is only a mirror of it.",
            "not_this": "urs/tables/*.tsv come from tools/murs-specs.py parsing master-urs.md — different source",
            "rows": len(body),
            "columns": columns,
            "all_versions": args.all_versions,
            "max_updated_at": wm["max_updated_at"],
            "hash": wm["hash"],
            "written_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "csv_path": OUT_CSV,
            "csv_bytes": len(text),
        }, fh, indent=2)
        fh.write("\n")

    say(f"wrote {OUT_CSV}: {len(body)} rows, {len(columns)} cols, newest {wm['max_updated_at']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"export_specs: FAILED: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
