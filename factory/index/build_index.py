#!/usr/bin/env python3
"""
build_index.py — ONE file that answers "what is in this repo and what is it for?"

WHY: a broad `find *.py` in /home/taza/repo returns 1,378 paths to an agent. It cannot read
them, so it reads a few and guesses the rest. Measured 2026-10-15: the architect slot burned
10 minutes and still asked Nick questions it could have answered, because finding the right
file was a search problem instead of a lookup problem. Same repo, same 10 minutes, but the
answer was one file away.

This writes FACTORY-SIDE artifacts only (no markdown — the one-markdown rule holds):
  index.json     every real source file: path, size, mtime, kind, purpose, host, spec_ids
  index.tsv      the same, flat, for grep
  stats.json     counts + when it was built

Machine-written on a timer, like architecture.json. It cannot drift from reality because
nobody edits it.

WHAT COUNTS AS "REAL SOURCE": tracked-by-intent files a human would care about, EXCLUDING
dependency noise. Measured: of 3,631 files in the repo, 2,769 are inside a .venv and 1,406
are .pyc bytecode — 76% is noise that buries ~136 real .py files. Those are excluded, which
is what makes a lookup possible.

PURPOSE is derived from the best available signal, in order:
  1. the file's own docstring / first comment line  (the author's words, not a guess)
  2. a systemd unit next to it (Description=)
  3. the filename, humanised
The purpose is CUT to one line. This is an index, not a description of everything.

Host is derived from the path (product/n100 -> n100, product/gflip -> gflip, factory -> factory).
spec_ids are found by grepping the file for URS-style ids, so the index links code to specs.
"""
import json, os, re, subprocess, sys, datetime
from collections import Counter, defaultdict

REPO = os.environ.get("INDEX_REPO", "/home/taza/repo")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# What a human cares about. Deliberately NOT: .pyc, .venv, node_modules, __pycache__, .git.
KINDS = {
    ".py": "python",
    ".sh": "shell",
    ".ts": "typescript",
    ".html": "html",
    ".service": "systemd-unit",
    ".timer": "systemd-timer",
    ".json": "data",
    ".tsv": "table",
    ".csv": "table",
    ".yml": "config",
    ".yaml": "config",
    ".sql": "sql",
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
             ".aider.tags.cache.v4", ".pi", "dist-info", ".mypy_cache", ".ruff_cache"}
MAX_BYTES = 3_000_000  # skip anything enormous (data dumps, models)

# URS-style spec ids: PROD-19, SSB-001, URS-KIT-103, AI-001, HAI-003, SCREEN-03, W9 ...
SPEC_RE = re.compile(r"\b((?:URS-[A-Z]+|[A-Z]{2,6})-\d{1,4})\b")


def humanise(name: str) -> str:
    base = re.sub(r"\.[a-z]+$", "", name)
    base = base.replace("_", " ").replace("-", " ")
    return base.strip().capitalize()[:100]


def purpose_of(path: str, ext: str) -> str:
    """The author's own one-liner, or a systemd Description, or a humanised filename."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
    except OSError:
        return humanise(os.path.basename(path))

    if ext == ".py":
        # The house style puts """ on its own line and the sentence on the NEXT line:
        #     """
        #     checklist_app -- CONSUMES the intercom. Does not read invoices.
        # so match the block, then take the first non-empty LINE of it.
        # Do NOT anchor to line-start: the house style puts a shebang on line 1 and the
        # triple quote on line 2, so ^\s*""" never matches. Take the first quoted block.
        m = re.search(r'(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', head, re.S)
        if m:
            for raw in m.group(1).splitlines():
                line = " ".join(raw.split())
                if not line:
                    continue
                # drop a leading "filename --" prefix the house style uses
                line = re.sub(r"^[A-Za-z0-9_.\-]+\.(py|sh)\s*[-—]{1,2}\s*", "", line)
                if len(line) > 8:
                    return line[:220]
        # a module-level comment block is the next best author's-words signal
        for raw in head.splitlines()[1:20]:
            line = raw.strip()
            if line.startswith("#") and len(line) > 14:
                body = line.lstrip("# ").strip()
                if not re.fullmatch(r"[-=_*\s]+", body):
                    return body[:220]
    if ext in (".service", ".timer"):
        m = re.search(r"(?m)^Description\s*=\s*(.+)$", head)
        if m:
            return m.group(1).strip()[:220]
    if ext == ".sh":
        for ln in head.splitlines()[:25]:
            s = ln.strip()
            if not s.startswith("#") or s.startswith("#!"):
                continue
            body = s.lstrip("# ").strip()
            # skip separators, rule lines, and headings made only of punctuation
            if len(body) < 14 or re.fullmatch(r"[-=_*#\s]+", body):
                continue
            if body.endswith(":") and len(body) < 30:
                continue
            return body[:220]
    if ext == ".html":
        m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
        if m:
            return m.group(1).strip()[:220]
    return humanise(os.path.basename(path))


