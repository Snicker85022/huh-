#!/usr/bin/env python3
"""
Taza OS — Square catalog sync.

Caches the FULL Square catalog into PostgreSQL (taza_ops.menu_items), one row
per sellable ITEM_VARIATION, keyed by the variation id (square_id) — the id that
order line items reference. Runs weekly under a systemd timer.

Why variation-grained: a Square order line item's catalog_object_id is the
ITEM_VARIATION id, so linking invoice_line_items.menu_item_id only works when
menu_items.square_id holds the variation id. (Verified against live orders,
2026-07-16.)

Behavior:
  * Upsert every active variation by (square_id).
  * Preserve the full catalog object in raw_payload (per-item "intelligence"
    custom attributes ride along here until mapped to dedicated columns).
  * Deactivate (is_active=FALSE) any square-sourced menu_item not seen this run,
    so the local cache mirrors the catalog without deleting history.

Config (see .env.example):
    SQUARE_ACCESS_TOKEN   required
    DATABASE_URL          required
    SQUARE_LOCATION_ID    optional; filters "active at this location"
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Iterable

import psycopg2
import psycopg2.extras
import requests

log = logging.getLogger("catalog_sync")
SQUARE_API_BASE = os.environ.get("SQUARE_API_BASE", "https://connect.squareup.com")
SQUARE_API_VERSION = os.environ.get("SQUARE_API_VERSION", "2025-01-23")


class Square:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Square-Version": SQUARE_API_VERSION,
                "Content-Type": "application/json",
            }
        )

    def search_objects(self, object_types: list[str]) -> Iterable[dict]:
        cursor = None
        while True:
            body: dict[str, Any] = {"object_types": object_types, "limit": 200}
            if cursor:
                body["cursor"] = cursor
            r = self.s.post(
                f"{SQUARE_API_BASE}/v2/catalog/search", json=body, timeout=60
            )
            r.raise_for_status()
            data = r.json()
            for obj in data.get("objects", []):
                yield obj
            cursor = data.get("cursor")
            if not cursor:
                return


def money(m: dict | None) -> int | None:
    return None if not m else m.get("amount")


def is_active(obj: dict, location_id: str | None) -> bool:
    if obj.get("is_deleted"):
        return False
    if obj.get("present_at_all_locations"):
        return True
    if location_id:
        return location_id in (obj.get("present_at_location_ids") or [])
    return True


def variation_name(item_name: str, var: dict) -> str:
    vn = (var.get("item_variation_data", {}) or {}).get("name") or ""
    if vn and vn.strip() and vn.strip().lower() != "regular":
        return f"{item_name} — {vn.strip()}"
    return item_name


def sync(sq: Square, conn, location_id: str | None) -> dict:
    # category id -> name
    categories = {
        o["id"]: (o.get("category_data", {}) or {}).get("name")
        for o in sq.search_objects(["CATEGORY"])
    }
    stats = {"items": 0, "variations": 0, "upserts": 0, "deactivated": 0}
    seen: list[str] = []

    for item in sq.search_objects(["ITEM"]):
        stats["items"] += 1
        idata = item.get("item_data", {}) or {}
        item_name = idata.get("name") or ""
        cat_id = (idata.get("reporting_category") or {}).get("id")
        category = categories.get(cat_id)
        desc = idata.get("description_plaintext") or idata.get("description")
        kitchen = idata.get("kitchen_name")
        active_item = is_active(item, location_id)

        for var in idata.get("variations", []):
            stats["variations"] += 1
            vid = var["id"]
            vdata = var.get("item_variation_data", {}) or {}
            seen.append(vid)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO taza_ops.menu_items
                        (square_id, square_item_id, name, category, description,
                         price_cents, pricing_type, default_unit_cost_cents,
                         kitchen_name, reporting_category_id, ecom_available,
                         is_active, catalog_version, last_synced_at,
                         source_system, external_id, external_updated_at,
                         external_payload_hash, raw_payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(),
                            'square', %s, %s, %s, %s)
                    ON CONFLICT (square_id) DO UPDATE SET
                        square_item_id          = EXCLUDED.square_item_id,
                        name                    = EXCLUDED.name,
                        category                = EXCLUDED.category,
                        description             = EXCLUDED.description,
                        price_cents             = EXCLUDED.price_cents,
                        pricing_type            = EXCLUDED.pricing_type,
                        default_unit_cost_cents = EXCLUDED.default_unit_cost_cents,
                        kitchen_name            = EXCLUDED.kitchen_name,
                        reporting_category_id   = EXCLUDED.reporting_category_id,
                        ecom_available          = EXCLUDED.ecom_available,
                        is_active               = EXCLUDED.is_active,
                        catalog_version         = EXCLUDED.catalog_version,
                        last_synced_at          = now(),
                        external_updated_at     = EXCLUDED.external_updated_at,
                        external_payload_hash   = EXCLUDED.external_payload_hash,
                        raw_payload             = EXCLUDED.raw_payload,
                        updated_at              = now()
                    """,
                    (
                        vid,
                        item["id"],
                        variation_name(item_name, var),
                        category,
                        desc,
                        money(vdata.get("price_money")),
                        vdata.get("pricing_type"),
                        money(vdata.get("default_unit_cost")),
                        kitchen,
                        cat_id,
                        idata.get("ecom_available"),
                        active_item and is_active(var, location_id),
                        var.get("version"),
                        vid,
                        var.get("updated_at"),
                        var.get("version") and str(var.get("version")),
                        psycopg2.extras.Json({"item": {k: item.get(k) for k in
                            ("id", "version", "updated_at")}, "item_name": item_name,
                            "variation": var}),
                    ),
                )
                stats["upserts"] += 1
        conn.commit()

    # Deactivate square-sourced rows not present in this run (catalog deletions).
    if seen:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE taza_ops.menu_items SET is_active = FALSE, updated_at = now()
                WHERE source_system = 'square' AND is_active = TRUE
                  AND square_id <> ALL(%s)
                """,
                (seen,),
            )
            stats["deactivated"] = cur.rowcount
        conn.commit()
    return stats


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    token = os.environ.get("SQUARE_ACCESS_TOKEN")
    dsn = os.environ.get("DATABASE_URL")
    if not token or not dsn:
        log.error("SQUARE_ACCESS_TOKEN and DATABASE_URL are required")
        return 2
    sq = Square(token)
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        stats = sync(sq, conn, os.environ.get("SQUARE_LOCATION_ID"))
        log.info("DONE %s", stats)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
