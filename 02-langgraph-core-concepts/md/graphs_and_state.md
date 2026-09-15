# Graphs and State
> Venkata Bhattaram (c) 2026

## Contents
* What is a graph in LangGraph
* State as the single source of truth
* Message passing between nodes

## Overview
Think of a LangGraph graph as a **relay race**, and **state** as the baton.
Runners (nodes) never talk to each other, shout instructions across the
track, or hand anything off directly. Each one just:

1. Receives the baton (the current state),
2. Does its own leg of the race (its own small piece of work),
3. Hands the *same* baton back — with maybe one thing added or changed — to
   the race official (LangGraph's runtime), who carries it to whoever runs
   next.

That baton is one shared Python object (usually a `TypedDict`) that every
node in the graph can see. It's the *only* way information ever moves
around the graph:

* A node **reads** whatever fields off the current state it actually needs.
* A node **returns** a small dict with just the field(s) it wants to
  change — never the whole state, just the update.
* LangGraph merges that update into the state and passes the result to
  whichever node runs next.

Because nodes never call each other directly, there's no hidden wiring to
go hunting for — every piece of information passed between nodes is sitting
in one place, in the open, at every step. That's what "state is the single
source of truth" means. It's also what "message passing between nodes"
means in LangGraph: a node's return value *is* the message, and state is
the mailbox every other node can read from.

## Code Example
```python
"""Two nodes communicating only through shared state — no direct calls."""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class PipelineState(TypedDict):
    text: str
    word_count: int
    upper: str


def count_words(state: PipelineState) -> dict:
    # Reads state["text"], writes state["word_count"].
    return {"word_count": len(state["text"].split())}


def to_upper(state: PipelineState) -> dict:
    # Reads state["text"] (written before the graph even started) and
    # state["word_count"] is available too, even though this node doesn't
    # use it — that's what "single source of truth" buys you.
    return {"upper": state["text"].upper()}


builder = StateGraph(PipelineState)
builder.add_node("count_words", count_words)
builder.add_node("to_upper", to_upper)

builder.add_edge(START, "count_words")
builder.add_edge("count_words", "to_upper")
builder.add_edge("to_upper", END)

graph = builder.compile()

final_state = graph.invoke(
    {"text": "LangGraph makes state explicit", "word_count": 0, "upper": ""}
)
print(final_state)
# -> {'text': 'LangGraph makes state explicit', 'word_count': 4,
#     'upper': 'LANGGRAPH MAKES STATE EXPLICIT'}
```

## Conclusion
`count_words` and `to_upper` never reference each other — each one only
reads and returns state. The graph is what threads the state through both
nodes in order. Keeping all communication in one explicit, typed object is
what makes LangGraph graphs easy to inspect, checkpoint, and debug later in
this tutorial.
