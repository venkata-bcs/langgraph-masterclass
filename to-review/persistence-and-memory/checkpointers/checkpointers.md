# Checkpointers
> Venkata Bhattaram (c) 2026

## Contents (Planned)
* What a checkpointer does
* In-memory checkpointer
* Threads and checkpoint IDs

## Overview
A checkpointer is what lets a *compiled* graph save its state after every
super-step and reload it later, keyed by a `thread_id`. Without one,
`invoke()` runs start to finish and the result exists only in whatever
variable you assigned it to — nothing persists, and there's no way to pause,
inspect, or resume a run.

LangGraph's simplest option, `InMemorySaver`, keeps that history in a plain
Python dict. It's zero-setup and fine for a unit test, but it lives and dies
with the process: restart the interpreter and every thread's history is
gone. That's a real limitation the moment persistence needs to survive
anything — a crash, a redeploy, or just running the same script twice.

So this tutorial starts persistence with **`SqliteSaver`** instead of
`InMemorySaver`: one local `.db` file, built on Python's own `sqlite3` /
`aiosqlite`, with nothing to install or run as a separate server. It's a
drop-in replacement — same `checkpointer=` argument at compile time, same
`thread_id`-based config, same `get_state` / `get_state_history` API — the
only thing that changes is that the history actually survives a restart.
When a single file and a single writer stop being enough (multiple
processes, a deployed service), [SQLite and Postgres Checkpointers](../sqlite-and-postgres-checkpointers/sqlite_and_postgres_checkpointers.md)
swaps in `PostgresSaver` behind that exact same interface.

A **thread** is the unit of persistence: every `invoke()` against the same
`thread_id` reads and extends the same history. `get_state(config)` returns
the latest checkpoint for that thread; `get_state_history(config)` returns
every checkpoint ever recorded for it, newest first, each with its own
`checkpoint_id`.

## Code Example
```python
"""Threads + checkpoint IDs, backed by SqliteSaver instead of the in-memory
checkpointer. Run this script twice in a row (`python checkpointers_demo.py`)
-- the count keeps climbing on the SECOND run, because it's reading state
back from checkpoints.db on disk, not from process memory.
"""
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph


class CounterState(TypedDict):
    count: int


def increment(state: CounterState) -> dict:
    return {"count": state.get("count", 0) + 1}


builder = StateGraph(CounterState)
builder.add_node("increment", increment)
builder.add_edge(START, "increment")
builder.add_edge("increment", END)

# One local file, no server, no daemon -- this is why SQLite, not bare
# in-memory, is where you should start persisting state.
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)

    # thread_id is the unit of persistence: every invoke() against this
    # thread_id reads and writes the same row in checkpoints.db.
    config = {"configurable": {"thread_id": "demo-thread-1"}}

    result = graph.invoke({}, config)
    print("count after this run:", result["count"])

    latest = graph.get_state(config)
    print("latest checkpoint_id:", latest.config["configurable"]["checkpoint_id"])

    history = list(graph.get_state_history(config))
    print(f"{len(history)} checkpoint(s) recorded for this thread so far")
```

First run prints `count after this run: 1`. Run the exact same script
again — no code change — and it prints `count after this run: 2`, because
`increment` read the count that `SqliteSaver` persisted to `checkpoints.db`
on the previous run. Swap `SqliteSaver` for `InMemorySaver` and re-run twice
to see the contrast: it resets to `1` every time, because there's no file on
disk backing it — the history existed only inside the process that already
exited.

## Conclusion
A checkpointer turns a graph run from "happens once, in memory, then
disappears" into "happens, gets recorded, and can be reloaded" — and the
`thread_id` you pass through `config` is what scopes that history to one
conversation, one job, one user session. `InMemorySaver` gets you the same
API instantly, which is exactly why it's fine for a quick test, but this
tutorial's running examples use `SqliteSaver` from here on, because a
tutorial exercise you can't restart and pick back up isn't demonstrating
persistence at all. Next, we go deeper on `SqliteSaver` (async included) and
bring in `PostgresSaver` for when one file and one process stop being
enough.
