"""Tests for the productivity module."""

import pandas as pd

from productivity import compute_productivity_indicators, compute_productivity_over_time


def make_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]).date,
        "commit_date": pd.to_datetime(
            ["2024-01-01T10:00:00Z", "2024-01-01T12:00:00Z", "2024-01-02T10:00:00Z"],
            utc=True,
        ),
        "total_changes": [10, 20, 30],
        "sha": ["a", "b", "c"],
        "author_name": ["alice", "alice", "bob"],
    })


def test_compute_productivity_indicators_empty():
    result = compute_productivity_indicators(pd.DataFrame())
    assert result["commits_per_day"] == 0.0
    assert result["avg_code_changes_per_commit"] == 0.0
    assert result["active_day_ratio"] == 0.0
    assert result["consistency_score"] == 0.0
    assert result["total_commits"] == 0


def test_compute_productivity_indicators_with_data():
    df = make_df()
    result = compute_productivity_indicators(df)
    assert result["total_commits"] == 3
    assert result["active_days"] == 2
    assert result["total_days"] == 1
    assert result["commits_per_day"] == 3.0
    assert result["avg_code_changes_per_commit"] == 20.0


def test_compute_productivity_indicators_single_day_consistency():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01"]).date,
        "total_changes": [10],
        "sha": ["a"],
        "author_name": ["alice"],
    })
    result = compute_productivity_indicators(df)
    assert result["consistency_score"] == 1.0


def test_compute_productivity_over_time_empty():
    result = compute_productivity_over_time(pd.DataFrame(), freq="W")
    assert result.empty


def test_compute_productivity_over_time_missing_column():
    result = compute_productivity_over_time(pd.DataFrame({"a": [1]}), freq="W")
    assert result.empty


def test_compute_productivity_over_time_with_data():
    df = make_df()
    result = compute_productivity_over_time(df, freq="W")
    assert len(result) == 1
    assert result["commits"].iloc[0] == 3
    assert result["total_changes"].iloc[0] == 60
