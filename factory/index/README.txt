REPO INDEX — one lookup file instead of a search
================================================

WHY THIS EXISTS (2026-10-15)
Nick: "is the way my git repos or databases structured hard to search? They all take a long
time to find information."

Measured answer: the repo is NOT slow to grep (20ms). The problem is VOLUME. A broad
`find *.py` returns 1,378 paths; a find over the repo returns 3,865. Of 3,631 files, 2,769
live inside a .venv and 1,406 are .pyc bytecode — 76% is dependency noise burying ~137 real
source files. An agent cannot read 1,378 paths, so it reads a few and GUESSES the rest.
Observed cost: the architect slot burned 10 minutes and still asked Nick questions it could
have answered from the repo.

So this is not a faster search. It is a LOOKUP: one file that already knows.

FILES
  index.json    every real source file: path, kind, bytes, host, purpose, spec_ids, unit
  index.tsv     the same, flat tab-separated — for grep by eye or by agent
  stats.json    counts only
  build.log     one line per build

WHAT IS IN IT
  331 files across 9 hosts (n100 108, factory 69, gflip 60, n100-systemd, urs, tools, …),
  covering python 137, shell 50, html 30, systemd-units 29, tables 26, typescript 19.
  112 URS spec_ids are linked back to the files that reference them.

  Excluded on purpose: .git, .venv, venv, node_modules, __pycache__, .pytest_cache,
  .aider.tags.cache.v4, dist-info, *.pyc. That exclusion is the whole point.

PURPOSE comes from the AUTHOR'S OWN WORDS, in this order:
  1. the file's docstring (first non-empty line) or its leading comment block
  2. a systemd unit's Description= when the file is a .service/.timer
  3. the <title> for html
  4. the filename humanised, as a last resort
  It is cut to one line. This is an index, not a description of everything.

HOW IT STAYS TRUE
  spec-index-build.timer runs spec-index-build.service hourly. Machine-written; nobody edits
  it, so it cannot drift from reality. Same pattern as the /architecture map.

HOW TO USE IT (for a human or an agent)
  List what is on a host:      grep -P "^n100\t" index.tsv | cut -f3,4
  Find anything about X:       grep -i "checklist" index.tsv
  Find what serves a spec:     grep -P "PROD-20|DEBT-007" index.tsv
  What runs a given script:    look at the `unit` column, or grep the .service files

  In an agent prompt, the line that matters is:
    "Read /home/taza/repo/factory/index/index.tsv FIRST. It lists every real source file
     with a one-line purpose. Use it to CHOOSE files, then read only those."

OPERATE
  systemctl list-timers spec-index-build.timer
  systemctl start spec-index-build.service      # rebuild now
  tail -5 /home/taza/repo/factory/index/build.log
