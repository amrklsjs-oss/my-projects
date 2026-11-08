from __future__ import annotations

from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

RANDOM_STATE = 42
PATIENT_ID_COL = "PATIENT_ID"
TIMESTAMP_COL = "TIMESTAMP"
HOSPITAL_ID_COL = "HOSPITAL_ID"
BASE_RISK_FEATURES = [
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "oxygen_saturation",
    "temperature",
]
CLUSTERING_FEATURES = BASE_RISK_FEATURES + ["wait_time"]
TIME_FEATURES = ["hour", "day", "week", "hour_sin", "hour_cos", "day_sin", "day_cos"]
LAG_SOURCE_FEATURES = ["heart_rate", "oxygen_saturation", "systolic_bp"]
ENCODE_COLUMNS = ["gender", "admission_type"]
RAW_FILE_CANDIDATES = ["healthcare_agent_datasett.csv", "healthcare_agent_dataset.csv"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_directories(output_dir: str | Path = "outputs", docs_dir: str | Path = "docs") -> tuple[Path, Path]:
    output_path = project_root() / Path(output_dir)
    docs_path = project_root() / Path(docs_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    docs_path.mkdir(parents=True, exist_ok=True)
    return output_path, docs_path


def resolve_project_path(path: str | Path, default_dir: str = "outputs") -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if candidate.parts and candidate.parts[0] in {"outputs", "docs", "src", "notebooks"}:
        return project_root() / candidate
    return project_root() / default_dir / candidate


def resolve_data_path(
    data_path: str | Path | None = None,
    extra_candidates: Iterable[str | Path] | None = None,
) -> Path:
    candidates: list[Path] = []
    if data_path is not None:
        candidates.append(Path(data_path))

    for name in RAW_FILE_CANDIDATES:
        candidates.extend(
            [
                Path(name),
                project_root() / name,
                project_root() / "notebooks" / name,
            ]
        )

    if extra_candidates is not None:
        candidates.extend(Path(candidate) for candidate in extra_candidates)

    for candidate in candidates:
        resolved = candidate.expanduser().resolve() if candidate.is_absolute() else (project_root() / candidate).resolve()
        if resolved.exists():
            return resolved

    searched = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "Could not find the healthcare dataset. Set `data_path` explicitly or place the CSV in the project root.\n"
        f"Searched candidates:\n{searched}"
    )


def load_raw_data(data_path: str | Path | None = None) -> pd.DataFrame:
    resolved_path = resolve_data_path(data_path)
    df = pd.read_csv(resolved_path)
    print(f"Loaded raw dataset from {resolved_path}")
    print(f"Raw shape: {df.shape}")
    return df


def write_initial_report(df: pd.DataFrame, docs_dir: str | Path = "docs") -> Path:
    _, docs_path = ensure_directories(docs_dir=docs_dir)
    report_path = docs_path / "initial_report.md"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# Initial Data Report\n\n")
        handle.write(f"Shape: {df.shape}\n\n")
        handle.write(df.describe(include="all").to_string())
    return report_path


def _sort_for_patient_time(df: pd.DataFrame) -> pd.DataFrame:
    sort_columns = [column for column in [PATIENT_ID_COL, TIMESTAMP_COL] if column in df.columns]
    if sort_columns:
        return df.sort_values(sort_columns).reset_index(drop=True)
    return df.reset_index(drop=True)


def _infer_column_groups(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    protected_columns = {PATIENT_ID_COL, HOSPITAL_ID_COL}
    numerical_cols = [
        column
        for column in df.select_dtypes(include=np.number).columns
        if column not in protected_columns
    ]
    categorical_cols = [
        column
        for column in df.select_dtypes(include=["object", "category"]).columns
        if column != TIMESTAMP_COL
    ]
    return numerical_cols, categorical_cols


def _fill_missing_values(df: pd.DataFrame, numerical_cols: list[str], categorical_cols: list[str]) -> pd.DataFrame:
    cleaned = df.copy()
    if TIMESTAMP_COL in cleaned.columns:
        cleaned[TIMESTAMP_COL] = pd.to_datetime(cleaned[TIMESTAMP_COL], errors="coerce")
    cleaned = _sort_for_patient_time(cleaned)

    if PATIENT_ID_COL in cleaned.columns:
        for column in numerical_cols:
            cleaned[column] = cleaned.groupby(PATIENT_ID_COL)[column].transform(
                lambda series: series.interpolate(limit_direction="both")
            )

        for column in categorical_cols:
            mode_series = cleaned[column].mode(dropna=True)
            fallback = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            cleaned[column] = cleaned.groupby(PATIENT_ID_COL)[column].transform(lambda series: series.ffill().bfill())
            cleaned[column] = cleaned[column].fillna(fallback)
    else:
        for column in numerical_cols:
            cleaned[column] = cleaned[column].interpolate(limit_direction="both")
        for column in categorical_cols:
            mode_series = cleaned[column].mode(dropna=True)
            fallback = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            cleaned[column] = cleaned[column].fillna(fallback)

    return cleaned


def _severity_score(row: pd.Series) -> int:
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


def add_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    engineered = df.copy()
    if TIMESTAMP_COL in engineered.columns:
        engineered[TIMESTAMP_COL] = pd.to_datetime(engineered[TIMESTAMP_COL], errors="coerce")
        engineered["hour"] = engineered[TIMESTAMP_COL].dt.hour
        engineered["day"] = engineered[TIMESTAMP_COL].dt.day
        engineered["week"] = engineered[TIMESTAMP_COL].dt.isocalendar().week.astype("Int64")

        engineered["hour_sin"] = np.sin(2 * np.pi * engineered["hour"].fillna(0) / 24)
        engineered["hour_cos"] = np.cos(2 * np.pi * engineered["hour"].fillna(0) / 24)
        engineered["day_sin"] = np.sin(2 * np.pi * engineered["day"].fillna(0) / 31)
        engineered["day_cos"] = np.cos(2 * np.pi * engineered["day"].fillna(0) / 31)

    missing_risk_columns = [column for column in BASE_RISK_FEATURES if column not in engineered.columns]
    if missing_risk_columns:
        raise ValueError(f"Missing required columns for severity score: {missing_risk_columns}")

    engineered["severity_score"] = engineered.apply(_severity_score, axis=1)

    if PATIENT_ID_COL in engineered.columns:
        for column in LAG_SOURCE_FEATURES:
            if column in engineered.columns:
                lag_values = engineered.groupby(PATIENT_ID_COL)[column].shift(1)
                engineered[f"{column}_lag1"] = lag_values.fillna(engineered[column])
    else:
        for column in LAG_SOURCE_FEATURES:
            if column in engineered.columns:
                engineered[f"{column}_lag1"] = engineered[column]

    return engineered


def encode_categorical_columns(
    df: pd.DataFrame,
    output_dir: str | Path = "outputs",
) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    output_path, _ = ensure_directories(output_dir=output_dir)
    encoded = df.copy()
    encoders: dict[str, LabelEncoder] = {}
    for column in ENCODE_COLUMNS:
        if column in encoded.columns:
            encoder = LabelEncoder()
            encoded[f"{column}_encoded"] = encoder.fit_transform(encoded[column].astype(str))
            encoders[column] = encoder

    if encoders:
        joblib.dump(encoders, output_path / "encoder.pkl")
    return encoded, encoders


def write_cleaning_log(
    missing_before: pd.Series,
    missing_after: pd.Series,
    docs_dir: str | Path = "docs",
) -> Path:
    _, docs_path = ensure_directories(docs_dir=docs_dir)
    log_path = docs_path / "cleaning_log.md"
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("# Cleaning Log\n\n")
        handle.write("## Missing Before\n")
        handle.write(missing_before.to_string())
        handle.write("\n\n## Missing After\n")
        handle.write(missing_after.to_string())
        handle.write("\n\n## Steps\n")
        handle.write("- Interpolation is applied per patient on numerical columns.\n")
        handle.write("- Categorical values are forward/back filled per patient, then mode-imputed.\n")
        handle.write("- Time-based, lag, and severity features are created once in preprocessing.\n")
        handle.write("- No scaling is applied in preprocessing to prevent leakage into Person 2.\n")
    return log_path


def save_cleaned_outputs(
    df: pd.DataFrame,
    output_dir: str | Path = "outputs",
) -> dict[str, Path]:
    output_path, _ = ensure_directories(output_dir=output_dir)
    cleaned_path = output_path / "cleaned_healthcare.csv"
    df.to_csv(cleaned_path, index=False)

    feature_list_path = output_path / "cleaned_columns.txt"
    feature_list_path.write_text("\n".join(df.columns.astype(str)), encoding="utf-8")

    if HOSPITAL_ID_COL in df.columns and TIMESTAMP_COL in df.columns:
        ts_columns = [column for column in [TIMESTAMP_COL, HOSPITAL_ID_COL, *BASE_RISK_FEATURES, "severity_score"] if column in df.columns]
        for hospital_id, hospital_df in df.groupby(HOSPITAL_ID_COL):
            hospital_df = hospital_df[ts_columns].sort_values(TIMESTAMP_COL)
            hospital_df.to_csv(output_path / f"timeseries_{hospital_id}.csv", index=False)

    return {
        "cleaned_data": cleaned_path,
        "column_list": feature_list_path,
    }


def run_preprocessing_pipeline(
    data_path: str | Path | None = None,
    output_dir: str | Path = "outputs",
    docs_dir: str | Path = "docs",
    save_outputs: bool = True,
) -> tuple[pd.DataFrame, dict[str, object]]:
    raw_df = load_raw_data(data_path)
    write_initial_report(raw_df, docs_dir=docs_dir)

    missing_before = raw_df.isnull().sum()
    numerical_cols, categorical_cols = _infer_column_groups(raw_df)
    cleaned_df = _fill_missing_values(raw_df, numerical_cols, categorical_cols)
    cleaned_df = add_feature_engineering(cleaned_df)
    cleaned_df, encoders = encode_categorical_columns(cleaned_df, output_dir=output_dir)
    missing_after = cleaned_df.isnull().sum()

    artifacts: dict[str, object] = {
        "missing_before": missing_before,
        "missing_after": missing_after,
        "encoders": encoders,
        "numerical_columns": numerical_cols,
        "categorical_columns": categorical_cols,
        "no_leakage_check": "Verified: preprocessing does not call any scaler. Cleaned data stays in original units.",
    }

    if save_outputs:
        output_paths = save_cleaned_outputs(cleaned_df, output_dir=output_dir)
        artifacts.update(output_paths)
        artifacts["cleaning_log"] = write_cleaning_log(missing_before, missing_after, docs_dir=docs_dir)

    print("Missing values before cleaning:")
    print(missing_before[missing_before > 0] if (missing_before > 0).any() else "No missing values detected.")
    print("\nMissing values after cleaning:")
    print(missing_after[missing_after > 0] if (missing_after > 0).any() else "No missing values remain.")
    print("\nLeakage check:")
    print(artifacts["no_leakage_check"])

    return cleaned_df, artifacts
