"""Productivity trend estimation module for CodeDNA.

Computes repository-based productivity indicators over time. These indicators
are descriptive only and are NOT a complete measure of individual productivity.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_productivity_indicators(df: pd.DataFrame) -> dict:
    """Compute a set of productivity indicators from commit data.

    Indicators:
        - commits_per_day
        - avg_code_changes_per_commit
        - active_day_ratio (active days / total days in range)
        - consistency_score (inverse of day-to-day commit variance)

    Args:
        df: Preprocessed commits DataFrame.

    Returns:
        Dictionary of productivity indicators.
    """
    if df.empty:
        return {
            "commits_per_day": 0.0,
            "avg_code_changes_per_commit": 0.0,
            "active_day_ratio": 0.0,
            "consistency_score": 0.0,
            "total_commits": 0,
        }

    total_commits = len(df)
    date_range = pd.to_datetime(df["date"]).max() - pd.to_datetime(df["date"]).min()
    total_days = max(date_range.days, 1)
    active_days = df["date"].nunique()

    commits_per_day = total_commits / total_days
    avg_changes = float(df["total_changes"].mean()) if "total_changes" in df.columns else 0.0
    active_day_ratio = active_days / total_days

    # Consistency: lower variance in daily commits = higher consistency
    daily_counts = df.groupby("date").size()
    if len(daily_counts) > 1:
        cv = daily_counts.std() / (daily_counts.mean() + 1e-6)
        consistency_score = max(0.0, 1.0 - min(cv, 1.0))
    else:
        consistency_score = 1.0

    indicators = {
        "commits_per_day": round(commits_per_day, 3),
        "avg_code_changes_per_commit": round(avg_changes, 2),
        "active_day_ratio": round(active_day_ratio, 3),
        "consistency_score": round(consistency_score, 3),
        "total_commits": total_commits,
        "active_days": int(active_days),
        "total_days": int(total_days),
    }
    logger.info("Computed productivity indicators: %s", indicators)
    return indicators


def compute_productivity_over_time(df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    """Compute productivity indicators aggregated over time periods.

    Args:
        df: Preprocessed commits DataFrame.
        freq: Pandas offset alias ('D' daily, 'W' weekly, 'M' monthly).

    Returns:
        DataFrame with productivity indicators per time period.
    """
    if df.empty or "commit_date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["period"] = df["commit_date"].dt.to_period(freq).astype(str)

    result = (
        df.groupby("period")
        .agg(
            commits=("sha", "count"),
            total_changes=("total_changes", "sum"),
            active_authors=("author_name", "nunique"),
        )
        .reset_index()
    )

    result["avg_changes_per_commit"] = (
        result["total_changes"] / result["commits"].replace(0, 1)
    ).round(2)

    return result