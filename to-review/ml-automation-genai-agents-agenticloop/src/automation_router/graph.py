"""LangGraph program: classify a single dropped file by name/content and
move it into the right target-data subfolder.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.automation_router.classifier import classify_file
from src.common import paths


class RouterState(TypedDict, total=False):
    file_path: str
    filename: str
    header_preview: str
    known_targets: list
    decision: dict
    moved_path: str


def inspect_file(state: RouterState) -> RouterState:
    path = Path(state["file_path"])
    state["filename"] = path.name
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            state["header_preview"] = f.readline().strip()
    except OSError:
        state["header_preview"] = ""

    paths.TARGET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    state["known_targets"] = sorted(
        p.name for p in paths.TARGET_DATA_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    return state


def classify(state: RouterState) -> RouterState:
    state["decision"] = classify_file(state["filename"], state["header_preview"], state["known_targets"])
    return state


def move_file(state: RouterState) -> RouterState:
    target_folder = state["decision"]["target_folder"]
    dest_dir = paths.TARGET_DATA_DIR / target_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / state["filename"]
    shutil.move(state["file_path"], dest_path)
    state["moved_path"] = str(dest_path)
    return state


def log_result(state: RouterState) -> RouterState:
    entry = {
        "filename": state["filename"],
        "moved_to": state.get("moved_path"),
        "decision": state.get("decision"),
    }
    paths.TARGET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = paths.TARGET_DATA_DIR / "_routing_log.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return state


def build_graph():
    graph = StateGraph(RouterState)
    graph.add_node("inspect_file", inspect_file)
    graph.add_node("classify", classify)
    graph.add_node("move_file", move_file)
    graph.add_node("log_result", log_result)

    graph.set_entry_point("inspect_file")
    graph.add_edge("inspect_file", "classify")
    graph.add_edge("classify", "move_file")
    graph.add_edge("move_file", "log_result")
    graph.add_edge("log_result", END)
    return graph.compile()
