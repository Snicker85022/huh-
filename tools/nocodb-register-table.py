#!/usr/bin/env python3
"""Register an EXISTING public table as a NocoDB model (correct source + columns).

Fixes the recurring "NocoDB shows empty / column does not exist" bug: when the
physical table changes, its NocoDB model must be rebuilt against the ACTUAL
columns. This deletes any stale model(s) for the table and re-registers it.

Usage: python3 tools/nocodb-register-table.py <table_name>
"""
import subprocess, sys, random, string, re

TABLE = sys.argv[1]
N100 = 'taza@192.168.2.102'
BASE = 'pckp5o6vpkbml4e'
SRC  = 'bji1ynay4n873ui'
WS   = 'w1fvdngk'

def sh(sql):
    # stdin pipe avoids the remote shell interpreting SQL operators like || and quotes
    r = subprocess.run(['ssh','-o','BatchMode=yes',N100,'psql','-U','taza','-d','tazaos','-tAc'],
                       input=sql, capture_output=True, text=True)
    return r.stdout.strip()

def rid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

# actual columns from Postgres
cols = []
q = f"SELECT column_name || '|' || data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='{TABLE}' ORDER BY ordinal_position;"
out = sh(q)
for line in out.splitlines():
    if '|' in line:
        name, typ = line.split('|', 1)
        cols.append((name, typ))
if not cols:
    sys.exit(f'no columns found for public.{TABLE}')

UMAP = {'text':'LongText','character varying':'SingleLineText','integer':'Number','bigint':'Number',
        'smallint':'Number','numeric':'Decimal','double precision':'Decimal','real':'Decimal',
        'boolean':'Checkbox','timestamp with time zone':'DateTime','timestamp without time zone':'DateTime',
        'json':'LongText','jsonb':'LongText'}

def uidt(t):
    return UMAP.get(t, 'LongText')

# 1) delete stale model(s) + dependents
models = sh(f"SELECT id FROM nc_models_v2 WHERE table_name='{TABLE}';").splitlines()
for mid in models:
    views = sh(f"SELECT id FROM nc_views_v2 WHERE fk_model_id='{mid}';").splitlines()
    for v in views:
        sh(f"DELETE FROM nc_grid_view_columns_v2 WHERE fk_view_id='{v}';")
        sh(f"DELETE FROM nc_grid_view_v2 WHERE fk_view_id='{v}';")
    sh(f"DELETE FROM nc_views_v2 WHERE fk_model_id='{mid}';")
    sh(f"DELETE FROM nc_view_sections WHERE fk_model_id='{mid}';")
    sh(f"DELETE FROM nc_columns_v2 WHERE fk_model_id='{mid}';")
    sh(f"DELETE FROM nc_model_stats_v2 WHERE fk_model_id='{mid}';")
    sh(f"DELETE FROM nc_models_v2 WHERE id='{mid}';")
print(f'removed {len(models)} stale model(s) for {TABLE}')

# 2) insert model + columns + view + grid
MID, VID = rid(), rid()
order = sh(f"SELECT COALESCE(MAX(\"order\"),0)+1 FROM nc_models_v2 WHERE base_id='{BASE}';") or '1'
L = [f"INSERT INTO nc_models_v2 (id, source_id, base_id, table_name, title, type, enabled, mm, synced, \"order\", fk_workspace_id, doc_version, has_children) VALUES ('{MID}','{SRC}','{BASE}','{TABLE}','{TABLE}','table',true,false,false,{order},'{WS}',1,false);"]
cids = []
for i,(name,typ) in enumerate(cols, start=1):
    cid = rid(); cids.append(cid)
    L.append(f"INSERT INTO nc_columns_v2 (id, source_id, base_id, fk_model_id, title, column_name, uidt, dt, pk, rqd, ai, \"order\", fk_workspace_id) VALUES ('{cid}','{SRC}','{BASE}','{MID}','{name}','{name}','{uidt(typ)}','{typ}',false,false,false,{i},'{WS}');")
L.append(f"INSERT INTO nc_views_v2 (id, source_id, base_id, fk_model_id, title, type, is_default, show_system_fields, lock_type, show, \"order\", meta, fk_workspace_id) VALUES ('{VID}','{SRC}','{BASE}','{MID}','{TABLE}',3,NULL,true,'collaborative',true,1,'{{}}','{WS}');")
L.append(f"INSERT INTO nc_grid_view_v2 (fk_view_id, source_id, base_id, fk_workspace_id) VALUES ('{VID}','{SRC}','{BASE}','{WS}');")
for i,cid in enumerate(cids, start=1):
    L.append(f"INSERT INTO nc_grid_view_columns_v2 (id, fk_view_id, fk_column_id, source_id, base_id, width, show, \"order\", fk_workspace_id) VALUES ('{rid()}','{VID}','{cid}','{SRC}','{BASE}','200px',true,{i},'{WS}');")

sql = 'BEGIN;\n' + '\n'.join(L) + '\nCOMMIT;\n'
r = subprocess.run(['ssh','-o','BatchMode=yes',N100,'psql','-U','taza','-d','tazaos','-v','ON_ERROR_STOP=1','-q','-f','-'],
                   input=sql, text=True, capture_output=True)
print('exit', r.returncode)
if r.returncode:
    print(r.stderr[:3000]); sys.exit(1)
print(f'{TABLE}: model {MID}, {len(cids)} columns, view {VID}')
