# Basics
> Venkata Bhattaram (c) 2026

## Contents (Planned)
* State
* Graph
* Node
* Edge
* Compile
* Invoke

## Overview
Before you build your first graph, it helps to know six words. LangGraph
reuses these same six ideas in every app you'll ever build with it, no
matter how big it gets. Get comfortable with them here in plain English, and
everything in the rest of this tutorial will just be new ways of combining
them.

Think of the whole thing like a factory assembly line:

* **State** is the box moving down the conveyor belt.
* **Node** is a worker station that opens the box, does one job, and puts it
  back on the belt.
* **Edge** is the stretch of belt connecting one station to the next.
* **Graph** is the factory floor plan showing every station and every belt.
* **Compile** is the safety inspection that turns the floor plan into a
  factory you're allowed to run.
* **Invoke** is pressing the "start" button and getting the finished box
  back out the other end.

## State
State is just a Python object — usually a `TypedDict`, a `dataclass`, or a
Pydantic model — that describes every piece of data your app needs to carry
around. It's a shared notebook: every node can read what's currently written
in it, and every node can write new entries into it.

```python
from typing import TypedDict

class GreetingState(TypedDict):
    name: str
    greeting: str
```

You never pass `name` or `greeting` around as separate function arguments.
Instead, one `GreetingState` dict travels through the whole graph, and each
node reads the fields it cares about and writes the fields it's responsible
for.

**Rookie tip:** if you've ever passed a `dict` (or a bunch of arguments)
between functions to keep track of "everything going on so far," State is
just that idea, formalized and made explicit.

## Graph
A Graph is the blueprint of your app — it lists every node you have and
every edge connecting them, before anything actually runs. In LangGraph you
build this blueprint with the `StateGraph` class, telling it up front what
shape your State has.

```python
from langgraph.graph import StateGraph

builder = StateGraph(GreetingState)
```

**Rookie tip:** a Graph is like a flowchart you'd draw on a whiteboard
first — boxes for steps, arrows for what happens next — except here you draw
it in Python code instead of on paper.

## Node
A Node is just a normal Python function (or `async def` function). It takes
the current State in as its only argument and returns a dictionary of
updates to merge into that State. It does not call other nodes directly and
does not know what runs before or after it — it only knows its own job.

```python
def greet_node(state: GreetingState) -> dict:
    return {"greeting": f"Hello, {state['name']}!"}

# add_node(name, function) takes two things: a string label ("greet") you'll
# use to refer to this step, and the function to run for it (greet_node).
builder.add_node("greet", greet_node)
```

**Rookie tip:** if you can write a normal Python function, you can write a
LangGraph node. The only rule is "State in, partial update out." The string
you pass to `add_node` doesn't have to match the function's name — it's just
a label you'll reuse when wiring edges next.

## Edge
An Edge is the arrow that says "after this node finishes, run that node
next." Every graph has two special built-in markers, `START` and `END`, so
you can say where execution begins and where it's allowed to finish.

```python
from langgraph.graph import START, END

builder.add_edge(START, "greet")
builder.add_edge("greet", END)
```

There's also a fancier kind, a **conditional edge**, where a small routing
function decides *which* node to go to next based on what's in State — but
that's a lesson of its own (see [Conditional Edges](../../02-langgraph-core-concepts/md/conditional_edges.md)).

**Rookie tip:** a normal edge is just "and then do this next" — the same
thing as writing two function calls back-to-back, except LangGraph tracks
the order for you so it can visualize, pause, and replay it later.

## Compile
Compile is the step where you tell LangGraph "I'm done wiring this graph
together — lock it in." It checks that your nodes and edges actually form a
valid graph (no dangling references, no missing `START`/`END`) and hands you
back a runnable object.

```python
graph = builder.compile()
```

**Rookie tip:** think of `builder` as a half-built Lego set and
`builder.compile()` as clicking the last brick in — after that, you have a
finished thing (`graph`) you can actually use, and you stop adding more
nodes or edges to it.

## Invoke
Invoke is how you actually run the compiled graph. You hand it a starting
State, LangGraph walks the graph from `START` to `END` running each node in
order, and you get back the final State once execution reaches `END`.

```python
result = graph.invoke({"name": "Venkata", "greeting": ""})
print(result["greeting"])  # -> Hello, Venkata!
```

If any node in your graph is `async def`, you'll call `graph.ainvoke(...)`
instead (from inside an `async def` function) — invoking is otherwise the
same idea. There's also `graph.stream(...)` for watching state updates as
they happen, node by node, instead of waiting for the final result.

**Rookie tip:** `compile()` happens once, when you're building the app.
`invoke()` happens every time you want to actually run it — the same
compiled `graph` can be invoked over and over with different starting
State.

## Conclusion
Six words, one mental model: a **Graph** is a map of **Nodes** connected by
**Edges**, all of them reading and writing one shared **State**; you
**Compile** the map once and **Invoke** it as many times as you like. Every
lesson from here on — branching, looping, persistence, multi-agent systems —
is this same handful of ideas, just arranged in new shapes. Head to
[Your First Graph](../../02-langgraph-core-concepts/md/your_first_graph.md)
to build one for real.

See [code/basics_demo.py](../code/basics_demo.py) for the complete script —
every snippet above, combined and runnable:
```bash
python basics_demo.py
```
