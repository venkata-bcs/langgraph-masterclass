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
