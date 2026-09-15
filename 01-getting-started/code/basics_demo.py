"""The six-word mental model from md/basics.md, combined into one runnable
script: State, Graph, Node, Edge, Compile, Invoke.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# State: the shared notebook every node reads from and writes into.
class GreetingState(TypedDict):
    name: str
    greeting: str


# Node: a plain function, state in, partial update out.
def greet_node(state: GreetingState) -> dict:
    return {"greeting": f"Hello, {state['name']}!"}


# Graph: the blueprint listing nodes and edges before anything runs.
builder = StateGraph(GreetingState)

# add_node(name, function) takes a string label and the function to run for it.
builder.add_node("greet", greet_node)

# Edge: "after this node finishes, run that node next." START/END mark the
# graph's entry and exit points.
builder.add_edge(START, "greet")
builder.add_edge("greet", END)

# Compile: lock in the wiring, get back a runnable graph.
graph = builder.compile()

# Invoke: run the compiled graph once with a starting state.
result = graph.invoke({"name": "Venkata", "greeting": ""})
print(result["greeting"])  # -> Hello, Venkata!
