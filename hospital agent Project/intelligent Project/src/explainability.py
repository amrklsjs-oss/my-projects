from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from .preprocessing import RANDOM_STATE, resolve_project_path

_EXPLAINER = None
_EXPLAINER_SIGNATURE: tuple[int, int, tuple[str, ...]] | None = None
_FEATURE_COLUMNS: list[str] | None = None


def _to_feature_frame(values: pd.DataFrame | pd.Series | dict | np.ndarray | list, feature_columns: Iterable[str]) -> pd.DataFrame:
    columns = list(feature_columns)
    if isinstance(values, pd.DataFrame):
        return values.loc[:, columns].copy()
    if isinstance(values, pd.Series):
        return pd.DataFrame([values.loc[columns].to_dict()], columns=columns)
    if isinstance(values, dict):
        return pd.DataFrame([values], columns=columns)

    array = np.asarray(values)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    return pd.DataFrame(array, columns=columns)


def _normalize_shap_values(
    shap_values: object,
    n_samples: int,
    n_features: int,
    n_classes: int,
) -> np.ndarray:
    if isinstance(shap_values, list):
        return np.stack([np.asarray(class_values) for class_values in shap_values], axis=2)

    values = np.asarray(shap_values)
    if values.ndim == 2:
        return values[:, :, np.newaxis]
    if values.ndim != 3:
        raise ValueError(f"Unexpected SHAP output shape: {values.shape}")
    if values.shape == (n_samples, n_features, n_classes):
        return values
    if values.shape == (n_classes, n_samples, n_features):
        return np.transpose(values, (1, 2, 0))
    if values.shape == (n_samples, n_classes, n_features):
        return np.transpose(values, (0, 2, 1))
    raise ValueError(f"Unable to normalize SHAP values with shape {values.shape}")


def init_explainer(
    model,
    scaler,
    background_data: pd.DataFrame | np.ndarray,
    feature_columns: list[str],
    background_size: int = 75,
    random_state: int = RANDOM_STATE,
    save_background_path: str | Path | None = "shap_background.csv",
):
    global _EXPLAINER, _EXPLAINER_SIGNATURE, _FEATURE_COLUMNS

    signature = (id(model), id(scaler), tuple(feature_columns))
    if _EXPLAINER is not None and _EXPLAINER_SIGNATURE == signature:
        print("Reusing cached SHAP explainer.")
        return _EXPLAINER

    background_frame = _to_feature_frame(background_data, feature_columns)
    background_frame = background_frame.sample(
        min(background_size, len(background_frame)),
        random_state=random_state,
    ).reset_index(drop=True)

    def predict_proba_from_raw(raw_values):
        raw_frame = _to_feature_frame(raw_values, feature_columns)
        return model.predict_proba(scaler.transform(raw_frame))

    _EXPLAINER = shap.KernelExplainer(predict_proba_from_raw, background_frame)
    _EXPLAINER_SIGNATURE = signature
    _FEATURE_COLUMNS = list(feature_columns)

    if save_background_path is not None:
        output_path = resolve_project_path(save_background_path, default_dir="outputs")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        background_frame.to_csv(output_path, index=False)

    print(f"Initialized SHAP explainer once with {len(background_frame)} background samples.")
    return _EXPLAINER


def get_explainer():
    if _EXPLAINER is None or _FEATURE_COLUMNS is None:
        raise RuntimeError("SHAP explainer has not been initialized. Call `init_explainer` first.")
    return _EXPLAINER


def compute_shap_values(
    explainer,
    samples: pd.DataFrame | pd.Series | dict | np.ndarray | list,
    class_names: list[str],
    nsamples: int = 100,
) -> tuple[pd.DataFrame, np.ndarray]:
    if _FEATURE_COLUMNS is None:
        raise RuntimeError("Feature columns are not cached. Initialize the SHAP explainer first.")

    sample_frame = _to_feature_frame(samples, _FEATURE_COLUMNS)
    raw_shap_values = explainer.shap_values(sample_frame, nsamples=nsamples)
    expected_values = explainer.expected_value
    n_classes = len(class_names) if len(class_names) > 1 else 1
    normalized = _normalize_shap_values(raw_shap_values, len(sample_frame), len(_FEATURE_COLUMNS), n_classes)
    return sample_frame, normalized


def save_global_shap_summary(
    explainer,
    samples: pd.DataFrame | np.ndarray,
    class_names: list[str],
    output_path: str | Path = "shap_summary.png",
    nsamples: int = 100,
) -> Path:
    sample_frame, shap_values = compute_shap_values(explainer, samples, class_names, nsamples=nsamples)
    importance = np.mean(np.abs(shap_values), axis=(0, 2))
    ranking = pd.Series(importance, index=sample_frame.columns).sort_values(ascending=True)

    figure, axis = plt.subplots(figsize=(10, 6))
    axis.barh(ranking.index, ranking.values, color="steelblue")
    axis.set_title("Global SHAP Feature Importance")
    axis.set_xlabel("Mean |SHAP value|")
    axis.set_ylabel("Feature")
    figure.tight_layout()

    resolved_output = resolve_project_path(output_path, default_dir="outputs")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(resolved_output, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return resolved_output


def save_individual_waterfall(
    explainer,
    sample: pd.DataFrame | pd.Series | dict | np.ndarray | list,
    predicted_label: str,
    class_names: list[str],
    output_path: str | Path = "shap_waterfall.png",
    nsamples: int = 50,
) -> Path:
    sample_frame, shap_values = compute_shap_values(explainer, sample, class_names, nsamples=nsamples)
    class_index = class_names.index(predicted_label)
    explanation = shap.Explanation(
        values=shap_values[0, :, class_index],
        base_values=np.asarray(explainer.expected_value)[class_index],
        data=sample_frame.iloc[0].to_numpy(),
        feature_names=sample_frame.columns.tolist(),
    )

    plt.figure(figsize=(10, 6))
    shap.waterfall_plot(explanation, show=False)
    plt.tight_layout()

    resolved_output = resolve_project_path(output_path, default_dir="outputs")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(resolved_output, dpi=150, bbox_inches="tight")
    plt.close()
    return resolved_output


def run_shap_sanity_check(
    explainer,
    samples: pd.DataFrame | np.ndarray,
    class_names: list[str],
    nsamples: int = 25,
) -> dict[str, object]:
    sample_frame, shap_values = compute_shap_values(explainer, samples, class_names, nsamples=nsamples)
    result = {
        "rows_explained": len(sample_frame),
        "feature_count": sample_frame.shape[1],
        "class_count": shap_values.shape[2],
        "status": "SHAP working test passed",
    }
    print(result["status"])
    print(result)
    return result
