"""Tests for the features module."""

import pandas as pd

from features import (
    compute_commits_per_day,
    compute_active_days,
    compute_weekend_activity,
    compute_avg_commits_per_week,
    compute_time_of_day_distribution,
    compute_avg_gap_between_commits,
    compute_code_change_volume,
    extract_features,
    features_to_dataframe,
)


def make_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]).date,
        "commit_date": pd.to_datetime(
            ["2024-01-01T10:00:00Z", "2024-01-01T12:00:00Z", "2024-01-02T10:00:00Z"],
            utc=True,
        ),
        "total_changes": [10, 20, 30],
    })


def test_compute_commits_per_day_empty():
    assert compute_commits_per_day(pd.DataFrame()) == 0.0


def test_compute_commits_per_day_no_date_column():
    assert compute_commits_per_day(pd.DataFrame({"a": [1]})) == 1.0


def test_compute_commits_per_day_with_data():
    df = make_df()
    assert compute_commits_per_day(df) == 3 / 2


def test_compute_active_days_empty():
    assert compute_active_days(pd.DataFrame()) == 0


def test_compute_active_days_no_date_column():
    assert compute_active_days(pd.DataFrame({"a": [1]})) == 0


def test_compute_active_days_with_data():
    df = make_df()
    assert compute_active_days(df) == 2


def test_compute_weekend_activity_empty():
    assert compute_weekend_activity(pd.DataFrame()) == 0


def test_compute_weekend_activity_no_column():
    assert compute_weekend_activity(pd.DataFrame({"a": [1]})) == 0


def test_compute_weekend_activity_with_column():
    df = pd.DataFrame({"is_weekend": [0, 1, 1]})
    assert compute_weekend_activity(df) == 2


def test_compute_avg_commits_per_week_empty():
    assert compute_avg_commits_per_week(pd.DataFrame()) == 0.0


def test_compute_avg_commits_per_week_single_day():
    df = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]).date})
    assert compute_avg_commits_per_week(df) == 1.0


def test_compute_avg_commits_per_week_multiple_weeks():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-08", "2024-01-15"]).date,
    })
    assert compute_avg_commits_per_week(df) == 1.5


def test_compute_time_of_day_distribution_empty():
    assert compute_time_of_day_distribution(pd.DataFrame()) == {str(h): 0 for h in range(24)}


def test_compute_time_of_day_distribution_no_hour_column():
    assert compute_time_of_day_distribution(pd.DataFrame({"a": [1]})) == {str(h): 0 for h in range(24)}


def test_compute_time_of_day_distribution_with_hour_column():
    df = pd.DataFrame({"hour": [9, 9, 17]})
    dist = compute_time_of_day_distribution(df)
    assert dist["9"] == 2
    assert dist["17"] == 1
    assert dist["0"] == 0


def test_compute_avg_gap_between_commits_empty():
    assert compute_avg_gap_between_commits(pd.DataFrame()) == 0.0


def test_compute_avg_gap_between_commits_single_row():
    df = pd.DataFrame({"commit_date": pd.to_datetime(["2024-01-01T10:00:00Z"], utc=True)})
    assert compute_avg_gap_between_commits(df) == 0.0


def test_compute_avg_gap_between_commits_multiple():
    df = pd.DataFrame({
        "commit_date": pd.to_datetime(
            ["2024-01-01T10:00:00Z", "2024-01-01T12:00:00Z"], utc=True
        ),
    })
    assert compute_avg_gap_between_commits(df) == 2.0


def test_compute_code_change_volume_empty():
    assert compute_code_change_volume(pd.DataFrame()) == 0


def test_compute_code_change_volume_with_data():
    df = pd.DataFrame({"total_changes": [10, 20, 30]})
    assert compute_code_change_volume(df) == 60


def test_extract_features_full():
    df = make_df()
    features = extract_features(df)
    assert "commits_per_day" in features
    assert "active_days" in features
    assert "weekend_activity" in features
    assert "avg_commits_per_week" in features
    assert "time_of_day_distribution" in features
    assert "avg_gap_between_commits_hours" in features
    assert "code_change_volume" in features
    assert "total_commits" in features
    assert features["total_commits"] == 3


def test_features_to_dataframe_empty():
    result = features_to_dataframe([])
    assert result.empty


def test_features_to_dataframe_with_data():
    fd = {
        "commits_per_day": 1.0,
        "active_days": 2,
        "weekend_activity": 0,
        "avg_commits_per_week": 7.0,
        "avg_gap_between_commits_hours": 24.0,
        "code_change_volume": 100,
        "total_commits": 5,
        "time_of_day_distribution": {"9": 3, "17": 2},
    }
    result = features_to_dataframe([fd])
    assert len(result) == 1
    assert result["commits_per_day"].iloc[0] == 1.0
    assert result["hour_9"].iloc[0] == 3
    assert result["hour_17"].iloc[0] == 2
    assert result["hour_0"].iloc[0] == 0
