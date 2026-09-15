# Edges
> Venkata Bhattaram (c) 2026

## Contents
* Normal edges
* START and END
* Sequencing nodes

## Overview
A normal edge connects one node to exactly one other node: when the first
finishes, the second always runs next. Every graph also has two special,
built-in nodes — `START` and `END` — that mark where execution enters and
leaves the graph. Chaining normal edges is how you sequence a fixed
pipeline of steps.

## Code Example
```python
"""Sequencing three nodes with normal edges, START, and END."""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class TextState(TypedDict):
    text: str
    steps: list[str]


def step_lower(state: TextState) -> dict:
    return {"text": state["text"].lower(), "steps": state["steps"] + ["lower"]}


def step_strip(state: TextState) -> dict:
    return {"text": state["text"].strip(), "steps": state["steps"] + ["strip"]}


def step_title(state: TextState) -> dict:
    return {"text": state["text"].title(), "steps": state["steps"] + ["title"]}


builder = StateGraph(TextState)
builder.add_node("lower", step_lower)
builder.add_node("strip", step_strip)
builder.add_node("title", step_title)

# Normal edges fix the order: START -> lower -> strip -> title -> END.
builder.add_edge(START, "lower")
builder.add_edge("lower", "strip")
builder.add_edge("strip", "title")
builder.add_edge("title", END)

graph = builder.compile()

result = graph.invoke({"text": "  hello LANGGRAPH world  ", "steps": []})
print(result["text"])   # -> "Hello Langgraph World"
print(result["steps"])  # -> ['lower', 'strip', 'title']
```

## Conclusion
`START` and `END` are just fixed entry/exit points; every edge in between is
a plain, unconditional handoff from one node to the next. This is enough for
any graph whose execution order never needs to change at runtime — for
graphs that do need to branch, see Conditional Edges next.
