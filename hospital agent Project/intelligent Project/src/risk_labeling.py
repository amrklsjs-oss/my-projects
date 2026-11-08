from __future__ import annotations

from pathlib import Path

import pandas as pd

from .preprocessing import BASE_RISK_FEATURES, resolve_project_path

RISK_LABELS = ["Low", "Medium", "High"]


def calculate_risk_score(row: pd.Series) -> int:
    score = 0
    if row["heart_rate"] > 100:
        score += 1
    if row["systolic_bp"] > 140:
        score += 1
    if row["diastolic_bp"] > 90:
        score += 1
    if row["oxygen_saturation"] < 92:
        score += 1
    if row["temperature"] > 38:
        score += 1
    return score


def risk_score_to_category(score: int) -> str:
    if score >= 3:
        return "High"
    if score >= 1:
        return "Medium"
    return "Low"


def class_distribution(series: pd.Series) -> pd.Series:
    return series.value_counts().reindex(RISK_LABELS, fill_value=0)


def apply_risk_labels(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    save_output: bool = True,
    print_distribution: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    missing_columns = [column for column in BASE_RISK_FEATURES if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Risk labeling requires unscaled medical features: {missing_columns}")

    labeled_df = df.copy()
    labeled_df["risk_score"] = labeled_df[BASE_RISK_FEATURES].apply(calculate_risk_score, axis=1)
    labeled_df["risk_category"] = pd.Categorical(
        labeled_df["risk_score"].map(risk_score_to_category),
        categories=RISK_LABELS,
        ordered=True,
    )

    distribution = class_distribution(labeled_df["risk_category"])
    if print_distribution:
        print("Risk class distribution:")
        print(distribution)

    if save_output:
        resolved_output = Path(output_path) if output_path is not None else Path("labeled_healthcare.csv")
        resolved_output = resolve_project_path(resolved_output, default_dir="outputs")
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        labeled_df.to_csv(resolved_output, index=False)

    return labeled_df, distribution
