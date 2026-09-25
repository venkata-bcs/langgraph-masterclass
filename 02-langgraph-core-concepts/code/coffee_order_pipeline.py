"""Coffee order pipeline: four nodes, one job each, partial updates only."""
import asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# Step 1: Set up the shop's reference data (plain Python, not part of the graph).
MENU = {"latte": 4.50, "espresso": 3.00, "cappuccino": 4.00}
SIZE_MULTIPLIER = {"small": 1.0, "medium": 1.25, "large": 1.5}
INVENTORY = {"latte": 10, "espresso": 0, "cappuccino": 5}


# Step 2: Define the state, the "order ticket" every node can read.
# Nodes may only write keys that are declared here.
class CoffeeOrder(TypedDict):
    drink: str
    size: str
    price: float
    in_stock: bool
    cup: str
    status: str


# Step 3: Node 1, take_order. Prices the order and returns only the keys it
# changed (price, status); every other key is left untouched.
def take_order(state: CoffeeOrder) -> dict:
    """Sync node: pure calculation, prices the order."""
    price = MENU[state["drink"]] * SIZE_MULTIPLIER[state["size"]]
    return {"price": round(price, 2), "status": "ordered"}


# Step 4: Node 2, check_inventory. An async node, because a real stock check
# would be I/O (database/API). asyncio.sleep stands in for that call.
async def check_inventory(state: CoffeeOrder) -> dict:
    """Async node: simulates an I/O-bound stock lookup."""
    await asyncio.sleep(0.1)
    return {"in_stock": INVENTORY.get(state["drink"], 0) > 0}


# Step 5: Node 3, brew. Reads in_stock, written by the previous node, and
# returns a different update depending on it. Sold out -> cup is never set.
def brew(state: CoffeeOrder) -> dict:
    """Sync node: reads earlier updates and decides what to make."""
    if not state["in_stock"]:
        return {"status": "sold out"}
    return {"cup": f"{state['size']} {state['drink']}", "status": "brewed"}


# Step 6: Node 4, serve. Overwrites status (last writer wins) and reads
# price, which take_order wrote three steps earlier.
def serve(state: CoffeeOrder) -> dict:
    """Sync node: final hand-off, only touches status."""
    if state["status"] != "brewed":
        return {"status": f"refunded ${state['price']:.2f}"}
    return {"status": "served"}


# Step 7: Create a graph builder bound to the CoffeeOrder state schema.
builder = StateGraph(CoffeeOrder)

# Step 8: Register each function as a named node. The name (first argument)
# is what edges and streamed output refer to.
builder.add_node("take_order", take_order)
builder.add_node("check_inventory", check_inventory)
builder.add_node("brew", brew)
builder.add_node("serve", serve)

# Step 9: Wire the nodes into a straight line: START -> ... -> END.
builder.add_edge(START, "take_order")
builder.add_edge("take_order", "check_inventory")
builder.add_edge("check_inventory", "brew")
builder.add_edge("brew", "serve")
builder.add_edge("serve", END)

# Step 10: Compile the builder into a runnable graph.
graph = builder.compile()


# Step 11: run_order runs one customer order through the graph.
async def run_order(drink: str, size: str) -> None:
    # Step 11a: Build the initial state. The customer supplies drink and size;
    # the other keys hold placeholders that the nodes will fill in.
    initial = {
        "drink": drink,
        "size": size,
        "price": 0.0,
        "in_stock": False,
        "cup": "",
        "status": "new",
    }
    print(f"\n--- Order: {size} {drink} ---")

    # Step 11b: Stream the run. stream_mode="updates" yields
    # {node_name: partial_update} after each node, so you can see exactly
    # which keys each node changed.
    async for step in graph.astream(initial, stream_mode="updates"):
        for node_name, update in step.items():
            print(f"{node_name:>16} -> {update}")

    # Step 11c: Run again with ainvoke to get the final merged state.
    # (Async API is required because check_inventory is async.)
    final = await graph.ainvoke(initial)
    print(f"{'final state':>16} -> {final}")


# Step 12: Place two orders: one in stock (latte), one sold out (espresso).
async def main() -> None:
    await run_order("latte", "large")
    await run_order("espresso", "small")


# Step 13: Start the async event loop.
asyncio.run(main())
