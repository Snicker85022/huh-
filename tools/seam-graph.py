#!/usr/bin/env python3
"""seam-graph.py — the mURS cross-spec relationships as a queryable edge table.

One row per directed edge (consumer -> producer), one NONE row per leaf spec.
Sources, in priority order:
  1. authored SEAM headers (tests/harness/cross-spec/tests-from-*.md)
  2. Nick-ruled EXTRA_EDGES (verbatim from the original stamps) — overrides #1
  3. ref-mining: [[SPEC:...]] refs whose sentence carries an explicit verb
     (consumes/reads/builds on/extends/feeds/triggers/governs/...). Every mined
     edge keeps the source sentence as its rule, so it stays auditable.
Anything that can't be classified goes to urs/seam-open.tsv, never guessed.

Usage:
  python3 tools/seam-graph.py             # dry-run summary
  python3 tools/seam-graph.py --write     # write the TSVs
  python3 tools/seam-graph.py --check     # validate against master-urs.md
  python3 tools/seam-graph.py --strip     # remove CROSS-SEAM: prose from master-urs.md
"""
import argparse, csv, os, re, shutil, subprocess, sys

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, 'master-urs.md')
EDGES  = os.path.join(ROOT, 'urs/seam-stamps.tsv')
OPEN   = os.path.join(ROOT, 'urs/seam-open.tsv')
SOURCES = ['tests/harness/cross-spec/tests-from-debate-team.md',
           'tests/harness/cross-spec/tests-from-cortex.md']

SPEC_HEAD = re.compile(r'^## ([A-Za-z0-9._-]+) — (.*)$', re.M)
STATUS    = re.compile(r'\*\*Status:\*\*\s*(.*?)\s*\|\s*\*\*Priority:\*\*')
BACKTICK  = re.compile(r'`([a-z][a-z0-9_]{2,})`')
REF_RE    = re.compile(r'\[\[SPEC:([A-Za-z0-9._-]+)\]\]')

