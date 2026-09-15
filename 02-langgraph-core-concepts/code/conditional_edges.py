"""
Conditional Edges -- routing a support ticket to the right handler.

Objective:
    Show how a graph can pick its next node AT RUNTIME instead of always
    following the same fixed path -- the LangGraph building block behind
    if/else-style branching and dynamic, data-dependent control flow.

What this code does:
    1. Defines TicketState, the shared object every node reads from and
       writes to.
    2. Defines four nodes: one that classifies a ticket's category, and
       three handler nodes (billing / technical / general).
    3. Defines a routing function that looks at the classified category
       and returns the *name* of the next node to run.
    4. Wires the graph with add_conditional_edges() so classify()'s output
       decides which handler runs next, instead of a fixed add_edge().
    5. Compiles and invokes the graph on three sample tickets, printing
       which handler each one was routed to.
"""
from typing import Literal, TypedDict

from langgraph.graph import StateGraph, START, END


# STEP 1 -- STATE: the shared object every node reads from and writes to.
class TicketState(TypedDict):
    message: str    # input: the raw ticket text
    category: str   # set by classify(), read by the routing function
    response: str   # set by whichever handler node actually runs


# STEP 2 -- NODES.

# 2a. classify: looks at the ticket text and decides its category. This
# node does NOT decide where the graph goes next -- it just records a
# category in state. Routing is a separate concern, handled in Step 3.
def classify(state: TicketState) -> dict:
    text = state["message"].lower()
    if "refund" in text or "charge" in text:
        category = "billing"
    elif "error" in text or "bug" in text:
        category = "technical"
    else:
        category = "general"
    return {"category": category}


# 2b-2d. Handler nodes: one per category, each just writes a canned
# response. In a real app these would call different tools/prompts.
def handle_billing(state: TicketState) -> dict:
    return {"response": "Routing to billing support."}


def handle_technical(state: TicketState) -> dict:
    return {"response": "Routing to technical support."}


def handle_general(state: TicketState) -> dict:
    return {"response": "Routing to general support."}


# STEP 3 -- ROUTING FUNCTION: reads state, returns the *name* of whichever
# node should run next. It doesn't run any node itself -- it only decides.
def route_by_category(state: TicketState) -> Literal["billing", "technical", "general"]:
    return state["category"]


# STEP 4 -- GRAPH: register every node under a string label.
builder = StateGraph(TicketState)
builder.add_node("classify", classify)
builder.add_node("billing", handle_billing)
builder.add_node("technical", handle_technical)
builder.add_node("general", handle_general)

# STEP 5 -- EDGES.

# 5a. Normal edge: the graph always starts at "classify".
builder.add_edge(START, "classify")

# 5b. Conditional edge: after "classify" runs, LangGraph calls
# route_by_category with the current state. Its return value
# ("billing" / "technical" / "general") is looked up in the path_map below
# to pick the next node -- this is what makes the branch decision happen
# at RUNTIME instead of being fixed when the graph is built.
# add_conditional_edges(source_node, routing_fn, path_map). The path_map is
# optional but makes the mapping from routing-function output -> node name
# explicit, so the routing function's return values stay decoupled from
# node ids.
builder.add_conditional_edges(
    "classify",
    route_by_category,
    {
        "billing": "billing",
        "technical": "technical",
        "general": "general",
    },
)

# 5c. Every handler is a dead end -- once one runs, the graph is done.
builder.add_edge("billing", END)
builder.add_edge("technical", END)
builder.add_edge("general", END)

# STEP 6 -- COMPILE: lock in the wiring, get back a runnable graph.
graph = builder.compile()

# STEP 7 -- INVOKE: run the SAME compiled graph on three different tickets
# and watch each one take a different path through the conditional edge.
for message in [
    "I was charged twice for my order",
    "The app crashes with an error on login",
    "What are your business hours?",
]:
    result = graph.invoke({"message": message, "category": "", "response": ""})
    print(f"{message!r} -> {result['category']} -> {result['response']}")
