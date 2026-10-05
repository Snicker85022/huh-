#!/usr/bin/env python3
"""Deterministic pipeline stages 1, 2, 8 — run in order, no AI judgment.

  Stage 1: determinism_class  (ordered keyword rule table, inspectable)
  Stage 2: decision_ids + branch_id  (from decision bodies, max D-number)
  Stage 8: recompute version_id (content hash) + report blank columns

Idempotent. Writes murs_specs.tsv + determinism-report.tsv.
"""
import csv, hashlib, re

T = 'urs/tables'
SPECS = f'{T}/murs_specs.tsv'
DECS  = f'{T}/decisions.tsv'

def load(path):
    return list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))

def vid(r):
    canon = '|'.join([r['spec_id'], r.get('branch_id',''), r['functional_requirement'],
        r['ac_normal'], r['ac_edge'], r['ac_negative'], r['ac_silent_failure'],
        r['ac_challenge'], r['verification_methods']])
    return hashlib.sha256(canon.encode()).hexdigest()[:16]

specs = load(SPECS)
decs  = load(DECS)

# ---------- Stage 1: determinism class ----------
# ordered rules; first match wins. Text = functional_requirement + name + user_requirement.
INF = [' ai ', ' llm', 'inference', 'prompt', 'whisper', 'confidence label',
       'fabricat', 'openrouter', 'model routing', 'embedding']
EXT = ['square', 'twilio', 'sendgrid', 'helcim', 'stripe', 'gmail', 'ntfy',
       'cloudflare', 'tailscale', 'alexa', 'apcupsd', 'places api', 'wix',
       'zebra', 'thermal', 'ups', 'zpl', 'printer', 'noco']
HUM = ['nick reviews', 'nick approves', 'sandra confirms', 'sandra reviews',
       'approval', 'observation log', 'runbook', 'onboarding', 'training script',
       'poster', 'taza way', 'declaration', 'decision capture', 'lexicon']
KG  = ['procedure_link', 'item_components', 'packing_profiles', 'equipment_list',
       'bill of materials', 'bom', 'catalog attribute', 'knowledge base', 'procedure']

def klass(r):
    if r['status'].strip().lower() in ('superseded', 'idea'):
        return ''
    fr = (r['functional_requirement'] + ' ' + r['name'] + ' ' + r['user_requirement']).lower()
    if any(k in fr for k in INF): return 'INF'
    if any(k in fr for k in EXT): return 'EXT'
    if any(k in fr for k in HUM): return 'HUM'
    if any(k in fr for k in KG):  return 'KG'
    return 'D'

# ---------- Stage 2: branch tagging ----------
REG = {r['spec_id'] for r in specs}
def find_ids(text):
    return [s for s in sorted(REG) if re.search(r'(?<![A-Za-z0-9_])'+re.escape(s)+r'(?![A-Za-z0-9_])', text)]
hits = {}
for d in decs:
    ids = find_ids(d['body'])
    if ids:
        hits[d['decision_id']] = ids
spec_dec = {}
for did, ids in hits.items():
    for s in ids:
        spec_dec.setdefault(s, []).append(did)
def dnum(d): return int(re.match(r'D(\d+)', d).group(1))
# explicit ground-truth tags not derivable from decision bodies
EXPLICIT = {'HW-007': 'D29', 'HW-011': 'D29,D30'}

for r in specs:
    ds = sorted(set(spec_dec.get(r['spec_id'], [])), key=dnum)
    if r['spec_id'] in EXPLICIT:
        ds = sorted(set(ds) | set(EXPLICIT[r['spec_id']].split(',')), key=dnum)
    r['decision_ids'] = ','.join(ds)
    if not r.get('branch_id'):
        r['branch_id'] = ds[-1] if ds else ''
    r['determinism_class'] = klass(r)   # stage 1
    r['version_id'] = vid(r)            # stage 8

COLS = list(specs[0].keys())
with open(SPECS, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, delimiter='\t', lineterminator='\n')
    w.writeheader(); w.writerows(specs)

# report
from collections import Counter
kc = Counter(r['determinism_class'] or '—' for r in specs)
print('determinism_class:', dict(sorted(kc.items())))
print('branch tagged:', sum(1 for r in specs if r['branch_id']), '/', len(specs))
print('decision-tagged:', sum(1 for r in specs if r['decision_ids']), '/', len(specs))
blank_det = sum(1 for r in specs if not r['determinism_class'])
print('blank determinism (superseded/idea):', blank_det)

with open(f'{T}/determinism-report.tsv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(['spec_id','determinism_class','status','branch_id','decision_ids'])
    for r in sorted(specs, key=lambda x: (x['determinism_class'] or '~', x['spec_id'])):
        w.writerow([r['spec_id'], r['determinism_class'], r['status'], r['branch_id'], r['decision_ids']])
print('wrote urs/tables/determinism-report.tsv')
