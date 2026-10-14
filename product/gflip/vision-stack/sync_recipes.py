#!/usr/bin/env python3
"""Mirror the dish -> ingredients source from n100 (tazaos) into world.db.

WHY A MIRROR AND NOT A LIVE QUERY: gflip's Postgres client is not in n100's
pg_hba, and adding it means an edit + RELOAD of pg_hba.conf (README-FIRST s5.8).
A read-only mirror keeps the vision stack self-contained, matches how the Square
sync already works, and makes the QC path testable when n100 is unreachable.

SOURCE ORDER for a dish's ingredient list (vision stack, bootstrap):
  1. world.db.recipes            <- this mirror (and any manual override)
  2. menu_items.description      <- parsed comma list from tazaos
  3. rag_operations_content      <- type='recipe' portion/ratio facts (context only)
"""
import json, re, sqlite3, subprocess, sys, datetime, os

REMOTE = "taza@192.168.2.102"
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'world', 'world.db')

SQL = ("select coalesce(name,'')||E'\\t'||coalesce(category,'')||E'\\t'||"
       "replace(coalesce(description,''),E'\\n',' ') from public.menu_items order by name")

def pull():
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", REMOTE,
           "sudo -n -u postgres psql -d tazaos -Atc \"%s\"" % SQL]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise SystemExit("pull failed: %s %s" % (out.returncode, out.stderr[:300]))
    return out.stdout

def ingredients_from_description(desc):
    """Bootstrap parse: take the comma-separated tail of the description."""
    d = (desc or '').strip()
    if not d or ',' not in d:
        return []
    tail = d.split(',', 1)[1]
    parts = [p.strip(' .;') for p in re.split(r'[,;]', tail)]
    return [p for p in parts if 2 <= len(p) <= 32][:12]

def main():
    raw = pull()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c = sqlite3.connect(DB); cur = c.cursor()
    cur.execute("""create table if not exists recipes(
        item text not null, category text, description text, ingredients text,
        source text, updated_ts text, primary key (item, source))""")
    n = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        f = line.split('\t')
        name = f[0].strip()
        cat = f[1].strip() if len(f) > 1 else ''
        desc = f[2].strip() if len(f) > 2 else ''
        if not name:
            continue
        ing = json.dumps(ingredients_from_description(desc))
        cur.execute("""insert into recipes(item,category,description,ingredients,source,updated_ts)
                       values(?,?,?,?,?,?)
                       on conflict(item,source) do update set
                         category=excluded.category, description=excluded.description,
                         ingredients=excluded.ingredients, updated_ts=excluded.updated_ts""",
                    (name, cat, desc, ing, 'tazaos.menu_items', now))
        n += 1
    c.commit()
    print("mirrored %d dishes from tazaos.menu_items" % n)
    for r in cur.execute("""select item, ingredients from recipes
                            where length(ingredients)>4 order by item limit 6"""):
        print("   %-42s %s" % (r[0][:42], r[1][:90]))
    print("   recipes rows:", cur.execute("select count(*) from recipes").fetchone()[0],
          "| with parsed ingredients:",
          cur.execute("select count(*) from recipes where length(ingredients)>4").fetchone()[0])
    c.close()

if __name__ == '__main__':
    main()


# ---------------------------------------------------------------------------
# The MEASUREMENT MEMORANDA. Nick captured this by hand (2026-09-06) and it is
# the authoritative quantity math: oz per person, per skewer, per ball, pan
# yields, platter builds by headcount. It reached n100 as
# tazaos.rag_operations_content, type='recipe' / 'rule', with machine-readable
# metadata_raw. Mirrored here as recipe_facts so the vision + label stack can do
# quantity math WITHOUT re-typing any of it.
Q_SQL = ("select coalesce(title,'')||E'\\t'||coalesce(type,'')||E'\\t'||"
         "replace(coalesce(metadata_raw,''),E'\\n',' ')||E'\\t'||"
         "replace(coalesce(content,''),E'\\n',' ') "
         "from public.rag_operations_content "
         "where type in ('recipe','rule','logistic') order by title")


def pull_query(sql):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", REMOTE,
           "sudo -n -u postgres psql -d tazaos -Atc \"%s\"" % sql]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if out.returncode != 0:
        raise SystemExit("pull failed: %s" % out.stderr[:300])
    return out.stdout


def sync_memoranda():
    raw = pull_query(Q_SQL)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c = sqlite3.connect(DB); cur = c.cursor()
    cur.execute("""create table if not exists recipe_facts(
        title text, kind text, fact_key text, fact_value text, unit text,
        content text, source text, updated_ts text,
        primary key (title, fact_key, source))""")
    nfacts = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        f = line.split('\t')
        title = f[0].strip()
        kind = f[1].strip() if len(f) > 1 else ''
        meta = f[2].strip() if len(f) > 2 else ''
        content = f[3].strip() if len(f) > 3 else ''
        if not title:
            continue
        for pair in meta.split(';'):
            if ':' not in pair:
                continue
            k, v = pair.split(':', 1)
            k, v = k.strip(), v.strip()
            if not k or not v:
                continue
            unit = ''
            m = re.search(r'([a-z_]+)$', k)
            if m:
                unit = {'oz': 'oz', 'pp': 'per_person', 'f': 'F', 'c': 'C',
                        'min': 'min', 'pp_': 'per_person'}.get(m.group(1), '')
            cur.execute("""insert into recipe_facts(title,kind,fact_key,fact_value,unit,
                                                     content,source,updated_ts)
                           values(?,?,?,?,?,?,?,?)
                           on conflict(title,fact_key,source) do update set
                             fact_value=excluded.fact_value, unit=excluded.unit,
                             content=excluded.content, updated_ts=excluded.updated_ts""",
                        (title, kind, k, v, unit, content[:400],
                         'tazaos.rag_operations_content', now))
            nfacts += 1
    c.commit()
    print("memoranda mirrored: %d fact rows" % nfacts)
    print("  total recipe_facts:", cur.execute("select count(*) from recipe_facts").fetchone()[0])
    for r in cur.execute("""select title, fact_key, fact_value, unit from recipe_facts
                            where fact_key in ('oz_per_person','oz_per_skewer','oz_per_ball',
                                               'oz_per_cube','ball_weight_oz','serves_pp')
                            order by title limit 12"""):
        print("   %-46s %-18s %-8s %s" % (r[0][:46], r[1], r[2], r[3]))
    c.close()


if __name__ == '__main__':
    main()
    sync_memoranda()
