# Wix import pipeline

Pulls **paid** Wix store (platter) orders → invoices → line items → payments
into PostgreSQL (`taza_ops`), idempotently, on a systemd timer.

## Why

Platter orders on the Wix store are deterministic: the customer pays online, the
order is auto-fired, and it **can't be modified once paid**. Today that "paid"
email is hand-copied onto a paper prep checklist. This pipeline replaces that
manual step — every paid order lands in `taza_ops` automatically, ready for the
day-of prep view.

Because paid orders are immutable, re-runs are almost entirely no-ops (skipped
via `external_payload_hash`).

## What it writes

| Wix source | taza_ops table |
|-----------|----------------|
| `buyerInfo` + `billingInfo.contactDetails` | `accounts` + `contacts` |
| order (one per Wix order) | `invoices` (status `Paid`; totals from `priceSummary`) |
| order | `orders` (`order_source='wix'`; fulfillment/pickup facts in `custom_attributes`) |
| `order.lineItems` | `invoice_line_items` (replaced each sync; `menu_item_id` NULL — Wix SKUs are a separate catalog; Wix `catalogItemId` kept in `catalog_object_id`) |
| `payments/list-by-ids` transactions | `payments` (`rail='wix'`; refunds captured as `payment_type='refund'`) |

All rows upsert on `(source_system='wix', external_id)`. Per-order failures route
to the `exceptions` queue — one bad order never aborts the run.

## APIs used

- **Search Orders** — `POST /ecom/v1/orders/search`, filtered to `paymentStatus=PAID`,
  cursor-paged. (Never returns `INITIALIZED` orders.)
- **List Transactions For Multiple Orders** — `POST /ecom/v1/payments/list-by-ids`
  (batched by 100 order IDs) for payments + refunds.

Auth: a Wix **account API key** in `Authorization`, scoped to the store's site
via the `wix-site-id` header.

## Deploy on the N100

```bash
cd /opt/taza-os/pipelines/wix_import            # wherever the repo is pulled
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env            # set WIX_API_KEY + WIX_SITE_ID + DATABASE_URL

# one-off run
set -a && . .env && set +a && python3 wix_import.py

# install the timer (edit paths in the unit files first)
sudo cp ../../deploy/systemd/taza-wix-import.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now taza-wix-import.timer
systemctl list-timers taza-wix-import.timer
journalctl -u taza-wix-import.service -f
```

## Prereqs

- Schema applied: `db/schema/apply.sh` then `db/migrations/001_square_import_support.sql`.
  **No new migration is required** — this pipeline reuses the columns migration
  001 added (`provider_status`, `raw_payload`, `invoice_number`, …). The
  `order_source`, `source_system`, and `payment_rail` enums already include `wix`.

## Config

| Var | Required | Default | Notes |
|-----|----------|---------|-------|
| `WIX_API_KEY` | yes | — | Wix account API key (keep secret) |
| `WIX_SITE_ID` | yes | — | Site the store belongs to |
| `DATABASE_URL` | yes | — | `postgres://taza@localhost:5432/taza_ops` |
| `WIX_API_BASE` | no | `https://www.wixapis.com` | |
| `WIX_PAYMENT_STATUSES` | no | `PAID` | comma-separated (e.g. `PAID,PARTIALLY_PAID`) |
| `WIX_UPDATED_AFTER_DAYS` | no | — | if set, only orders updated within N days |

## Exit codes

`0` clean · `1` completed with per-order errors (see `exceptions`) · `2` misconfig.
