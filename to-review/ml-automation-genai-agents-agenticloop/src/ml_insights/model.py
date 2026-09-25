"""Trains and evaluates a small reorder-risk classifier -- this is the
project's 'ML' demo. Deliberately simple (RandomForest over one-hot
categorical + numeric features) so the pipeline mechanics -- train/test
split, evaluation metrics, a persisted model + report -- stay the point,
not model sophistication.
"""
from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

_CATEGORICAL = ["category", "supplier", "warehouse"]


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), _CATEGORICAL)],
        remainder="passthrough",
    )
    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)),
    ])


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> dict:
    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    metrics = {
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
    }
    return {"pipeline": pipeline, "metrics": metrics, "X_test": X_test, "y_test": y_test, "y_pred": y_pred}
