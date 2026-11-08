from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


FEATURE_COLUMNS = [
    "failed_logins",
    "unique_ports",
    "bytes_out",
    "process_count",
    "privilege_score",
    "off_hours",
    "asset_criticality",
]


@dataclass
class DetectionResult:
    anomaly_score: float
    attack_type: str
    severity: str
    confidence: float
    explanation: str


class RuleBasedDetectionModel:
    """Small explainable fallback model used when scikit-learn is unavailable."""

    def predict_one(self, row: Dict[str, float]) -> DetectionResult:
        failed_logins = float(row.get("failed_logins", 0))
        unique_ports = float(row.get("unique_ports", 0))
        bytes_out = float(row.get("bytes_out", 0))
        process_count = float(row.get("process_count", 0))
        privilege_score = float(row.get("privilege_score", 0))
        off_hours = float(row.get("off_hours", 0))
        asset_criticality = float(row.get("asset_criticality", 0))

        if failed_logins >= 12:
            attack_type = "Brute Force"
            explanation = "Many failed logins from the same source indicate credential guessing."
        elif unique_ports >= 20:
            attack_type = "Port Scan"
            explanation = "A high number of unique destination ports indicates reconnaissance."
        elif bytes_out >= 800:
            attack_type = "Data Exfiltration"
            explanation = "Large outbound traffic from a critical asset suggests data staging or exfiltration."
        elif process_count >= 35 and privilege_score >= 7:
            attack_type = "Privilege Escalation"
            explanation = "Unusual process activity with high privilege usage suggests escalation."
        elif off_hours and asset_criticality >= 8:
            attack_type = "Suspicious Access"
            explanation = "Critical asset access outside normal hours is abnormal."
        else:
            attack_type = "Benign"
            explanation = "The event stays close to the expected baseline."

        anomaly_score = min(
            1.0,
            failed_logins / 25
            + unique_ports / 80
            + bytes_out / 3000
            + process_count / 120
            + privilege_score / 40
            + off_hours * 0.08
            + asset_criticality / 80,
        )
        confidence = 0.55 if attack_type == "Benign" else min(0.96, 0.62 + anomaly_score / 3)
        severity = severity_from_score(anomaly_score, attack_type)
        return DetectionResult(
            anomaly_score=round(anomaly_score, 3),
            attack_type=attack_type,
            severity=severity,
            confidence=round(confidence, 3),
            explanation=explanation,
        )


def severity_from_score(score: float, attack_type: str) -> str:
    if attack_type == "Benign":
        return "Low"
    if score >= 0.78:
        return "Critical"
    if score >= 0.55:
        return "High"
    return "Medium"


def load_events(path: str | Path) -> List[Dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def numeric_features(row: Dict[str, str]) -> Dict[str, float]:
    return {column: float(row.get(column, 0) or 0) for column in FEATURE_COLUMNS}


def predict_events(rows: Iterable[Dict[str, str]]) -> List[Dict[str, object]]:
    model = RuleBasedDetectionModel()
    predictions = []
    for row in rows:
        result = model.predict_one(numeric_features(row))
        predictions.append(
            {
                "event_id": row.get("event_id", ""),
                "true_label": row.get("label", "Unknown"),
                "predicted_label": result.attack_type,
                "severity": result.severity,
                "confidence": result.confidence,
                "anomaly_score": result.anomaly_score,
                "explanation": result.explanation,
            }
        )
    return predictions


def evaluate_predictions(predictions: List[Dict[str, object]]) -> Dict[str, object]:
    total = len(predictions)
    correct = sum(1 for item in predictions if item["true_label"] == item["predicted_label"])
    by_label = Counter(str(item["predicted_label"]) for item in predictions)
    return {
        "total_events": total,
        "accuracy": round(correct / total, 3) if total else 0,
        "predicted_distribution": dict(by_label),
    }


def export_predictions(input_csv: str | Path, output_json: str | Path) -> Dict[str, object]:
    rows = load_events(input_csv)
    predictions = predict_events(rows)
    summary = evaluate_predictions(predictions)
    Path(output_json).write_text(
        json.dumps({"summary": summary, "predictions": predictions}, indent=2),
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    summary_data = export_predictions(
        project_root / "data" / "sample_cyber_events.csv",
        project_root / "data" / "sample_predictions.json",
    )
    print(json.dumps(summary_data, indent=2))
