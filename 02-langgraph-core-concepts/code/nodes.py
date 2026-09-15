"""Sync and async nodes living in the same graph."""
import asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class OrderState(TypedDict):
    order_id: str
    is_valid: bool
    total: float


def validate_order(state: OrderState) -> dict:
    """Sync node: pure, CPU-only logic."""
    return {"is_valid": state["total"] > 0}


async def fetch_shipping_estimate(state: OrderState) -> dict:
    """Async node: simulates an I/O-bound call, e.g. a shipping API."""
    await asyncio.sleep(0.1)
    return {"total": state["total"] + 5.0}


builder = StateGraph(OrderState)
builder.add_node("validate_order", validate_order)
builder.add_node("fetch_shipping_estimate", fetch_shipping_estimate)

builder.add_edge(START, "validate_order")
builder.add_edge("validate_order", "fetch_shipping_estimate")
builder.add_edge("fetch_shipping_estimate", END)

graph = builder.compile()


# Because the graph contains an async node, it must be run through the async
# API — graph.invoke() would raise TypeError("No synchronous function
# provided to ...") since there is no sync implementation to fall back to.
async def main() -> None:
    result = await graph.ainvoke(
        {"order_id": "A101", "is_valid": False, "total": 100.0}
    )
    print(result)


asyncio.run(main())
