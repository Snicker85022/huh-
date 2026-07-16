# Catalog sync

Caches the **full Square catalog** into `taza_ops.menu_items`, one row per
sellable `ITEM_VARIATION`, keyed by the **variation id** (`square_id`). Runs
**weekly** under a systemd timer. This is the foundation that makes invoice
line-item linking work — order line items reference the variation id, so
`menu_items.square_id` must hold that same id.

## What it does

- Pages the entire catalog (`ITEM` + `CATEGORY`) via `SearchCatalogObjects`.
- Upserts each variation: name, category, price, cost, pricing type, kitchen
  name, active flag, `catalog_version`, and the full object in `raw_payload`
  (per-item intelligence custom attributes ride along here until mapped to the
  dedicated `menu_items` columns).
- **Deactivates** (`is_active = FALSE`) any square-sourced row no longer in the
  catalog — the cache mirrors Square without deleting history.

## Deploy on the N100

```bash
cd /opt/taza-os/pipelines/catalog_sync
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env        # SQUARE_ACCESS_TOKEN + DATABASE_URL

set -a && . .env && set +a && python3 catalog_sync.py   # one-off

sudo cp ../../deploy/systemd/taza-catalog-sync.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now taza-catalog-sync.timer
```

Run the catalog sync **before** the first Square invoice import so line items
resolve to `menu_items`.
