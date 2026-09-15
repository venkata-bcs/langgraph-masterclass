"""Fan-out to multiple nodes, fan-in merging, and LangGraph's superstep model."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END


class ResearchState(TypedDict):
    topic: str
    findings: Annotated[list[str], operator.add]
    summary: str


def fetch_weather(state: ResearchState) -> dict:
    # Runs in the SAME superstep as fetch_news -- both fire off of the same
    # START -> fan-out edges, concurrently, not one-after-the-other.
    return {"findings": [f"weather report for {state['topic']}"]}


def fetch_news(state: ResearchState) -> dict:
    return {"findings": [f"news headlines for {state['topic']}"]}


def summarize(state: ResearchState) -> dict:
    # Only runs once BOTH fetch_weather and fetch_news have finished and
    # their findings have been merged (fan-in) -- LangGraph waits for every
    # incoming edge into this node before calling it.
    return {"summary": f"{len(state['findings'])} findings: {state['findings']}"}


builder = StateGraph(ResearchState)
builder.add_node("fetch_weather", fetch_weather)
builder.add_node("fetch_news", fetch_news)
builder.add_node("summarize", summarize)

# Fan-out: two edges out of START -> both nodes run in the same superstep.
builder.add_edge(START, "fetch_weather")
builder.add_edge(START, "fetch_news")
# Fan-in: two edges INTO summarize -> LangGraph waits for both before running it.
builder.add_edge("fetch_weather", "summarize")
builder.add_edge("fetch_news", "summarize")
builder.add_edge("summarize", END)
graph = builder.compile()

# state coming IN: {"topic": "LangGraph", "findings": [], "summary": ""}
# superstep 1: fetch_weather and fetch_news both run, each appending to findings
# superstep 2: summarize runs once, after both updates are merged (fan-in)
result = graph.invoke({"topic": "LangGraph", "findings": [], "summary": ""})
print(result["findings"])  # -> ['weather report for LangGraph', 'news headlines for LangGraph']
print(result["summary"])   # -> "2 findings: [...]"
