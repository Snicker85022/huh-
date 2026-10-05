#!/usr/bin/env python3
"""Deterministic formal-mirror pass (stages 3-6), no LLM judgment.

ac_formal        = measurable assertions extracted from AC text (numbers/units/never/zero/exactly)
vm_formal        = evidence artifact per VM line
functional_formal = backticked identifiers + determinism_class tag
failure_formal   = 'Fallback: X' and 'detected by: Y'
"""
import csv, re

T = 'urs/tables'
SPECS = f'{T}/murs_specs.tsv'
rows = list(csv.DictReader(open(SPECS, encoding='utf-8'), delimiter='\t'))

UNIT = r'(?:ms|sec|seconds?|min|minutes?|h|hrs?|hours?|days?|chars?|characters?|consecutive|rows?)'
CMP = re.compile(r'(?:\b(?:≤|<=|>=|≥|<|>)\s*)?(\d+(?:\.\d+)?)\s*' + UNIT)
WITHIN = re.compile(r'within\s+(\d+(?:\.\d+)?)\s*' + UNIT)

def ac_formal(r):
    out = []
    for k in ['ac_normal','ac_edge','ac_negative','ac_silent_failure','ac_challenge','ac_block']:
        t = r[k] or ''
        for m in CMP.finditer(t):
            out.append(m.group(0).strip())
        for m in WITHIN.finditer(t):
            out.append(m.group(0).strip())
        if re.search(r'\bnever\b', t, re.I): out.append('never')
        if re.search(r'\bzero\b', t, re.I): out.append('zero')
        if re.search(r'exactly\s+one\b', t, re.I): out.append('exactly one')
        m = re.search(r'at most\s+(\d+)', t, re.I)
        if m: out.append('at most ' + m.group(1))
        m = re.search(r'at least\s+(\d+)', t, re.I)
        if m: out.append('at least ' + m.group(1))
    # dedupe, keep order
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); res.append(x)
    return '; '.join(res)

def vm_formal(r):
    t = r['verification_methods'] or ''
    ev = [m.group(1).strip() for m in re.finditer(r'Evidence:\s*(.*?)(?=\s*;|$)', t)]
    return '; '.join(dict.fromkeys(e for e in ev if e))

def functional_formal(r):
    t = r['functional_requirement'] or ''
    ids = dict.fromkeys(m.group(1) for m in re.finditer(r'`([a-z_][a-z0-9_]*)`', t))
    cls = r['determinism_class'] or ''
    return f"[{cls}] " + (', '.join(list(ids)[:12]) if ids else '')

def failure_formal(r):
    t = r['failure_behavior'] or ''
    out = []
    m = re.search(r'Fallback:\s*(.*?)(?:\n|$)', t, re.S)
    if m: out.append('fallback=' + re.sub(r'\s+', ' ', m.group(1)).strip()[:80])
    m = re.search(r'detected by:\s*(.*?)(?:\n|$)', t, re.S)
    if m: out.append('detected_by=' + re.sub(r'\s+', ' ', m.group(1)).strip()[:80])
    return '; '.join(out)

for r in rows:
    r['ac_formal'] = ac_formal(r)
    r['vm_formal'] = vm_formal(r)
    r['functional_formal'] = functional_formal(r)
    r['failure_formal'] = failure_formal(r)

COLS = list(rows[0].keys())
with open(SPECS, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, delimiter='\t', lineterminator='\n')
    w.writeheader(); w.writerows(rows)

print('ac_formal filled:', sum(1 for r in rows if r['ac_formal']))
print('vm_formal filled:', sum(1 for r in rows if r['vm_formal']))
print('functional_formal filled:', sum(1 for r in rows if r['functional_formal']))
print('failure_formal filled:', sum(1 for r in rows if r['failure_formal']))
print()
for sid in ['W9', 'D29.A' if False else 'W5', 'PROD-30']:
    for r in rows:
        if r['spec_id'] == sid:
            print(f"--- {sid} ---")
            print('ac_formal:', r['ac_formal'][:160])
            print('vm_formal:', r['vm_formal'][:120])
            print('functional_formal:', r['functional_formal'][:120])
            print('failure_formal:', r['failure_formal'][:120])
