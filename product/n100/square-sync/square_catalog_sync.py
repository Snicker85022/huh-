#!/usr/bin/env python3
"""
Square catalog local mirror — weekly full pull-and-upsert.

Pulls every ITEM (with variations and custom attribute values) from the
Square Catalog API, resolves custom-attribute definitions to human keys,
and upserts into square_catalog_items. Items no longer returned by the
API are marked is_active=FALSE (soft delete). Each run writes a row to
square_catalog_sync_log.

v1 strategy is a weekly full pull. This is more robust on an N100 that
may be offline when a catalog.version.updated webhook fires. Switch to
webhook-driven incremental sync later if pull volume becomes a problem.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("square_catalog_sync")

SQUARE_TOKEN = os.environ.get("SQUARE_ACCESS_TOKEN")
SQUARE_BASE = os.environ.get("SQUARE_API_BASE", "https://connect.squareup.com/v2")
SQUARE_VERSION = os.environ.get("SQUARE_API_VERSION", "2025-01-23")
PG_DSN = os.environ.get(
    "TAZAOS_PG_DSN", "dbname=tazaos user=taza host=/var/run/postgresql"
)

# Map from Tier 1 column name -> list of candidate custom attribute definition
# keys (Square exposes attributes by definition "key" which is set by whoever
# created the attribute in the Seller Dashboard). We check several plausible
# spellings so the sync tolerates the actual naming the catering team used.
TIER1_ATTRIBUTES = {
    "serves_min": ["serves_min", "min_serves", "servings_min"],
    "serves_max": ["serves_max", "max_serves", "servings_max"],
    "pricing_unit": ["pricing_unit", "price_unit", "unit"],
    "dietary_flags": ["dietary_flags", "diet_flags", "dietary"],
    "allergen_notes": ["allergen_notes", "allergens_notes", "allergen"],
    "station_type": ["station_type", "station"],
    "hot_hold_max_min": ["hot_hold_max_min", "hot_hold_max", "hot_hold_minutes"],
    "cold_hold_max_min": ["cold_hold_max_min", "cold_hold_max", "cold_hold_minutes"],
    "prep_advance_max_hr": [
        "prep_advance_max_hr",
        "prep_advance_hours",
        "prep_advance_max",
    ],
    "quality_risk": ["quality_risk", "risk"],
    "default_pan_footprint": [
        "default_pan_footprint",
        "pan_footprint",
        "default_pan",
    ],
}


class SyncError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {SQUARE_TOKEN}",
        "Square-Version": SQUARE_VERSION,
        "Content-Type": "application/json",
    }


def _post(path, body):
    url = f"{SQUARE_BASE}{path}"
    for attempt in range(3):
        r = requests.post(url, headers=_headers(), json=body, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            wait = 2 ** attempt
            log.warning("Square %s %s -> retry in %ss", path, r.status_code, wait)
            time.sleep(wait)
            continue
        if r.status_code >= 400:
            raise SyncError(f"Square {path} {r.status_code}: {r.text[:500]}")
        return r.json()
    raise SyncError(f"Square {path} failed after retries")


def fetch_attribute_definitions():
    """Return dict of definition_id -> attribute_key (short name)."""
    defs = {}
    cursor = None
    while True:
        body = {"object_types": ["CUSTOM_ATTRIBUTE_DEFINITION"], "limit": 200}
        if cursor:
            body["cursor"] = cursor
        data = _post("/catalog/search", body)
        for obj in data.get("objects", []) or []:
            defn = obj.get("custom_attribute_definition_data") or {}
            key = defn.get("key") or defn.get("name")
            if key:
                defs[obj["id"]] = key.strip().lower().replace(" ", "_")
        cursor = data.get("cursor")
        if not cursor:
            break
    log.info("Fetched %d custom attribute definitions", len(defs))
    return defs


def fetch_items():
    """Return list of ITEM catalog objects with variations + custom attrs."""
    items = []
    variations_by_item = {}
    cursor = None
    while True:
        body = {
            "object_types": ["ITEM", "ITEM_VARIATION", "CATEGORY"],
            "include_deleted_objects": False,
            "include_related_objects": True,
            "limit": 200,
        }
        if cursor:
            body["cursor"] = cursor
        data = _post("/catalog/search", body)
        for obj in data.get("objects", []) or []:
            if obj.get("type") == "ITEM":
                items.append(obj)
            elif obj.get("type") == "ITEM_VARIATION":
                item_id = (obj.get("item_variation_data") or {}).get("item_id")
                if item_id:
                    variations_by_item.setdefault(item_id, []).append(obj)
        for obj in data.get("related_objects", []) or []:
            if obj.get("type") == "ITEM_VARIATION":
                item_id = (obj.get("item_variation_data") or {}).get("item_id")
                if item_id:
                    variations_by_item.setdefault(item_id, []).append(obj)
        cursor = data.get("cursor")
        if not cursor:
            break
    for it in items:
        it["_variations"] = variations_by_item.get(it["id"], [])
    log.info("Fetched %d items from Square", len(items))
    return items


def _resolve_attr(custom_map, candidates):
    """Look up a Tier 1 column across possible attribute keys / def ids."""
    if not custom_map:
        return None
    for cand in candidates:
        cand_l = cand.lower()
        for _def_id, entry in custom_map.items():
            key = (entry.get("key") or "").lower()
            name = (entry.get("name") or "").lower()
            if cand_l in (key, name):
                return entry
    return None


def _val(entry):
    """Extract a scalar Python value from a custom attribute value dict."""
    if not entry:
        return None
    for k in (
        "string_value",
        "number_value",
        "boolean_value",
        "selection_uid_values",
    ):
        if k in entry and entry[k] is not None:
            return entry[k]
    return None


def _as_int(v):
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return None


def _as_list(v):
    if v is None:
        return None
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]


def _lowest_price_cents(item):
    """Item-level price = min variation price_money.amount."""
    prices = []
    for var in item.get("_variations") or []:
        pm = (var.get("item_variation_data") or {}).get("price_money") or {}
        amt = pm.get("amount")
        if isinstance(amt, int):
            prices.append(amt)
    return min(prices) if prices else None


def _currency(item):
    for var in item.get("_variations") or []:
        pm = (var.get("item_variation_data") or {}).get("price_money") or {}
        cur = pm.get("currency")
        if cur:
            return cur
    return "USD"


def transform_item(item, attr_defs, categories_by_id):
    data = item.get("item_data") or {}
    custom_map = item.get("custom_attribute_values") or {}

    # Build a normalized attribute lookup keyed by both definition key and
    # legacy definition_id form.
    norm_custom = {}
    for def_id_or_key, entry in custom_map.items():
        norm_custom[def_id_or_key] = entry
        # If the key in the map is a definition id we know, also alias by key.
        if def_id_or_key in attr_defs:
            norm_custom[attr_defs[def_id_or_key]] = entry

    tier1 = {}
    for col, candidates in TIER1_ATTRIBUTES.items():
        entry = _resolve_attr(norm_custom, candidates)
        tier1[col] = _val(entry)

    cat_id = data.get("category_id") or (data.get("categories") or [{}])[0].get(
        "id"
    ) if data.get("categories") else data.get("category_id")

    updated_at = item.get("updated_at")
    if updated_at:
        try:
            # Square returns ISO-8601 with 'Z'; normalize for psycopg2.
            updated_at = updated_at.replace("Z", "+00:00")
        except AttributeError:
            updated_at = None

    return {
        "square_id": item["id"],
        "name": data.get("name") or "(unnamed)",
        "description": data.get("description") or data.get("description_plaintext"),
        "category_id": cat_id,
        "category_name": categories_by_id.get(cat_id) if cat_id else None,
        "is_active": not item.get("is_deleted", False),
        "is_deleted": bool(item.get("is_deleted", False)),
        "version": item.get("version"),
        "square_updated_at": updated_at,
        "price_cents": _lowest_price_cents(item),
        "currency": _currency(item),
        "variation_count": len(item.get("_variations") or []),
        "serves_min": _as_int(tier1["serves_min"]),
        "serves_max": _as_int(tier1["serves_max"]),
        "pricing_unit": tier1["pricing_unit"],
        "dietary_flags": _as_list(tier1["dietary_flags"]),
        "allergen_notes": tier1["allergen_notes"],
        "station_type": tier1["station_type"],
        "hot_hold_max_min": _as_int(tier1["hot_hold_max_min"]),
        "cold_hold_max_min": _as_int(tier1["cold_hold_max_min"]),
        "prep_advance_max_hr": _as_int(tier1["prep_advance_max_hr"]),
        "quality_risk": tier1["quality_risk"],
        "default_pan_footprint": tier1["default_pan_footprint"],
        "custom_attributes": json.dumps(custom_map) if custom_map else None,
        "raw_item": json.dumps(item),
    }


UPSERT_SQL = """
INSERT INTO square_catalog_items (
    square_id, name, description, category_id, category_name,
    is_active, is_deleted, version, square_updated_at,
    price_cents, currency, variation_count,
    serves_min, serves_max, pricing_unit, dietary_flags, allergen_notes,
    station_type, hot_hold_max_min, cold_hold_max_min, prep_advance_max_hr,
    quality_risk, default_pan_footprint,
    custom_attributes, raw_item, last_synced_at
) VALUES (
    %(square_id)s, %(name)s, %(description)s, %(category_id)s, %(category_name)s,
    %(is_active)s, %(is_deleted)s, %(version)s, %(square_updated_at)s,
    %(price_cents)s, %(currency)s, %(variation_count)s,
    %(serves_min)s, %(serves_max)s, %(pricing_unit)s, %(dietary_flags)s, %(allergen_notes)s,
    %(station_type)s, %(hot_hold_max_min)s, %(cold_hold_max_min)s, %(prep_advance_max_hr)s,
    %(quality_risk)s, %(default_pan_footprint)s,
    %(custom_attributes)s::jsonb, %(raw_item)s::jsonb, NOW()
)
ON CONFLICT (square_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    category_id = EXCLUDED.category_id,
    category_name = EXCLUDED.category_name,
    is_active = EXCLUDED.is_active,
    is_deleted = EXCLUDED.is_deleted,
    version = EXCLUDED.version,
    square_updated_at = EXCLUDED.square_updated_at,
    price_cents = EXCLUDED.price_cents,
    currency = EXCLUDED.currency,
    variation_count = EXCLUDED.variation_count,
    serves_min = EXCLUDED.serves_min,
    serves_max = EXCLUDED.serves_max,
    pricing_unit = EXCLUDED.pricing_unit,
    dietary_flags = EXCLUDED.dietary_flags,
    allergen_notes = EXCLUDED.allergen_notes,
    station_type = EXCLUDED.station_type,
    hot_hold_max_min = EXCLUDED.hot_hold_max_min,
    cold_hold_max_min = EXCLUDED.cold_hold_max_min,
    prep_advance_max_hr = EXCLUDED.prep_advance_max_hr,
    quality_risk = EXCLUDED.quality_risk,
    default_pan_footprint = EXCLUDED.default_pan_footprint,
    custom_attributes = EXCLUDED.custom_attributes,
    raw_item = EXCLUDED.raw_item,
    last_synced_at = NOW();
"""


def sync_to_postgres(rows):
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    seen_ids = [r["square_id"] for r in rows]
    upserted = 0
    deactivated = 0
    try:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(UPSERT_SQL, row)
                upserted += 1
            # Soft-delete anything no longer returned by Square.
            if seen_ids:
                cur.execute(
                    """
                    UPDATE square_catalog_items
                       SET is_active = FALSE, last_synced_at = NOW()
                     WHERE is_active = TRUE
                       AND NOT (square_id = ANY(%s))
                    """,
                    (seen_ids,),
                )
                deactivated = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return upserted, deactivated


def write_sync_log(status, seen, upserted, deactivated, attr_defs_seen, error=None):
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO square_catalog_sync_log
                    (finished_at, status, items_seen, items_upserted,
                     items_deactivated, attr_defs_seen, error_message)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s)
                """,
                (status, seen, upserted, deactivated, attr_defs_seen, error),
            )
    finally:
        conn.close()


