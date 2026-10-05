#!/usr/bin/env python3
"""murs-specs.py — ONE row per fully-defined spec (wide table), as Nick asked.

Everything about a spec is a COLUMN on its row:
  identity + dimensions, prose sections, 5 AC classes, VMs (packed + count flags),
  seam edges (consumes / consumed_by + count), domain rules (text + count).

Decisions/branches live separately in decisions_log.tsv (append-only).
"""
import csv, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'urs/tables')
MASTER = os.path.join(ROOT, 'master-urs.md')

COLS = ['spec_id','name','legacy_id','status','priority','release','record_type','domain',
        'determinism_class','required_for_release','notion_url',
        'user_requirement','functional_requirement','failure_behavior','dependency_notes',
        'open_questions','ac_normal','ac_edge','ac_negative','ac_silent_failure',
        'ac_challenge','ac_block','verification_methods','vm_count','vm_auto_count',
        'vm_nick_count','consumes','consumed_by','seam_count','rules','rule_count','source']

def W(s):
    return re.sub(r'\s+', ' ', s).strip()

def section(block, header):
    m = re.search(r'(?m)^\*\*' + re.escape(header) + r':\*\*[ \t]*\r?\n', block)
    if not m:
        return ''
    rest = block[m.end():]
    end = re.search(r'(?m)^(?=\*\*|_Notion:)', rest)
    return W(rest[:end.start()] if end else rest)

# --- parse master-urs.md for identity + prose ---
raw = open(MASTER, encoding='utf-8').read()
specs = {}
for block in re.split(r'(?m)^## ', raw)[1:]:
    head = block.split('\n', 1)[0].strip()
    if ' — ' not in head:
        continue
    sid, name = [x.strip() for x in head.split(' — ', 1)]
    legacy = re.search(r'\*\*Legacy ID \(ID\.2\):\*\*\s*(\S+)', block)
    st = re.search(r'(?m)^\*\*Status:\*\*[^\n]*', block)
    status = prio = rel = ''
    if st:
        line = st.group(0)
        m = re.search(r'Status:\*\*\s*([^|]*?)\s*(?:\||$)', line); status = m.group(1).strip() if m else ''
        m = re.search(r'Priority:\*\*\s*([^|]*?)\s*(?:\||$)', line); prio = m.group(1).strip() if m else ''
        m = re.search(r'Release:\*\*\s*(.*?)\s*$', line); rel = m.group(1).strip() if m else ''
    specs[sid] = {
        'spec_id': sid, 'name': name, 'legacy_id': legacy.group(1) if legacy else '',
        'status': status, 'priority': prio, 'release': rel,
        'record_type': section(block, 'Record Type'), 'domain': section(block, 'Domain'),
        'determinism_class': '', 'required_for_release': section(block, 'Required for Release'),
        'notion_url': re.search(r'_Notion:\s*(\S+)', block).group(1) if re.search(r'_Notion:\s*(\S+)', block) else '',
        'user_requirement': section(block, 'User Requirement Statement'),
        'functional_requirement': section(block, 'Functional Requirement Specification'),
        'failure_behavior': section(block, 'Failure Behavior'),
        'dependency_notes': section(block, 'Dependency Notes'),
        'open_questions': section(block, 'Open Questions'),
        'ac_normal': '', 'ac_edge': '', 'ac_negative': '', 'ac_silent_failure': '',
        'ac_challenge': '', 'ac_block': '', 'verification_methods': '',
        'vm_count': 0, 'vm_auto_count': 0, 'vm_nick_count': 0,
        'consumes': '', 'consumed_by': '', 'seam_count': 0, 'rules': '', 'rule_count': 0,
        'source': 'master-urs.md'}

# --- AC into 5 class columns (+ unclassed block) ---
for r in csv.DictReader(open(os.path.join(T, 'acceptance_criteria.tsv'), encoding='utf-8'), delimiter='\t'):
    sid = r['spec_id']
    if sid not in specs:
        continue
    k = {'NORMAL':'ac_normal','EDGE':'ac_edge','NEGATIVE':'ac_negative',
         'SILENT-FAILURE':'ac_silent_failure','CHALLENGE':'ac_challenge'}.get(r['ac_class'])
    if k:
        specs[sid][k] = (specs[sid][k] + ' ; ' + r['ac_text']).strip(' ;')
    else:
        specs[sid]['ac_block'] = (specs[sid]['ac_block'] + ' ; ' + r['ac_text']).strip(' ;')

