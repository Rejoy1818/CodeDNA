"""NLP analysis module for CodeDNA.

Applies NLTK-based text preprocessing and feature extraction to commit
messages. Output is descriptive statistics only — no mental-state inference
is made from commit text.
"""

import logging
import re
import string
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer

    # Download required NLTK data (quietly)
    for resource in ("punkt", "stopwords", "wordnet", "omw-1.4"):
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass

    _STOPWORDS = set(stopwords.words("english"))
    _LEMMATIZER = WordNetLemmatizer()
    _NLTK_AVAILABLE = True
except Exception:  # pragma: no cover - fallback when NLTK unavailable
    _STOPWORDS = set()
    _LEMMATIZER = None
    _NLTK_AVAILABLE = False


def preprocess_text(text: str) -> str:
    """Clean and normalise a single commit message.

    Steps: lowercase, remove punctuation/digits, tokenise, remove stopwords,
    lemmatise.

    Args:
        text: Raw commit message string.

    Returns:
        Cleaned, normalised string.
    """
    if not text:
        return ""

    text = text.lower()
    text = re.sub(rf"[{re.escape(string.punctuation)}0-9]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if _NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(text)
            tokens = [t for t in tokens if t and t not in _STOPWORDS]
            if _LEMMATIZER:
                tokens = [_LEMMATIZER.lemmatize(t) for t in tokens]
            return " ".join(tokens)
        except Exception:
            pass

    # Fallback: simple split
    tokens = [t for t in text.split() if t and t not in _STOPWORDS]
    return " ".join(tokens)


def extract_message_features(df: pd.DataFrame) -> dict:
    """Compute descriptive NLP features from commit messages.

    Args:
        df: DataFrame with a 'message' column.

    Returns:
        Dictionary of aggregate message statistics.
    """
    if df.empty or "message" not in df.columns:
        return {
            "total_messages": 0,
            "avg_message_length": 0.0,
            "avg_word_count": 0.0,
            "most_common_words": [],
            "unique_words": 0,
        }

    messages = df["message"].fillna("").astype(str)
    cleaned = messages.apply(preprocess_text)

    word_lists = cleaned.apply(lambda t: t.split())
    all_words = [w for words in word_lists for w in words]

    # Word frequency
    from collections import Counter
    word_counts = Counter(all_words)
    most_common = word_counts.most_common(20)

    features = {
        "total_messages": int(len(messages)),
        "non_empty_messages": int((messages.str.len() > 0).sum()),
        "avg_message_length": float(messages.str.len().mean()),
        "avg_word_count": float(word_lists.apply(len).mean()),
        "most_common_words": most_common,
        "unique_words": len(set(all_words)),
    }
    logger.info("Extracted NLP features from %d messages", features["total_messages"])
    return features


def analyse_message_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Analyse how commit message characteristics change over time.

    Groups by month and computes average message length and word count.

    Args:
        df: DataFrame with 'commit_date' and 'message' columns.

    Returns:
        DataFrame indexed by month with message statistics.
    """
    if df.empty or "message" not in df.columns or "commit_date" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month"] = df["commit_date"].dt.to_period("M").astype(str)
    cleaned = df["message"].fillna("").astype(str).apply(preprocess_text)
    df["word_count"] = cleaned.apply(lambda t: len(t.split()))
    df["message_length"] = df["message"].str.len()

    trends = (
        df.groupby("month")
        .agg(
            commit_count=("message", "count"),
            avg_message_length=("message_length", "mean"),
            avg_word_count=("word_count", "mean"),
        )
        .reset_index()
    )
    return trends