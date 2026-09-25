"""LangGraph program: detect schema evolution in the registry -- both
forward (a column/table newly activated) and rollback (one newly
deactivated) -- and react accordingly: forward changes trigger a fresh
genAI data-generation run; rollbacks archive the now-inactive table's
target-data out of the join path. A load_handler node then routes and
rejoins the affected data itself, so this graph is a complete, self
contained agentic loop -- observe -> decide -> act -> reload -> persist
state -- rather than stopping at "regenerated the raw files" and leaving
target-data/joined/ stale until some other script happens to run the rest
of the pipeline.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.automation_router.watcher import scan_once
from src.common.schema_registry import snapshot
from src.data_loader.graph import run as run_loader
from src.genai_datagen.graph import run as run_datagen
from src.schema_evolution import detector, rollback


class SchemaEvolutionState(TypedDict, total=False):
    current_tables: dict
    current_snapshot: dict
    previous_snapshot: dict
    changes: dict
    regenerated: bool
    archived: dict
    routed_files: int
    load_outputs: dict


def read_registry(state: SchemaEvolutionState) -> SchemaEvolutionState:
    state["current_tables"] = detector.load_current_schema()
    state["current_snapshot"] = snapshot(state["current_tables"])
    return state


def load_previous_state(state: SchemaEvolutionState) -> SchemaEvolutionState:
    state["previous_snapshot"] = detector.load_previous_snapshot()
    return state


def detect_diff(state: SchemaEvolutionState) -> SchemaEvolutionState:
    state["changes"] = detector.diff_schema(state["previous_snapshot"], state["current_snapshot"])
    return state


def maybe_regenerate(state: SchemaEvolutionState) -> SchemaEvolutionState:
    changes = state["changes"]
    if detector.has_changes(changes):
        print("Schema evolution detected:", changes)
        run_datagen()
        state["regenerated"] = True
    else:
        state["regenerated"] = False
    return state


def rollback_archive(state: SchemaEvolutionState) -> SchemaEvolutionState:
    inactive_tables = state["changes"]["newly_inactive_tables"]
    archived = rollback.archive_rolled_back_tables(inactive_tables) if inactive_tables else {}
    if archived:
        print("Rolled back tables archived:", archived)
    state["archived"] = archived
    return state


def load_handler(state: SchemaEvolutionState) -> SchemaEvolutionState:
    """Handles reloading target-data after the loop has acted: routes any
    freshly regenerated source-data files into their target-data
    subfolders, then rejoins target-data into a fresh
    target-data/joined/ output. Only runs when there was actually something
    to react to -- an idle pass (no schema change) leaves target-data alone.
    """
    if not (state["regenerated"] or state["archived"]):
        state["routed_files"] = 0
        state["load_outputs"] = {}
        return state

    routed = scan_once()
    state["routed_files"] = len(routed)
    print(f"load_handler: routed {len(routed)} file(s) into target-data/")

    try:
        loader_result = run_loader()
        state["load_outputs"] = loader_result["outputs"]
        print("load_handler: target-data/joined/ refreshed:", loader_result["outputs"])
    except (FileNotFoundError, ValueError) as exc:
        state["load_outputs"] = {}
        print(f"load_handler: skipped join ({exc})")

    return state


def save_state(state: SchemaEvolutionState) -> SchemaEvolutionState:
    detector.save_snapshot(state["current_snapshot"])
    return state


def build_graph():
    graph = StateGraph(SchemaEvolutionState)
    graph.add_node("read_registry", read_registry)
    graph.add_node("load_previous_state", load_previous_state)
    graph.add_node("detect_diff", detect_diff)
    graph.add_node("maybe_regenerate", maybe_regenerate)
    graph.add_node("rollback_archive", rollback_archive)
    graph.add_node("load_handler", load_handler)
    graph.add_node("save_state", save_state)

    graph.set_entry_point("read_registry")
    graph.add_edge("read_registry", "load_previous_state")
    graph.add_edge("load_previous_state", "detect_diff")
    graph.add_edge("detect_diff", "maybe_regenerate")
    graph.add_edge("maybe_regenerate", "rollback_archive")
    graph.add_edge("rollback_archive", "load_handler")
    graph.add_edge("load_handler", "save_state")
    graph.add_edge("save_state", END)
    return graph.compile()


def run() -> SchemaEvolutionState:
    app = build_graph()
    return app.invoke({})
