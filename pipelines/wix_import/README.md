# Wix import pipeline

Pulls Wix eCommerce **platter-store orders → payments/refunds** into PostgreSQL
(`taza_ops`), idempotently, on a systemd timer. This is the **second payment
rail** (Schema Contract §5): Square = catering invoices; **Wix Payments = the
online platter store** (≤10% of revenue).

## What it writes

| Wix source | taza_ops table |
|------------|----------------|
| `order.buyerInfo` + `order.billingInfo.contactDetails` | `accounts` + `contacts` |
| `order` (`POST /ecom/v1/orders/search`) | `orders` (`order_source='wix'`; status/totals mapped; full order in `raw_payload`) |
| `orderTransactions.payments` (`POST /ecom/v1/payments/list-by-ids`) | `payments` (`payment_type='full'`, `rail='wix'`) |
| `orderTransactions.refunds` | `payments` (`payment_type='refund'`, `status='refunded'`) |

A Wix platter sale is a store **order**, not a Square-style invoice, so it lands
in `orders` — not `invoices`. The order's **line items are preserved in
`orders.raw_payload`**; a relational line-item breakout is a later follow-up.

All rows upsert on `(source_system='wix', external_id)`. Unchanged orders are
skipped via `external_payload_hash`. Per-order failures route to the
`exceptions` queue — one bad order never aborts the run.

Wix money is a decimal string in the order currency (e.g. `"19.00"`); the
pipeline converts to integer cents (`ROUND_HALF_UP`) before writing.

## Deploy on the N100

```bash
cd /opt/taza-os/pipelines/wix_import          # wherever the repo is pulled
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env          # set WIX_API_KEY + WIX_SITE_ID + DATABASE_URL

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

- Schema applied: `db/schema/apply.sh`, then migrations `001`, `002`, `003`.
- A Wix API key with **Read Orders** (`ECOM.READ_ORDERS`) and **Read
  Transactions** (`ECOM.READ_TRANSACTIONS`) permission scopes, plus the site id.

## Exit codes

`0` clean · `1` completed with per-order errors (see `exceptions`) · `2` misconfig.
