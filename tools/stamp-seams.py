#!/usr/bin/env python3
"""stamp-seams.py — apply Rec 6 "CROSS-SEAM" stamps, deterministically.

Seats BOTH ends of every seam an authored cross-spec test declares (SEAM: headers
in tests/harness/cross-spec/tests-from-*.md): the consumer's Dependency Notes gets
a line naming the producer it consumes and the fixture rule ("reads
<producer>-produced fixtures, never mock them").

Nothing is invented. Edges come from the authored SEAM headers; every id is
validated against the real spec registry in master-urs.md; descriptions are the
headers' own parentheticals, verbatim. Three safety valves, each reported:

  * SUPERSEDED consumers are skipped
  * seams with no NAMED consumer ("-> all writers") are left for a human
  * seams where the two authored passes DISAGREE on direction are left for a
    human (the highest-value finding per tests/harness/README.md)

Idempotent: a spec already carrying a CROSS-SEAM line is left alone.

Usage:
  python3 tools/stamp-seams.py                # dry-run
  python3 tools/stamp-seams.py --apply        # write master-urs.md + refs check
"""
import argparse, os, re, shutil, subprocess, sys, datetime

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, 'master-urs.md')
SOURCES = ['tests/harness/cross-spec/tests-from-debate-team.md',
           'tests/harness/cross-spec/tests-from-cortex.md']

SPEC_HEAD = re.compile(r'^## ([A-Za-z0-9._-]+) — (.*)$', re.M)
STATUS    = re.compile(r'\*\*Status:\*\*\s*(.*?)\s*\|\s*\*\*Priority:\*\*')
DEPNOTES  = re.compile(r'^\*\*Dependency Notes:\*\*')
VERIF     = re.compile(r'^\*\*Verification Method:\*\*')


def load_registry(text):
    return {m.group(1): m.group(2).strip() for m in SPEC_HEAD.finditer(text)}


def expand(text):
    """URS-KIT-101..107 -> URS-KIT-101 ... URS-KIT-107 ; INFRA-007/008/009 -> all three"""
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
    return re.sub(r'[A-Za-z][A-Za-z0-9]*-\d+(?:/\d+)+', inherit, text)


def find_ids(text, registry):
    text = expand(text)
    return [s for s in registry
            if re.search(r'(?<![\w-])' + re.escape(s) + r'(?![\w-])', text)]


def parse_seams(registry):
    seams = []
    idx = 0
    for rel in SOURCES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        for ln_no, line in enumerate(open(path, encoding='utf-8'), 1):
            if not line.startswith('SEAM:'):
                continue
            body = line[5:].strip()
            core = re.sub(r'\([^)]*\)', ' ', body)     # ids live outside parens
            circular = ('<->' in core) or re.search(r'circular', body, re.I)
            if circular:
                prod_txt = cons_txt = ''
            elif '->' in core or '→' in core:
                seg = re.split(r'\s*(?:->|→)\s*', core)
                prod_txt, cons_txt = ' '.join(seg[:-1]), seg[-1]
            elif re.search(r'\bbetween\b|\bshared\b', core, re.I):
                ids = find_ids(core, registry)          # mutual seam: 1st producer, rest consumers
                prod_txt, cons_txt = (ids[0] if ids else ''), ' '.join(ids[1:])
            else:
                prod_txt, cons_txt = '', ''             # no direction stated
            desc = {}
            for chunk in re.split(r'\s*\+\s*', body):
                ids, m = find_ids(chunk, registry), re.search(r'\(([^)]+)\)', chunk)
                if ids and m:
                    for s in ids:
                        desc.setdefault(s, m.group(1))
            seams.append({'idx': idx, 'file': rel, 'line': ln_no, 'body': body,
                          'prod': find_ids(prod_txt, registry),
                          'cons': find_ids(cons_txt, registry), 'desc': desc})
            idx += 1
    return seams


