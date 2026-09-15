# Parallel Execution (Fan-Out/Fan-In)
> Venkata Bhattaram (c) 2026

## Contents
* Fan-out to multiple nodes
* Fan-in and merging state
* The superstep execution model

## Overview
LangGraph executes a graph in **supersteps** (borrowed from the Pregel
model): at each superstep, every node whose incoming edges are satisfied
runs, and every node that runs in the same superstep runs *concurrently*,
not in some implicit left-to-right order. That's what makes **fan-out**
possible: point more than one edge out of the same node (or `START`), and
every one of those destination nodes runs together in the next superstep.
**Fan-in** is the mirror image — point more than one edge *into* the same
node, and LangGraph waits until every incoming branch has finished and its
updates have been merged before calling that node. Reducers (see
[Reducers](../../03-state-management/md/reducers.md)) are what make fan-in
safe: without one, two branches writing to the same field in the same
superstep would silently clobber each other.

## Code Example
```python
"""Fan-out to multiple nodes, fan-in merging, and LangGraph's superstep model."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END


class ResearchState(TypedDict):
    topic: str
    findings: Annotated[list[str], operator.add]
    summary: str


def fetch_weather(state: ResearchState) -> dict:
    # Runs in the SAME superstep as fetch_news -- both fire off of the same
    # START -> fan-out edges, concurrently, not one-after-the-other.
    return {"findings": [f"weather report for {state['topic']}"]}


def fetch_news(state: ResearchState) -> dict:
    return {"findings": [f"news headlines for {state['topic']}"]}


def summarize(state: ResearchState) -> dict:
    # Only runs once BOTH fetch_weather and fetch_news have finished and
    # their findings have been merged (fan-in) -- LangGraph waits for every
    # incoming edge into this node before calling it.
    return {"summary": f"{len(state['findings'])} findings: {state['findings']}"}


builder = StateGraph(ResearchState)
builder.add_node("fetch_weather", fetch_weather)
builder.add_node("fetch_news", fetch_news)
builder.add_node("summarize", summarize)

# Fan-out: two edges out of START -> both nodes run in the same superstep.
builder.add_edge(START, "fetch_weather")
builder.add_edge(START, "fetch_news")
# Fan-in: two edges INTO summarize -> LangGraph waits for both before running it.
builder.add_edge("fetch_weather", "summarize")
builder.add_edge("fetch_news", "summarize")
builder.add_edge("summarize", END)
graph = builder.compile()

# state coming IN: {"topic": "LangGraph", "findings": [], "summary": ""}
# superstep 1: fetch_weather and fetch_news both run, each appending to findings
# superstep 2: summarize runs once, after both updates are merged (fan-in)
result = graph.invoke({"topic": "LangGraph", "findings": [], "summary": ""})
print(result["findings"])  # -> ['weather report for LangGraph', 'news headlines for LangGraph']
print(result["summary"])   # -> "2 findings: [...]"
```

Note: `findings` here is a `list`, and `operator.add` doesn't guarantee
*which* branch's item lands first — only that both land. Running this
script more than once can print the two findings in either order.

## Conclusion
Fan-out and fan-in are both just edges — nothing about `add_edge` itself
changes — the concurrency comes from the superstep model underneath: nodes
with satisfied incoming edges run together, and a node with multiple
incoming edges waits for all of them. The one thing you must get right is
giving any field two branches might both write to a proper reducer, or
concurrent writes will conflict. Next we look at fanning out to a number of
branches that isn't known until runtime: map-reduce with `Send`.
