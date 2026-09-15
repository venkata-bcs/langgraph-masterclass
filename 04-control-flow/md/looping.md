# Looping
> Venkata Bhattaram (c) 2026

## Contents
* Cycles in a graph
* Loop termination conditions
* Recursion limits

## Overview
A **cycle** is just an edge that routes back to a node the graph has already
run — there's nothing special about the edge itself, only about where it
points. Combine a conditional edge with a destination that's the *same*
node (or an earlier one), and you get a loop: the node keeps re-running,
each time seeing the state left behind by its previous run, until a
**termination condition** in the routing function decides to route to `END`
instead. Without a condition that eventually does that, the loop never
stops on its own — which is why LangGraph enforces a **recursion limit**: a
cap on how many supersteps a single run can take (25 by default). Hit the
cap before your loop's real termination condition fires, and LangGraph
raises `GraphRecursionError` rather than spinning forever.

## Code Example
```python
"""A cycle in a graph, a loop termination condition, and the recursion limit."""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError


class CounterState(TypedDict):
    count: int
    target: int


def increment(state: CounterState) -> dict:
    # state coming IN:  {"count": N, "target": T}
    # state going OUT: {"count": N + 1, "target": T}  (default overwrite reducer)
    return {"count": state["count"] + 1}


def should_continue(state: CounterState) -> str:
    # Checked after EVERY pass through increment. Returning "increment"
    # re-enters the cycle; returning END breaks out of it. Without a
    # condition like this that eventually returns END, the edge below would
    # fire forever.
    return "increment" if state["count"] < state["target"] else END


builder = StateGraph(CounterState)
builder.add_node("increment", increment)
builder.add_edge(START, "increment")
# The conditional edge points back at "increment" itself -- that's the cycle.
builder.add_conditional_edges(
    "increment", should_continue, {"increment": "increment", END: END}
)
graph = builder.compile()

# state coming IN:  {"count": 0, "target": 5}
# increment runs 5 times, should_continue re-entering the loop each time
# until count == target, then routing to END.
# state going OUT: {"count": 5, "target": 5}
result = graph.invoke({"count": 0, "target": 5})
print(result)  # -> {'count': 5, 'target': 5}

# LangGraph caps how many supersteps a run can take -- the default
# recursion_limit is 25. A loop that legitimately needs more iterations
# than the configured limit raises GraphRecursionError instead of running
# forever:
try:
    graph.invoke({"count": 0, "target": 100}, config={"recursion_limit": 10})
except GraphRecursionError as exc:
    print("Hit recursion limit:", type(exc).__name__)
```

## Conclusion
A loop is nothing more than an edge whose destination is a node already on
the call path — the termination condition inside the routing function is
what makes it a *bounded* loop instead of an infinite one. Always design
that condition first (what state, exactly, means "stop"), and treat
`recursion_limit` as a safety net for bugs in that condition, not as the
mechanism you rely on to end a loop on purpose. Next we look at running
multiple nodes at once instead of one after another: parallel execution.
