#!/usr/bin/env python3
"""
Square menu catalog weekly sync
Runs every Sunday at 3am via systemd timer
Updates menu_items table in tazaos Postgres DB
"""
import os, json, logging, requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('square_sync')

SQUARE_TOKEN = os.environ.get('SQUARE_ACCESS_TOKEN')
SQUARE_BASE = 'https://connect.squareup.com/v2'

def fetch_catalog():
    headers = {'Authorization': f'Bearer {SQUARE_TOKEN}', 'Content-Type': 'application/json'}
    items = []
    cursor = None
    while True:
        body = {'object_types': ['ITEM', 'ITEM_VARIATION', 'CATEGORY'], 'limit': 200}
        if cursor:
            body['cursor'] = cursor
        r = requests.post(f'{SQUARE_BASE}/catalog/search', headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        objects = data.get('objects', [])
        items.extend([o for o in objects if o['type'] == 'ITEM'])
        cursor = data.get('cursor')
        if not cursor:
            break
    log.info(f'Fetched {len(items)} items from Square')
    return items

def sync_to_postgres(items):
    import psycopg2
    conn = psycopg2.connect(dbname='tazaos', user='taza')
    cur = conn.cursor()
    updated = 0
    for item in items:
        sid = item['id']
        name = item['item_data']['name']
        desc = item['item_data'].get('description', '')
        cat = 'Catering' if name.startswith('Catering') else 'Restaurant'
        cur.execute('''
            INSERT INTO menu_items (square_id, name, category, description, is_active, last_synced_at)
            VALUES (%s, %s, %s, %s, TRUE, NOW())
            ON CONFLICT (square_id) DO UPDATE SET
                name=EXCLUDED.name,
                category=EXCLUDED.category,
                description=EXCLUDED.description,
                last_synced_at=NOW()
        ''', (sid, name, cat, desc))
        updated += 1
    conn.commit()
    log.info(f'Synced {updated} items to Postgres')
    cur.close()
    conn.close()
    return updated

if __name__ == '__main__':
    if not SQUARE_TOKEN:
        log.error('SQUARE_ACCESS_TOKEN not set')
        exit(1)
    items = fetch_catalog()
    count = sync_to_postgres(items)
    log.info(f'Square sync complete: {count} items')
