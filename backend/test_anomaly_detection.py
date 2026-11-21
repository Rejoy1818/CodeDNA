"""Tests for the anomaly_detection module."""

import pandas as pd
import pytest

from anomaly_detection import AnomalyDetector, DEFAULT_FEATURE_COLUMNS


def make_feature_df(n=10):
    return pd.DataFrame({
        "commits_per_day": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0][:n],
        "active_days": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10][:n],
        "weekend_activity": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1][:n],
        "avg_commits_per_week": [7.0, 14.0, 21.0, 28.0, 35.0, 42.0, 49.0, 56.0, 63.0, 70.0][:n],
        "avg_gap_between_commits_hours": [24.0, 12.0, 8.0, 6.0, 4.8, 4.0, 3.4, 3.0, 2.7, 2.4][:n],
        "code_change_volume": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100][:n],
    })


def test_default_feature_columns():
    assert DEFAULT_FEATURE_COLUMNS == [
        "commits_per_day",
        "active_days",
        "weekend_activity",
        "avg_commits_per_week",
        "avg_gap_between_commits_hours",
        "code_change_volume",
    ]


def test_init_invalid_contamination():
    with pytest.raises(ValueError, match="contamination must be between"):
        AnomalyDetector(contamination=0.0)
    with pytest.raises(ValueError, match="contamination must be between"):
        AnomalyDetector(contamination=0.5)
    with pytest.raises(ValueError, match="contamination must be between"):
        AnomalyDetector(contamination=1.0)


def test_init_invalid_n_estimators():
    with pytest.raises(ValueError, match="n_estimators must be at least"):
        AnomalyDetector(n_estimators=5)


def test_fit_single_sample_raises():
    detector = AnomalyDetector()
    with pytest.raises(ValueError, match="at least 2 samples"):
        detector.fit(make_feature_df(1))


def test_fit_missing_columns_raises():
    detector = AnomalyDetector()
    with pytest.raises(ValueError, match="Missing feature columns"):
        detector.fit(pd.DataFrame({"a": [1, 2]}))


def test_fit_valid_returns_metadata():
    detector = AnomalyDetector()
    result = detector.fit(make_feature_df(5))
    assert detector._is_fitted
    assert result["n_samples"] == 5
    assert result["n_features"] == len(DEFAULT_FEATURE_COLUMNS)


def test_predict_before_fit_raises():
    detector = AnomalyDetector()
    with pytest.raises(RuntimeError, match="not been fitted"):
        detector.predict(make_feature_df(5))


def test_predict_missing_columns_raises():
    detector = AnomalyDetector()
    detector.fit(make_feature_df(5))
    with pytest.raises(ValueError, match="Missing feature columns"):
        detector.predict(pd.DataFrame({"a": [1, 2]}))


def test_predict_returns_results():
    detector = AnomalyDetector()
    detector.fit(make_feature_df(10))
    results = detector.predict(make_feature_df(3))
    assert len(results) == 3
    for r in results:
        assert "anomaly_score" in r
        assert "is_anomaly" in r
        assert "detected_at" in r
        assert isinstance(r["is_anomaly"], bool)


def test_predict_single():
    detector = AnomalyDetector()
    detector.fit(make_feature_df(10))
    features = {
        "commits_per_day": 5.0,
        "active_days": 5,
        "weekend_activity": 0,
        "avg_commits_per_week": 35.0,
        "avg_gap_between_commits_hours": 4.8,
        "code_change_volume": 50,
    }
    result = detector.predict_single(features)
    assert "anomaly_score" in result
    assert "is_anomaly" in result
