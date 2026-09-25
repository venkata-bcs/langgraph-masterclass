"""Polling-based watcher for source-data/. Detects newly created files,
runs each through the automation_router LangGraph program, and moves them
into the right target-data subfolder.

A polling loop is used instead of OS filesystem-event APIs so this works
identically (and dependency-free) across platforms, and so a single scan can
be triggered on demand from another script (e.g. run_pipeline_once.py).
"""
from __future__ import annotations

import json
import time

from src.automation_router.graph import build_graph
from src.common import paths

_STATE_PATH = paths.STATE_DIR / "router_processed_files.json"


def _load_processed() -> set:
    if _STATE_PATH.exists():
        return set(json.loads(_STATE_PATH.read_text(encoding="utf-8")))
    return set()


def _save_processed(processed: set) -> None:
    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(sorted(processed)), encoding="utf-8")


def scan_once() -> list:
    paths.SOURCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    processed = _load_processed()
    app = build_graph()
    results = []
    for entry in sorted(paths.SOURCE_DATA_DIR.iterdir()):
        if not entry.is_file() or entry.name.startswith(".") or entry.name in processed:
            continue
        result = app.invoke({"file_path": str(entry)})
        results.append(result)
        processed.add(entry.name)
    _save_processed(processed)
    return results


def watch_loop(poll_interval: int = 5) -> None:
    print(f"Watching {paths.SOURCE_DATA_DIR} every {poll_interval}s (Ctrl+C to stop)...")
    try:
        while True:
            for result in scan_once():
                print(f"routed: {result.get('filename')} -> {result.get('decision', {}).get('target_folder')}")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Stopped.")
