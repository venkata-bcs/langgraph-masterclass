"""LangGraph program: train + evaluate the reorder-risk classifier over the
latest joined dataset, and write a metrics report + at-risk product
predictions.
"""
from __future__ import annotations

import json
from typing import TypedDict

import joblib
from langgraph.graph import END, StateGraph

from src.common import paths
from src.ml_insights import features
from src.ml_insights import model as ml_model


class MLState(TypedDict, total=False):
    dataset: object
    X: object
    y: object
    result: dict
    report_paths: dict


def load_joined_data(state: MLState) -> MLState:
    state["dataset"] = features.load_dataset()
    return state


def engineer_features(state: MLState) -> MLState:
    X, y = features.split_features_label(state["dataset"])
    state["X"] = X
    state["y"] = y
    return state


def train_model(state: MLState) -> MLState:
    state["result"] = ml_model.train_and_evaluate(state["X"], state["y"])
    return state


def evaluate_model(state: MLState) -> MLState:
    metrics = state["result"]["metrics"]
    print(
        f"ML demo -- reorder-risk classifier: accuracy={metrics['accuracy']} "
        f"(train={metrics['train_rows']} rows, test={metrics['test_rows']} rows)"
    )
    return state


def write_report(state: MLState) -> MLState:
    out_dir = paths.TARGET_DATA_DIR / "ml"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = paths.timestamp()
    result = state["result"]

    metrics_path = out_dir / f"{ts}_metrics.json"
    metrics_path.write_text(json.dumps(result["metrics"], indent=2), encoding="utf-8")

    model_path = out_dir / f"{ts}_model.joblib"
    joblib.dump(result["pipeline"], model_path)

    predictions = result["X_test"].copy()
    predictions["actual_reorder_risk"] = result["y_test"].values
    predictions["predicted_reorder_risk"] = result["y_pred"]
    predictions_path = out_dir / f"{ts}_predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    state["report_paths"] = {
        "metrics": str(metrics_path),
        "model": str(model_path),
        "predictions": str(predictions_path),
    }
    return state


def build_graph():
    graph = StateGraph(MLState)
    graph.add_node("load_joined_data", load_joined_data)
    graph.add_node("engineer_features", engineer_features)
    graph.add_node("train_model", train_model)
    graph.add_node("evaluate_model", evaluate_model)
    graph.add_node("write_report", write_report)

    graph.set_entry_point("load_joined_data")
    graph.add_edge("load_joined_data", "engineer_features")
    graph.add_edge("engineer_features", "train_model")
    graph.add_edge("train_model", "evaluate_model")
    graph.add_edge("evaluate_model", "write_report")
    graph.add_edge("write_report", END)
    return graph.compile()


def run() -> MLState:
    app = build_graph()
    return app.invoke({})
