import re, glob, os
from collections import Counter

CLUST = '/home/taza/repo/notion-export/clusters'
OUT = '/home/taza/repo/urs/pass0-gist.txt'

def grab(block, key, lim=400):
    m = re.search(r'\*\*' + re.escape(key) + r':\*\*\s*\n?(.*?)(?=\n\*\*|\n_Notion:|\Z)', block, re.S)
    if not m:
        return ''
    return re.sub(r'\s+', ' ', m.group(1)).strip()[:lim]

def status_parts(block):
    m = re.search(r'\*\*Status:\*\*\s*(.*?)\s*\|\s*\*\*Priority:\*\*\s*(.*?)\s*\|\s*\*\*Release:\*\*\s*(.*)', block)
    if not m:
        m2 = re.search(r'\*\*Status:\*\*\s*(.*)', block)
        return (m2.group(1).strip() if m2 else '', '', '')
    return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

rows = []
for path in sorted(glob.glob(CLUST + '/*.md')):
    text = open(path, encoding='utf-8').read()
    blocks = re.split(r'(?m)^## ', text)[1:]
    for b in blocks:
        first = b.split('\n', 1)[0].strip()
        parts = first.split(' — ', 1)
        code = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ''
        status, prio, rel = status_parts(b)
        rr = ''
        m = re.search(r'\*\*Required for Release:\*\*\s*(.*)', b)
        if m: rr = m.group(1).strip()
        dom = ''
        m = re.search(r'\*\*Domain:\*\*\s*\n?\s*(.*?)(?=\n\*\*|\Z)', b, re.S)
        if m: dom = re.sub(r'\s+', ' ', m.group(1)).strip()[:60]
        frs = grab(b, 'Functional Requirement Specification', 320)
        kind = 'FRS' if frs else ''
        if not frs:
            frs = grab(b, 'User Requirement Statement', 260)
            kind = 'URS'
        rows.append((os.path.basename(path), code, title, status, prio, rel, rr, kind, dom, frs))

with open(OUT, 'w', encoding='utf-8') as f:
    for r in rows:
        fname, code, title, status, prio, rel, rr, kind, dom, frs = r
        f.write(f"{fname:22s} {code:16s} | {status:22s} | P:{prio:4s} | RL:{rel:6s} | RR:{rr:3s} | {kind:3s} | {frs}\n")
    f.write(f"\nTOTAL ROWS: {len(rows)}\n")

print(f"TOTAL ROWS: {len(rows)}")
print("\n=== per-cluster row counts ===")
for f, n in sorted(Counter(r[0] for r in rows).items()):
    print(f"  {f:22s} {n}")
print("\n=== status distribution ===")
for s, n in Counter(r[3] for r in rows).most_common():
    print(f"  {s or '(empty)':30s} {n}")
print("\n=== required-for-release distribution ===")
for s, n in Counter(r[6] for r in rows).most_common():
    print(f"  {s or '(empty)':30s} {n}")
print("\n=== sample (first 30 rows) ===")
for r in rows[:30]:
    fname, code, title, status, prio, rel, rr, kind, dom, frs = r
    print(f"{fname:22s} {code:16s} | {status:22s} | P:{prio:4s} | RL:{rel:6s} | RR:{rr:3s} | {kind:3s} | {frs}")
