import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from src.evaluate import evaluate_model


def test_evaluate_model_returns_correct_metrics():
    y_true = np.array([0, 1, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 1, 0])

    result = evaluate_model(y_true, y_pred)

    assert result["accuracy"] == accuracy_score(y_true, y_pred)
    assert result["precision"] == precision_score(y_true, y_pred, average="macro")
    assert result["recall"] == recall_score(y_true, y_pred, average="macro")
    assert result["f1_score"] == f1_score(y_true, y_pred, average="macro")
