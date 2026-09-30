#!/usr/bin/env python3
"""One-time conversion: wrap all cross-references in [[SPEC:...]] pointers.

Safe-by-construction: single-pass re.sub per line (replacements are never
re-scanned), so no double-wrapping. Skips spec header lines and Notion URLs.
After conversion, refs.py check reports any pointer that doesn't resolve.
"""
import csv, glob, os, re

# --- load registry ---
REG = set()
for p in ['notion-export/master-urs.csv','notion-export/planner-urs-rows.csv']:
    for r in csv.DictReader(open(p, encoding='utf-8')):
        REG.add(r['Spec ID'].strip())

# --- load alias map, split by class ---
ALIAS = {}      # literal -> canonical  (short-form + family)
DANGLE = set()  # literals that have no spec (keep literal so check() flags them)
for row in csv.reader(open('urs/alias-map.tsv', encoding='utf-8'), delimiter='\t'):
    if not row or row[0] == 'alias':
        continue
    literal = row[0]
    cls = row[2] if len(row) > 2 else ''
    canonical = row[1] if len(row) > 1 else ''
    if cls == 'legacy-decision-ref':
        continue  # D-XXX are decision refs, not spec refs — leave raw
    if canonical:
        ALIAS[literal] = canonical
    else:
        DANGLE.add(literal)

# terms = canonical IDs + aliases + dangling literals, longest first
terms = sorted(REG | set(ALIAS) | DANGLE, key=len, reverse=True)
pat = re.compile(r'\b(' + '|'.join(re.escape(t) for t in terms) + r')\b')

def canon(t):
    if t in REG: return t
    if t in ALIAS: return ALIAS[t]
    return t  # dangling: keep literal, check() will flag it

files = sorted(glob.glob('notion-export/clusters/*.md'))
total_wrapped = 0
per_file = {}
for path in files:
    lines = open(path, encoding='utf-8').read().split('\n')
    n = 0
    for i, line in enumerate(lines):
        if line.startswith('## ') or line.startswith('_Notion:'):
            continue
        new, cnt = pat.subn(lambda m: f"[[SPEC:{canon(m.group(1))}]]", line)
        if cnt:
            lines[i] = new
            n += cnt
    if n:
        open(path, 'w', encoding='utf-8').write('\n'.join(lines))
        per_file[os.path.basename(path)] = n
        total_wrapped += n

print(f"wrapped {total_wrapped} cross-references across {len(per_file)} files\n")
for f, n in sorted(per_file.items(), key=lambda x: -x[1]):
    print(f"  {f:24s} {n}")