def build_category_map():
    cats = {}
    cursor = None
    while True:
        body = {"object_types": ["CATEGORY"], "limit": 200}
        if cursor:
            body["cursor"] = cursor
        data = _post("/catalog/search", body)
        for obj in data.get("objects", []) or []:
            cats[obj["id"]] = (obj.get("category_data") or {}).get("name")
        cursor = data.get("cursor")
        if not cursor:
            break
    return cats


def main():
    if not SQUARE_TOKEN:
        log.error("SQUARE_ACCESS_TOKEN not set")
        write_sync_log("failed", 0, 0, 0, 0, "SQUARE_ACCESS_TOKEN not set")
        sys.exit(2)

    start = time.time()
    try:
        attr_defs = fetch_attribute_definitions()
        categories = build_category_map()
        items = fetch_items()
        rows = [transform_item(it, attr_defs, categories) for it in items]
        upserted, deactivated = sync_to_postgres(rows)
        write_sync_log("ok", len(rows), upserted, deactivated, len(attr_defs))
        elapsed = time.time() - start
        log.info(
            "Sync OK: seen=%d upserted=%d deactivated=%d attr_defs=%d elapsed=%.1fs",
            len(rows),
            upserted,
            deactivated,
            len(attr_defs),
            elapsed,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Sync failed")
        write_sync_log("failed", 0, 0, 0, 0, str(exc)[:2000])
        sys.exit(1)


if __name__ == "__main__":
    main()
