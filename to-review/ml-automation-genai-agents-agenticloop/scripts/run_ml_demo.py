"""CLI: train + evaluate the reorder-risk ML demo over the latest joined
dataset in target-data/joined/. Run scripts/run_data_loader.py (or
run_pipeline_once.py) first so a joined dataset exists.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ml_insights.graph import run


def main():
    result = run()
    print("Report written to:")
    for kind, path in result["report_paths"].items():
        print(f" - {kind}: {path}")


if __name__ == "__main__":
    main()