EXTRA_EDGES = [
    ('W15',           'PROD-06',     'task_chain_trigger',    'PROD-06 triggers W15 BEO on deposit confirm',             'D1-D16'),
    ('URS-CREW-001',  'W15',         'beo_checklist',         'tablet reads W15-produced BEO fixtures',                 'crew-tablet'),
    ('PROD-07',       'W15',         'kitchen_departure_time', 'reads W15-produced timeline',                          'D3-split'),
    ('W7',            'CX-001',      'invoice_block',          'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('W7',            'CX-002',      'invoice_block',          'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('W7',            'CX-003',      'invoice_block',          'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('W7',            'CX-004',      'invoice_block',          'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('W7',            'CX-005',      'invoice_block',          'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('W7',            'CX-006',      'venue_departure',        'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('W7',            'CX-007',      'invoice_block',          'assembles CX-produced blocks, never re-generates them', 'W7-CX'),
    ('URS-CRM-002',   'W2',          'lead_tags',              'W2 tags are tags, not stages',                         'lead-stages'),
    ('URS-CRM-002',   'W7',          'ready_to_invoice',       'W7 fires at Ready to Invoice',                         'lead-stages'),
]

CONSUMES_VERBS = ['consumes', 'reads', 'depends on', 'builds on', 'extends', 'uses',
                  'fed by', 'pre-filled from', 'sourced from', 'queries', 'calls',
                  'pulls from', 'reads from', 'assembles', 'ingests']
PRODUCES_VERBS = ['feeds', 'consumed by', 'produced for', 'governs', 'sole writer',
                  'sole source', 'triggers', 'fires', 'spawns', 'emits', 'outputs',
                  'drives', 'provides']
SKIP_VERBS = ['parent', 'umbrella', 'package', 'see ', 'per ', 'resolved by',
              'detected by', 'noted', 'superseded by', 'supersedes', 'absorb',
              'absorbs', 'folded into', 'implemented by', 'implements', 'cross-ref',
              'reconcile', 'stale', 'mapped', 'alias', 'legacy', 'renamed',
              'replaced by', 'part of', 'defined in', 'described in', 'deferred',
              'via', 'through', 'with ', 'scope cut', 'merged', 'single spec']


def load_registry(text):
    return {m.group(1): m.group(2).strip() for m in SPEC_HEAD.finditer(text)}

def load_status(text):
    st = {}
    for block in re.split(r'(?m)^## ', text)[1:]:
        sid = block.split('\n', 1)[0].split(' — ', 1)[0].strip()
        m = STATUS.search(block)
        st[sid] = m.group(1).strip() if m else ''
    return st

def expand(text):
    def rng(m):
        pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        w = len(m.group(2))
        return ' '.join(f'{pre}{i:0{w}d}' for i in range(a, b + 1))
    text = re.sub(r'([A-Za-z0-9-]*-)(\d+)\.\.(\d+)', rng, text)
    def inherit(m):
        parts, out, prefix = m.group(0).split('/'), [], ''
        for tok in parts:
            full = re.match(r'^([A-Za-z][A-Za-z0-9]*-)(\d+)$', tok)
            if full:
                prefix, out = full.group(1), out + [tok]
            elif re.match(r'^\d+$', tok) and prefix:
                out.append(prefix + tok)
            else:
                out.append(tok)
        return ' '.join(out)
    return re.sub(r'[A-Za-z][A-Za-z0-9]*-[0-9]+(?:/[0-9]+)+', inherit, text)

def find_ids(text, registry):
    text = expand(text)
    return [s for s in registry if re.search(r'(?<![\w-])' + re.escape(s) + r'(?![\w-])', text)]

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40] or 'seam'

def expand_refs(text):
    def rng(m):
        a, b = m.group(1), m.group(2)
        ma, mb = re.match(r'^(.*?)(\d+)$', a), re.match(r'^(.*?)(\d+)$', b)
        if ma and mb and ma.group(1) == mb.group(1) and int(mb.group(2)) >= int(ma.group(2)) and int(mb.group(2)) - int(ma.group(2)) <= 50:
            p, n1, n2 = ma.group(1), int(ma.group(2)), int(mb.group(2))
            w = len(ma.group(2))
            return ' '.join(f'[[SPEC:{p}{i:0{w}d}]]' for i in range(n1, n2 + 1))
        return m.group(0)
    return re.sub(r'\[\[SPEC:([A-Za-z0-9._-]+)\]\]\s*\.\.\s*\[\[SPEC:([A-Za-z0-9._-]+)\]\]', rng, text)

def classify_line(line):
    low = line.lower()
    for v in SKIP_VERBS:
        if v in low:
            return None
    for v in PRODUCES_VERBS:
        if v in low:
            return 'PRODUCES'
    for v in CONSUMES_VERBS:
        if v in low:
            return 'CONSUMES'
    return None

def mine(raw, registry, status):
    mined, mutual, superseded = {}, [], []
    for block in re.split(r'(?m)^## ', raw)[1:]:
        sid = block.split('\n', 1)[0].split(' — ', 1)[0].strip()
        for line in expand_refs(block).split('\n'):
            if '[[SPEC:' not in line:
                continue
            cls = classify_line(line)
            if cls is None:
                continue
            refs = [m.group(1) for m in REF_RE.finditer(line)]
            m = BACKTICK.search(line)
            art = m.group(1) if m else 'output'
            rule = re.sub(r'\s+', ' ', line.strip())[:160]
            for x in refs:
                if x == sid or x not in registry:
                    continue
                if 'superseded' in status.get(x, '').lower():
                    superseded.append((sid, x, rule))
                    continue
                c, p = (sid, x) if cls == 'CONSUMES' else (x, sid)
                mined.setdefault((c, p), {'artifact': art, 'rule': rule, 'seam': 'ref-mine', 'source': 'ref-mine'})
    for (a, b) in list(mined):
        if (b, a) in mined:
            mutual.append((a, b))
            mined.pop((a, b), None)
            mined.pop((b, a), None)
    return mined, mutual, superseded

def parse_seams(registry):
    seams = []
    for rel in SOURCES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        for ln_no, line in enumerate(open(path, encoding='utf-8'), 1):
            if not line.startswith('SEAM:'):
                continue
            body = line[5:].strip()
            core = re.sub(r'\([^)]*\)', ' ', body)
            desc = re.search(r'\(([^)]+)\)', body)
            tag = slug(desc.group(1) if desc else body[:40])
            seg = [s for s in re.split(r'\s*(?:->|→)\s*', core) if s.strip()] if ('->' in core or '→' in core) else []
            seams.append({'file': os.path.basename(rel), 'line': ln_no, 'body': body,
                          'tag': tag, 'seg': seg, 'ids': find_ids(core, registry)})
    return seams

def build(registry, status):
    seams = parse_seams(registry)
    edges, open_rows = {}, []
    for s in seams:
        ids = s['ids']
        if 'SEC-002' in s['body'] and 'consumers' in s['body']:
            open_rows.append((s, 'human-consumer', 'SEC-002 — consumer is Nick (human operator)'))
            continue
        if 'all consumers' in s['body'] or s['body'].rstrip().endswith('consumers'):
            open_rows.append((s, 'no-named-consumer', 'HW topology — "all consumers"'))
            continue
        if 'all PostgreSQL writers' in s['body']:
            open_rows.append((s, 'no-named-consumer', 'PROD-20 x PROD-27 — "all writers"; delegated (Q3)'))
            continue
        if '<->' in s['body'] or 'circular' in s['body'].lower():
            open_rows.append((s, 'delegated', 'SCREEN-10 <-> W4 — not circular per Nick; Whisper open (Q2)'))
            continue
        if 'PROD-19' in ids and any(i.startswith('URS-KIT-10') for i in ids):
            open_rows.append((s, 'conflict', 'PROD-19 <-> URS-KIT-101..107 direction disputed (Q1)'))
            continue
        if not s['seg']:
            if 'shared between' in s['body'] or 'between' in s['body'].lower():
                open_rows.append((s, 'shared-resource', 'shared resource — no single producer/consumer'))
            else:
                open_rows.append((s, 'no-direction', 'voice stack — no direction stated'))
            continue
        for i in range(1, len(s['seg'])):
            prods = find_ids(s['seg'][i-1], registry)
            cons  = find_ids(s['seg'][i], registry)
            for p in prods:
                if 'superseded' in status.get(p, '').lower():
                    open_rows.append((s, 'superseded-producer', f'{p} superseded'))
                    continue
                for c in cons:
                    if c == p:
                        continue
                    key = (c, p)
                    edges.setdefault(key, {'artifact': '', 'rule': '', 'seam': s['tag'],
                                           'source': 'debate-team' if 'debate' in s['file'] else 'cortex'})
                    m = BACKTICK.search(s['body'])
                    edges[key]['artifact'] = edges[key]['artifact'] or (m.group(1) if m else 'output')
                    edges[key]['rule'] = edges[key]['rule'] or f'{c} reads {p}-produced fixtures, never mock them'
    overrides = []
    for c, p, a, r, seam in EXTRA_EDGES:
        if (p, c) in edges:
            overrides.append((c, p))
            del edges[(p, c)]
        edges.setdefault((c, p), {'artifact': a, 'rule': r, 'seam': seam, 'source': 'nick-2026-10-01'})
    for c, p in overrides:
        open_rows.append(({'file': 'nick-2026-10-01', 'line': 0,
                           'body': f'{p} -> {c} (authored seam) reversed by Nick ruling'},
                          'nick-override', f'{c} CONSUMES {p} per the original stamp'))
    return edges, open_rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--strip', action='store_true')
    args = ap.parse_args()

    raw = open(MASTER, encoding='utf-8').read()
    registry = load_registry(raw)
    status = load_status(raw)
    edges, open_rows = build(registry, status)

    mined, mutual, superseded = mine(raw, registry, status)
    for (c, p), e in mined.items():
        if (c, p) in edges or (p, c) in edges:
            continue
        edges[(c, p)] = e
    for a, b in mutual:
        open_rows.append(({'file': 'ref-mine', 'line': 0, 'body': f'{a} <-> {b}'},
                          'mutual-mined', f'bidirectional refs {a} <-> {b} — needs a ruling'))
    for sid, x, rule in superseded:
        open_rows.append(({'file': 'ref-mine', 'line': 0, 'body': f'{sid} -> {x}'},
                          'superseded-target', f'{sid} references Superseded {x}: {rule[:70]}'))

    if args.strip:
        lines = [ln for ln in raw.split('\n') if not ln.startswith('CROSS-SEAM:')]
        shutil.copy(MASTER, MASTER + '.bak')
        open(MASTER, 'w', encoding='utf-8').write('\n'.join(lines))
        print('stripped CROSS-SEAM prose lines from master-urs.md')
        subprocess.run([sys.executable, os.path.join(ROOT, 'urs/refs.py'), 'check'], cwd=ROOT)
        return

    if args.check:
        rows = list(csv.reader(open(EDGES, encoding='utf-8'), delimiter='\t'))[1:]
        by_spec, seen, probs, warns = {}, {}, [], []
        for r in rows:
            by_spec.setdefault(r[0], []).append(r)
        for sid in registry:
            if sid not in by_spec:
                probs.append(f'{sid}: missing (no CONSUMES and no NONE row)')
            elif len(by_spec[sid]) > 1 and any(r[1] == 'NONE' for r in by_spec[sid]):
                probs.append(f'{sid}: has both NONE and edge rows')
        for r in rows:
            if r[1] == 'CONSUMES':
                t = r[2]
                if t not in registry:
                    probs.append(f'{r[0]} -> {t}: target does not resolve')
                if 'superseded' in status.get(t, '').lower():
                    warns.append(f'{r[0]} -> {t}: target is Superseded')
                if (r[0], t) in seen:
                    probs.append(f'{r[0]} -> {t}: duplicate edge')
                if (t, r[0]) in seen:
                    probs.append(f'{r[0]} <-> {t}: mutual edges')
                seen[(r[0], t)] = True
        print(f'edge rows: {len(rows)}')
        print(f'errors: {len(probs)}')
        for p in probs:
            print('  ERROR', p)
        print(f'warnings: {len(warns)}')
        for w in warns:
            print('  WARN ', w)
        return 0 if not probs else 1

    rows = []
    for (c, p), e in sorted(edges.items()):
        rows.append([c, 'CONSUMES', p, e['artifact'], e['rule'], e['seam'], e['source']])
    for sid in sorted(registry):
        if not any(r[0] == sid for r in rows):
            rows.append([sid, 'NONE', '', '', 'no cross-spec dependency identified', '', 'linter'])
    rows.sort(key=lambda r: (r[1] == 'NONE', r[0], r[2]))

    print(f'registry specs        : {len(registry)}')
    print(f'CONSUMES edges        : {sum(1 for r in rows if r[1] == "CONSUMES")}')
    print(f'  curated (seams+rulings): {sum(1 for r in rows if r[1] == "CONSUMES" and r[6] != "ref-mine")}')
    print(f'  ref-mined             : {sum(1 for r in rows if r[1] == "CONSUMES" and r[6] == "ref-mine")}')
    print(f'NONE leaf specs       : {sum(1 for r in rows if r[1] == "NONE")}')
    print(f'open seams            : {len(open_rows)}')

    if args.write:
        with open(EDGES, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh, delimiter='\t', lineterminator='\n')
            w.writerow(['spec_id', 'role', 'target_spec', 'artifact', 'rule', 'seam', 'source'])
            w.writerows(rows)
        with open(OPEN, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh, delimiter='\t', lineterminator='\n')
            w.writerow(['file', 'line', 'status', 'note', 'body'])
            for s, why, note in sorted(open_rows, key=lambda x: x[1]):
                w.writerow([s['file'], s['line'], why, note, s['body']])
        print(f'wrote {EDGES}')
        print(f'wrote {OPEN}')

if __name__ == '__main__':
    main()
