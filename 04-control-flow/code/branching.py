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
