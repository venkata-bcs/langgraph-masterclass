# Reducers
> Venkata Bhattaram (c) 2026

## Contents
* Default overwrite behavior
* Annotated reducers
* operator.add and add_messages
* The Annotated[] syntax, old and new
* How state flows between nodes

## Overview
When a node returns `{"field": value}`, LangGraph has to decide how to
combine that update with whatever `field` already held. By default it
**overwrites** — the new value replaces the old one. That's fine for scalars
like a running total you recompute each time, but wrong for anything you want
to *accumulate*, like a list of messages or log entries. To change the merge
behavior, annotate the field's type with a **reducer function**: a
`(current, update) -> new_value` callable that LangGraph calls automatically
every time that field is updated.

## The Annotated[] Syntax, Old and New
`log: Annotated[List[str], operator.add]` breaks down into two separate
things:
* The `:` is an ordinary variable annotation (`name: type`) — inside a
  `TypedDict` it just declares a field, with no value assigned.
* `Annotated[List[str], operator.add]` is the *type*. `Annotated` (from
  `typing`, or `typing_extensions` on Python 3.7/3.8) lets you attach extra
  metadata to a type hint without changing the type itself — to Python and
  to type checkers, `Annotated[X, anything]` behaves exactly like `X`. Strip
  the wrapper and the real type of `log` is just `List[str]`; the second
  argument, `operator.add`, is metadata that LangGraph reads at graph-build
  time and uses as that field's reducer.

`messages: Annotated[List, add_messages]` works the same way: type `List`,
reducer `add_messages`.

## Code Example
```python
"""Default overwrite vs. an Annotated reducer that accumulates."""
import operator
from typing import List, TypedDict
from typing_extensions import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


class ReducerDemoState(TypedDict):
    # No annotation -> default reducer -> plain overwrite.
    latest_step: str

    # Annotated with operator.add -> each update is CONCATENATED onto the
    # existing list instead of replacing it.
    log: Annotated[List[str], operator.add]

    # Annotated with add_messages -> LangGraph's built-in reducer for chat
    # message lists. It appends new messages and updates existing ones
    # in place when they share an id, instead of just concatenating.
    messages: Annotated[List, add_messages]


def step_one(state: ReducerDemoState) -> dict:
    # `state` is the CURRENT merged state, handed in by LangGraph -- not
    # passed here by step_two or any other node. Return only the fields
    # this node wants to change; LangGraph merges the rest.
    #
    # state coming IN:  {"latest_step": "",           "log": [],                  "messages": []}
    # state going OUT (after LangGraph merges this return value):
    #                   {"latest_step": "step_one",   "log": ["step_one ran"],    "messages": []}
    return {
        "latest_step": "step_one",      # overwrites latest_step
        "log": ["step_one ran"],        # gets appended to log
    }


def step_two(state: ReducerDemoState) -> dict:
    # By the time this runs, state["latest_step"] and state["log"] already
    # reflect step_one's merged update.
    #
    # state coming IN:  {"latest_step": "step_one",  "log": ["step_one ran"], "messages": []}
    # state going OUT (after LangGraph merges this return value):
    #                   {"latest_step": "step_two",  "log": ["step_one ran", "step_two ran"], "messages": []}
    return {
        "latest_step": "step_two",      # overwrites latest_step again
        "log": ["step_two ran"],        # appended, step_one's entry stays
    }


builder = StateGraph(ReducerDemoState)
# add_node("step_one", step_one) passes the FUNCTION ITSELF (no parens, no
# call, no arguments) -- it just registers "step_one" as a name LangGraph
# can route to, plus which function to run when it does. LangGraph is the
# one that calls step_one(state) later, during invoke(), supplying state
# itself.
builder.add_node("step_one", step_one)
builder.add_node("step_two", step_two)
builder.add_edge(START, "step_one")
builder.add_edge("step_one", "step_two")
builder.add_edge("step_two", END)
graph = builder.compile()

# invoke() supplies the INITIAL state -- latest_step="", log=[], messages=[]
# -- as a literal dict, right here, in this one call. LangGraph calls
# step_one first (per the START -> step_one edge), merges its update, then
# calls step_two with that merged state, merges again, and returns the
# final state below. See the "state coming IN / going OUT" comments above
# step_one and step_two for the value at each hop.
result = graph.invoke({"latest_step": "", "log": [], "messages": []})
print(result["latest_step"])  # -> "step_two"  (overwritten, only last wins)
print(result["log"])          # -> ["step_one ran", "step_two ran"]  (accumulated)
```

