# Conditional Edges
> Venkata Bhattaram (c) 2026

## Contents
* Routing functions
* add_conditional_edges
* Dynamic branching

## Overview
A conditional edge lets the graph pick its next node at runtime instead of
following a fixed path. You write a small **routing function** that inspects
the current state and returns the name of whichever branch should run next;
`add_conditional_edges` wires that function to a node so its return value
decides where execution goes. This is how LangGraph implements
if/else-style branching and dynamic, data-dependent control flow.

## Code Example
```python
"""Route a support ticket to a handler node based on its content."""
from typing import Literal, TypedDict

from langgraph.graph import StateGraph, START, END


class TicketState(TypedDict):
    message: str
    category: str
    response: str


def classify(state: TicketState) -> dict:
    text = state["message"].lower()
    if "refund" in text or "charge" in text:
        category = "billing"
    elif "error" in text or "bug" in text:
        category = "technical"
    else:
        category = "general"
    return {"category": category}


def handle_billing(state: TicketState) -> dict:
    return {"response": "Routing to billing support."}


def handle_technical(state: TicketState) -> dict:
    return {"response": "Routing to technical support."}


def handle_general(state: TicketState) -> dict:
    return {"response": "Routing to general support."}


def route_by_category(state: TicketState) -> Literal["billing", "technical", "general"]:
    """Routing function: reads state, returns the *name* of the next node."""
    return state["category"]


builder = StateGraph(TicketState)
builder.add_node("classify", classify)
builder.add_node("billing", handle_billing)
builder.add_node("technical", handle_technical)
builder.add_node("general", handle_general)

builder.add_edge(START, "classify")

# add_conditional_edges(source_node, routing_fn, path_map). The path_map is
# optional but makes the mapping from routing-function output -> node name
# explicit, so the routing function's return values stay decoupled from
# node ids.
builder.add_conditional_edges(
    "classify",
    route_by_category,
    {
        "billing": "billing",
        "technical": "technical",
        "general": "general",
    },
)

builder.add_edge("billing", END)
builder.add_edge("technical", END)
builder.add_edge("general", END)

graph = builder.compile()

for message in [
    "I was charged twice for my order",
    "The app crashes with an error on login",
    "What are your business hours?",
]:
    result = graph.invoke({"message": message, "category": "", "response": ""})
    print(f"{message!r} -> {result['category']} -> {result['response']}")
```

## Conclusion
`add_conditional_edges` turns a plain function into the graph's branching
logic: given the current state, it returns which node runs next, and the
graph follows that decision on every run. This is the building block for
everything from simple if/else routing to the `tools_condition` pattern used
by tool-calling agents later in this tutorial.
