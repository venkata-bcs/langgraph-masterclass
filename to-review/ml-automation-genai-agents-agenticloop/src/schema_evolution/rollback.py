"""Archives target-data for tables that schema evolution rolled back
(deactivated), so downstream joins/ML stop picking up stale data for a
table that's no longer part of the active schema.

Archiving (move, not delete) rather than deleting: a rollback might itself
get reverted later (the table reactivated again), so the data stays
recoverable instead of being destroyed.
"""
from __future__ import annotations

import json
import shutil

from src.common import paths

_ROLLBACK_LOG_PATH = paths.TARGET_DATA_DIR / "_rollback_log.jsonl"


def archive_table(table_name: str) -> str:
    """Moves target-data/<table_name>/ to target-data/_archived/<table_name>/<ts>/.
    Returns the archive path, or "" if there was nothing to archive.
    """
    source_dir = paths.TARGET_DATA_DIR / table_name
    if not source_dir.is_dir() or not any(source_dir.iterdir()):
        return ""

    archive_dir = paths.TARGET_DATA_DIR / "_archived" / table_name / paths.timestamp()
    archive_dir.mkdir(parents=True, exist_ok=True)
    for entry in list(source_dir.iterdir()):
        shutil.move(str(entry), str(archive_dir / entry.name))
    source_dir.rmdir()
    return str(archive_dir)


def archive_rolled_back_tables(table_names: list) -> dict:
    archived = {}
    for table_name in table_names:
        archive_path = archive_table(table_name)
        if archive_path:
            archived[table_name] = archive_path

    if archived:
        paths.TARGET_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with _ROLLBACK_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"archived": archived}) + "\n")

    return archived
