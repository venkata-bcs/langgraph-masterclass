# Subgraphs
> Venkata Bhattaram (c) 2026

## Contents
* Nesting graphs as nodes
* Shared vs isolated state
* Reusing subgraphs across projects

## Overview
A compiled LangGraph graph can be used as a node in a *different* graph —
that's a subgraph. From the parent's point of view, the whole child graph
(however many nodes and edges it has internally) behaves like any other
single node: it takes the current state and returns an update, and its
internal steps never show up as separate nodes in the parent. There are two
ways to wire one in, depending on whether the parent and child **share
state**:
* If the child's schema uses the *same key names* as the parent, the
  compiled child graph can be added directly with `add_node("name",
  child_graph)` — LangGraph passes the parent's state straight in.
* If the child has its own, **isolated** schema with different key names,
  it can't be added directly. Instead you wrap it in an ordinary node
  function that translates the parent's state into the child's schema,
  calls `child_graph.invoke(...)`, and translates the result back.

Because a compiled graph is just a Python object, either form can be
imported and reused as a node across as many parent graphs and projects as
need it — you write the subgraph once.

## Code Example
```python
"""Nesting a compiled graph as a node: shared state vs. an isolated schema."""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# --- Child graph #1: SHARED state -- "number" and "doubled" are the exact
# same key names the parent state uses, so this compiled graph can be added
# directly as a node with add_node("shared_child", child_graph).
class SharedChildState(TypedDict):
    number: int
    doubled: int


def double(state: SharedChildState) -> dict:
    return {"doubled": state["number"] * 2}


child_builder = StateGraph(SharedChildState)
child_builder.add_node("double", double)
child_builder.add_edge(START, "double")
child_builder.add_edge("double", END)
child_graph = child_builder.compile()


# --- Child graph #2: ISOLATED state -- its own schema ("value"/"result"),
# with no keys in common with the parent. It can't be added directly; it
# needs a small wrapper node that translates the parent's state into the
# child's, invokes the child graph, and translates the result back.
class IsolatedChildState(TypedDict):
    value: int
    result: int


def triple(state: IsolatedChildState) -> dict:
    return {"result": state["value"] * 3}


isolated_builder = StateGraph(IsolatedChildState)
isolated_builder.add_node("triple", triple)
isolated_builder.add_edge(START, "triple")
isolated_builder.add_edge("triple", END)
isolated_child_graph = isolated_builder.compile()


class ParentState(TypedDict):
    number: int
    doubled: int
    tripled: int


def run_isolated_child(state: ParentState) -> dict:
    # Translate parent state -> child schema, invoke the child graph, then
    # translate its result back -- required because ParentState and
    # IsolatedChildState don't share key names.
    child_result = isolated_child_graph.invoke({"value": state["number"], "result": 0})
    return {"tripled": child_result["result"]}


builder = StateGraph(ParentState)
# child_graph shares "number"/"doubled" with ParentState, so it's added AS
# a node directly -- LangGraph passes the parent's current state straight
# into it and merges its final state back, with the child's own nodes and
# edges completely hidden from the parent graph.
builder.add_node("shared_child", child_graph)
builder.add_node("isolated_child", run_isolated_child)
builder.add_edge(START, "shared_child")
builder.add_edge(START, "isolated_child")
builder.add_edge("shared_child", END)
builder.add_edge("isolated_child", END)
graph = builder.compile()

# state coming IN:  {"number": 5, "doubled": 0, "tripled": 0}
# shared_child and isolated_child both read the ORIGINAL number=5 (they run
# in the same superstep, fanned out from START) and write different fields,
# so there's no ordering dependency between them.
# state going OUT: {"number": 5, "doubled": 10, "tripled": 15}
result = graph.invoke({"number": 5, "doubled": 0, "tripled": 0})
print(result)
```

## Conclusion
Whether a subgraph plugs in directly or needs a translating wrapper node
comes down entirely to whether its schema's keys line up with the parent's
— the mechanics of running it (`add_node`, edges, `compile()`) are identical
either way. Because `child_graph` and `isolated_child_graph` are ordinary
compiled `StateGraph` objects, they can be defined once in a shared module
and imported into any parent graph that needs that behavior, in this
project or another one. This closes out control flow; next we move on to
making state durable across runs: persistence and memory.
