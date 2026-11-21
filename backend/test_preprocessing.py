"""Tests for the preprocessing module."""

import pandas as pd

from preprocessing import normalise_timestamps, aggregate_commits, compute_repository_features


def test_normalise_timestamps_column_missing_returns_unchanged():
    df = pd.DataFrame({"a": [1, 2]})
    result = normalise_timestamps(df, "commit_date")
    pd.testing.assert_frame_equal(result, df)


def test_normalise_timestamps_converts_to_utc():
    df = pd.DataFrame({"commit_date": ["2024-01-01T10:00:00Z", "2024-01-02T11:00:00Z"]})
    result = normalise_timestamps(df, "commit_date")
    assert result["commit_date"].dt.tz is not None
    assert str(result["commit_date"].dt.tz) == "UTC"


def test_normalise_timestamps_handles_naive_timestamps():
    df = pd.DataFrame({"commit_date": ["2024-01-01 10:00:00", "2024-01-02 11:00:00"]})
    result = normalise_timestamps(df, "commit_date")
    assert result["commit_date"].dt.tz is not None


def test_aggregate_commits_empty():
    result = aggregate_commits([])
    assert result.empty


def test_aggregate_commits_with_data():
    commits = [
        {"sha": "abc", "commit_date": "2024-01-01T10:00:00Z", "message": "init"},
        {"sha": "def", "commit_date": "2024-01-02T11:00:00Z", "message": "fix"},
    ]
    result = aggregate_commits(commits)
    assert len(result) == 2
    assert "commit_date" in result.columns
    assert result["commit_date"].dt.tz is not None


def test_compute_repository_features_empty_df():
    result = compute_repository_features(pd.DataFrame())
    assert result["commits_per_day"] == 0.0
    assert result["active_days"] == 0
    assert result["weekend_activity"] == 0
    assert result["avg_commits_per_week"] == 0.0
    assert result["avg_gap_between_commits_hours"] == 0.0
    assert result["code_change_volume"] == 0


def test_compute_repository_features_missing_column():
    result = compute_repository_features(pd.DataFrame({"sha": ["a"]}))
    assert result["commits_per_day"] == 0.0
    assert result["active_days"] == 0


def test_compute_repository_features_with_commits():
    df = pd.DataFrame({
        "commit_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02"], utc=True),
        "additions": [10, 20, 30],
        "deletions": [5, 10, 15],
    })
    result = compute_repository_features(df)
    assert result["commits_per_day"] > 0
    assert result["active_days"] == 2
    assert result["code_change_volume"] == 90
    import json
    tod = json.loads(result["time_of_day_distribution"])
    assert len(tod) == 24
    assert sum(tod.values()) == 3


def test_compute_repository_features_weekend_activity():
    # 2024-01-06 is a Saturday
    df = pd.DataFrame({
        "commit_date": pd.to_datetime(["2024-01-06T10:00:00Z"], utc=True),
        "additions": [1],
        "deletions": [0],
    })
    result = compute_repository_features(df)
    assert result["weekend_activity"] == 1
