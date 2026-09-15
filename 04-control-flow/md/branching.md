# Branching
> Venkata Bhattaram (c) 2026

## Contents
* If/else style routing
* Multiple destination edges

## Overview
So far every graph has moved in one fixed direction: `add_edge` always sends
the graph to the same next node, no matter what the state holds. Branching
means the *next* node depends on state — the graph equivalent of an
`if`/`else`. LangGraph does this with `add_conditional_edges`, which pairs a
node with a **routing function**: a plain function that reads state and
returns the name (or names) of whichever node(s) should run next. Unlike a
regular node, a routing function never returns a state update — its only
job is to pick a destination.

A routing function can return a single node name (classic if/else), or a
*list* of node names, which fans out to **multiple destination edges** at
once — every node in the list runs in the same superstep, not just one of
them.

## Code Example
```python
"""If/else routing with add_conditional_edges, and fanning out to multiple
destinations from one conditional edge."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END


class GradeState(TypedDict):
    score: int
    result: str
    log: Annotated[list[str], operator.add]


def check_score(state: GradeState) -> dict:
    # Just passes state through -- the routing decision happens in
    # route_by_score below, not in a node's return value.
    return {}


def pass_node(state: GradeState) -> dict:
    return {"result": "pass"}


def fail_node(state: GradeState) -> dict:
    return {"result": "fail"}


def audit_node(state: GradeState) -> dict:
    return {"log": [f"audited score={state['score']}"]}


def route_by_score(state: GradeState) -> list[str]:
    # A routing function reads state and returns node NAME(S) to run next --
    # it never updates state itself. Returning a list fans out to MULTIPLE
    # destination edges at once: both branches below run in this superstep,
    # not just one.
    if state["score"] >= 50:
        return ["pass_node", "audit_node"]
    return ["fail_node", "audit_node"]


builder = StateGraph(GradeState)
builder.add_node("check_score", check_score)
builder.add_node("pass_node", pass_node)
builder.add_node("fail_node", fail_node)
builder.add_node("audit_node", audit_node)

builder.add_edge(START, "check_score")
builder.add_conditional_edges("check_score", route_by_score)
builder.add_edge("pass_node", END)
builder.add_edge("fail_node", END)
builder.add_edge("audit_node", END)
graph = builder.compile()

# state coming IN:  {"score": 72, "result": "", "log": []}
# route_by_score sees score=72 -> ["pass_node", "audit_node"] -> BOTH run
# state going OUT: {"score": 72, "result": "pass", "log": ["audited score=72"]}
print(graph.invoke({"score": 72, "result": "", "log": []}))

# state coming IN:  {"score": 40, "result": "", "log": []}
# route_by_score sees score=40 -> ["fail_node", "audit_node"] -> BOTH run
# state going OUT: {"score": 40, "result": "fail", "log": ["audited score=40"]}
print(graph.invoke({"score": 40, "result": "", "log": []}))
```

## Conclusion
`add_conditional_edges` is what turns a straight-line graph into one that
makes decisions: the routing function inspects state and hands back a node
name, and LangGraph takes it from there. Returning a single name gives you
plain if/else branching; returning a list gives you multiple destination
edges that all fire in the same step. Next we look at what happens when an
edge routes back to a node the graph has already visited: looping.
