#!/usr/bin/env python3
"""murs-to-tables.py — extract the mURS into the stacked relational tables.

The markdown is parsed once, deterministically, into named-field TSVs under
urs/tables/. These tables are the FRAMEWORK: structure exists first so the 28
decisions can be compared side by side instead of argued one at a time.

Usage: python3 tools/murs-to-tables.py
"""
import csv, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, 'master-urs.md')
SCHEMA = os.path.join(ROOT, 'docs/schema-stub.md')
OUT = os.path.join(ROOT, 'urs/tables')
os.makedirs(OUT, exist_ok=True)

raw = open(MASTER, encoding='utf-8').read()

def W(s):
    return re.sub(r'\s+', ' ', s).strip()

def write(name, header, rows):
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter='\t', lineterminator='\n')
        w.writerow(header)
        w.writerows(rows)
    print(f'  {name:26s} {len(rows):4d} rows')

def section_raw(block, header):
    """raw text under a **Header:**, preserving newlines, stopping at next **/_Notion"""
    m = re.search(r'(?m)^\*\*' + re.escape(header) + r':\*\*[ \t]*\r?\n', block)
    if not m:
        return ''
    rest = block[m.end():]
    end = re.search(r'(?m)^(?=\*\*|_Notion:)', rest)
    return (rest[:end.start()] if end else rest).strip()

# ---------------- specs ----------------
spec_rows = []
for block in re.split(r'(?m)^## ', raw)[1:]:
    head = block.split('\n', 1)[0].strip()
    if ' — ' not in head:
        continue
    sid, name = [x.strip() for x in head.split(' — ', 1)]
    legacy = (re.search(r'\*\*Legacy ID \(ID\.2\):\*\*\s*(\S+)', block) or [None, ''])[0]
    legacy = re.search(r'\*\*Legacy ID \(ID\.2\):\*\*\s*(\S+)', block)
    legacy = legacy.group(1) if legacy else ''
    stline = re.search(r'(?m)^\*\*Status:\*\*[^\n]*', block)
    status = prio = rel = ''
    if stline:
        line = stline.group(0)
        status = (re.search(r'Status:\*\*\s*([^|]*?)\s*$', line) or [None,''])[1] if re.search(r'Status:\*\*\s*([^|]*?)\s*$', line) else ''
        m = re.search(r'Priority:\*\*\s*([^|]*?)\s*(?:\||$)', line)
        prio = m.group(1).strip() if m else ''
        m = re.search(r'Release:\*\*\s*(.*?)\s*$', line)
        rel = m.group(1).strip() if m else ''
        m = re.search(r'Status:\*\*\s*([^|]*?)\s*(?:\||$)', line)
        status = m.group(1).strip() if m else ''
    spec_rows.append([
        sid, name, legacy, status, prio, rel,
        W(section_raw(block, 'Record Type')), W(section_raw(block, 'Domain')),
        W(section_raw(block, 'Required for Release')),
        re.search(r'_Notion:\s*(\S+)', block).group(1) if re.search(r'_Notion:\s*(\S+)', block) else ''])
write('specs.tsv',
      ['spec_id','name','legacy_id','status','priority','release','record_type','domain','required_for_release','notion_url'],
      spec_rows)

# ---------------- decisions ----------------
dec_section = raw.split('## Decisions (locked)', 1)[1].split('\n## AI-001', 1)[0]
dec_blocks = re.split(r'(?m)^- \*\*D(\d+) — ', dec_section)[1:]
dec_rows, seen = [], set()
for i in range(0, len(dec_blocks), 2):
    dnum, body = dec_blocks[i], dec_blocks[i+1].strip()
    if dnum in seen:
        continue
    seen.add(dnum)
    title = body.split('**', 1)[0].strip().rstrip('.').strip()
    rest = body.split('**', 1)[1].strip() if '**' in body else ''
    dec_rows.append(['D' + dnum, title, 'yes' if 'LOCKED' in (title + ' ' + rest).upper() else '', W(rest)])
write('decisions.tsv', ['decision_id','title','locked','body'], dec_rows)

