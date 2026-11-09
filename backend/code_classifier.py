"""AI vs human code classification module for CodeDNA.

Trains a TF-IDF + RandomForest classifier to distinguish AI-generated
from human-written code. Includes input validation, label validation,
stratify guards for small/single-class datasets, and a maximum code
size limit to prevent memory exhaustion.
"""

import logging
import os
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

logger = logging.getLogger(__name__)

MAX_CODE_SIZE_CHARS = 200_000  # 200KB per code sample to prevent OOM
VALID_LABELS = {0, 1}
MIN_SAMPLES_FOR_STRATIFY = 2  # need at least 2 per class for stratify


class CodeClassifier:
    """TF-IDF + RandomForest classifier for AI vs human code detection."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        vectorizer_path: Optional[str] = None,
        max_code_size: int = MAX_CODE_SIZE_CHARS,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        """Initialise the classifier.

        Args:
            model_path: Optional path to save/load the trained model.
            vectorizer_path: Optional path to save/load the vectorizer.
            max_code_size: Max characters per code sample.
            n_estimators: Number of trees in RandomForest.
            random_state: Seed for reproducibility.
        """
        self.model_path = model_path or os.getenv("CODEDNA_CLASSIFIER_MODEL_PATH")
        self.vectorizer_path = vectorizer_path or os.getenv(
            "CODEDNA_VECTORIZER_PATH"
        )
        self.max_code_size = max_code_size
        self.n_estimators = n_estimators
        self.random_state = random_state

        self.vectorizer: Optional[TfidfVectorizer] = None
        self.model: Optional[RandomForestClassifier] = None
        self._is_fitted = False

    def _validate_labels(self, labels: List[int]) -> None:
        """Ensure all labels are 0 or 1 and both classes are present.

        Args:
            labels: List of integer labels.

        Raises:
            ValueError: If labels contain invalid values or only one class.
        """
        invalid = [l for l in labels if l not in VALID_LABELS]
        if invalid:
            raise ValueError(
                f"Labels must be 0 or 1; found invalid values: {sorted(set(invalid))}"
            )
        unique = set(labels)
        if len(unique) < 2:
            raise ValueError(
                f"Need both classes (0 and 1) for training; found only {unique}"
            )

    def _sanitize_code(self, code: str) -> str:
        """Basic sanitization: strip null bytes and collapse whitespace."""
        code = code.replace("\x00", "")
        code = re.sub(r"\s+", " ", code).strip()
        return code

    def _validate_code_size(self, code: str) -> None:
        """Reject code samples that exceed the maximum size.

        Args:
            code: Source code string.

        Raises:
            ValueError: If code exceeds max_code_size.
        """
        if len(code) > self.max_code_size:
            raise ValueError(
                f"Code sample too large: {len(code)} chars > {self.max_code_size} limit"
            )

    def fit(
        self,
        code_samples: List[str],
        labels: List[int],
        test_size: float = 0.2,
    ) -> Dict[str, Any]:
        """Train the classifier on labelled code samples.

        Args:
            code_samples: List of source code strings.
            labels: List of 0 (human) or 1 (AI) labels.
            test_size: Fraction of data to hold out for evaluation.

        Returns:
            Dictionary with training metadata and classification report.

        Raises:
            ValueError: If validation fails (labels, sizes, too few samples).
        """
        if len(code_samples) != len(labels):
            raise ValueError("code_samples and labels must have equal length")

        self._validate_labels(labels)

        # Sanitize and size-check every sample
        cleaned: List[str] = []
        for code in code_samples:
            if not isinstance(code, str):
                raise ValueError("All code samples must be strings")
            self._validate_code_size(code)
            cleaned.append(self._sanitize_code(code))

        n_samples = len(cleaned)
        if n_samples < 4:
            raise ValueError(
                f"Need at least 4 samples to train, got {n_samples}"
            )

        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        X = self.vectorizer.fit_transform(cleaned)

        # Guard stratify: only use it when every class has >= 2 samples
        label_counts: Dict[int, int] = {}
        for lab in labels:
            label_counts[lab] = label_counts.get(lab, 0) + 1
        min_class_count = min(label_counts.values())
        use_stratify = min_class_count >= MIN_SAMPLES_FOR_STRATIFY

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, labels, test_size=test_size, random_state=self.random_state,
                stratify=labels if use_stratify else None,
            )
        except ValueError as exc:
            # Fallback: no stratification if split still fails
            logger.warning("Stratified split failed (%s); retrying without stratify", exc)
            X_train, X_test, y_train, y_test = train_test_split(
                X, labels, test_size=test_size, random_state=self.random_state,
            )

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(X_train, y_train)
        self._is_fitted = True

        # Evaluate on hold-out set
        y_pred = self.model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Persist model + vectorizer
        if self.model_path:
            try:
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                joblib.dump(self.model, self.model_path)
                logger.info("Classifier model saved to %s", self.model_path)
            except OSError as exc:
                logger.warning("Failed to save classifier model: %s", exc)

        if self.vectorizer_path:
            try:
                os.makedirs(os.path.dirname(self.vectorizer_path), exist_ok=True)
                joblib.dump(self.vectorizer, self.vectorizer_path)
                logger.info("Vectorizer saved to %s", self.vectorizer_path)
            except OSError as exc:
                logger.warning("Failed to save vectorizer: %s", exc)

        return {
            "n_samples": n_samples,
            "n_train": len(y_train),
            "n_test": len(y_test),
            "stratify_used": use_stratify,
            "classification_report": report,
        }

    def predict(
        self, code_samples: List[str]
    ) -> List[Dict[str, Any]]:
        """Classify code samples as AI-generated (1) or human (0).

        Args:
            code_samples: List of source code strings.

        Returns:
            List of dicts with is_ai_generated, confidence, classified_at.
        """
        if not self._is_fitted or self.model is None or self.vectorizer is None:
            raise RuntimeError("Classifier has not been fitted yet")

        results: List[Dict[str, Any]] = []
        for code in code_samples:
            self._validate_code_size(code)
            cleaned = self._sanitize_code(code)
            X = self.vectorizer.transform([cleaned])
            prob = self.model.predict_proba(X)[0]
            pred = int(self.model.predict(X)[0])
            confidence = float(max(prob))
            results.append(
                {
                    "is_ai_generated": bool(pred == 1),
                    "confidence": confidence,
                    "classified_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        return results

    def predict_single(self, code: str) -> Dict[str, Any]:
        """Classify a single code sample (convenience wrapper)."""
        return self.predict([code])[0]

    @classmethod
    def load(
        cls, model_path: str, vectorizer_path: Optional[str] = None
    ) -> "CodeClassifier":
        """Load a previously saved classifier from disk.

        Args:
            model_path: Path to the saved model file.
            vectorizer_path: Optional path to the saved vectorizer.

        Returns:
            CodeClassifier instance with model restored.
        """
        model = joblib.load(model_path)
        vectorizer = (
            joblib.load(vectorizer_path) if vectorizer_path else None
        )
        clf = cls(
            model_path=model_path,
            vectorizer_path=vectorizer_path,
        )
        clf.model = model
        clf.vectorizer = vectorizer
        clf._is_fitted = True
        logger.info("Classifier loaded from %s", model_path)
        return clf