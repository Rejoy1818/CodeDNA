"""Tests for the generate_sample_data module."""

from generate_sample_data import generate, HUMAN_SAMPLES, AI_GENERATED_SAMPLES


def test_generate_default_returns_balanced_samples():
    data = generate(num_per_class=10)
    assert len(data) == 20
    labels = [l for _, l in data]
    assert labels.count(0) == 10
    assert labels.count(1) == 10


def test_generate_returns_tuples():
    data = generate(num_per_class=5)
    for item in data:
        assert isinstance(item, tuple)
        assert len(item) == 2
        code, label = item
        assert isinstance(code, str)
        assert label in (0, 1)


def test_human_samples_non_empty():
    assert len(HUMAN_SAMPLES) > 0
    for s in HUMAN_SAMPLES:
        assert isinstance(s, str)
        assert len(s.strip()) > 0


def test_ai_samples_non_empty():
    assert len(AI_GENERATED_SAMPLES) > 0
    for s in AI_GENERATED_SAMPLES:
        assert isinstance(s, str)
        assert len(s.strip()) > 0
