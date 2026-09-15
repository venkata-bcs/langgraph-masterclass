"""MessagesState, the add_messages reducer, and trimming history."""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState, add_messages
from langchain_core.messages import HumanMessage, AIMessage, trim_messages


def chatbot_node(state: MessagesState) -> dict:
    # state coming IN (1st call):  {"messages": [HumanMessage("Hello!")]}
    # state going OUT (after add_messages merge):
    #   {"messages": [HumanMessage("Hello!"), AIMessage("You said: Hello!")]}
    #
    # state coming IN (2nd call, after the manual append below):
    #   {"messages": [HumanMessage("Hello!"), AIMessage("You said: Hello!"),
    #                 HumanMessage("How are you?")]}
    # state going OUT (after add_messages merge): the 4th message,
    #   AIMessage("You said: How are you?"), is appended onto that list.
    last_user_msg = state["messages"][-1].content
    # Returning a message here is appended (not overwritten) thanks to the
    # add_messages reducer baked into MessagesState.
    return {"messages": [AIMessage(content=f"You said: {last_user_msg}")]}


builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot_node)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)
graph = builder.compile()

# INITIAL state: one HumanMessage, set right here as a literal dict.
state = {"messages": [HumanMessage(content="Hello!")]}
state = graph.invoke(state)  # chatbot_node runs once; state now has 2 messages

# Appending a HumanMessage OUTSIDE the graph -- plain list concatenation,
# not the add_messages reducer (that only runs during graph.invoke/merge).
state["messages"] = state["messages"] + [HumanMessage(content="How are you?")]
state = graph.invoke(state)  # chatbot_node runs again; state now has 4 messages

for m in state["messages"]:
    print(type(m).__name__, "->", m.content)
# -> HumanMessage -> Hello!
# -> AIMessage    -> You said: Hello!
# -> HumanMessage -> How are you?
# -> AIMessage    -> You said: How are you?

# Updating a message in place: give the new message the SAME id as an
# existing one, and add_messages replaces it instead of appending.
edited = AIMessage(content="You said: hi there", id=state["messages"][1].id)
merged = add_messages(state["messages"], [edited])
print(merged[1].content)  # -> "You said: hi there" (replaced, not appended)

# Trimming history before sending it to a model, e.g. to stay under a token
# budget — keep only the most recent messages that fit.
trimmed = trim_messages(
    state["messages"],
    max_tokens=20,
    token_counter=len,       # simple stand-in: count messages, not tokens
    strategy="last",
    start_on="human",
)
print(len(trimmed), "of", len(state["messages"]), "messages kept")
