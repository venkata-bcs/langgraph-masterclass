# Multiple Schemas (Input/Output/Internal)
> Venkata Bhattaram (c) 2026

## Contents
* Separate input and output schemas
* Private internal state
* Overlapping keys

## Overview
A single "state" schema doesn't have to be what callers pass in and get
back. LangGraph lets you give `StateGraph` separate **input** and **output**
schemas: the caller only needs to supply the input fields, and only sees the
output fields in the result — even though internally the graph may compute
and pass around a lot more. Any field that exists on the internal state but
not on the output schema is effectively **private**: it's used for
inter-node bookkeeping and never leaks out. Fields with the same name across
schemas are treated as the same key.

## Code Example
```python
"""Separate input/output schemas with private internal-only state."""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# What the caller must provide.
class InputSchema(TypedDict):
    question: str


# What the caller gets back. Note: no `raw_search_results` here.
class OutputSchema(TypedDict):
    answer: str


# The full internal state — a superset of input and output, plus a field
# ("raw_search_results") that's only used to pass data between nodes and
# is never exposed to the caller.
class OverallState(TypedDict):
    question: str            # overlaps with InputSchema
    raw_search_results: str  # private: internal-only
    answer: str               # overlaps with OutputSchema


def search_node(state: OverallState) -> dict:
    # Pretend this called a search tool.
    #
    # state coming IN (OverallState, seeded from the InputSchema field only):
    #   {"question": "What is LangGraph?"}
    # state going OUT (after merge): adds raw_search_results:
    #   {"question": "What is LangGraph?", "raw_search_results": "[search hits for: What is LangGraph?]"}
    return {"raw_search_results": f"[search hits for: {state['question']}]"}


def answer_node(state: OverallState) -> dict:
    # Uses the private field, but only publishes `answer`.
    #
    # state coming IN:
    #   {"question": "What is LangGraph?", "raw_search_results": "[search hits for: What is LangGraph?]"}
    # state going OUT (after merge): adds answer:
    #   {..., "answer": "Answer based on [search hits for: What is LangGraph?]"}
    return {"answer": f"Answer based on {state['raw_search_results']}"}


builder = StateGraph(OverallState, input=InputSchema, output=OutputSchema)
builder.add_node("search", search_node)
builder.add_node("answer", answer_node)
builder.add_edge(START, "search")
builder.add_edge("search", "answer")
builder.add_edge("answer", END)
graph = builder.compile()

# Caller only passes `question` (the input schema) as the INITIAL state --
# `raw_search_results` and `answer` aren't seeded here; search_node and
# answer_node fill them in as the graph runs...
result = graph.invoke({"question": "What is LangGraph?"})

# ...and only gets `answer` back (the output schema) — `raw_search_results`
# was used internally but never appears in the result.
print(result)  # -> {'answer': 'Answer based on [search hits for: What is LangGraph?]'}
```

## Conclusion
Separating input, output, and internal (overall) schemas keeps a graph's
public contract narrow even as its internal state grows to hold scratch
data, intermediate results, and bookkeeping fields. Overlapping keys — like
`question` and `answer` here — are how LangGraph ties the three schemas
together; anything else stays private to the graph. This pattern is
especially useful once graphs grow large enough that "everything the caller
passed in plus everything every node needs" would otherwise become one huge,
leaky schema.
