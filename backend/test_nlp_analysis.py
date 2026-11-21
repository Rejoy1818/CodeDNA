"""Tests for the nlp_analysis module."""

import pandas as pd

from nlp_analysis import preprocess_text, extract_message_features, analyse_message_trends


def test_preprocess_text_empty():
    assert preprocess_text("") == ""
    assert preprocess_text(None) == ""


def test_preprocess_text_lowercases_and_removes_punctuation():
    result = preprocess_text("Hello, World! 123")
    assert "hello" in result
    assert "world" in result
    assert "," not in result
    assert "!" not in result


def test_preprocess_text_removes_punctuation():
    result = preprocess_text("Hello, World! 123")
    assert "," not in result
    assert "!" not in result


def test_preprocess_text_lowercases():
    result = preprocess_text("HELLO WORLD")
    assert result == result.lower()


def test_extract_message_features_empty():
    result = extract_message_features(pd.DataFrame())
    assert result["total_messages"] == 0
    assert result["avg_message_length"] == 0.0
    assert result["most_common_words"] == []


def test_extract_message_features_missing_column():
    result = extract_message_features(pd.DataFrame({"sha": ["a"]}))
    assert result["total_messages"] == 0


def test_extract_message_features_with_messages():
    df = pd.DataFrame({"message": ["fix bug", "add feature", "fix bug again"]})
    result = extract_message_features(df)
    assert result["total_messages"] == 3
    assert result["non_empty_messages"] == 3
    assert result["avg_message_length"] > 0


def test_analyse_message_trends_missing_columns():
    result = analyse_message_trends(pd.DataFrame({"sha": ["a"]}))
    assert result.empty


def test_analyse_message_trends_missing_message():
    result = analyse_message_trends(
        pd.DataFrame({"commit_date": pd.to_datetime(["2024-01-01"])})
    )
    assert result.empty


def test_analyse_message_trends_with_data():
    df = pd.DataFrame({
        "commit_date": pd.to_datetime(["2024-01-01T10:00:00Z", "2024-01-15T10:00:00Z"], utc=True),
        "message": ["fix bug", "add feature"],
    })
    result = analyse_message_trends(df)
    assert len(result) == 1
    assert result["commit_count"].iloc[0] == 2
