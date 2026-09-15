# Your First Graph
> Venkata Bhattaram (c) 2026

## Contents
* Hello-world StateGraph
* Defining state
* Adding a node
* Compiling and invoking
* Visualizing the graph

## Overview
Every LangGraph app starts the same way: define a **state** shape, wrap one or
more functions as **nodes**, wire them together with **edges**, and
**compile** the result into a runnable graph. This lesson builds the smallest
possible graph — one node that says hello — so you can see the whole
lifecycle end to end before adding any complexity.

## Code Example
```python
"""Hello-world StateGraph: define state, add a node, compile, invoke."""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# 1. STATE — describe the data that flows through the graph.
class GreetingState(TypedDict):
    name: str       # input: who to greet
    greeting: str   # output: the message we build


# 2. NODE — a plain function. It receives the current state and returns a
#    dict with just the field(s) it wants to update. That's the whole rule.
def greet_node(state: GreetingState) -> dict:
    person_name = state["name"]
    message = f"Hello, {person_name}!"
    return {"greeting": message}


# 3. GRAPH — create a builder for our state shape.
builder = StateGraph(GreetingState)

# add_node(name, function) always takes TWO things:
#   name     -> a string label. This is how you'll refer to this step
#               below when wiring edges.
#   function -> the node function that should run for that step.
# We label this step "greet" and point it at greet_node.
NODE_NAME = "greet"
builder.add_node(NODE_NAME, greet_node)

# add_edge(from_label, to_label) connects steps using those string labels.
# START and END are built-in markers for "where the graph begins/ends".
builder.add_edge(START, NODE_NAME)   # start the graph -> run "greet" first
builder.add_edge(NODE_NAME, END)     # after "greet" runs -> graph is done

# 4. COMPILE — lock in the wiring and get back a graph you can run.
graph = builder.compile()

# 5. INVOKE — run the graph once with a starting state.
result = graph.invoke({"name": "Venkata", "greeting": ""})
print(result["greeting"])  # -> Hello, Venkata!

# 6. (optional) Visualize the graph topology as Mermaid source — paste the
#    output into a Mermaid renderer to see the boxes-and-arrows picture.
print(graph.get_graph().draw_mermaid())
```

## Conclusion
You built and ran a complete LangGraph app: a typed state, one node, two
edges, and a compiled, invokable graph. Every graph in this tutorial —
however large — is the same four ingredients repeated: state, nodes, edges,
compile. Next, we look more closely at what "state" and "graph" actually mean
in LangGraph.
