import csv, glob, os, re
from collections import Counter, defaultdict

# --- registry: canonical IDs from CSV (287), cluster from markdown ---
rows = []
for p in ['notion-export/master-urs.csv', 'notion-export/planner-urs-rows.csv']:
    rows.extend(list(csv.DictReader(open(p, encoding='utf-8'))))
registry = {r['Spec ID'].strip() for r in rows}
by_id = {r['Spec ID'].strip(): r for r in rows}

cluster_of = {}
for path in sorted(glob.glob('notion-export/clusters/*.md')):
    cluster = os.path.basename(path)[:-3]
    for line in open(path, encoding='utf-8'):
        if line.startswith('## '):
            head = line[3:].strip()
            code = head.split(' — ', 1)[0].strip()
            cluster_of[code] = cluster

ids = sorted(registry, key=len, reverse=True)
id_re = re.compile(r'\b(' + '|'.join(re.escape(i) for i in ids) + r')\b')
candidate_re = re.compile(r'\b[A-Z]{2,}-\d+[A-Z0-9-]*\b|\bW\d+\b|\bV2-[A-Z]+-\d+\b')
# legacy alias families: CLOSE 1, SHOP 3, INVOICE 13, CATALOG 10, PACK 2, EXCEPT 5 (space-number)
family_re = re.compile(r'\b(CLOSE|SHOP|INVOICE|CATALOG|PACK|EXCEPT)\s+(\d+)\b')
decision_re = re.compile(r'\bD-\d+\b')

out_claims = defaultdict(set)
in_claims  = defaultdict(set)
families = Counter()
short_forms = defaultdict(set)   # token -> canonical IDs it resolves to
dangling = defaultdict(set)
evidence = {}

def snip(text, m):
    s = max(0, m.start()-45); e = min(len(text), m.end()+45)
    return text[s:e].replace('\n',' ').strip()

for r in rows:
    sid = r['Spec ID'].strip()
    for field, tset in [('Inputs', in_claims), ('Outputs', out_claims)]:
        text = r.get(field) or ''
        if not text.strip():
            continue
        seen = set()
        for m in id_re.finditer(text):
            tgt = m.group(1)
            if tgt == sid or tgt in seen:
                continue
            seen.add(tgt)
            tset[sid].add(tgt)
            evidence[(sid, tgt, field)] = snip(text, m)
        # legacy alias families
        for m in family_re.finditer(text):
            families[m.group(0)] += 1
            evidence[(sid, m.group(0), field+'-FAMILY')] = snip(text, m)
        # decision refs D-xxx
        for m in decision_re.finditer(text):
            evidence[(sid, m.group(0), field+'-DECISION')] = snip(text, m)
        # candidate id-like tokens not in registry
        for m in candidate_re.finditer(text):
            tok = m.group(0)
            if tok in registry or tok == sid:
                continue
            if family_re.fullmatch(tok) or decision_re.fullmatch(tok):
                continue
            # short-form resolution: URS-{tok} in registry?
            cand = 'URS-' + tok
            if cand in registry:
                short_forms[tok].add(cand)
                evidence[(sid, tok, field+'-SHORT')] = snip(text, m)
                continue
            # V2-{tok} in registry?
            cand2 = 'V2-' + tok
            if cand2 in registry:
                short_forms[tok].add(cand2)
                evidence[(sid, tok, field+'-SHORT')] = snip(text, m)
                continue
            dangling[sid].add(tok)
            evidence[(sid, tok, field+'-DANGLING')] = snip(text, m)

# build canonical edges from claims, using resolved short forms too
for sid in list(out_claims):
    pass
pairs = set()
for s, tgts in out_claims.items():
    for t in tgts: pairs.add((s, t))
for s, tgts in in_claims.items():
    for t in tgts: pairs.add((t, s))

edges = []
for src, tgt in sorted(pairs):
    out_ok = tgt in out_claims.get(src, set())
    in_ok  = src in in_claims.get(tgt, set())
    st = 'MIRRORED' if (out_ok and in_ok) else ('ONE_WAY_OUT' if out_ok else 'ONE_WAY_IN')
    edges.append((src, tgt, st))

mirrored = [e for e in edges if e[2]=='MIRRORED']
oneway = [e for e in edges if e[2]!='MIRRORED']

# --- write ---
with open('urs/pass0-edges.tsv','w',encoding='utf-8',newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['source','target','status','source_cluster','target_cluster','evidence'])
    for src, tgt, st in edges:
        w.writerow([src, tgt, st, cluster_of.get(src,''), cluster_of.get(tgt,''),
                    evidence.get((src,tgt,'Outputs')) or evidence.get((src,tgt,'Inputs')) or ''])

with open('urs/pass0-edges-findings.md','w',encoding='utf-8') as f:
    f.write("# Pass 0 — Edge / Reciprocity Findings\n\n")
    f.write(f"Registry: {len(registry)} specs. Canonical edges: {len(edges)} "
            f"({len(mirrored)} mirrored, {len(oneway)} one-way).\n\n")
    f.write("## ONE_WAY edges\n\n")
    for src, tgt, st in sorted(oneway):
        f.write(f"- {src} → {tgt}  [{st}]  ({cluster_of.get(src,'')} → {cluster_of.get(tgt,'')})\n")
    f.write("\n## Short-form references (resolved to canonical IDs)\n\n")
    for tok in sorted(short_forms):
        f.write(f"- `{tok}` → {sorted(short_forms[tok])}\n")
    f.write("\n## Dangling references (no canonical ID exists)\n\n")
    for src in sorted(dangling):
        for tok in sorted(dangling[src]):
            f.write(f"- {src} → `{tok}`: {evidence.get((src,tok,'Inputs-DANGLING')) or evidence.get((src,tok,'Outputs-DANGLING')) or ''}\n")
    f.write("\n## Legacy alias families (need canonical mapping)\n\n")
    for tok, n in families.most_common():
        f.write(f"- `{tok}` ×{n}\n")

# --- stdout ---
print(f"registry: {len(registry)} | edges: {len(edges)} (mirrored {len(mirrored)}, one-way {len(oneway)})")
print(f"short-form tokens: {len(short_forms)} | dangling tokens: {len(set(t for s in dangling.values() for t in s))} | legacy families: {sum(families.values())}")
print()
print("=== ONE_WAY edges ===")
for src, tgt, st in oneway:
    print(f"  {src:12s} -> {tgt:14s} [{st}]  {cluster_of.get(src,''):>14s} -> {cluster_of.get(tgt,'')}")
print()
print("=== short forms resolved ===")
for tok in sorted(short_forms):
    print(f"  {tok:14s} -> {sorted(short_forms[tok])}")
print()
print("=== dangling ===")
for src in sorted(dangling):
    for tok in sorted(dangling[src]):
        print(f"  {src:12s} -> {tok}")
print()
print("=== legacy alias families ===")
for tok, n in families.most_common():
    print(f"  {tok:14s} x{n}")