## How State Flows Between Nodes
Each node function (`step_one`, `step_two`) takes one argument, `state`,
typed as `ReducerDemoState` — at runtime just a plain `dict` matching that
shape (`TypedDict` gives type checkers hints, but adds no runtime
enforcement). A node never calls another node directly; it only reads
`state` and returns a small dict of the fields it wants to change.

`graph.invoke({...})` starts the run with that dict as the initial state.
LangGraph then walks the edges you wired:

1. `START -> step_one`: LangGraph calls `step_one(initial_state)`.
2. `step_one` returns `{"latest_step": "step_one", "log": ["step_one ran"]}`.
   LangGraph merges this into the state using each field's reducer:
   `latest_step` is overwritten, `log` is concatenated onto via
   `operator.add`.
3. `step_one -> step_two`: LangGraph calls `step_two(merged_state)` — the
   *updated* state, not the dict originally passed to `invoke`.
4. `step_two` returns its own update; the same merge happens again.
5. `step_two -> END`: the graph stops, and `invoke()` returns the final
   merged state — the `result` dict printed above.

**Initial values and how they change at each hop** — the initial state is
set in exactly one place: the dict literal passed to `graph.invoke(...)`
near the bottom of the Code Example above. From there:

| point in the run | `latest_step` | `log` | `messages` |
|---|---|---|---|
| initial (the `invoke(...)` argument) | `""` | `[]` | `[]` |
| after `step_one` merges | `"step_one"` | `["step_one ran"]` | `[]` |
| after `step_two` merges | `"step_two"` | `["step_one ran", "step_two ran"]` | `[]` |

`latest_step` changes by **overwrite** each time (no reducer — the new
value replaces the old one), so only the *last* node to touch it shows up
in the final result. `log` changes by **concatenation** (`operator.add`
reducer), so every node's contribution survives. `messages` never changes
here at all — neither `step_one` nor `step_two` returns a `"messages"` key,
so there's nothing for `add_messages` to merge in; it stays `[]` throughout.
The comments directly above each `return` in `step_one` and `step_two` (and
above the `invoke(...)` call) show this same state-in/state-out trace right
next to the code that produces it.

So `state` is always "whatever the merged state is right now," handed to a
node by LangGraph based on the graph's edges — never passed hand-to-hand
between node functions.

## Why add_node Takes a Function Reference, Not a Call
`builder.add_node("step_one", step_one)` passes `step_one` with no
parentheses — a reference to the function object, not a call to it. Compare:

```python
step_one          # the function itself: "here's a thing you can call"
step_one(state)   # actually calling it, right now, with an argument
```

`add_node` only registers two things: a **name** for the node (`"step_one"`,
the string other calls like `add_edge(START, "step_one")` refer to), and the
**function to run** when that node executes (`step_one`). The actual call —
`step_one(state)` — happens later, inside `graph.invoke(...)`, and LangGraph
is the one making that call and supplying `state`. This is the same pattern
as passing a callback, e.g. `button.on_click(handle_click)`: the function
isn't invoked at registration time, only stored for the caller to invoke
later.

## Conclusion
A field's reducer is what turns "the last node to touch this wins" into
"every node's contribution is preserved." `operator.add` is the general-purpose
choice for lists and numbers you want to accumulate; `add_messages` is a
specialized reducer built for chat history, and it's what powers the
`MessagesState` schema we build next. The rule to remember: no annotation
means overwrite, an `Annotated[..., reducer_fn]` means merge.
