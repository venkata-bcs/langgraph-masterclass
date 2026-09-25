"""Line-based parser for config/schema_registry.yaml.

The registry uses plain YAML for table names and the `active:` flag, but
column activation is expressed literally through commenting: an active
column is a normal `- name` list item under `columns:`; a not-yet-active
("pending") column is the exact same line prefixed with `#`. Removing that
`#` (or flipping a table's `active:` flag to true) is how a user evolves the
schema -- this parser is what lets the rest of the system see that edit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_TABLE_HEADER_RE = re.compile(r"^  ([A-Za-z][\w-]*):\s*$")
_ACTIVE_RE = re.compile(r"^\s*active:\s*(true|false)\s*$", re.IGNORECASE)
_COLUMNS_HEADER_RE = re.compile(r"^\s*columns:\s*$")
_ACTIVE_COLUMN_RE = re.compile(r"^\s*-\s+([\w.\-]+)")
_PENDING_COLUMN_RE = re.compile(r"^\s*#\s*-\s+([\w.\-]+)")


@dataclass
class TableSchema:
    name: str
    active: bool = False
    columns: list = field(default_factory=list)
    pending_columns: list = field(default_factory=list)


def parse_schema_registry(path: Path) -> dict:
    """Parse the schema registry file into {table_name: TableSchema}."""
    tables: dict = {}
    current: TableSchema | None = None
    in_columns = False

    text = Path(path).read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        header_match = _TABLE_HEADER_RE.match(raw_line)
        if header_match:
            current = TableSchema(name=header_match.group(1))
            tables[current.name] = current
            in_columns = False
            continue

        if current is None:
            continue

        if _COLUMNS_HEADER_RE.match(raw_line):
            in_columns = True
            continue

        active_match = _ACTIVE_RE.match(raw_line)
        if active_match:
            current.active = active_match.group(1).lower() == "true"
            in_columns = False
            continue

        if in_columns:
            pending_match = _PENDING_COLUMN_RE.match(raw_line)
            if pending_match:
                current.pending_columns.append(pending_match.group(1))
                continue
            active_col_match = _ACTIVE_COLUMN_RE.match(raw_line)
            if active_col_match:
                current.columns.append(active_col_match.group(1))
                continue
            if raw_line.strip() == "":
                continue
            in_columns = False

    return tables


def snapshot(tables: dict) -> dict:
    """A comparable, JSON-serializable snapshot used for diffing runs."""
    return {
        name: {"active": t.active, "columns": list(t.columns)}
        for name, t in tables.items()
    }
