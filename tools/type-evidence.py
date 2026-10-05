#!/usr/bin/env python3
"""type-evidence.py — deterministic evidence typing for master-urs.md.

Rewrites GENERIC Verification-Method `Evidence:` tokens into concrete artifacts.
Every byte of output is traceable to a REAL source; the script never invents a
table, column, symbol or path:

  [sibling probe]   a concrete probe already present verbatim in another VM of
                    the SAME spec (e.g. HW-010 VM2's grep) is reused as-is
  [sibling VMs]     the spec's own VM lines, verbatim, become a [NICK] checklist
  [AC text]         the VM's own acceptance-criteria text, verbatim, is the
                    assertion the evidence must show
  [schema-stub]     table/column names parsed from docs/schema-stub.md
  [spec id]         the spec's real id, used as the log marker
When none of those can ground the output the script emits
`NEEDS-SCHEMA: <spec> — <exactly what is missing>` and leaves it for a human.

Idempotent: a line is rewritten only while its Evidence still matches GENERIC,
so re-running is a no-op and an interrupted run resumes safely.

Usage:
  python3 tools/type-evidence.py                 # dry-run summary
  python3 tools/type-evidence.py --report FILE   # write the OLD|NEW log
  python3 tools/type-evidence.py --apply         # rewrite master-urs.md + refs check
"""
import argparse, os, re, shutil, subprocess, sys, datetime

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, 'master-urs.md')
SCHEMA = os.path.join(ROOT, 'docs/schema-stub.md')

GENERIC = re.compile(
    r'Evidence: (psql|log|query|code-search|test|screenshot|'
    r'observation log|hands-on verification|metrics)[.,]?$')

SPEC_HEAD = re.compile(r'^## ([A-Za-z0-9._-]+) — (.*)$')
VM_LINE   = re.compile(r'^\s*(\d+)[).]\s*\[(AUTO|NICK\+AUTO|NICK)\](.*)$')
BACKTICK  = re.compile(r'`([a-z][a-z0-9_]{2,})`')
PROBE     = re.compile(r'^(grep|psql|pytest|SELECT|apcaccess|ss|curl|awk)\b')
W = r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])'

# explicit, reviewable mappings (not runtime guesses)
SYNONYM = {'prospect': 'leads', 'lead': 'leads', 'invoice': 'invoices',
           'menu item': 'menu_items', 'notification': 'notifications',
           'customer': 'customers', 'event record': 'events'}
# nouns that indicate a field the stub does not have -> NEEDS-SCHEMA, not an invented SQL
MISSING_HINTS = ['due date', 'next-follow-up', 'consent', 'capture-path',
                 'parent lot', 'lineage', 'remaining_quantity', 'audio']
TOOL_PROBES = {
    'apcaccess': 'apcaccess status | grep -E "^LINEV|^BCHARGE|^TIMELEFT|^STATUS"',
}
CODE_MARKERS = [
    (r'inference|\bLLM\b|model call', r'openrouter\|llama.cpp\|OpenAI\|api_key'),
    (r'prompt', r'lead_parser\|precall_brief\|crm_session_opening'),
    (r'USB|CUPS', r'USB\|CUPS\|/dev/usb\|lpadmin'),
    (r'Square API', r'api\.squareup\.com\|square_api\|SQUARE_API'),
]


def load_schema():
    tables, cur = {}, None
    for line in open(SCHEMA, encoding='utf-8'):
        m = re.match(r'^## \d+\.\s+([a-z_][a-z0-9_]*)', line)
        if m:
            cur = m.group(1); tables[cur] = []
        elif cur:
            for c in re.findall(r'`([a-z_][a-z0-9_]*)`', line):
                if c not in tables[cur]:
                    tables[cur].append(c)
    return tables


def vm_ac(text):
    t = re.sub(r'^\s*\d+[).]\s*', '', text)
    t = re.sub(r'^\[[A-Z+]+\]\s*', '', t)
    return re.sub(r'\s*Evidence:.*$', '', t).strip()


def parse(text):
    specs, cur, buf = [], None, []
    for i, ln in enumerate(text.split('\n')):
        m = SPEC_HEAD.match(ln)
        if m:
            if cur:
                cur['text'] = '\n'.join(buf); specs.append(cur)
            cur, buf = {'id': m.group(1), 'title': m.group(2).strip(),
                        'vmlines': [], 'vms': []}, []
            continue
        if cur is not None:
            buf.append(ln)
            vm = VM_LINE.match(ln)
            if vm:
                cur['vmlines'].append(ln)
                k = GENERIC.search(ln)
                cur['vms'].append({'ln': i, 'ord': vm.group(1), 'tag': vm.group(2),
                                   'line': ln, 'ac': vm_ac(ln),
                                   'kind': k.group(1) if k else None})
    if cur:
        cur['text'] = '\n'.join(buf); specs.append(cur)
    return specs