def find_conflicts(seams):
    """flag seams where some producer->consumer pair is asserted in BOTH directions.
    That is a real disagreement between the two authored passes -- per
    tests/harness/README.md it is the highest-value finding, so it is NOT stamped."""
    pairs = {}
    for s in seams:
        for p in s['prod']:
            for c in s['cons']:
                if p != c:
                    pairs.setdefault((p, c), set()).add(s['idx'])
    bad = set()
    for (p, c), ids in pairs.items():
        if (c, p) in pairs:
            bad |= ids | pairs[(c, p)]
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--report')
    args = ap.parse_args()

    raw = open(MASTER, encoding='utf-8').read()
    registry = load_registry(raw)
    seams = parse_seams(registry)
    conflicts = find_conflicts(seams)

    stamped, status = set(), {}
    blocks = {}
    for block in re.split(r'(?m)^## ', raw)[1:]:
        sid = block.split('\n', 1)[0].split(' — ', 1)[0].strip()
        blocks[sid] = block
        if re.search(r'(?m)^CROSS-SEAM:', block):
            stamped.add(sid)
        m = STATUS.search(block)
        status[sid] = (m.group(1).strip() if m else '')

    assigned, skipped, unresolved = {}, [], []
    for s in seams:
        if s['idx'] in conflicts:
            unresolved.append(('DIRECTION CONFLICT', s)); continue
        dead = [p_ for p_ in s['prod'] if 'superseded' in status.get(p_, '').lower()]
        if dead:
            # don't instruct consumers to run a superseded producer's tests --
            # surfacing the dangling supersession is the point (see PROD-25/PROD-10).
            unresolved.append((f'PRODUCER SUPERSEDED ({"/".join(dead)})', s)); continue
        cons = [c for c in s['cons'] if c in registry and c not in s['prod']]
        if not cons:
            unresolved.append(('NO NAMED CONSUMER', s)); continue
        for c in cons:
            if c in assigned:
                continue
            if c in stamped:
                skipped.append((c, 'already stamped')); continue
            if 'superseded' in status.get(c, '').lower():
                skipped.append((c, f"superseded ({status[c]})")); continue
            assigned[c] = s

    changes = []
    for c, s in assigned.items():
        prods, desc = s['prod'], s['desc']
        plinks = ' + '.join(f'[[SPEC:{p}]]' for p in prods)
        pdesc = f" ({desc[prods[0]]})" if len(prods) == 1 and prods[0] in desc else ''
        pids = '/'.join(prods)
        changes.append((c, (f'CROSS-SEAM: consumes {plinks}{pdesc}. '
                            f"Before {c} tests run, confirm {pids}'s [AUTO] tests pass; "
                            f'{c} tests read {pids}-produced fixtures, never mock them.'), s))

    print(f'seams parsed            : {len(seams)}')
    print(f'already stamped         : {len(stamped)}  ({", ".join(sorted(stamped))})')
    print(f'new consumer stamps     : {len(changes)}')
    for c, stamp, s in sorted(changes):
        print(f'  + {c:22s} <- {"/".join(s["prod"])}')
    print(f'skipped                 : {len(skipped)}')
    for c, why in sorted(set(skipped)):
        print(f'  - {c:22s} {why}')
    print(f'unresolved (for a human): {len(unresolved)}')
    for why, s in unresolved:
        print(f'  ? {why:20s} {os.path.basename(s["file"])}:{s["line"]}  {s["body"][:70]}')

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write(f'# Cross-seam stamps — report ({datetime.datetime.now():%Y-%m-%d %H:%M})\n\n')
            fh.write('Generated by tools/stamp-seams.py from the authored SEAM headers in\n')
            for s in SOURCES:
                fh.write(f'  - {s}\n')
            fh.write(f'\n{len(changes)} new consumer stamps; {len(stamped)} pre-existing; '
                     f'{len(skipped)} skipped; {len(unresolved)} unresolved.\n\n')
            for c, stamp, s in sorted(changes):
                fh.write(f'{c} <- {"/".join(s["prod"])}   [seam {os.path.basename(s["file"])}:{s["line"]}]\n    {stamp}\n\n')
            fh.write('## Unresolved (need a human)\n\n')
            for why, s in unresolved:
                fh.write(f'- **{why}** — {os.path.basename(s["file"])}:{s["line"]}\n    {s["body"]}\n')
        print(f'report -> {args.report}')

    if not args.apply:
        print('\n(dry-run — nothing written; pass --apply to write)')
        return

    lines = raw.split('\n')
    bounds, cur = {}, None
    for i, ln in enumerate(lines):
        m = SPEC_HEAD.match(ln)
        if m:
            if cur:
                bounds[cur][1] = i
            cur = m.group(1); bounds[cur] = [i, len(lines)]
    if cur:
        bounds[cur][1] = len(lines)
    for c, stamp, _ in changes:
        s, e = bounds[c]
        for j in range(s, e):
            if DEPNOTES.match(lines[j]) or VERIF.match(lines[j]):
                lines.insert(j + 1, stamp)
                for k in bounds:
                    if bounds[k][0] > j:
                        bounds[k][0] += 1; bounds[k][1] += 1
                break

    shutil.copy(MASTER, MASTER + '.bak')
    open(MASTER, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'\napplied -> {MASTER} (backup: master-urs.md.bak)')
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'urs/refs.py'), 'check'],
                       cwd=ROOT, capture_output=True, text=True)
    print('refs.py check:', (r.stdout or r.stderr).strip())


if __name__ == '__main__':
    main()