# ---------------- AC + VM ----------------
ac_rows, vm_rows = [], []
for block in re.split(r'(?m)^## ', raw)[1:]:
    head = block.split('\n', 1)[0].strip()
    if ' — ' not in head:
        continue
    sid = head.split(' — ', 1)[0].strip()

    ac = section_raw(block, 'Acceptance Criteria')
    parts = re.split(r'(?m)^(?=(?:NORMAL|EDGE|NEGATIVE|SILENT-FAILURE|CHALLENGE):)', ac)
    classes = []
    for p in parts:
        m = re.match(r'(NORMAL|EDGE|NEGATIVE|SILENT-FAILURE|CHALLENGE):\s*(.*)', p, re.S)
        if m:
            classes.append([sid, m.group(1), W(m.group(2))])
    if not classes and ac:
        classes.append([sid, '', W(ac)])
    ac_rows.extend(classes)

    vm = section_raw(block, 'Verification Method')
    for line in vm.split('\n'):
        m = re.match(r'^\s*(\d+)[).]\s*\[(AUTO|NICK\+AUTO|NICK)\]\s*(.*)', line)
        if m:
            text = m.group(3).strip()
            ev = ''
            if 'Evidence:' in text:
                text, ev = [x.strip() for x in text.split('Evidence:', 1)]
            vm_rows.append([sid, m.group(1), m.group(2), W(text), W(ev)])
write('acceptance_criteria.tsv', ['spec_id','ac_class','ac_text'], ac_rows)
write('verification_methods.tsv', ['spec_id','vm_no','tag','vm_text','evidence'], vm_rows)

# ---------------- domain_rules (seeded; real, numeric) ----------------
domain_rules = [
 ['RULE-BERRY-T36', 'Don\'t buy berries any earlier than T-36 hours or they\'ll mold',
  'purchase_time <= event_time - 36h', 'ingredient_order', 'temporal', 'PROD-01,KIT-001', 'Nick 2026-10-01'],
 ['RULE-AUDIO-60S', 'Voice clips longer than 60s are rejected at capture',
  'audio_clip_duration_s <= 60', 'voice_note', 'numeric', 'W5,INT-005', 'D13'],
 ['RULE-AUDIO-SLA', 'Transcription SLA: <=15s audio -> <1s; 16-60s -> <3s',
  '(dur<=15 -> lat<1000ms) AND (16<=dur<=60 -> lat<3000ms)', 'voice_note', 'temporal', 'W5,INT-005', 'D13'],
 ['RULE-BRIEF-900', 'Pre-call brief must be <= 900 characters',
  'brief_char_count <= 900', 'precall_brief', 'numeric', 'AI-007,W3', 'D9'],
 ['RULE-BRIEF-WINDOW', 'Brief fires on task entering its 60-min window, never later than 5 min before due',
  'fire_time in [due_time - 60min, due_time - 5min]', 'task', 'temporal', 'W3', 'D9'],
 ['RULE-PAY-10S', 'Payment provider failover: 10s per provider, never cumulative',
  'attempt_timeout_ms = 10000', 'payment_attempt', 'numeric', 'PROD-30', 'D26'],
 ['RULE-TV-45S', 'Killed Chrome must auto-relaunch within 45s',
  'relaunch_time_s <= 45', 'tv_display', 'temporal', 'TV-007', 'TV-007'],
 ['RULE-NOTIFY-CHANNEL', 'Actionable notifications go Twilio SMS; non-urgent go ntfy',
  'actionable -> channel=twilio_sms; else channel=ntfy', 'notification', 'routing', 'PROD-25,W1,W2,W3,W6,W13', 'D10'],
 ['RULE-SQ-2MISS', 'Menu item deactivated only after 2 consecutive sync misses',
  'misses >= 2 -> is_active = false', 'menu_items', 'numeric', 'W9', 'D14'],
 ['RULE-SQ-2FAIL', 'Two consecutive full-sync failures fire SMS to Nick',
  'full_sync_failures >= 2 -> alert(Nick, twilio_sms)', 'catalog_sync', 'numeric', 'W9', 'D14'],
 ['RULE-DEPOSIT-FROZEN', 'Deposit dollar amount is frozen at first publish',
  'deposit_basis_cents immutable after publish', 'invoices', 'guard', 'PROD-08,PROD-30', 'D19'],
]
write('domain_rules.tsv',
      ['rule_id','rule_text','formal','entity','constraint_type','applies_to_specs','source'],
      domain_rules)

# ---------------- branches (framework: seeded) ----------------
BR = ['branch_id','decision_id','branch_title','status','dev_hours_initial_est','elapsed_focus_hours',
      'elapsed_wallclock_hours','elapsed_hours','dev_hours_remaining','maintenance_hours_month',
      'recovery_rebuild_hours','capex_cents','opex_cents_month','trigger_predicate',
      'pivot_penalty_hours','formal_logic_spec','rationale_prose','rationale_formal','parent_branch_id']
