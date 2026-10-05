#!/usr/bin/env python3
"""Sync master-urs.md -> NocoDB's master_urs table (tazaos, public schema).

Runs on gflip: parses the local markdown, pushes UPSERTs to n100 via ssh psql.
NocoDB's "Taza OS" base reads public.master_urs (space-named columns).
Only rows whose content actually changed get updated_at bumped.
"""
import pathlib, re, sys, subprocess, time

MURS = pathlib.Path('/home/taza/repo/master-urs.md')
TABLE = 'public.master_urs'
N100 = 'taza@192.168.2.102'

COLS = ['Spec ID','Name','Record Type','Domain','Target Release','URS Priority',
        'Implementation Status','User Requirement Statement','Atomic Requirement',
        'Functional Requirement Specification','Intent / User Need','Inputs','Outputs',
        'Trigger','Invariants','Failure Behavior','Failure Mode Addressed','Out of Scope',
        'Acceptance Criteria','Verification Method','Maintenance Requirements',
        'Dependency Notes','External Dependencies','Open Questions','Notes','Rationale',
        'Required for Release','_url']

FIELD_MAP = {
    'Record Type':'Record Type','Domain':'Domain','User Requirement Statement':'User Requirement Statement',
    'Atomic Requirement':'Atomic Requirement','Functional Requirement Specification':'Functional Requirement Specification',
    'Intent / User Need':'Intent / User Need','Inputs':'Inputs','Outputs':'Outputs','Trigger':'Trigger',
    'Invariants':'Invariants','Failure Behavior':'Failure Behavior','Failure Mode Addressed':'Failure Mode Addressed',
    'Out of Scope':'Out of Scope','Acceptance Criteria':'Acceptance Criteria','Verification Method':'Verification Method',
    'Maintenance Requirements':'Maintenance Requirements','Dependency Notes':'Dependency Notes',
    'External Dependencies':'External Dependencies','Open Questions':'Open Questions','Notes':'Notes',
    'Rationale':'Rationale','Required for Release':'Required for Release',
}

def parse():
    text = MURS.read_text(encoding='utf-8')
    specs = []
    for block in text.split('\n## ')[1:]:
        first = block.split('\n',1)[0].strip()
        if ' — ' not in first:
            continue
        sid, name = first.split(' — ', 1)
        rec = {c: '' for c in COLS}
        rec['Spec ID'] = sid.strip()
        rec['Name'] = name.strip()
        m = re.search(r'\*\*Status:\*\*\s*(.*?)\s*\|\s*\*\*Priority:\*\*\s*(.*?)\s*\|\s*\*\*Release:\*\*\s*(.*?)(?:\r?\n|$)', block)
        if m:
            rec['Implementation Status'] = m.group(1).strip()
            rec['URS Priority'] = m.group(2).strip()
            rec['Target Release'] = m.group(3).strip()
        u = re.search(r'(?m)^_Notion:\s*(\S+)', block)
        if u:
            rec['_url'] = u.group(1).strip()
        hdr = re.compile(r'(?m)^\*\*([^*]+?):\*\*[ \t]*\r?$')
        matches = list(hdr.finditer(block))
        for i, fm in enumerate(matches):
            col = FIELD_MAP.get(fm.group(1).strip())
            if not col:
                continue
            start = fm.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(block)
            val = block[start:end]
            val = re.sub(r'\n?_Notion:\s*\S+\s*$', '', val)
            rec[col] = val.strip()
        specs.append(rec)
    return specs

def sql_lit(s):
    s = str(s or '')
    tag = 'mursq'
    while tag in s:
        tag += 'x'
    return f'${tag}${s}${tag}$'

def build_sql(specs):
    parts = [f'CREATE UNIQUE INDEX IF NOT EXISTS master_urs_specid_uq ON {TABLE} ("Spec ID") WHERE "Spec ID" IS NOT NULL AND "Spec ID" <> \'\';']
    data = [c for c in COLS if c != 'Spec ID']
    for rec in specs:
        cols = '", "'.join(COLS)
        vals = ', '.join(sql_lit(rec[c]) for c in COLS)
        upd = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in data)
        changed = ' OR '.join(f'master_urs."{c}" IS DISTINCT FROM EXCLUDED."{c}"' for c in data)
        parts.append(
            f'INSERT INTO {TABLE} ("{cols}", "created_at", "updated_at") '
            f'VALUES ({vals}, now(), now()) '
            f'ON CONFLICT ("Spec ID") WHERE "Spec ID" IS NOT NULL AND "Spec ID" <> \'\' DO UPDATE SET {upd}, "updated_at" = now() '
            f'WHERE ({changed});')
    return '\n'.join(parts) + '\n'

def main():
    dry = '--dry' in sys.argv
    specs = parse()
    print(f'parsed {len(specs)} specs', file=sys.stderr)
    if dry:
        print('DRY RUN — not pushing.', file=sys.stderr)
        return 0
    sql = build_sql(specs)
    t0 = time.time()
    r = subprocess.run(
        ['ssh','-o','BatchMode=yes',N100,'psql','-U','taza','-d','tazaos','-v','ON_ERROR_STOP=1','-q','-f','-'],
        input=sql, text=True, capture_output=True)
    if r.returncode != 0:
        print('SYNC FAILED:', r.stderr.strip()[:2000], file=sys.stderr)
        return 1
    print(f'synced {len(specs)} specs in {time.time()-t0:.1f}s', file=sys.stderr)
    return 0

if __name__ == '__main__':
    sys.exit(main())
