"""Tests for the code_classifier module."""

import os
import tempfile

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from code_classifier import CodeClassifier, MAX_CODE_SIZE_CHARS


def make_samples(n=10):
    samples = []
    labels = []
    for i in range(n):
        samples.append(f"def func_{i}():\n    return {i}\n")
        labels.append(i % 2)
    return samples, labels


def test_init_defaults():
    clf = CodeClassifier()
    assert clf.max_code_size == MAX_CODE_SIZE_CHARS
    assert clf.n_estimators == 100
    assert clf.random_state == 42
    assert clf.model is None
    assert clf.vectorizer is None
    assert not clf._is_fitted


def test_fit_mismatched_lengths():
    clf = CodeClassifier()
    with pytest.raises(ValueError, match="equal length"):
        clf.fit(["a", "b"], [0])


def test_fit_invalid_labels():
    clf = CodeClassifier()
    with pytest.raises(ValueError, match="Labels must be 0 or 1"):
        clf.fit(["a", "b", "c"], [0, 1, 2])


def test_fit_single_class():
    clf = CodeClassifier()
    with pytest.raises(ValueError, match="Need both classes"):
        clf.fit(["a", "b"], [0, 0])


def test_fit_too_few_samples():
    clf = CodeClassifier()
    with pytest.raises(ValueError, match="at least 4 samples"):
        clf.fit(["a", "b", "c"], [0, 1, 0])


def test_fit_valid_returns_metrics():
    clf = CodeClassifier()
    samples, labels = make_samples(20)
    metrics = clf.fit(samples, labels)
    assert clf._is_fitted
    assert clf.model is not None
    assert clf.vectorizer is not None
    assert metrics["n_samples"] == 20
    assert "classification_report" in metrics


def test_predict_before_fit_raises():
    clf = CodeClassifier()
    with pytest.raises(RuntimeError, match="not been fitted"):
        clf.predict(["def foo():\n    pass"])


def test_predict_valid():
    clf = CodeClassifier()
    samples, labels = make_samples(20)
    clf.fit(samples, labels)
    results = clf.predict(["def foo():\n    return 1\n"])
    assert len(results) == 1
    assert "is_ai_generated" in results[0]
    assert "confidence" in results[0]
    assert "classified_at" in results[0]
    assert 0.0 <= results[0]["confidence"] <= 1.0


def test_predict_single():
    clf = CodeClassifier()
    samples, labels = make_samples(20)
    clf.fit(samples, labels)
    result = clf.predict_single("def foo():\n    pass\n")
    assert "is_ai_generated" in result
    assert "confidence" in result


def test_code_size_limit():
    clf = CodeClassifier(max_code_size=10)
    with pytest.raises(ValueError, match="too large"):
        clf.fit(["x" * 100, "short"], [0, 1])


def test_save_and_load_model():
    clf = CodeClassifier()
    samples, labels = make_samples(20)
    clf.fit(samples, labels)

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.joblib")
        vec_path = os.path.join(tmpdir, "vectorizer.joblib")
        clf.model_path = model_path
        clf.vectorizer_path = vec_path
        # Re-fit to persist
        clf.fit(samples, labels)
        assert os.path.exists(model_path)
        assert os.path.exists(vec_path)

        loaded = CodeClassifier.load(model_path, vec_path)
        assert loaded._is_fitted
        result = loaded.predict(["def foo():\n    pass\n"])
        assert "is_ai_generated" in result[0]
