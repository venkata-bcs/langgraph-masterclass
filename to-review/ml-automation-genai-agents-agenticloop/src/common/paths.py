"""Shared filesystem paths and small helpers used across all pipelines."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATA_DIR = PROJECT_ROOT / "source-data"
TARGET_DATA_DIR = PROJECT_ROOT / "target-data"
STATE_DIR = PROJECT_ROOT / "state"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