# --- VM packed + count flags ---
vm_lines = {}
for r in csv.DictReader(open(os.path.join(T, 'verification_methods.tsv'), encoding='utf-8'), delimiter='\t'):
    sid = r['spec_id']
    if sid not in specs:
        continue
    ev = (' — Evidence: ' + r['evidence']) if r['evidence'] else ''
    vm_lines.setdefault(sid, []).append(f"{r['vm_no']}) [{r['tag']}] {r['vm_text']}{ev}")
    specs[sid]['vm_count'] += 1
    if r['tag'] == 'AUTO': specs[sid]['vm_auto_count'] += 1
    else: specs[sid]['vm_nick_count'] += 1
for sid, lines in vm_lines.items():
    specs[sid]['verification_methods'] = ' ; '.join(lines)

# --- seams into consumes / consumed_by columns ---
consumed_by = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'urs/seam-stamps.tsv'), encoding='utf-8'), delimiter='\t'):
    if r['role'] != 'CONSUMES':
        continue
    c, p = r['spec_id'], r['target_spec']
    if c in specs:
        specs[c]['consumes'] = (specs[c]['consumes'] + ',' + p).strip(',') if specs[c]['consumes'] else p
        specs[c]['seam_count'] += 1
    if p in specs:
        consumed_by.setdefault(p, set()).add(c)
for p, cs in consumed_by.items():
    if p in specs:
        specs[p]['consumed_by'] = ','.join(sorted(cs))
        specs[p]['seam_count'] += len(cs)

# --- domain rules into rules column ---
for r in csv.DictReader(open(os.path.join(T, 'domain_rules.tsv'), encoding='utf-8'), delimiter='\t'):
    for sid in [x.strip() for x in r['applies_to_specs'].split(',') if x.strip()]:
        if sid in specs:
            specs[sid]['rules'] = (specs[sid]['rules'] + ' ; ' + f"{r['rule_id']}: {r['formal']}").strip(' ;')
            specs[sid]['rule_count'] += 1

with open(os.path.join(T, 'murs_specs.tsv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(COLS)
    for sid in sorted(specs):
        w.writerow([specs[sid].get(c, '') for c in COLS])
print('murs_specs.tsv:', len(specs), 'rows (one row per spec)')

# --- decisions_log: one row per branch (decision rows + alternatives) ---
log = []
for r in csv.DictReader(open(os.path.join(T, 'branches.tsv'), encoding='utf-8'), delimiter='\t'):
    log.append([r['decision_id'], r['branch_id'], r['branch_title'], r['status'],
                r['dev_hours_initial_est'], r['elapsed_focus_hours'], r['elapsed_wallclock_hours'],
                r['elapsed_hours'], r['dev_hours_remaining'], r['maintenance_hours_month'],
                r['recovery_rebuild_hours'], r['capex_cents'], r['opex_cents_month'],
                r['trigger_predicate'], r['pivot_penalty_hours'], r['formal_logic_spec'],
                r['rationale_prose'], r['rationale_formal'], r['parent_branch_id'],
                '', '', 'branches.tsv'])
LOGC = ['decision_id','branch_id','branch_title','branch_status','dev_hours_initial_est',
        'elapsed_focus_hours','elapsed_wallclock_hours','elapsed_hours','dev_hours_remaining',
        'maintenance_hours_month','recovery_rebuild_hours','capex_cents','opex_cents_month',
        'trigger_predicate','pivot_penalty_hours','formal_logic_spec','rationale_prose',
        'rationale_formal','parent_branch_id','milestone_reached','milestone_reached_at','source']
with open(os.path.join(T, 'decisions_log.tsv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(LOGC); w.writerows(log)
print('decisions_log.tsv:', len(log), 'rows (one row per branch/decision)')
