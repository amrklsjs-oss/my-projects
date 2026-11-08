from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.clustering import plot_cluster_comparison, run_fcm_exploration
from src.explainability import (
    init_explainer,
    run_shap_sanity_check,
    save_global_shap_summary,
    save_individual_waterfall,
)
from src.model import train_svm
from src.predict import load_prediction_artifacts, predict_patient
from src.preprocessing import ensure_directories, resolve_data_path, run_preprocessing_pipeline
from src.risk_labeling import RISK_LABELS, apply_risk_labels


def main() -> None:
    project_root = Path(__file__).resolve().parent
    outputs_dir, docs_dir = ensure_directories()

    data_path = resolve_data_path()
    print(f"Using real dataset: {data_path}")

    cleaned_df, preprocessing_artifacts = run_preprocessing_pipeline(
        data_path=data_path,
        output_dir=outputs_dir,
        docs_dir=docs_dir,
        save_outputs=True,
    )

    labeled_df, class_distribution = apply_risk_labels(
        cleaned_df,
        output_path=outputs_dir / "labeled_healthcare.csv",
        save_output=True,
        print_distribution=True,
    )

    clustered_df, clustering_artifacts = run_fcm_exploration(
        labeled_df,
        output_dir=outputs_dir,
        labeled_output_name="labeled_healthcare.csv",
        save_outputs=True,
    )
    cluster_plot_path = plot_cluster_comparison(clustered_df, output_path=outputs_dir / "cluster_plot.png")

    training_artifacts = train_svm(
        clustered_df,
        output_dir=outputs_dir,
        save_artifacts=True,
    )

    model = training_artifacts["model"]
    scaler = training_artifacts["scaler"]
    feature_columns = training_artifacts["feature_columns"]
    X_test = training_artifacts["X_test"]

    explainer = init_explainer(
        model,
        scaler,
        training_artifacts["shap_background"],
        feature_columns,
        background_size=75,
        save_background_path=outputs_dir / "shap_background.csv",
    )

    shap_summary_path = save_global_shap_summary(
        explainer,
        X_test.sample(min(50, len(X_test)), random_state=42),
        list(model.classes_),
        output_path=outputs_dir / "shap_summary.png",
        nsamples=50,
    )

    sample_patient = X_test.iloc[[0]]
    predicted_label = model.predict(scaler.transform(sample_patient))[0]
    shap_waterfall_path = save_individual_waterfall(
        explainer,
        sample_patient,
        predicted_label,
        list(model.classes_),
        output_path=outputs_dir / "shap_waterfall.png",
        nsamples=50,
    )

    shap_check = run_shap_sanity_check(
        explainer,
        sample_patient,
        list(model.classes_),
        nsamples=25,
    )

    load_prediction_artifacts(
        model=model,
        scaler=scaler,
        explainer=explainer,
        background_data=training_artifacts["shap_background"],
        feature_columns=feature_columns,
        model_path=outputs_dir / "svm_model.pkl",
        scaler_path=outputs_dir / "scaler.pkl",
        background_path=outputs_dir / "shap_background.csv",
        features_path=outputs_dir / "model_features.txt",
    )
    prediction_example = predict_patient(sample_patient.iloc[0].to_dict(), nsamples=25)
    (outputs_dir / "prediction_example.json").write_text(json.dumps(prediction_example, indent=2), encoding="utf-8")

    required_outputs = [
        outputs_dir / "svm_model.pkl",
        outputs_dir / "labeled_healthcare.csv",
        outputs_dir / "scaler.pkl",
        outputs_dir / "confusion_matrix.png",
        outputs_dir / "shap_summary.png",
    ]

    missing_outputs = [str(path) for path in required_outputs if not path.exists()]
    if missing_outputs:
        raise FileNotFoundError(f"Pipeline completed but required outputs are missing: {missing_outputs}")

    metrics = json.loads((outputs_dir / "model_metrics.json").read_text(encoding="utf-8"))

    print("\nClass distribution (Low / Medium / High):")
    for label in RISK_LABELS:
        print(f"{label}: {metrics['class_distribution'][label]}")

    print(f"\nAccuracy: {metrics['accuracy']:.4f}")
    print(f"F1-score (weighted): {metrics['f1_weighted']:.4f}")

    print("\nConfirmation of no leakage:")
    print(preprocessing_artifacts["no_leakage_check"])
    print("Model scaling is applied once in Person 3 and saved as outputs/scaler.pkl.")

    print("\nGenerated output files:")
    for path in [
        outputs_dir / "cleaned_healthcare.csv",
        outputs_dir / "labeled_healthcare.csv",
        outputs_dir / "scaler.pkl",
        outputs_dir / "svm_model.pkl",
        outputs_dir / "confusion_matrix.png",
        outputs_dir / "shap_summary.png",
        outputs_dir / "shap_waterfall.png",
        outputs_dir / "prediction_example.json",
        cluster_plot_path,
    ]:
        print(path)

    print("\nSHAP working confirmation:")
    print(shap_check["status"])
    print(f"SHAP summary: {shap_summary_path}")
    print(f"SHAP waterfall: {shap_waterfall_path}")

    print("\nPIPELINE SUCCESSFULLY EXECUTED")


if __name__ == "__main__":
    main()
