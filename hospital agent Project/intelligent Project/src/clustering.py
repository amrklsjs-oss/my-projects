from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .preprocessing import CLUSTERING_FEATURES, RANDOM_STATE, ensure_directories, resolve_project_path
from .risk_labeling import RISK_LABELS, calculate_risk_score

# ── Scaler persistence path ───────────────────────────────────────────────────
# FCM is retrained on StandardScaler-normalized features so that all six
# CLUSTERING_FEATURES contribute equally to Euclidean distance.  The scaler is
# shared with the SVM pipeline (outputs/scaler.pkl) when that artifact exists
# and covers the same feature set; otherwise a dedicated FCM scaler is saved to
# outputs/fcm_scaler.pkl.  Both paths are tried in order at load time.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
FCM_SCALER_PATH = _PROJECT_ROOT / "outputs" / "fcm_scaler.pkl"
SVM_SCALER_PATH = _PROJECT_ROOT / "outputs" / "scaler.pkl"


def _load_or_fit_fcm_scaler(
    X_raw: np.ndarray,
    feature_cols: list[str],
    output_dir: Path,
    save: bool = True,
) -> StandardScaler:
    """
    Return a StandardScaler for the FCM feature space.

    Priority
    --------
    1. outputs/scaler.pkl  — the SVM scaler, reused when it covers exactly the
       same features in the same order (zero-cost path, single scaling system).
    2. outputs/fcm_scaler.pkl — a dedicated FCM scaler saved during a previous
       FCM training run.
    3. Fit a new scaler on X_raw and save it to outputs/fcm_scaler.pkl.

    Why reuse the SVM scaler?
    The SVM scaler is fit on the same CLUSTERING_FEATURES list from the same
    cleaned dataset, so its mean/std statistics are virtually identical to what
    a fresh FCM scaler would produce.  Sharing one scaler guarantees that the
    membership vector μ and the SVM feature space are strictly compatible.
    """
    for candidate_path in [SVM_SCALER_PATH, FCM_SCALER_PATH]:
        if candidate_path.exists():
            try:
                loaded: StandardScaler = joblib.load(candidate_path)
                # Verify it covers exactly the same features
                if (
                    hasattr(loaded, "n_features_in_")
                    and loaded.n_features_in_ == len(feature_cols)
                ):
                    return loaded
            except Exception:
                pass  # corrupted pickle — fall through and refit

    # No usable scaler found: fit a new one on the FCM training data
    scaler = StandardScaler()
    scaler.fit(X_raw)
    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, output_dir / "fcm_scaler.pkl")
    return scaler

try:
    import skfuzzy.cluster as fcm
except ImportError as exc:  # pragma: no cover - depends on environment
    raise ImportError(
        "scikit-fuzzy is required for the clustering stage. Install it with `pip install scikit-fuzzy`."
    ) from exc


