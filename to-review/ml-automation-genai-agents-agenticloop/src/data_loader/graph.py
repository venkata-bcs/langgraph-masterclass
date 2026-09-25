"""LangGraph program: discover target-data tables, join them, and write a
denormalized output for downstream analytics.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.data_loader import loader


class LoaderState(TypedDict, total=False):
    table_files: dict
    dataframes: dict
    joined: object
    outputs: dict


def discover(state: LoaderState) -> LoaderState:
    state["table_files"] = loader.discover_tables()
    return state


def load(state: LoaderState) -> LoaderState:
    state["dataframes"] = loader.load_tables(state["table_files"])
    return state


def join(state: LoaderState) -> LoaderState:
    state["joined"] = loader.join_tables(state["dataframes"])
    return state


def write_output(state: LoaderState) -> LoaderState:
    state["outputs"] = loader.write_joined_output(state["joined"])
    return state


def build_graph():
    graph = StateGraph(LoaderState)
    graph.add_node("discover", discover)
    graph.add_node("load", load)
    graph.add_node("join", join)
    graph.add_node("write_output", write_output)

    graph.set_entry_point("discover")
    graph.add_edge("discover", "load")
    graph.add_edge("load", "join")
    graph.add_edge("join", "write_output")
    graph.add_edge("write_output", END)
    return graph.compile()


def run() -> LoaderState:
    app = build_graph()
    return app.invoke({})
