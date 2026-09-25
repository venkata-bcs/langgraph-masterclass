"""Feature engineering for the reorder-risk ML demo: turns the latest
joined target-data dataset into a supervised learning problem.

The label (reorder risk) is derived directly from quantity_on_hand vs
reorder_level, but those two columns are deliberately EXCLUDED from the
feature set -- the model has to learn risk purely from product attributes
(category, supplier, warehouse, price). That's the realistic framing: by
the time you already know quantity_on_hand you don't need a model.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.common import paths

FEATURE_COLUMNS = ["category", "supplier", "unit_price", "warehouse"]
LABEL_COLUMN = "reorder_risk"


def latest_joined_csv() -> Path:
    joined_dir = paths.TARGET_DATA_DIR / "joined"
    files = sorted(joined_dir.glob("*_joined.csv"))
    if not files:
        raise FileNotFoundError(
            "No joined dataset found in target-data/joined/. Run the data_loader "
            "pipeline first (scripts/run_data_loader.py or run_pipeline_once.py)."
        )
    return files[-1]


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(latest_joined_csv())
    required = FEATURE_COLUMNS + ["quantity_on_hand", "reorder_level"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"joined dataset is missing required columns: {missing}")

    df = df.dropna(subset=required).copy()
    df[LABEL_COLUMN] = (df["quantity_on_hand"] <= df["reorder_level"]).astype(int)
    return df


def split_features_label(df: pd.DataFrame):
    return df[FEATURE_COLUMNS], df[LABEL_COLUMN]
