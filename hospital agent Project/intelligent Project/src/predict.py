from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .explainability import compute_shap_values, get_explainer, init_explainer
from .preprocessing import ensure_directories, resolve_project_path

_MODEL = None
_SCALER = None
_EXPLAINER = None
_FEATURE_COLUMNS: list[str] | None = None


def _to_feature_frame(values: pd.DataFrame | pd.Series | dict | np.ndarray | list, feature_columns: list[str]) -> pd.DataFrame:
    if isinstance(values, pd.DataFrame):
        return values.loc[:, feature_columns].copy()
    if isinstance(values, pd.Series):
        return pd.DataFrame([values.loc[feature_columns].to_dict()], columns=feature_columns)
    if isinstance(values, dict):
        return pd.DataFrame([values], columns=feature_columns)

    array = np.asarray(values)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    return pd.DataFrame(array, columns=feature_columns)


def load_prediction_artifacts(
    model=None,
    scaler=None,
    explainer=None,
    background_data: pd.DataFrame | np.ndarray | None = None,
    feature_columns: list[str] | None = None,
    model_path: str | Path = "svm_model.pkl",
    scaler_path: str | Path = "scaler.pkl",
    background_path: str | Path = "shap_background.csv",
    features_path: str | Path = "model_features.txt",
) -> dict[str, object]:
    global _MODEL, _SCALER, _EXPLAINER, _FEATURE_COLUMNS

    ensure_directories()

    if feature_columns is None:
        resolved_features = resolve_project_path(features_path, default_dir="outputs")
        feature_columns = [line.strip() for line in resolved_features.read_text(encoding="utf-8").splitlines() if line.strip()]

    _FEATURE_COLUMNS = feature_columns
    _MODEL = model if model is not None else joblib.load(resolve_project_path(model_path, default_dir="outputs"))
    if scaler is not None:
        _SCALER = scaler
    else:
        resolved_scaler = resolve_project_path(scaler_path, default_dir="outputs")
        if not resolved_scaler.exists():
            legacy_scaler = resolve_project_path("svm_scaler.pkl", default_dir="outputs")
            resolved_scaler = legacy_scaler if legacy_scaler.exists() else resolved_scaler
        _SCALER = joblib.load(resolved_scaler)

    if explainer is not None:
        _EXPLAINER = explainer
    else:
        if background_data is None:
            resolved_background = resolve_project_path(background_path, default_dir="outputs")
            background_data = pd.read_csv(resolved_background)
        _EXPLAINER = init_explainer(
            _MODEL,
            _SCALER,
            background_data,
            _FEATURE_COLUMNS,
            save_background_path=None,
        )

    return {
        "model": _MODEL,
        "scaler": _SCALER,
        "explainer": _EXPLAINER,
        "feature_columns": _FEATURE_COLUMNS,
    }


def predict_patient(
    patient_features: pd.DataFrame | pd.Series | dict | np.ndarray | list,
    nsamples: int = 50,
) -> dict[str, object]:
    global _MODEL, _SCALER, _EXPLAINER, _FEATURE_COLUMNS

    if _MODEL is None or _SCALER is None or _FEATURE_COLUMNS is None:
        load_prediction_artifacts()
    if _EXPLAINER is None:
        _EXPLAINER = get_explainer()

    input_frame = _to_feature_frame(patient_features, _FEATURE_COLUMNS)
    scaled_input = _SCALER.transform(input_frame)
    prediction = _MODEL.predict(scaled_input)[0]
    probabilities = _MODEL.predict_proba(scaled_input)[0]

    _, shap_values = compute_shap_values(_EXPLAINER, input_frame, list(_MODEL.classes_), nsamples=nsamples)
    class_index = list(_MODEL.classes_).index(prediction)
    shap_explanation = {
        feature: float(shap_values[0, index, class_index])
        for index, feature in enumerate(_FEATURE_COLUMNS)
    }
    shap_explanation = dict(
        sorted(shap_explanation.items(), key=lambda item: abs(item[1]), reverse=True)
    )

    return {
        "condition": prediction,
        "probability": float(np.max(probabilities)),
        "shap_explanation": shap_explanation,
        "all_probabilities": {
            label: float(probability)
            for label, probability in zip(_MODEL.classes_, probabilities)
        },
    }
