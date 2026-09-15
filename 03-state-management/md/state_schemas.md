# State Schemas
> Venkata Bhattaram (c) 2026

## Contents
* TypedDict state
* Dataclass state
* Pydantic state

## Overview
A graph's state is just a schema plus a set of update rules. LangGraph
doesn't force one particular way to define that schema — it accepts a
`TypedDict`, a `dataclass`, or a Pydantic `BaseModel`. They all work the same
way at runtime: nodes read fields off the current state and return a dict of
the fields they want to update. The difference is what you get at
*definition* time — plain dict-style typing, attribute access with defaults,
or full runtime validation.

## Code Example
```python
"""The same state modeled three ways: TypedDict, dataclass, and Pydantic."""
from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END


# 1. TypedDict — the lightest option. Pure type hints, no runtime checks.
#    Access fields with state["field"]. This is what most examples use.
class TypedDictState(TypedDict):
    name: str
    greeting: str


# 2. dataclass — attribute access (state.name) and you can give fields
#    default values. Still no runtime validation of types.
@dataclass
class DataclassState:
    name: str
    greeting: str = ""


# 3. Pydantic BaseModel — attribute access PLUS runtime validation. If a
#    node returns a value that doesn't match the annotated type, Pydantic
#    raises instead of silently accepting bad data.
class PydanticState(BaseModel):
    name: str
    greeting: str = ""


def greet_typed_dict(state: TypedDictState) -> dict:
    # state coming IN:  {"name": "Venkata", "greeting": ""}
    # state going OUT (after merge): {"name": "Venkata", "greeting": "Hello, Venkata!"}
    return {"greeting": f"Hello, {state['name']}!"}


def greet_dataclass(state: DataclassState) -> dict:
    # state coming IN:  DataclassState(name="Venkata", greeting="")  -- the
    # dataclass default fills in `greeting` since only "name" was passed in.
    # state going OUT (after merge): DataclassState(name="Venkata", greeting="Hello, Venkata!")
    return {"greeting": f"Hello, {state.name}!"}


def greet_pydantic(state: PydanticState) -> dict:
    # state coming IN:  PydanticState(name="Venkata", greeting="")  -- same
    # default-filling behavior as the dataclass above.
    # state going OUT (after merge): PydanticState(name="Venkata", greeting="Hello, Venkata!")
    return {"greeting": f"Hello, {state.name}!"}


def run(state_cls, node_fn, initial: dict) -> None:
    builder = StateGraph(state_cls)
    builder.add_node("greet", node_fn)
    builder.add_edge(START, "greet")
    builder.add_edge("greet", END)
    graph = builder.compile()

    result = graph.invoke(initial)
    print(state_cls.__name__, "->", result)


# Each call below supplies the INITIAL state as a literal dict; StateGraph
# converts it into the schema instance the node function expects (a plain
# dict for TypedDict, or a constructed DataclassState / PydanticState
# instance for the other two) before calling node_fn(state) inside run().
run(TypedDictState, greet_typed_dict, {"name": "Venkata", "greeting": ""})
run(DataclassState, greet_dataclass, {"name": "Venkata"})
run(PydanticState, greet_pydantic, {"name": "Venkata"})

# Runtime validation only happens for the Pydantic schema:
try:
    PydanticState(name=123)  # wrong type for `name`
except Exception as exc:
    print("Pydantic caught it:", type(exc).__name__)
```

## Conclusion
`TypedDict`, `dataclass`, and Pydantic `BaseModel` all define a valid
LangGraph state schema — pick `TypedDict` for the least ceremony, `dataclass`
when you want attribute access and defaults, and Pydantic when you want
runtime validation on every state update. The graph wiring (`add_node`,
`add_edge`, `compile`) is identical regardless of which one you choose. Next,
we look at how LangGraph decides what happens when two nodes write to the
same field: reducers.
