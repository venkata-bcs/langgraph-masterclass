"""Detects schema evolution: compares the currently-active schema in
config/schema_registry.yaml against the last known snapshot, and reports
which tables/columns were newly activated (forward evolution) or newly
deactivated (rollback) since then. Rollback is the mirror image of
evolution: re-commenting a column or flipping a table's `active:` flag back
to false is just as much a state transition the agent should react to as
uncommenting one.
"""
from __future__ import annotations

import json

from src.common import paths
from src.common.schema_registry import parse_schema_registry

_STATE_PATH = paths.STATE_DIR / "schema_state.json"


def load_current_schema() -> dict:
    registry_path = paths.PROJECT_ROOT / "config" / "schema_registry.yaml"
    return parse_schema_registry(registry_path)


def load_previous_snapshot() -> dict:
    if _STATE_PATH.exists():
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_snapshot(current_snapshot: dict) -> None:
    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(current_snapshot, indent=2), encoding="utf-8")


def diff_schema(previous: dict, current: dict) -> dict:
    changes = {
        "newly_active_tables": [],
        "newly_inactive_tables": [],
        "newly_active_columns": {},
        "newly_inactive_columns": {},
    }
    for table_name, table_state in current.items():
        prev_table = previous.get(table_name)
        was_active = bool(prev_table and prev_table.get("active"))
        is_active = table_state["active"]

        if is_active and not was_active:
            changes["newly_active_tables"].append(table_name)
        if was_active and not is_active:
            changes["newly_inactive_tables"].append(table_name)

        if prev_table is None:
            continue

        prev_cols = prev_table.get("columns", [])
        curr_cols = table_state["columns"]
        added_cols = [c for c in curr_cols if c not in prev_cols]
        removed_cols = [c for c in prev_cols if c not in curr_cols]

        if added_cols and is_active:
            changes["newly_active_columns"][table_name] = added_cols
        if removed_cols and was_active:
            changes["newly_inactive_columns"][table_name] = removed_cols

    return changes


def has_forward_changes(changes: dict) -> bool:
    return bool(changes["newly_active_tables"] or changes["newly_active_columns"])


def has_rollback_changes(changes: dict) -> bool:
    return bool(changes["newly_inactive_tables"] or changes["newly_inactive_columns"])


def has_changes(changes: dict) -> bool:
    return has_forward_changes(changes) or has_rollback_changes(changes)
