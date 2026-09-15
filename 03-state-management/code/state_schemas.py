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
