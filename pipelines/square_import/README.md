# Square import pipeline

Pulls Square invoices → orders → line items → payments into PostgreSQL
(`taza_ops`), idempotently, on a systemd timer.

## What it writes

| Square source | taza_ops table |
|---------------|----------------|
| `invoice.primary_recipient` | `accounts` + `contacts` |
| `invoice` | `invoices` (status mapped; raw kept in `provider_status` + `raw_payload`) |
| `order` (batch-retrieve by `order_id`) | `orders` |
| `order.line_items` | `invoice_line_items` (replaced each sync; `catalog_object_id` → `menu_items`) |
| `order.tenders` | `payments` (deposit vs balance inferred by amount) |

All rows upsert on `(source_system='square', external_id)`. Unchanged invoices
are skipped via `external_payload_hash`. Per-invoice failures route to the
`exceptions` queue — one bad invoice never aborts the run.

## Deploy on the N100

```bash
cd /opt/taza-os/pipelines/square_import        # wherever the repo is pulled
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env           # set SQUARE_ACCESS_TOKEN + DATABASE_URL

# one-off run
set -a && . .env && set +a && python3 square_import.py

# install the timer (edit paths in the unit files first)
sudo cp ../../deploy/systemd/taza-square-import.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now taza-square-import.timer
systemctl list-timers taza-square-import.timer
journalctl -u taza-square-import.service -f
```

## Prereqs

- Schema applied: `db/schema/apply.sh` then `db/migrations/001_square_import_support.sql`.
- `menu_items` populated from the Square catalog sync (so `catalog_object_id`
  line items link to a `menu_item_id`; unlinked/ad-hoc items still import with
  `menu_item_id` NULL).

## Exit codes

`0` clean · `1` completed with per-invoice errors (see `exceptions`) · `2` misconfig.
