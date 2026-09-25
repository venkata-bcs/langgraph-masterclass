"""CLI: check config/schema_registry.yaml for newly activated tables/columns
(evolution) or newly deactivated ones (rollback). The graph's load_handler
node then routes + rejoins target-data itself whenever it acts, so a single
run of this script is a complete, self-contained pass of the agentic loop.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.schema_evolution.graph import run


def main():
    result = run()
    if result["regenerated"]:
        print("Schema evolution detected -- regenerated data:", result["changes"])
    elif result["archived"]:
        print("Rollback detected -- no active columns/tables added:", result["changes"])
    else:
        print("No schema changes detected.")

    if result["archived"]:
        print("Archived rolled-back tables:")
        for table_name, path in result["archived"].items():
            print(f" - {table_name}: {path}")

    if result["routed_files"] or result["load_outputs"]:
        print(f"load_handler: routed {result['routed_files']} file(s); joined output:")
        for kind, path in result["load_outputs"].items():
            print(f" - {kind}: {path}")


if __name__ == "__main__":
    main()