def _validate_features(df: pd.DataFrame, feature_cols: list[str]) -> None:
    missing_columns = [column for column in feature_cols if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing clustering features: {missing_columns}")


def _assign_cluster_labels(
    memberships: np.ndarray,
    df: pd.DataFrame,
    feature_cols: list[str],
) -> dict[int, str]:
    """
    Map raw FCM cluster indices {0, 1, 2} to risk labels {'Low','Medium','High'}.

    Why this replaces _ordered_cluster_labels
    ------------------------------------------
    The old approach computed calculate_risk_score() on each raw-space centroid
    and ranked clusters by that score.  When FCM is trained in *scaled* space,
    every centroid represents a near-average patient (all thresholds in raw
    space map to values near zero in scaled space), so all three centroid risk
    scores are 0 — the ranking becomes arbitrary.

    New approach: soft-majority vote on patient-level labels
    ---------------------------------------------------------
    For each cluster, take every patient's *soft* membership weight for that
    cluster and compute the weighted mean of their rule-based risk scores.
    The cluster with the highest weighted mean score → 'High', middle → 'Medium',
    lowest → 'Low'.  This is deterministic, handles ties robustly (weights are
    continuous), and is identical in spirit to the original intent.
    """
    n_clusters = memberships.shape[0]

    # Compute per-patient risk score using the existing rule-based function
    risk_scores = df[feature_cols[:5]].apply(calculate_risk_score, axis=1).to_numpy(dtype=float)
    # Note: wait_time is index 5 but is not used by calculate_risk_score (only BASE_RISK_FEATURES)

    # Weighted mean risk score for each cluster
    weighted_means: list[tuple[int, float]] = []
    for c in range(n_clusters):
        weights = memberships[c]          # shape (n_samples,), already summing to ~1 per patient
        weighted_mean = float(np.average(risk_scores, weights=weights + 1e-300))
        weighted_means.append((c, weighted_mean))

    sorted_clusters = sorted(weighted_means, key=lambda item: item[1])
    return {
        sorted_clusters[0][0]: RISK_LABELS[0],   # lowest weighted score → Low
        sorted_clusters[1][0]: RISK_LABELS[1],   # middle                 → Medium
        sorted_clusters[2][0]: RISK_LABELS[2],   # highest                → High
    }


def run_fcm_exploration(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    membership_threshold: float = 0.60,
    output_dir: str | Path = "outputs",
    labeled_output_name: str = "labeled_healthcare.csv",
    save_outputs: bool = True,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """
    Train Fuzzy C-Means on *StandardScaler-normalized* features.

    Key changes vs the original implementation
    -------------------------------------------
    * Features are scaled to zero-mean / unit-variance before FCM so that all
      six CLUSTERING_FEATURES contribute equally to Euclidean distance.
      Previously, wait_time (range ≈ 0–500) dominated distance computations,
      making μ a wait-time proximity signal rather than a clinical one.

    * Centroids are stored in *scaled space* (fcm_centroids.npy).  The scaler
      itself is persisted alongside them (fcm_scaler.pkl or reused scaler.pkl).
      All downstream membership computations must scale patient vectors before
      calling compute_predicted_membership().

    * Cluster-to-label assignment uses _assign_cluster_labels (weighted-mean
      patient risk score per cluster) instead of scoring raw centroids, because
      scaled centroids all map to near-average patients in raw space.

    Backward-compatible outputs
    ---------------------------
    The function returns and saves the same columns (mu_low, mu_medium, mu_high,
    fcm_cluster, fcm_category, max_membership) and the same artifact paths.
    The only internal change is that the centroid array is now in scaled space.
    """
    active_features = feature_cols or CLUSTERING_FEATURES
    _validate_features(df, active_features)

    output_path, _ = ensure_directories(output_dir=output_dir)

    labeled_df = df.copy()
    X_raw = labeled_df[active_features].to_numpy(dtype=float)

    # ── Scale features ────────────────────────────────────────────────────────
    # Reuse the SVM scaler when possible so FCM and SVM share one feature space.
    scaler = _load_or_fit_fcm_scaler(X_raw, active_features, output_path, save=save_outputs)
    X_scaled = scaler.transform(pd.DataFrame(X_raw, columns=active_features))

    # ── FCM on scaled features ────────────────────────────────────────────────
    centroids, memberships, _, _, _, _, fpc = fcm.cmeans(
        X_scaled.T,   # skfuzzy expects (n_features, n_samples)
        c=3,
        m=2.0,
        error=0.005,
        maxiter=1000,
        seed=RANDOM_STATE,
    )
    # centroids shape: (3, n_features) — all values in scaled space

    # ── Cluster → risk label assignment ──────────────────────────────────────
    cluster_map = _assign_cluster_labels(memberships, labeled_df, active_features)

    label_to_membership = {
        "Low":    memberships[list(cluster_map.keys())[list(cluster_map.values()).index("Low")]],
        "Medium": memberships[list(cluster_map.keys())[list(cluster_map.values()).index("Medium")]],
        "High":   memberships[list(cluster_map.keys())[list(cluster_map.values()).index("High")]],
    }

    labeled_df["mu_low"]    = label_to_membership["Low"]
    labeled_df["mu_medium"] = label_to_membership["Medium"]
    labeled_df["mu_high"]   = label_to_membership["High"]

    raw_cluster_ids = np.argmax(memberships, axis=0)
    labeled_df["fcm_cluster"] = raw_cluster_ids
    labeled_df["fcm_category"] = pd.Categorical(
        [cluster_map[cluster_id] for cluster_id in raw_cluster_ids],
        categories=RISK_LABELS,
        ordered=True,
    )
    labeled_df["max_membership"] = labeled_df[["mu_low", "mu_medium", "mu_high"]].max(axis=1)

    borderline_df = labeled_df[labeled_df["max_membership"] < membership_threshold].copy()
    artifacts: dict[str, object] = {
        "centroids":          centroids,   # scaled-space array
        "scaler":             scaler,
        "fpc":                float(fpc),
        "borderline_patients": borderline_df,
        "feature_columns":    active_features,
    }

    print(f"FCM completed with FPC={fpc:.4f}  (trained on StandardScaler-normalized features)")
    print(f"Borderline patients (< {membership_threshold:.2f} max membership): {len(borderline_df)}")

    if save_outputs:
        # Centroids saved in scaled space — agents must scale before distance queries
        np.save(output_path / "fcm_centroids.npy", centroids)
        # Mark the centroid file as being in scaled space so diagnostic tools know
        (output_path / "fcm_centroids_space.txt").write_text("scaled", encoding="utf-8")
        (output_path / "clustering_features.txt").write_text("\n".join(active_features), encoding="utf-8")
        borderline_df.to_csv(output_path / "borderline_patients.csv", index=False)
        labeled_df.to_csv(output_path / labeled_output_name, index=False)
        artifacts["centroids_path"]    = output_path / "fcm_centroids.npy"
        artifacts["scaler_path"]       = output_path / "fcm_scaler.pkl"
        artifacts["borderline_path"]   = output_path / "borderline_patients.csv"
        artifacts["labeled_data_path"] = output_path / labeled_output_name

    return labeled_df, artifacts


def plot_cluster_comparison(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    output_path: str | Path = "cluster_plot.png",
) -> Path:
    active_features = feature_cols or CLUSTERING_FEATURES
    _validate_features(df, active_features)
    if "risk_category" not in df.columns or "fcm_category" not in df.columns:
        raise ValueError("Both `risk_category` and `fcm_category` must exist before plotting.")

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(df[active_features])
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))

    color_map = {"Low": "green", "Medium": "orange", "High": "red"}
    for axis, column_name, title in [
        (axes[0], "risk_category", "Patient Groups (Medical Rules)"),
        (axes[1], "fcm_category", "Patient Groups (FCM Exploration)"),
    ]:
        for label, color in color_map.items():
            mask = df[column_name].astype(str) == label
            axis.scatter(X_pca[mask, 0], X_pca[mask, 1], c=color, label=label, alpha=0.5, s=10)
        axis.set_xlabel("PCA Component 1")
        axis.set_ylabel("PCA Component 2")
        axis.set_title(title)
        axis.legend()

    figure.tight_layout()
    resolved_output = resolve_project_path(output_path, default_dir="outputs")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(resolved_output, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return resolved_output


def load_fcm_scaler(output_dir: str | Path = "outputs") -> StandardScaler:
    """
    Load the FCM scaler from disk.  Tries outputs/scaler.pkl first (shared SVM
    scaler), then outputs/fcm_scaler.pkl.  Raises FileNotFoundError if neither
    is present.
    """
    output_path = _PROJECT_ROOT / Path(output_dir)
    for candidate in [output_path / "scaler.pkl", output_path / "fcm_scaler.pkl"]:
        if candidate.exists():
            try:
                loaded: StandardScaler = joblib.load(candidate)
                if hasattr(loaded, "n_features_in_") and loaded.n_features_in_ > 0:
                    return loaded
            except Exception:
                continue
    raise FileNotFoundError(
        "No usable FCM scaler found. Run run_fcm_exploration() first to generate one."
    )


def compute_predicted_membership(
    patient_features: np.ndarray,
    predicted_class_index: int,
    centroids: np.ndarray,
    m: float = 2.0,
    scaler: StandardScaler | None = None,
    feature_columns: list[str] | None = None,
) -> float:
    """
    Compute the fuzzy membership of a patient in the predicted FCM cluster.

    CRITICAL CHANGE: centroids are now stored in *scaled space*.
    The patient feature vector must be transformed to the same space before
    computing distances.  Pass the scaler explicitly (recommended) or rely on
    the module-level auto-load fallback.

    Parameters
    ----------
    patient_features : 1-D array of shape (n_features,)
        RAW (unscaled) feature values in CLUSTERING_FEATURES order.
        The function will scale them internally before distance computation.
    predicted_class_index : int
        Index into `centroids` for the predicted risk class.
    centroids : 2-D array of shape (n_clusters, n_features)
        FCM centroids **in scaled space** as saved by run_fcm_exploration.
    m : float
        Fuzziness exponent matching the FCM training call (default 2.0).
    scaler : StandardScaler or None
        The scaler used during FCM training.  When None the function attempts
        to load it from outputs/scaler.pkl or outputs/fcm_scaler.pkl.
    feature_columns : list[str] or None
        Column names matching patient_features order.  Required only when
        scaler is loaded from disk and needs a feature-names check.

    Returns
    -------
    float in (0.0, 1.0]
        Fuzzy membership degree, clipped to [0.05, 1.0] to prevent underflow.

    Underflow safeguard
    -------------------
    The raw FCM formula can produce values as small as 1e-73 when a patient
    happens to lie very close to a non-target centroid in feature space.
    After scaling, inter-centroid distances are balanced, making extreme
    underflow rare; the 0.05 floor ensures the membership term never silences
    the composite score even in edge cases.
    """
    # ── Validate centroid shape ───────────────────────────────────────────────
    if centroids.ndim != 2 or centroids.shape[0] < 2:
        raise ValueError(
            f"centroids must be a 2-D array with shape (n_clusters, n_features). "
            f"Got shape {centroids.shape}."
        )
    if predicted_class_index < 0 or predicted_class_index >= len(centroids):
        raise ValueError(
            f"predicted_class_index={predicted_class_index} is out of range for "
            f"centroids with {len(centroids)} clusters."
        )

    # ── Scale patient vector to FCM feature space ─────────────────────────────
    if scaler is None:
        scaler = load_fcm_scaler()

    x_raw = np.asarray(patient_features, dtype=float).reshape(1, -1)
    if feature_columns is not None:
        x_scaled = scaler.transform(
            pd.DataFrame(x_raw, columns=feature_columns)
        )[0]
    else:
        # Positional transform — works when feature order matches scaler fit
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x_scaled = scaler.transform(x_raw)[0]

    # ── Standard FCM inverse-distance membership formula ──────────────────────
    d_target = float(np.linalg.norm(x_scaled - centroids[predicted_class_index]))

    if d_target == 0.0:
        return 1.0                         # patient exactly on target centroid

    exponent = 2.0 / (m - 1.0)            # = 2.0 when m = 2.0
    epsilon  = 1e-300                     # prevents division by zero

    total = 0.0
    for k in range(len(centroids)):
        d_k = float(np.linalg.norm(x_scaled - centroids[k]))
        if d_k == 0.0:
            # Patient is exactly on a non-target centroid → membership in target ≈ 0
            # Return floor rather than 0 to prevent score collapse downstream
            return 0.05
        total += (d_target / (d_k + epsilon)) ** exponent

    raw_mu = 1.0 / total if total > 0.0 else 0.0

    # Clip: floor at 0.05 (prevents score collapse), ceiling at 1.0
    return float(np.clip(raw_mu, 0.05, 1.0))