"""CLI: run the genAI data-generation LangGraph program.

Usage: python scripts/run_genai_datagen.py [--count N]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.genai_datagen.graph import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=60, help="Number of products to generate")
    args = parser.parse_args()

    result = run(count=args.count)
    print("Generated files:")
    for f in result["written_files"]:
        print(f" - {f}")


if __name__ == "__main__":
    main()
