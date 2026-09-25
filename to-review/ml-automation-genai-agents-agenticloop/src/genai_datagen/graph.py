"""LangGraph program: generate schema-driven products/inventory (+ any
evolved tables) synthetic data and drop timestamped CSVs into source-data/
for the automation router to pick up.
"""
from __future__ import annotations

from typing import TypedDict

import pandas as pd
from langgraph.graph import END, StateGraph

from src.common import paths
from src.common.schema_registry import parse_schema_registry
from src.genai_datagen import generator


class DataGenState(TypedDict, total=False):
    count: int
    tables: dict
    dataframes: dict
    run_ts: str
    written_files: list


def load_schema(state: DataGenState) -> DataGenState:
    registry_path = paths.PROJECT_ROOT / "config" / "schema_registry.yaml"
    state["tables"] = parse_schema_registry(registry_path)
    state["run_ts"] = paths.timestamp()
    return state


def generate_core_tables(state: DataGenState) -> DataGenState:
    tables = state["tables"]
    count = state.get("count", 60)
    dataframes: dict = {}

    products_rows = generator.generate_products(count, tables["products"].columns)
    dataframes["products"] = pd.DataFrame(products_rows)

    product_records = dataframes["products"][["product_id", "category"]].to_dict("records")
    inventory_rows = generator.generate_inventory(product_records, tables["inventory"].columns)
    dataframes["inventory"] = pd.DataFrame(inventory_rows)

    state["dataframes"] = dataframes
    return state


def generate_evolved_tables(state: DataGenState) -> DataGenState:
    tables = state["tables"]
    dataframes = state["dataframes"]
    product_ids = dataframes["products"]["product_id"].tolist()

    category_schema = tables.get("product-category")
    if category_schema and category_schema.active:
        rows = generator.generate_product_category(category_schema.columns)
        dataframes["product-category"] = pd.DataFrame(rows)

    prices_schema = tables.get("product-prices-month-year")
    if prices_schema and prices_schema.active:
        rows = generator.generate_product_prices_month_year(product_ids, prices_schema.columns)
        dataframes["product-prices-month-year"] = pd.DataFrame(rows)

    suppliers_schema = tables.get("suppliers")
    if suppliers_schema and suppliers_schema.active:
        rows = generator.generate_suppliers(suppliers_schema.columns)
        dataframes["suppliers"] = pd.DataFrame(rows)

    return state


def write_outputs(state: DataGenState) -> DataGenState:
    paths.SOURCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for table_name, df in state["dataframes"].items():
        out_path = paths.SOURCE_DATA_DIR / f"{state['run_ts']}_{table_name}.csv"
        df.to_csv(out_path, index=False)
        written.append(str(out_path))
    state["written_files"] = written
    return state


def build_graph():
    graph = StateGraph(DataGenState)
    graph.add_node("load_schema", load_schema)
    graph.add_node("generate_core_tables", generate_core_tables)
    graph.add_node("generate_evolved_tables", generate_evolved_tables)
    graph.add_node("write_outputs", write_outputs)

    graph.set_entry_point("load_schema")
    graph.add_edge("load_schema", "generate_core_tables")
    graph.add_edge("generate_core_tables", "generate_evolved_tables")
    graph.add_edge("generate_evolved_tables", "write_outputs")
    graph.add_edge("write_outputs", END)
    return graph.compile()


def run(count: int = 60) -> DataGenState:
    app = build_graph()
    return app.invoke({"count": count})
