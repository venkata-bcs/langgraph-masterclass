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