branches = []
for d in dec_rows:
    branches.append([d[0], d[0], d[1], 'unknown', '', '', '', '', '', '', '', '', '', '', '', '', d[3], '', ''])
branches += [
 ['BR-INF-CLOUD',  'D4',  'Cloud-first inference (OpenRouter)', 'active',   '', '', '', '', '', '', '', '', '', 'spend > threshold OR p95 latency > 2s', '', 'Route(t) => cloud_endpoint(t)', 'V1.0 ships on cloud; local deferred to V1.x', '', ''],
 ['BR-INF-LOCAL',  'D4',  'Local llama.cpp (INFRA-003)',        'deferred', '', '', '', '', '', '', '', '', '', 'N100 has GPU headroom',               '', 'Route(t) => local_endpoint(t)', 'Local when spend/latency justify',        '', ''],
 ['BR-DISP-SSE',   'D3',  'SSE display transport',             'active',   '', '', '', '', '', '', '', '', '', 'event rate within SSE capacity',      '', 'Push(e) => SSE(e)',          'One V1.0 transport',                      '', ''],
 ['BR-DISP-WS',    'D3',  'WebSocket + delta (INFRA-007)',      'deferred', '', '', '', '', '', '', '', '', '', 'V1.x upgrade window',                 '', 'Push(e) => WS_delta(e)',      'Later if SSE proves insufficient',         '', ''],
 ['BR-CAT-PULL',   'D14', '6h scheduled pull',                 'active',   '', '', '', '', '', '', '', '', '', 'always',                             '', 'Sync() => scheduled_pull(6h)', 'V1.0 primary',                             '', ''],
 ['BR-CAT-PUSH',   'D14', 'Square webhook (catalog.version.updated)', 'deferred', '', '', '', '', '', '', '', '', '', 'V1.1',                        '', 'Sync() => webhook_driven()',  'V1.1 extension stub',                      '', ''],
]
write('branches.tsv', BR, branches)

# ---------------- state_machines (seeded from schema-stub) ----------------
sm = []
stext = open(SCHEMA, encoding='utf-8').read()
for sec in re.split(r'(?m)^## \d+\.\s+', stext)[1:]:
    name = sec.split('\n', 1)[0].strip()
    m = re.search(r'`(?:delivery_)?status`[^\n]*?\n?\s*\(([^)]*)\)', sec)
    if m:
        states = [x.strip() for x in re.split(r'[→|]', m.group(1))]
        sm.append([name, ' → '.join(states), '', '', ''])
sm.append(['leads', 'prospect → qualified → opportunity → closed', '', '', ''])
write('state_machines.tsv', ['entity','states','guard','required_inputs','checkpoint_required'], sm)

open(os.path.join(OUT, 'schema.md'), 'w', encoding='utf-8').write('''# mURS stacked tables — column dictionary

Every table is TSV (tab-separated). One row = one fact. Named fields only.
These tables are the FRAMEWORK. `master-urs.md` is currently the parse source;
the tables are where sorting/filtering/comparing happens.

## specs.tsv
spec_id | name | legacy_id | status | priority | release | record_type | domain | required_for_release | notion_url

## decisions.tsv
decision_id | title | locked | body   (D20 absent in the source)

## branches.tsv  (GORE / weighted-branch log)
branch_id | decision_id | branch_title | status(active|deferred|unknown)
dev_hours_initial_est | elapsed_focus_hours | elapsed_wallclock_hours | elapsed_hours
dev_hours_remaining | maintenance_hours_month | recovery_rebuild_hours
capex_cents | opex_cents_month | trigger_predicate | pivot_penalty_hours
formal_logic_spec | rationale_prose | rationale_formal | parent_branch_id

Hours semantics (Nick): elapsed = focus + wallclock; focus = his attention;
wallclock = AI in-flight = the stress window. Estimates are to first useful
milestone. Cost columns start blank and are filled as estimates come in.

## domain_rules.tsv  (business rules the system must enforce, not just document)
rule_id | rule_text | formal | entity | constraint_type(temporal|numeric|guard|routing)
applies_to_specs | source

## state_machines.tsv  (FSM backbone; guards are human checkpoints)
entity | states | guard | required_inputs | checkpoint_required

## acceptance_criteria.tsv / verification_methods.tsv
spec_id | ac_class | ac_text
spec_id | vm_no | tag | vm_text | evidence
''')
print('  schema.md written')