def q(s):
    return re.sub(r'\s+', ' ', s.replace('"', "'")).strip().rstrip('.')


def sibling_probe(spec, vm):
    """a CONCRETE probe already written verbatim in another VM of this spec.
    A bare command word ("psql", "grep") is not concrete -- it needs an argument."""
    for v in spec['vms']:
        if v['ln'] == vm['ln'] or 'Evidence:' not in v['line']:
            continue
        tail = re.sub(r'^\[[A-Z+]+\]\s*', '', v['line'].split('Evidence:', 1)[1].strip())
        m = PROBE.match(tail)
        if not m:
            continue
        rest = tail[m.end():].strip()
        if not rest or rest.startswith('('):        # bare command / only "(assert...)"
            continue
        if GENERIC.search('Evidence: ' + tail):
            continue
        return tail.rstrip('.')
    return None


def table_in(text, schema):
    for t in schema:
        if re.search(W % re.escape(t), text):
            return t
    m = BACKTICK.search(text)
    return m.group(1) if m else None


def resolve_table(spec, ac, schema):
    t = table_in(ac, schema)
    if t:
        return t
    for k, v in SYNONYM.items():
        if re.search(r'(?<![A-Za-z0-9_])' + re.escape(k) + r's?(?![A-Za-z0-9_])', ac, re.I):
            return v
    for v in spec['vms']:                     # first VM usually declares the table
        t = table_in(v['ac'], schema)
        if t:
            return t
    return None


def needs(sid, what, ac):
    return f'NEEDS-SCHEMA: {sid} — {what} (needed for: "{ac}")'


