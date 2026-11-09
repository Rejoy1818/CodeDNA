"""Feature extraction module for CodeDNA.

Calculates behavioural features from preprocessed commit data:
commits per day, active days, time-of-day distribution, weekend activity,
gaps between commits, and code-change volume.
"""

import logging
import json
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_commits_per_day(df: pd.DataFrame) -> float:
    """Average number of commits per day over the observed period."""
    if df.empty:
        return 0.0
    unique_days = df["date"].nunique() if "date" in df.columns else 1
    if unique_days == 0:
        return 0.0
    return len(df) / unique_days


def compute_active_days(df: pd.DataFrame) -> int:
    """Number of distinct days with at least one commit."""
    if df.empty or "date" not in df.columns:
        return 0
    return int(df["date"].nunique())


def compute_weekend_activity(df: pd.DataFrame) -> int:
    """Count of commits made on weekends."""
    if df.empty or "is_weekend" not in df.columns:
        return 0
    return int(df["is_weekend"].sum())


def compute_avg_commits_per_week(df: pd.DataFrame) -> float:
    """Average commits per week."""
    if df.empty:
        return 0.0
    weeks = (pd.to_datetime(df["date"]).max() - pd.to_datetime(df["date"]).min()).days / 7.0
    if weeks <= 0:
        weeks = 1.0
    return len(df) / weeks


def compute_time_of_day_distribution(df: pd.DataFrame) -> dict:
    """Distribution of commits by hour of the day (0-23)."""
    if df.empty or "hour" not in df.columns:
        return {str(h): 0 for h in range(24)}
    dist = df["hour"].value_counts().to_dict()
    return {str(h): int(dist.get(h, 0)) for h in range(24)}


def compute_avg_gap_between_commits(df: pd.DataFrame) -> float:
    """Average gap between consecutive commits in hours."""
    if df.empty or len(df) < 2:
        return 0.0
    sorted_dates = df["commit_date"].sort_values()
    diffs = sorted_dates.diff().dropna()
    if diffs.empty:
        return 0.0
    avg_hours = diffs.dt.total_seconds().mean() / 3600.0
    return float(avg_hours)


def compute_code_change_volume(df: pd.DataFrame) -> int:
    """Total lines added plus deleted across all commits."""
    if df.empty:
        return 0
    return int(df["total_changes"].sum())


def extract_features(df: pd.DataFrame) -> dict:
    """Extract the full feature set from a preprocessed commits DataFrame.

    Args:
        df: Preprocessed DataFrame from preprocessing.preprocess().

    Returns:
        Dictionary of feature name -> value.
    """
    features = {
        "commits_per_day": compute_commits_per_day(df),
        "active_days": compute_active_days(df),
        "weekend_activity": compute_weekend_activity(df),
        "avg_commits_per_week": compute_avg_commits_per_week(df),
        "time_of_day_distribution": compute_time_of_day_distribution(df),
        "avg_gap_between_commits_hours": compute_avg_gap_between_commits(df),
        "code_change_volume": compute_code_change_volume(df),
        "total_commits": len(df),
    }
    logger.info("Extracted features: %s", features)
    return features


def features_to_dataframe(feature_dicts: list) -> pd.DataFrame:
    """Convert a list of feature dictionaries into a DataFrame for ML.

    Args:
        feature_dicts: List of feature dicts from extract_features().

    Returns:
        DataFrame with numeric feature columns suitable for scikit-learn.
    """
    if not feature_dicts:
        return pd.DataFrame()

    rows = []
    for fd in feature_dicts:
        row = {
            "commits_per_day": fd.get("commits_per_day", 0.0),
            "active_days": fd.get("active_days", 0),
            "weekend_activity": fd.get("weekend_activity", 0),
            "avg_commits_per_week": fd.get("avg_commits_per_week", 0.0),
            "avg_gap_between_commits_hours": fd.get("avg_gap_between_commits_hours", 0.0),
            "code_change_volume": fd.get("code_change_volume", 0),
            "total_commits": fd.get("total_commits", 0),
        }
        # Flatten time-of-day distribution into 24 hour columns
        tod = fd.get("time_of_day_distribution", {})
        for h in range(24):
            row[f"hour_{h}"] = int(tod.get(str(h), 0))
        rows.append(row)

    return pd.DataFrame(rows)