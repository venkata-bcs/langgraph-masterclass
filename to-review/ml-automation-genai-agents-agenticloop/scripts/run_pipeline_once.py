"""CLI: run the full pipeline once, end to end:
  1. check for schema evolution/rollback -- its own load_handler already
     routes + rejoins target-data whenever it acts (see
     src/schema_evolution/graph.py)
  2. otherwise (nothing changed) generate a fresh batch of data, route it,
     and join it here instead
  3. train + evaluate the reorder-risk ML demo over the joined output
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automation_router.watcher import scan_once
from src.data_loader.graph import run as run_loader
from src.genai_datagen.graph import run as run_datagen
from src.ml_insights.graph import run as run_ml_demo
from src.schema_evolution.graph import run as run_schema_check


def main():
    evolution_result = run_schema_check()

    if evolution_result["regenerated"] or evolution_result["archived"]:
        # schema_evolution's own load_handler node already routed + rejoined
        # target-data as part of the agentic loop -- nothing left to do here.
        routed_count = evolution_result["routed_files"]
        joined_outputs = evolution_result["load_outputs"]
    else:
        run_datagen()
        routed_count = len(scan_once())
        joined_outputs = run_loader()["outputs"]

    print(f"Routed {routed_count} file(s).")
    print("Joined output written to:")
    for kind, path in joined_outputs.items():
        print(f" - {kind}: {path}")

    ml_result = run_ml_demo()
    print("ML report written to:")
    for kind, path in ml_result["report_paths"].items():
        print(f" - {kind}: {path}")


if __name__ == "__main__":
    main()
