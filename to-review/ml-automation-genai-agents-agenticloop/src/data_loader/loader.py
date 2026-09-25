"""Load all target-data table folders and join them into one denormalized
dataset.

Each genai_datagen run writes a complete fresh snapshot of every table
(product IDs restart at P00001 each time), not incremental new rows. So a
table's *current* state is its single latest timestamped file, not the
union of every file ever routed into that folder -- concatenating history
would reuse the same IDs across unrelated runs and fan out the join.
"""
from __future__ import annotations

import pandas as pd

from src.common import paths

_SKIP_DIRS = {"joined"}


def discover_tables() -> dict:
    """Returns {table_name: Path to its latest snapshot CSV}."""
    paths.TARGET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tables = {}
    for entry in sorted(paths.TARGET_DATA_DIR.iterdir()):
        if not entry.is_dir() or entry.name in _SKIP_DIRS or entry.name.startswith("_"):
            continue
        csv_files = sorted(entry.glob("*.csv"))
        if csv_files:
            tables[entry.name] = csv_files[-1]
    return tables


def load_tables(table_files: dict) -> dict:
    return {table_name: pd.read_csv(path) for table_name, path in table_files.items()}


def join_tables(dataframes: dict) -> pd.DataFrame:
    if "products" not in dataframes:
        raise ValueError("no 'products' table available in target-data to join from")

    result = dataframes["products"].copy()

    if "inventory" in dataframes:
        result = result.merge(dataframes["inventory"], on="product_id", how="left", suffixes=("", "_inv"))

    if "product-category" in dataframes and "product_category_id" in result.columns:
        cat = dataframes["product-category"].rename(columns={"category_id": "product_category_id"})
        result = result.merge(cat, on="product_category_id", how="left", suffixes=("", "_cat"))

    if "suppliers" in dataframes and "supplier_id" in result.columns:
        result = result.merge(dataframes["suppliers"], on="supplier_id", how="left", suffixes=("", "_sup"))

    if "product-prices-month-year" in dataframes:
        prices = dataframes["product-prices-month-year"]
        latest = prices.sort_values("month_year").groupby("product_id", as_index=False).last()
        latest = latest.rename(columns={
            "list_price": "current_list_price",
            "discount_pct": "current_discount_pct",
            "month_year": "current_price_month_year",
        })
        keep_cols = ["product_id", "current_list_price", "current_discount_pct", "current_price_month_year"]
        result = result.merge(latest[keep_cols], on="product_id", how="left")

    return result


def write_joined_output(df: pd.DataFrame) -> dict:
    out_dir = paths.TARGET_DATA_DIR / "joined"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = paths.timestamp()
    csv_path = out_dir / f"{ts}_joined.csv"
    df.to_csv(csv_path, index=False)

    parquet_path = out_dir / f"{ts}_joined.parquet"
    try:
        df.to_parquet(parquet_path, index=False)
    except (ImportError, ValueError):
        parquet_path = None

    return {"csv": str(csv_path), "parquet": str(parquet_path) if parquet_path else None}
