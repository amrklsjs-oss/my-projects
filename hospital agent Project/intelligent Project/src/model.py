from __future__ import annotations

from pathlib import Path
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .preprocessing import CLUSTERING_FEATURES, RANDOM_STATE, ensure_directories
from .risk_labeling import RISK_LABELS, class_distribution


def _validate_training_frame(df: pd.DataFrame, feature_cols: list[str], target_col: str) -> None:
    missing_columns = [column for column in feature_cols + [target_col] if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Training data is missing required columns: {missing_columns}")


def _validate_class_coverage(y: pd.Series) -> pd.Series:
    distribution = class_distribution(y)
    missing_classes = distribution[distribution == 0].index.tolist()
    if missing_classes:
        raise ValueError(
            "SVM training requires every risk class to exist after Person 2 labeling. "
            f"Missing classes: {missing_classes}\nCurrent distribution:\n{distribution}"
        )
    too_small = distribution[distribution < 2].index.tolist()
    if too_small:
        raise ValueError(
            "Each risk class needs at least two samples before the stratified Person 3 split. "
            f"Too small: {too_small}\nCurrent distribution:\n{distribution}"
        )
    return distribution


def _save_confusion_matrix(
    y_true: pd.Series,
    y_pred: np.ndarray,
    output_path: Path,
) -> Path:
    matrix = confusion_matrix(y_true, y_pred, labels=RISK_LABELS)
    figure, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(matrix, interpolation="nearest", cmap="Blues")
    axis.set_title("Confusion Matrix - Patient Risk Prediction")
    figure.colorbar(image, ax=axis)
    axis.set_xticks(np.arange(len(RISK_LABELS)), RISK_LABELS, rotation=45)
    axis.set_yticks(np.arange(len(RISK_LABELS)), RISK_LABELS)
    axis.set_ylabel("True Label")
    axis.set_xlabel("Predicted Label")

    for row in range(len(RISK_LABELS)):
        for column in range(len(RISK_LABELS)):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center", color="red")

    figure.tight_layout()
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return output_path


def train_svm(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    target_col: str = "risk_category",
    output_dir: str | Path = "outputs",
    save_artifacts: bool = True,
    test_size: float = 0.2,
) -> dict[str, object]:
    active_features = feature_cols or CLUSTERING_FEATURES
    _validate_training_frame(df, active_features, target_col)

    X = df[active_features].copy()
    y = df[target_col].astype(str).copy()

    distribution = _validate_class_coverage(y)
    print("Model class distribution:")
    print(distribution)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    min_train_class_count = int(y_train.value_counts().min())
    if min_train_class_count < 2:
        raise ValueError(
            "Training split does not leave enough samples per class for cross-validation. "
            f"Minimum class count in training split: {min_train_class_count}"
        )
    cv_folds = min(3, min_train_class_count)

    param_dist = {
        "C": [0.1, 1, 10, 50],
        "gamma": ["scale", 0.01, 0.1, 1.0],
        "kernel": ["rbf"],
    }
    search = RandomizedSearchCV(
        estimator=SVC(class_weight="balanced", probability=True, random_state=RANDOM_STATE),
        param_distributions=param_dist,
        n_iter=6,
        cv=cv_folds,
        scoring="f1_weighted",
        n_jobs=1,
        random_state=RANDOM_STATE,
    )
    search.fit(X_train_scaled, y_train)

    best_params = search.best_params_
    model = SVC(
        **best_params,
        class_weight="balanced",
        probability=True,
        random_state=RANDOM_STATE,
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1-score (weighted): {weighted_f1:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, labels=RISK_LABELS, zero_division=0))

    output_path, _ = ensure_directories(output_dir=output_dir)
    confusion_matrix_path = output_path / "confusion_matrix.png"
    _save_confusion_matrix(y_test, y_pred, confusion_matrix_path)

    shap_background = X_train.sample(min(75, len(X_train)), random_state=RANDOM_STATE).reset_index(drop=True)

    artifacts: dict[str, object] = {
        "model": model,
        "scaler": scaler,
        "best_params": best_params,
        "feature_columns": active_features,
        "X_train": X_train.reset_index(drop=True),
        "X_test": X_test.reset_index(drop=True),
        "y_train": y_train.reset_index(drop=True),
        "y_test": y_test.reset_index(drop=True),
        "y_pred": y_pred,
        "accuracy": accuracy,
        "f1_weighted": weighted_f1,
        "class_distribution": distribution,
        "shap_background": shap_background,
        "confusion_matrix_path": confusion_matrix_path,
    }

    if save_artifacts:
        joblib.dump(model, output_path / "svm_model.pkl")
        joblib.dump(scaler, output_path / "scaler.pkl")
        joblib.dump(scaler, output_path / "svm_scaler.pkl")
        shap_background.to_csv(output_path / "shap_background.csv", index=False)
        (output_path / "model_features.txt").write_text("\n".join(active_features), encoding="utf-8")
        metrics_payload = {
            "accuracy": accuracy,
            "f1_weighted": weighted_f1,
            "class_distribution": {label: int(distribution[label]) for label in RISK_LABELS},
            "best_params": best_params,
        }
        (output_path / "model_metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
        artifacts["model_path"] = output_path / "svm_model.pkl"
        artifacts["scaler_path"] = output_path / "scaler.pkl"
        artifacts["legacy_scaler_path"] = output_path / "svm_scaler.pkl"
        artifacts["background_path"] = output_path / "shap_background.csv"
        artifacts["metrics_path"] = output_path / "model_metrics.json"

    return artifacts
