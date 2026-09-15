"""Verify the install: check versions, and confirm a graph actually compiles
and runs end to end before moving on to the next lesson.
"""
import langchain_core
import langgraph
from langgraph.graph import END, START, StateGraph


def main() -> None:
    print("langgraph:", langgraph.__version__)
    print("langchain-core:", langchain_core.__version__)

    class PingState(dict):
        pass

    def ping(state: dict) -> dict:
        return {"ok": True}

    builder = StateGraph(dict)
    builder.add_node("ping", ping)
    builder.add_edge(START, "ping")
    builder.add_edge("ping", END)
    graph = builder.compile()

    result = graph.invoke({})
    assert result["ok"] is True
    print("Installation verified: a compiled graph ran successfully.")


if __name__ == "__main__":
    main()
