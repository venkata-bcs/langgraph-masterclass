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
