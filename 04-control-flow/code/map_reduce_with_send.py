"""The Send object for dynamic parallel branches, and aggregating results."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class MapReduceState(TypedDict):
    items: list[str]
    lengths: Annotated[list[int], operator.add]


class ItemState(TypedDict):
    item: str


def dispatch(state: MapReduceState) -> list[Send]:
    # Send(node_name, state) dynamically creates ONE parallel branch per
    # item. Unlike a fixed add_edge/add_conditional_edges, the NUMBER of
    # branches isn't known until this function runs -- it depends on
    # len(state["items"]), which could be 0, 3, or 300.
    return [Send("measure", {"item": item}) for item in state["items"]]


def measure(state: ItemState) -> dict:
    # Each Send() invocation runs this node with its OWN small state
    # ({"item": ...}), independent of every other branch.
    return {"lengths": [len(state["item"])]}


builder = StateGraph(MapReduceState)
builder.add_node("measure", measure)
builder.add_conditional_edges(START, dispatch, ["measure"])
builder.add_edge("measure", END)
graph = builder.compile()

# state coming IN:  {"items": ["langgraph", "state", "reducer"], "lengths": []}
# dispatch fans out to 3 dynamic Send branches, one per item (the map step)
# each measure() call appends its own length; operator.add aggregates them
# into one list back on the parent state (the reduce step).
result = graph.invoke({"items": ["langgraph", "state", "reducer"], "lengths": []})
print(result["lengths"])  # -> [9, 5, 7]  (order may vary; each branch runs independently)
