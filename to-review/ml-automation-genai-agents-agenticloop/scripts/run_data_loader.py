"""CLI: run the data-loader LangGraph program that joins all target-data
tables into one denormalized dataset.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_loader.graph import run


def main():
    result = run()
    print("Joined output written to:")
    for kind, path in result["outputs"].items():
        print(f" - {kind}: {path}")


if __name__ == "__main__":
    main()