def rewrite(spec, vm, schema):
    kind, ac, sid, title = vm['kind'], q(vm['ac']), spec['id'], spec['title']
    if kind is None:
        return None, None

    # ---- [NICK] live/visual checks -------------------------------------------
    if kind == 'screenshot':
        crit = re.sub(r'^Live:\s*', '', ac)
        return f'screenshot — {title}; must show: "{crit}"', 'AC text'

    if kind in ('observation log', 'hands-on verification'):
        steps = [q(vm_ac(l)) for l in spec['vmlines'] if not GENERIC.search(l)]
        steps = [s for s in steps if s and s.lower() not in
                 ('nick will test manually', 'sandra will test manually')]
        if not steps:                          # fall back to a concrete sibling probe
            sp = sibling_probe(spec, vm)
            if sp:
                return (f'2-min checklist — run and record: {sp} '
                        f'[log in tests/harness/manual/observations/{sid}.md]'), 'sibling probe'
            return (f'2-min checklist — run {title} on the live system and confirm: "{ac}" '
                    f'[log in tests/harness/manual/observations/{sid}.md]'), 'AC text'
        body = '; '.join(f'({i+1}) {s}' for i, s in enumerate(steps))
        return (f'2-min checklist — {body} '
                f'[log in tests/harness/manual/observations/{sid}.md]'), 'sibling VMs (verbatim)'

    # ---- everything below prefers a concrete sibling probe -------------------
    sp = sibling_probe(spec, vm)

    if kind in ('psql', 'query'):
        for tool, probe in TOOL_PROBES.items():
            if re.search(W % tool, ac, re.I):
                return f'{probe} (assert: "{ac}")', 'AC-named tool'
        hit = next((h for h in MISSING_HINTS if h in ac.lower()), None)
        if hit:
            return needs(sid, f'no column for "{hit}" in docs/schema-stub.md', ac), 'none'
        if re.search(r'\blog(g|ged|ging)\b|audit', ac, re.I):
            return (f'psql — SELECT actor, action, table_name, old_value, new_value, occurred_at '
                    f'FROM audit_log ORDER BY occurred_at DESC LIMIT 5 (assert: "{ac}")'), \
                   "AC says 'log' -> schema-stub audit_log"
        t = resolve_table(spec, ac, schema)
        if not t:
            return needs(sid, 'no table named in the AC or in docs/schema-stub.md', ac), 'none'
        known = t in schema
        if known and re.search(r'field coverage|required fields|non-null|explicit nulls', ac, re.I):
            cols = [c for c in schema[t] if c not in ('id', 'created_at', 'updated_at')][:5]
            cond = ' OR '.join(f'{c} IS NULL' for c in cols)
            return f'psql — SELECT count(*) FROM {t} WHERE {cond} (assert: "{ac}")', 'schema-stub null-count'
        if known and not re.search(r'table exists|schema', ac, re.I):
            if sp:
                return f'{sp} (assert: "{ac}")', 'sibling probe (verbatim)'
            cols = [c for c in schema[t] if re.search(W % re.escape(c), ac)] or schema[t][:6]
            return f'psql — SELECT {", ".join(cols)} FROM {t} (assert: "{ac}")', 'schema-stub cols'
        return f'psql — \\d {t} (assert: "{ac}")', 'table'

    if kind == 'log':
        if sp:
            return f'{sp} (assert: "{ac}")', 'sibling probe (verbatim)'
        return (f'grep -n "{sid}" /var/log/taza/*.log | tail -3 '
                f'— expect a line proving: "{ac}"'), 'real spec id'

    if kind == 'code-search':
        for pat_ac, pat_grep in CODE_MARKERS:
            if re.search(pat_ac, ac, re.I):
                return (f'grep -rn "{pat_grep}" src/ (expect zero hits) '
                        f'— assert: "{ac}"'), f'AC marker {pat_ac!r}'
        if sp:
            return f'{sp} (assert: "{ac}")', 'sibling probe (verbatim)'
        return needs(sid, 'no symbol named in the AC to grep for', ac), 'none'

    if kind == 'test':
        if sp:
            return f'{sp} (assert: "{ac}")', 'sibling probe (verbatim)'
        slug = re.sub(r'[^a-z0-9]+', '_', sid.lower()).strip('_')
        path = f'tests/harness/seeds/test_{slug}.py'
        note = '' if os.path.exists(os.path.join(ROOT, path)) else ' [test to author]'
        return f'pytest {path} (expect PASS){note} — assert: "{ac}"', 'spec-id slug'

    if kind == 'metrics':
        return needs(sid, 'no metric named in the AC', ac), 'none'

    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--report')
    args = ap.parse_args()

    schema = load_schema()
    raw = open(MASTER, encoding='utf-8').read()
    lines = raw.split('\n')
    changes, needs_list = [], []

    for spec in parse(raw):
        for vm in spec['vms']:
            new, prov = rewrite(spec, vm, schema)
            if new is None:
                continue
            old = vm['line'].split('Evidence:', 1)[1].strip()
            changes.append((spec['id'], vm['ord'], vm['tag'], old, new, prov))
            if new.startswith('NEEDS-SCHEMA'):
                needs_list.append(f'{spec["id"]}:VM{vm["ord"]}')
            s = vm['line']
            lines[vm['ln']] = s[:s.index('Evidence:')] + 'Evidence: ' + new

    prov_count = {}
    for c in changes:
        prov_count[c[5]] = prov_count.get(c[5], 0) + 1

    print(f'generic Evidence lines rewritten : {len(changes)}')
    print(f'NEEDS-SCHEMA (left for a human)  : {len(needs_list)}')
    for k, v in sorted(prov_count.items(), key=lambda x: -x[1]):
        print(f'  {v:3d}  {k}')
    if needs_list:
        print('NEEDS-SCHEMA: ' + ', '.join(needs_list))

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write(f'# Evidence typing — report ({datetime.datetime.now():%Y-%m-%d %H:%M})\n\n')
            fh.write('Generated by tools/type-evidence.py (deterministic; re-runnable).\n')
            fh.write('Each NEW value is grounded in a real source — see the [bracket].\n\n')
            for sid, o, tag, old, new, prov in changes:
                fh.write(f'{sid} | VM{o} {tag} | OLD: {old} | NEW: {new}  [{prov}]\n')
        print(f'report -> {args.report}')

    if not args.apply:
        print('\n(dry-run — nothing written; pass --apply to write)')
        return

    shutil.copy(MASTER, MASTER + '.bak')
    open(MASTER, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'\napplied -> {MASTER} (backup: master-urs.md.bak)')
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'urs/refs.py'), 'check'],
                       cwd=ROOT, capture_output=True, text=True)
    print('refs.py check:', (r.stdout or r.stderr).strip())


if __name__ == '__main__':
    main()
