#!/usr/bin/env python3
"""
Reference resolver for the mURS corpus.

Implements Nick's Excel 'dynamic pointer' idea, mapped onto specs:

- The registry (master-urs.csv + planner-urs-rows.csv) is the NAMED-FIELDS table.
  Spec ID = the name. It survives renames because we update ONE row, not every
  mention (same reason a named range survives a cell move).
- [[SPEC:ID]] is the dynamic pointer — static prose + resolved reference.
- A legacy alias (CLOSE 1, KIT-101, D-019...) resolves through alias-map.tsv.
- Anything unresolved reports like an Excel #REF! — dangling, never silent.

Usage:
  python3 urs/refs.py check      # scan corpus for refs, report dangling/aliases
  python3 urs/refs.py render ID  # human-readable view of one spec, refs expanded
"""
import csv, glob, os, re, sys

REG = {}
for path in glob.glob('master-urs.md'):
    for block in re.split(r'(?m)^## ', open(path, encoding='utf-8').read()):
        head = block.split('\n', 1)[0].strip()
        if ' — ' in head:
            sid, name = head.split(' — ', 1)
            REG[sid.strip()] = name.strip()

ALIAS = {}
for row in csv.reader(open('urs/alias-map.tsv', encoding='utf-8'), delimiter='\t'):
    if row and row[0] != 'alias' and len(row) >= 2 and row[1]:
        ALIAS[row[0]] = row[1]

CLUSTER = {}
for path in ['master-urs.md']:
    cl = os.path.basename(path)[:-3]
    for line in open(path, encoding='utf-8'):
        if line.startswith('## '):
            code = line[3:].split(' — ',1)[0].strip()
            CLUSTER[code] = cl

TOKEN = re.compile(r'\[\[SPEC:([A-Za-z0-9._-]+)\]\]')

def resolve(rid):
    """rid -> (status, canonical_id, title). status: ok | alias | dangling"""
    if rid in REG:
        return ('ok', rid, REG[rid])
    if rid in ALIAS and ALIAS[rid] in REG:
        return ('alias', ALIAS[rid], REG[ALIAS[rid]])
    return ('dangling', rid, '')

def render(text):
    def rep(m):
        rid = m.group(1)
        st, cid, title = resolve(rid)
        if st == 'ok':
            return f"{cid} · {title}"
        if st == 'alias':
            return f"{rid} → {cid} · {title}"
        return f"{rid} · [MISSING]"
    return TOKEN.sub(rep, text)

def check():
    problems = []
    for path in sorted(['master-urs.md']):
        text = open(path, encoding='utf-8').read()
        for m in TOKEN.finditer(text):
            rid = m.group(1)
            st, cid, title = resolve(rid)
            if st == 'dangling':
                problems.append((path, rid, 'dangling'))
            elif st == 'alias':
                problems.append((path, rid, f'alias->{cid}'))
    return problems

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("usage: refs.py check | render <ID>")
    cmd = sys.argv[1]
    if cmd == 'check':
        probs = check()
        print(f"{len(probs)} token problems")
        for p, rid, what in probs:
            print(f"  {p:28s} {rid:16s} {what}")
    elif cmd == 'render':
        sid = sys.argv[2]
        # find the spec block
        for path in ['master-urs.md']:
            text = open(path, encoding='utf-8').read()
            for block in re.split(r'(?m)^## ', text)[1:]:
                code = block.split('\n',1)[0].split(' — ',1)[0].strip()
                if code == sid:
                    print(f"## {sid} · {REG.get(sid,'?')}  ({CLUSTER.get(sid,'?')})\n")
                    print(render(block))
                    sys.exit(0)
        sys.exit(f"{sid} not found")
