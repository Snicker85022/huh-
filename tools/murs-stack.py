#!/usr/bin/env python3
"""murs-stack.py — collapse the mURS into ONE stacked table + ONE decision log.

Long format (JMP-style): every row carries every flag it needs, with a row_type
column so one view can be sorted/filtered to show different things.

  row_type : spec | ac | vm | rule | seam | branch
  decisions live separately in decisions_log (append-only history).

Reads the extracted tables under urs/tables/ + the seam tables, writes:
  urs/tables/murs_stack.tsv
  urs/tables/decisions_log.tsv
"""
import csv, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'urs/tables')
SEAM = os.path.join(ROOT, 'urs/seam-stamps.tsv')
OPEN = os.path.join(ROOT, 'urs/seam-open.tsv')

COLS = ['row_type','spec_id','name','decision_id','branch_id','branch_title','status',
        'branch_status','priority','release','record_type','domain','determinism_class',
        'ac_class','ac_text','vm_no','vm_tag','vm_text','evidence','rule_id','rule_text',
        'rule_formal','constraint_type','entity','applies_to_specs','seam_role','target_spec',
        'artifact','seam_rule','formal_logic_spec','dev_hours_initial_est','elapsed_focus_hours',
        'elapsed_wallclock_hours','elapsed_hours','dev_hours_remaining','maintenance_hours_month',
        'recovery_rebuild_hours','capex_cents','opex_cents_month','trigger_predicate',
        'pivot_penalty_hours','rationale_prose','rationale_formal','parent_branch_id',
        'milestone_reached','milestone_reached_at','source']

def rd(name):
    with open(os.path.join(T, name), encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))

def row(**kw):
    return [kw.get(c, '') for c in COLS]

stack = []

# specs
for r in rd('specs.tsv'):
    stack.append(row(row_type='spec', spec_id=r['spec_id'], name=r['name'], status=r['status'],
                     priority=r['priority'], release=r['release'], record_type=r['record_type'],
                     domain=r['domain'], source='master-urs.md'))

# acceptance criteria
for r in rd('acceptance_criteria.tsv'):
    stack.append(row(row_type='ac', spec_id=r['spec_id'], ac_class=r['ac_class'],
                     ac_text=r['ac_text'], source='master-urs.md'))

# verification methods
for r in rd('verification_methods.tsv'):
    stack.append(row(row_type='vm', spec_id=r['spec_id'], vm_no=r['vm_no'], vm_tag=r['tag'],
                     vm_text=r['vm_text'], evidence=r['evidence'], source='master-urs.md'))

# domain rules
for r in rd('domain_rules.tsv'):
    stack.append(row(row_type='rule', rule_id=r['rule_id'], rule_text=r['rule_text'],
                     rule_formal=r['formal'], constraint_type=r['constraint_type'],
                     entity=r['entity'], applies_to_specs=r['applies_to_specs'], source=r['source']))

# seams (edges + NONE leaves + open)
for r in csv.DictReader(open(SEAM, encoding='utf-8'), delimiter='\t'):
    if r['role'] == 'CONSUMES':
        stack.append(row(row_type='seam', seam_role='CONSUMES', spec_id=r['spec_id'],
                         target_spec=r['target_spec'], artifact=r['artifact'],
                         seam_rule=r['rule'], source=r['source']))
    else:
        stack.append(row(row_type='seam', seam_role='NONE', spec_id=r['spec_id'], source=r['source']))
for r in csv.DictReader(open(OPEN, encoding='utf-8'), delimiter='\t'):
    stack.append(row(row_type='seam', seam_role='OPEN', status=r['status'],
                     rationale_prose=r['note'], source=f"{r['file']}:{r['line']}"))

# branches
for r in rd('branches.tsv'):
    stack.append(row(row_type='branch', decision_id=r['decision_id'], branch_id=r['branch_id'],
                     branch_title=r['branch_title'], branch_status=r['status'],
                     dev_hours_initial_est=r['dev_hours_initial_est'],
                     elapsed_focus_hours=r['elapsed_focus_hours'],
                     elapsed_wallclock_hours=r['elapsed_wallclock_hours'],
                     elapsed_hours=r['elapsed_hours'], dev_hours_remaining=r['dev_hours_remaining'],
                     maintenance_hours_month=r['maintenance_hours_month'],
                     recovery_rebuild_hours=r['recovery_rebuild_hours'],
                     capex_cents=r['capex_cents'], opex_cents_month=r['opex_cents_month'],
                     trigger_predicate=r['trigger_predicate'],
                     pivot_penalty_hours=r['pivot_penalty_hours'],
                     formal_logic_spec=r['formal_logic_spec'],
                     rationale_prose=r['rationale_prose'], rationale_formal=r['rationale_formal'],
                     parent_branch_id=r['parent_branch_id'], source='branches.tsv'))

with open(os.path.join(T, 'murs_stack.tsv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(COLS); w.writerows(stack)

# decisions log
log = []
for r in rd('decisions.tsv'):
    log.append([r['decision_id'], r['title'], r['locked'], r['body'], 'master-urs.md'])
with open(os.path.join(T, 'decisions_log.tsv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(['decision_id','title','locked','body','source']); w.writerows(log)

from collections import Counter
c = Counter(x[0] for x in stack)
print('murs_stack.tsv   :', len(stack), 'rows')
for k in sorted(c): print(f'    {k:8s} {c[k]}')
print('decisions_log.tsv:', len(log), 'rows')