def host_of(rel: str) -> str:
    parts = rel.split(os.sep)
    if "product" in parts:
        i = parts.index("product")
        if i + 1 < len(parts):
            return parts[i + 1]
    if "factory" in parts:
        return "factory"
    if parts and parts[0] in ("tools", "urs", "job_runner", "tests", "doe", "config"):
        return parts[0]
    return "repo"


def spec_ids_in(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(400_000)
    except OSError:
        return []
    return sorted(set(SPEC_RE.findall(text)))[:25]


def systemd_neighbour(rel: str) -> str:
    """A unit anywhere named like this file, so the index says what runs it."""
    base = re.sub(r"\.[a-z]+$", "", os.path.basename(rel))
    for root, dirs, files in os.walk(os.path.join(REPO, "product")):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith((".service", ".timer")) and base and base in f:
                return os.path.relpath(os.path.join(root, f), REPO)
    return ""


def walk():
    """Yield (relpath, size, mtime) for real source, walking PRUNED so noise is never seen."""
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".aider")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in KINDS:
                continue
            full = os.path.join(root, f)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if st.st_size > MAX_BYTES:
                continue
            yield os.path.relpath(full, REPO), st.st_size, int(st.st_mtime)


def main() -> int:
    if not os.path.isdir(REPO):
        print(f"build_index: repo not found: {REPO}", file=sys.stderr)
        return 1

    entries = []
    for rel, size, mtime in walk():
        ext = os.path.splitext(rel)[1].lower()
        entries.append({
            "path": rel,
            "kind": KINDS[ext],
            "bytes": size,
            "mtime": datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).isoformat(timespec="seconds"),
            "host": host_of(rel),
            "purpose": purpose_of(os.path.join(REPO, rel), ext),
            "spec_ids": spec_ids_in(os.path.join(REPO, rel)) if ext in (".py", ".sh", ".html") else [],
            "unit": systemd_neighbour(rel) if ext in (".py", ".sh") else "",
        })

    entries.sort(key=lambda e: (e["host"], e["path"]))

    by_host = Counter(e["host"] for e in entries)
    by_kind = Counter(e["kind"] for e in entries)
    by_spec = defaultdict(list)
    for e in entries:
        for s in e["spec_ids"]:
            by_spec[s].append(e["path"])

    index = {
        "what_this_is": "An index of every real source file in the one repo. Built to be READ "
                        "instead of searched: a broad find *.py returns 1,378 paths, which is "
                        "not a lookup. Machine-written; never hand-edited.",
        "repo": REPO,
        "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "counts": {"files": len(entries), "by_host": dict(by_host), "by_kind": dict(by_kind),
                   "spec_ids_referenced": len(by_spec)},
        "excluded": sorted(SKIP_DIRS) + ["*.pyc"],
        "entries": entries,
    }

    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
        fh.write("\n")

    with open(os.path.join(OUT_DIR, "index.tsv"), "w", encoding="utf-8") as fh:
        fh.write("host\tkind\tpath\tpurpose\tspec_ids\tunit\tbytes\n")
        for e in entries:
            fh.write("\t".join([
                e["host"], e["kind"], e["path"],
                e["purpose"].replace("\t", " "),
                ",".join(e["spec_ids"]), e["unit"], str(e["bytes"]),
            ]) + "\n")

    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump({"built_at": index["built_at"], "files": len(entries),
                   "by_host": dict(by_host), "by_kind": dict(by_kind),
                   "spec_ids_referenced": len(by_spec)}, fh, indent=2)
        fh.write("\n")

    print(f"index: {len(entries)} real files "
          f"({dict(by_host)}), {len(by_spec)} spec_ids linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
