# Map-Reduce with Send
> Venkata Bhattaram (c) 2026

## Contents
* The Send object
* Dynamic parallel branches
* Aggregating results

## Overview
Fan-out with `add_edge`/`add_conditional_edges` (see
[Parallel Execution](./parallel_execution.md)) requires knowing the
destination node names up front, at graph-build time. Sometimes the number
of parallel branches you need only becomes known at *run* time — for
example, one branch per item in a list whose length varies per call.
That's what `Send` is for: a routing function returns a list of `Send(node_name,
state)` objects instead of node names, and LangGraph spins up one
independent branch per `Send`, each with its own small state. This is the
classic **map** step. The **reduce** step is nothing new — it's the same
reducer mechanism from [Reducers](../../03-state-management/md/reducers.md):
each dynamic branch returns an update, and a field annotated with a reducer
(like `operator.add`) aggregates every branch's contribution back onto the
parent state.

## Code Example
```python
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
```

## Conclusion
`Send` decouples "how many branches" from "how the graph is wired": the
graph declares one `measure` node, and `dispatch` decides at runtime how
many times to run it and what state to give each run. Aggregating the
results back is just a reducer doing what it always does — `Send` only
changes how *many* updates arrive in a superstep, not how they get merged.
This closes out the fan-out/fan-in family of patterns; next we look at
nesting one compiled graph inside another: subgraphs.
