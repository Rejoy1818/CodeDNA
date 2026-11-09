"""Preprocessing utilities for CodeDNA commit data.

Handles timezone-aware datetime normalisation, commit aggregation, and
feature preparation for anomaly detection and classification.
"""

import logging
from datetime import timezone
from typing import Optional, List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def normalise_timestamps(df: pd.DataFrame, column: str = "commit_date") -> pd.DataFrame:
    """Normalise commit timestamps to timezone-aware UTC.

    Parses ISO 8601 timestamps and converts them to timezone-aware UTC
    datetimes. Naive timestamps are assumed to already be UTC and are
    localized (not converted) accordingly.

    Args:
        df: DataFrame containing a timestamp column.
        column: Name of the timestamp column.

    Returns:
        DataFrame with the timestamp column converted to UTC.
    """
    if column not in df.columns:
        return df

    df = df.copy()
    parsed = pd.to_datetime(df[column], utc=True, errors="coerce")
    # tz_convert(None) strips timezone info; it does NOT convert to local time.
    # We keep timestamps timezone-aware in UTC throughout the pipeline.
    df[column] = parsed
    return df


def aggregate_commits(
    commits: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Convert a list of commit dicts into a DataFrame with normalised dates.

    Args:
        commits: List of commit dictionaries from GitHub API.

    Returns:
        DataFrame with commit_date as timezone-aware UTC datetime.
    """
    df = pd.DataFrame(commits)
    if df.empty:
        return df
    return normalise_timestamps(df, "commit_date")


def compute_repository_features(commits_df: pd.DataFrame) -> Dict[str, Any]:
    """Compute behavioural features from a commits DataFrame.

    Args:
        commits_df: DataFrame with commit_date column.

    Returns:
        Dictionary of computed features.
    """
    if commits_df.empty or "commit_date" not in commits_df.columns:
        return {
            "commits_per_day": 0.0,
            "active_days": 0,
            "weekend_activity": 0,
            "avg_commits_per_week": 0.0,
            "avg_gap_between_commits_hours": 0.0,
            "code_change_volume": 0,
            "time_of_day_distribution": "{}",
        }

    df = commits_df.sort_values("commit_date")
    dates = df["commit_date"].dt.date
    unique_days = dates.nunique()

    total_commits = len(df)
    first_date = dates.min()
    last_date = dates.max()
    span_days = max((last_date - first_date).days, 1)

    commits_per_day = total_commits / span_days
    avg_commits_per_week = commits_per_day * 7

    # Weekend activity: commits on Saturday (5) or Sunday (6)
    weekend_mask = df["commit_date"].dt.dayofweek.isin([5, 6])
    weekend_activity = int(weekend_mask.sum())

    # Average gap between consecutive commits in hours
    if total_commits > 1:
        gaps = df["commit_date"].diff().dropna()
        avg_gap_hours = float(gaps.dt.total_seconds().mean() / 3600)
    else:
        avg_gap_hours = 0.0

    # Code change volume
    additions = df.get("additions", pd.Series([0] * len(df))).fillna(0)
    deletions = df.get("deletions", pd.Series([0] * len(df))).fillna(0)
    code_change_volume = int(additions.sum() + deletions.sum())

    # Time-of-day distribution as JSON
    hour_dist = df["commit_date"].dt.hour.value_counts().sort_index()
    time_distribution = {
        str(h): int(hour_dist.get(h, 0)) for h in range(24)
    }
    import json
    time_distribution_json = json.dumps(time_distribution)

    return {
        "commits_per_day": round(commits_per_day, 4),
        "active_days": int(unique_days),
        "weekend_activity": weekend_activity,
        "avg_commits_per_week": round(avg_commits_per_week, 4),
        "avg_gap_between_commits_hours": round(avg_gap_hours, 4),
        "code_change_volume": code_change_volume,
        "time_of_day_distribution": time_distribution_json,
    }