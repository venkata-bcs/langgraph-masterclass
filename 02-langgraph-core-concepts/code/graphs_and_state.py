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
