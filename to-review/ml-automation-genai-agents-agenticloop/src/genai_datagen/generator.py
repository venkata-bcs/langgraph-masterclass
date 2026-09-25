"""Synthetic data generation for the genAI datagen pipeline.

Row volume is produced with Faker (fast, free, and good enough for
inventory/product test data). The LLM is used sparingly -- once per run,
cached to disk -- to generate a small set of realistic, on-theme reference
values (category names, supplier names, category blurbs) rather than
per-row, which would be slow and expensive at any real scale.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta

from faker import Faker

from src.common import paths
from src.common.llm_clients import LLMUnavailableError, chat

fake = Faker()

_REFERENCE_CACHE_PATH = paths.STATE_DIR / "reference_data_cache.json"

_FALLBACK_CATEGORIES = [
    "Beverages", "Snacks", "Dairy", "Frozen Foods", "Household Supplies",
    "Personal Care", "Bakery", "Produce",
]
_FALLBACK_SUPPLIERS = [
    "Northwind Traders", "Acme Wholesale", "BlueOak Distribution",
    "Harborline Supply Co", "Summit Logistics", "Cascade Foods Inc",
]
_WAREHOUSES = ["WH-EAST", "WH-WEST", "WH-CENTRAL", "WH-SOUTH"]


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in LLM response")
    return text[start : end + 1]


def _load_reference_lists(refresh: bool = False) -> dict:
    if not refresh and _REFERENCE_CACHE_PATH.exists():
        return json.loads(_REFERENCE_CACHE_PATH.read_text(encoding="utf-8"))

    categories, suppliers, provider = _FALLBACK_CATEGORIES, _FALLBACK_SUPPLIERS, "fallback"
    try:
        raw, provider = chat(
            user=(
                "Return ONLY a JSON object with two keys: 'categories' (8 short "
                "grocery/retail product category names) and 'suppliers' (6 "
                "plausible wholesale supplier company names). No prose, no "
                "markdown fences, just the JSON object."
            ),
            system="You generate realistic reference data as strict JSON.",
        )
        parsed = json.loads(_extract_json(raw))
        categories = parsed.get("categories") or categories
        suppliers = parsed.get("suppliers") or suppliers
    except (LLMUnavailableError, ValueError, json.JSONDecodeError):
        pass

    data = {"categories": categories, "suppliers": suppliers, "source": provider}
    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    _REFERENCE_CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def generate_products(count: int, columns: list) -> list:
    refs = _load_reference_lists()
    categories = refs["categories"]
    suppliers = refs["suppliers"]
    # Numbering must match generate_product_category()'s CAT{i:03d} and
    # generate_suppliers()'s SUP{i:03d} schemes so those tables can actually
    # be joined against products on product_category_id / supplier_id.
    category_to_id = {name: f"CAT{i:03d}" for i, name in enumerate(categories, start=1)}
    supplier_to_id = {name: f"SUP{i:03d}" for i, name in enumerate(suppliers, start=1)}

    rows = []
    for i in range(1, count + 1):
        category = random.choice(categories)
        supplier = random.choice(suppliers)
        row = {
            "product_id": f"P{i:05d}",
            "product_name": fake.catch_phrase(),
            "category": category,
            "unit_price": round(random.uniform(1.5, 89.99), 2),
            "supplier": supplier,
            "created_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
            "product_category_id": category_to_id[category],
            "supplier_id": supplier_to_id[supplier],
        }
        rows.append({k: row.get(k) for k in columns if k in row})
    return rows


def _category_risk_bias(category: str) -> float:
    """Deterministic per-category value in [0, 1), used to make ~40% of
    categories systematically higher stockout risk than the rest.

    Category names are themselves LLM-generated and vary run to run, so this
    hashes the name rather than hardcoding specific ones. The point is to
    give the ml_insights demo a real, learnable category -> risk
    relationship instead of pure noise, while staying independent of any
    particular category vocabulary.
    """
    digest = hashlib.md5(category.encode("utf-8")).hexdigest()
    return int(digest[:4], 16) / 0xFFFF


def generate_inventory(products: list, columns: list) -> list:
    """products: list of {"product_id": str, "category": str} dicts."""
    rows = []
    for idx, product in enumerate(products, start=1):
        high_risk = _category_risk_bias(product.get("category", "")) < 0.4
        if high_risk:
            quantity_on_hand = random.randint(0, 120)
            reorder_level = random.randint(60, 140)
        else:
            quantity_on_hand = random.randint(50, 500)
            reorder_level = random.randint(10, 80)

        row = {
            "inventory_id": f"INV{idx:05d}",
            "product_id": product["product_id"],
            "warehouse": random.choice(_WAREHOUSES),
            "quantity_on_hand": quantity_on_hand,
            "reorder_level": reorder_level,
            "last_restocked_at": fake.date_time_between(start_date="-90d", end_date="now").isoformat(),
        }
        rows.append({k: row.get(k) for k in columns if k in row})
    return rows


def generate_product_category(columns: list) -> list:
    refs = _load_reference_lists()
    rows = []
    for i, name in enumerate(refs["categories"], start=1):
        row = {
            "category_id": f"CAT{i:03d}",
            "category_name": name,
            "category_description": f"Products classified under {name.lower()}.",
            "parent_category_id": None,
        }
        rows.append({k: row.get(k) for k in columns if k in row})
    return rows


def generate_suppliers(columns: list) -> list:
    refs = _load_reference_lists()
    regions = ["North", "South", "East", "West", "Central"]
    rows = []
    for i, name in enumerate(refs["suppliers"], start=1):
        row = {
            "supplier_id": f"SUP{i:03d}",
            "supplier_name": name,
            "region": random.choice(regions),
            "reliability_score": round(random.uniform(0.7, 0.99), 2),
        }
        rows.append({k: row.get(k) for k in columns if k in row})
    return rows


def generate_product_prices_month_year(product_ids: list, columns: list, months_back: int = 6) -> list:
    rows = []
    price_idx = 1
    today = datetime.now()
    for pid in product_ids:
        base_price = round(random.uniform(1.5, 89.99), 2)
        for m in range(months_back):
            month_dt = today.replace(day=1) - timedelta(days=30 * m)
            row = {
                "price_id": f"PRC{price_idx:06d}",
                "product_id": pid,
                "month_year": month_dt.strftime("%Y-%m"),
                "list_price": round(base_price * random.uniform(0.92, 1.08), 2),
                "discount_pct": random.choice([0, 0, 0, 5, 10, 15]),
            }
            rows.append({k: row.get(k) for k in columns if k in row})
            price_idx += 1
    return rows
