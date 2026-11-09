"""Anomaly detection module for CodeDNA.

Uses scikit-learn Isolation Forest to detect anomalous repository
activity patterns. Supports multi-sample baseline training so the
detector is not fit on a single repository (which would always be
flagged as anomalous).
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)

# Default feature columns used for anomaly detection
DEFAULT_FEATURE_COLUMNS = [
    "commits_per_day",
    "active_days",
    "weekend_activity",
    "avg_commits_per_week",
    "avg_gap_between_commits_hours",
    "code_change_volume",
]


class AnomalyDetector:
    """Isolation Forest based anomaly detector with multi-sample baseline."""

    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42,
        model_path: Optional[str] = None,
    ):
        """Initialise the anomaly detector.

        Args:
            contamination: Expected proportion of anomalies (0.0-0.5).
            n_estimators: Number of trees in the Isolation Forest.
            random_state: Seed for reproducibility.
            model_path: Optional path to save/load the trained model.
        """
        if not 0.0 < contamination < 0.5:
            raise ValueError("contamination must be between 0.0 and 0.5")
        if n_estimators < 10:
            raise ValueError("n_estimators must be at least 10")

        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model_path = model_path or os.getenv("CODEDNA_ANOMALY_MODEL_PATH")

        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_columns: List[str] = list(DEFAULT_FEATURE_COLUMNS)
        self._is_fitted = False

    def fit(
        self, df: pd.DataFrame, feature_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fit the detector on a multi-repository baseline.

        Requires at least 2 samples to train meaningfully. Fits on a single
        sample raises a ValueError to avoid degenerate behaviour.

        Args:
            df: DataFrame containing feature columns.
            feature_columns: Columns to use for detection. Defaults to
                DEFAULT_FEATURE_COLUMNS.

        Returns:
            Dictionary with fit metadata (n_samples, n_features).

        Raises:
            ValueError: If fewer than 2 samples or missing columns.
        """
        if feature_columns is not None:
            self.feature_columns = list(feature_columns)

        missing = [c for c in self.feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")

        X = df[self.feature_columns].copy()
        X = X.fillna(0)

        n_samples = len(X)
        if n_samples < 2:
            raise ValueError(
                f"Need at least 2 samples to train anomaly detector, got {n_samples}"
            )

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)
        self._is_fitted = True

        # Persist model if a path is configured
        if self.model_path:
            try:
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                joblib.dump(
                    {
                        "model": self.model,
                        "scaler": self.scaler,
                        "feature_columns": self.feature_columns,
                    },
                    self.model_path,
                )
                logger.info("Anomaly model saved to %s", self.model_path)
            except OSError as exc:
                logger.warning("Failed to save anomaly model: %s", exc)

        logger.info(
            "Anomaly detector fitted on %d samples with %d features",
            n_samples, len(self.feature_columns),
        )
        return {
            "n_samples": n_samples,
            "n_features": len(self.feature_columns),
            "contamination": self.contamination,
        }

    def predict(
        self, df: pd.DataFrame, feature_columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Predict anomaly scores for repositories.

        Args:
            df: DataFrame containing feature columns.
            feature_columns: Columns to use (must match fit columns).

        Returns:
            List of dicts with anomaly_score and is_anomaly per row.
        """
        if not self._is_fitted or self.model is None or self.scaler is None:
            raise RuntimeError("Detector has not been fitted yet")

        if feature_columns is not None:
            cols = list(feature_columns)
        else:
            cols = self.feature_columns

        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")

        X = df[cols].copy().fillna(0)
        X_scaled = self.scaler.transform(X)

        scores = self.model.decision_function(X_scaled)
        predictions = self.model.predict(X_scaled)  # -1 = anomaly, 1 = normal

        results: List[Dict[str, Any]] = []
        for score, pred in zip(scores, predictions):
            results.append(
                {
                    "anomaly_score": float(score),
                    "is_anomaly": bool(pred == -1),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        return results

    def predict_single(
        self, features: Dict[str, Any], feature_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Predict anomaly for a single repository (convenience wrapper)."""
        df = pd.DataFrame([features])
        results = self.predict(df, feature_columns=feature_columns)
        return results[0]

    @classmethod
    def load(cls, model_path: str) -> "AnomalyDetector":
        """Load a previously saved detector from disk.

        Args:
            model_path: Path to the saved model file.

        Returns:
            AnomalyDetector instance with model restored.
        """
        bundle = joblib.load(model_path)
        detector = cls(
            contamination=bundle.get("contamination", 0.1),
            n_estimators=bundle.get("n_estimators", 100),
            random_state=bundle.get("random_state", 42),
            model_path=model_path,
        )
        detector.model = bundle["model"]
        detector.scaler = bundle["scaler"]
        detector.feature_columns = bundle["feature_columns"]
        detector._is_fitted = True
        logger.info("Anomaly detector loaded from %s", model_path)
        return detector