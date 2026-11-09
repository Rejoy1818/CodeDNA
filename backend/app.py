"""CodeDNA — Flask backend application (security-hardened).

Provides REST API endpoints for:
- Repository data collection from GitHub API
- Preprocessing and feature extraction
- Anomaly detection (Isolation Forest)
- Commit message NLP analysis
- Productivity trend estimation
- AI vs human code classification
- Dashboard data retrieval

Security measures:
- python-dotenv for secret management (SECRET_KEY, GITHUB_TOKEN, API keys)
- Flask-Talisman security headers (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- Flask-Limiter rate limiting (default 100/day, 10/hour; stricter on mutating endpoints)
- Restricted CORS via CORS_ORIGIN environment variable
- API key authentication with role-based access control (admin/user) from API_KEYS env var
- Input validation and sanitization on all request bodies
- Generic error messages (no internal leakage)
- debug=False, host="127.0.0.1" in production
- Duplicate commit check before insert (B4)
"""

import os
import json
import logging
import re
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

import pandas as pd

from dotenv import load_dotenv
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.exc import IntegrityError

from database import (
    init_db, get_session, get_engine,
    Repository, Commit, Feature, Anomaly,
    ClassificationResult,
)
from data_collection import GitHubAPI
from preprocessing import aggregate_commits
from features import extract_features, features_to_dataframe
from anomaly_detection import AnomalyDetector
from nlp_analysis import extract_message_features, analyse_message_trends
from productivity import compute_productivity_indicators, compute_productivity_over_time
from code_classifier import CodeClassifier

# ---------------------------------------------------------------------------
# Environment & logging
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32).hex())

# CORS — restricted to trusted origin(s)
_cors_origin = os.getenv("CORS_ORIGIN")
if _cors_origin:
    CORS(app, origins=[o.strip() for o in _cors_origin.split(",")])
else:
    CORS(app, origins=[])  # No cross-origin access by default

# Flask-Talisman security headers
_is_production = os.getenv("FLASK_ENV", "development") == "production"
Talisman(
    app,
    force_https=_is_production,
    strict_transport_security=_is_production,
    frame_options="DENY",
    content_security_policy={
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline']"],
        "img-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
    },
    content_security_policy_nonce_in=["script-src"],
    referrer_policy="strict-origin-when-cross-origin",
)

# Rate limiting — default 100 per day, 10 per hour
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per day", "10 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URL", "memory://"),
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = os.getenv("CODEDNA_DB", "sqlite:///codedna.db")
engine = init_db(DB_PATH)

# GitHub API client (lazy initialisation)
_github_client = None


def get_github_client() -> GitHubAPI:
    global _github_client
    if _github_client is None:
        _github_client = GitHubAPI()
    return _github_client


# ---------------------------------------------------------------------------
# Authentication helpers — API keys from env var (key:role pairs)
# ---------------------------------------------------------------------------

API_KEY_HEADER = "X-API-Key"


def _parse_api_keys() -> dict:
    """Parse API_KEYS env var into a {key: role} mapping.

    Format: key1:admin,key2:user,key3:user
    Entries without a role default to "user".
    """
    raw = os.getenv("API_KEYS", "")
    keys: dict = {}
    if not raw:
        return keys
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            key, role = entry.split(":", 1)
            key = key.strip()
            role = role.strip() or "user"
        else:
            key = entry
            role = "user"
        if key:
            keys[key] = role
    return keys


_API_KEYS = _parse_api_keys()


def _get_api_key() -> Optional[str]:
    """Extract API key from request headers."""
    key = request.headers.get(API_KEY_HEADER)
    if not key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
    return key


def require_api_key(f):
    """Decorator: require a valid API key from the API_KEYS env mapping."""

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = _get_api_key()
        if not api_key:
            return jsonify({"error": "Authentication required"}), 401
        role = _API_KEYS.get(api_key)
        if role is None:
            return jsonify({"error": "Invalid or inactive API key"}), 401
        g.current_token = api_key
        g.current_user_role = role
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator: require admin role (must be stacked after require_api_key)."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Input validation / sanitization
# ---------------------------------------------------------------------------

_OWNER_REPO_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?$")
_MAX_FILE_PATH_LEN = 500


def _validate_owner_repo(owner: str, repo: str) -> None:
    if not owner or not repo:
        raise ValueError("owner and repo are required")
    if len(owner) > 39:
        raise ValueError("owner name too long")
    if len(repo) > 100:
        raise ValueError("repo name too long")
    if not _OWNER_REPO_RE.match(owner):
        raise ValueError("owner contains invalid characters")
    if not _OWNER_REPO_RE.match(repo):
        raise ValueError("repo contains invalid characters")


def _parse_max_commits(data: dict, default: int = 500) -> int:
    raw = data.get("max_commits", default)
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ValueError("max_commits must be a valid integer")
    if value < 1 or value > 10000:
        raise ValueError("max_commits must be between 1 and 10000")
    return value


def _sanitize_file_path(value: str) -> str:
    """Trim and cap file_path to avoid oversized DB values."""
    if not isinstance(value, str):
        return ""
    return value[:_MAX_FILE_PATH_LEN]


def _get_json_body() -> dict:
    """Safely parse JSON body, returning empty dict on failure."""
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Error handlers — generic messages, no leakage
# ---------------------------------------------------------------------------

@app.errorhandler(400)
def _bad_request(e):
    return jsonify({"error": "Invalid request"}), 400


@app.errorhandler(401)
def _unauthorized(e):
    return jsonify({"error": "Authentication required"}), 401


@app.errorhandler(403)
def _forbidden(e):
    return jsonify({"error": "Access denied"}), 403


@app.errorhandler(404)
def _not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(429)
def _rate_limited(e):
    return jsonify({"error": "Rate limit exceeded. Try again later."}), 429


@app.errorhandler(500)
def _internal_error(e):
    logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
@limiter.limit("100 per minute")
def health():
    return jsonify({"status": "ok", "service": "codedna-backend"})


# ---------------------------------------------------------------------------
# Repository collection (auth required)
# ---------------------------------------------------------------------------

@app.route("/api/repositories/collect", methods=["POST"])
@require_api_key
@limiter.limit("10 per minute")
def collect_repository():
    """Collect repository data from GitHub API.

    Body: { "owner": "string", "repo": "string", "max_commits": 500 }
    """
    try:
        data = _get_json_body()
        owner = data.get("owner", "")
        repo = data.get("repo", "")
        _validate_owner_repo(owner, repo)
        max_commits = _parse_max_commits(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Check for duplicate repository (owner + repo_name unique constraint)
    session = get_session(DB_PATH)
    try:
        existing = (
            session.query(Repository)
            .filter_by(owner=owner, repo_name=repo)
            .first()
        )
        if existing:
            return jsonify({"error": "Repository already being tracked"}), 409
    finally:
        session.close()

    client = get_github_client()
    try:
        result = client.collect_repository_data(owner, repo, max_commits=max_commits)
    except Exception:
        logger.exception("GitHub API collection failed for %s/%s", owner, repo)
        return jsonify({"error": "Failed to collect repository data"}), 502

    if "error" in result:
        return jsonify({"error": "Repository not found or inaccessible"}), 404

    # Persist to database
    session = get_session(DB_PATH)
    try:
        repo_meta = result["repository"]
        db_repo = Repository(
            repo_name=repo_meta["name"],
            owner=repo_meta["owner"],
            description=repo_meta.get("description"),
            language=repo_meta.get("language"),
            last_collected=datetime.now(timezone.utc),
        )
        session.add(db_repo)
        session.flush()

        commits = result["commits"]
        seen_shas = set()
        for c in commits:
            sha = c.get("sha", "")
            if not sha:
                continue
            # Fix B4: skip duplicate commit SHAs within the batch
            if sha in seen_shas:
                continue
            seen_shas.add(sha)

            # Fix B4: check exists before insert in the database
            existing_commit = (
                session.query(Commit)
                .filter_by(repo_id=db_repo.id, sha=sha)
                .first()
            )
            if existing_commit:
                continue

            commit_date = None
            if c.get("commit_date"):
                try:
                    commit_date = datetime.fromisoformat(
                        c["commit_date"].replace("Z", "+00:00")
                    )
                except ValueError:
                    commit_date = datetime.now(timezone.utc)

            db_commit = Commit(
                repo_id=db_repo.id,
                sha=sha,
                author_name=c.get("author_name", ""),
                author_email=c.get("author_email", ""),
                commit_date=commit_date,
                message=c.get("message", ""),
                additions=c.get("additions", 0),
                deletions=c.get("deletions", 0),
                total_changes=c.get("total_changes", 0),
            )
            session.add(db_commit)

        session.commit()
        logger.info(
            "Stored repository %s/%s with %d commits", owner, repo, len(commits)
        )

        return jsonify({
            "repository": repo_meta,
            "commit_count": len(commits),
            "message": "Repository collected successfully",
        })
    except IntegrityError:
        session.rollback()
        return jsonify({"error": "Repository already being tracked"}), 409
    except Exception:
        session.rollback()
        logger.exception("Failed to persist repository data")
        return jsonify({"error": "Failed to save repository data"}), 500
    finally:
        session.close()


@app.route("/api/repositories", methods=["GET"])
@require_api_key
@limiter.limit("60 per minute")
def list_repositories():
    """List all tracked repositories."""
    session = get_session(DB_PATH)
    try:
        repos = session.query(Repository).all()
        return jsonify([
            {
                "id": r.id,
                "name": r.repo_name,
                "owner": r.owner,
                "description": r.description,
                "language": r.language,
                "created_at": (
                    r.created_at.isoformat() if r.created_at else None
                ),
                "last_collected": (
                    r.last_collected.isoformat() if r.last_collected else None
                ),
            }
            for r in repos
        ])
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Features & analysis
# ---------------------------------------------------------------------------

def _get_commit_dicts(session, repo_id: int) -> list:
    """Fetch commits for a repo as dicts."""
    commits = session.query(Commit).filter_by(repo_id=repo_id).all()
    return [
        {
            "sha": c.sha,
            "author_name": c.author_name,
            "author_email": c.author_email,
            "commit_date": (
                c.commit_date.isoformat() if c.commit_date else None
            ),
            "message": c.message,
            "additions": c.additions,
            "deletions": c.deletions,
            "total_changes": c.total_changes,
        }
        for c in commits
    ]


@app.route("/api/repositories/<int:repo_id>/features", methods=["GET"])
@require_api_key
@limiter.limit("30 per minute")
def get_features(repo_id: int):
    """Compute and return behavioural features for a repository."""
    session = get_session(DB_PATH)
    try:
        commit_dicts = _get_commit_dicts(session, repo_id)
        if not commit_dicts:
            return jsonify({"error": "No commits found for this repository"}), 404

        df = aggregate_commits(commit_dicts)
        if df.empty:
            return jsonify({"error": "No commits found for this repository"}), 404

        # features.py expects a "date" column; add it from commit_date
        if "date" not in df.columns and "commit_date" in df.columns:
            df["date"] = df["commit_date"].dt.date

        features = extract_features(df)

        # Persist features
        db_feature = Feature(
            repo_id=repo_id,
            commits_per_day=features["commits_per_day"],
            active_days=features["active_days"],
            weekend_activity=features["weekend_activity"],
            avg_commits_per_week=features["avg_commits_per_week"],
            time_of_day_distribution=json.dumps(
                features["time_of_day_distribution"]
            ),
            avg_gap_between_commits_hours=features[
                "avg_gap_between_commits_hours"
            ],
            code_change_volume=features["code_change_volume"],
        )
        session.add(db_feature)
        session.commit()

        return jsonify(features)
    finally:
        session.close()


@app.route("/api/repositories/<int:repo_id>/anomalies", methods=["GET"])
@require_api_key
@limiter.limit("20 per minute")
def detect_anomalies(repo_id: int):
    """Run Isolation Forest anomaly detection on repository features."""
    session = get_session(DB_PATH)
    try:
        commit_dicts = _get_commit_dicts(session, repo_id)
        if not commit_dicts:
            return jsonify({"error": "No commits found"}), 404

        df = aggregate_commits(commit_dicts)
        if df.empty:
            return jsonify({"error": "No commits found"}), 404

        if "date" not in df.columns and "commit_date" in df.columns:
            df["date"] = df["commit_date"].dt.date

        feature_df = features_to_dataframe([extract_features(df)])
        if feature_df.empty:
            return jsonify({"error": "Could not compute features"}), 500

        # Multi-sample baseline: combine current features with all existing
        # feature rows so Isolation Forest isn't fit on a single sample.
        all_features = session.query(Feature).all()
        baseline_rows = [extract_features(df)]
        for f in all_features:
            baseline_rows.append({
                "commits_per_day": f.commits_per_day,
                "active_days": f.active_days,
                "weekend_activity": f.weekend_activity,
                "avg_commits_per_week": f.avg_commits_per_week,
                "avg_gap_between_commits_hours": f.avg_gap_between_commits_hours,
                "code_change_volume": f.code_change_volume,
            })
        baseline_df = features_to_dataframe(baseline_rows)

        detector = AnomalyDetector(contamination=0.1)
        try:
            detector.fit(baseline_df)
        except ValueError:
            return jsonify({
                "message": "Insufficient data for anomaly detection",
                "anomalies": [],
            })

        result = detector.predict(feature_df)
        is_anomaly = bool(result[0]["is_anomaly"])
        anomaly_score = float(result[0]["anomaly_score"])

        # Persist
        db_anomaly = Anomaly(
            repo_id=repo_id,
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
        )
        session.add(db_anomaly)
        session.commit()

        return jsonify({
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
        })
    finally:
        session.close()


# ---------------------------------------------------------------------------
# NLP analysis
# ---------------------------------------------------------------------------

@app.route("/api/repositories/<int:repo_id>/nlp", methods=["GET"])
@require_api_key
@limiter.limit("30 per minute")
def get_nlp(repo_id: int):
    """Return NLP analysis of commit messages."""
    session = get_session(DB_PATH)
    try:
        commit_dicts = _get_commit_dicts(session, repo_id)
        if not commit_dicts:
            return jsonify({"error": "No commits found"}), 404

        df = aggregate_commits(commit_dicts)
        if df.empty:
            return jsonify({"error": "No commits found"}), 404

        if "date" not in df.columns and "commit_date" in df.columns:
            df["date"] = df["commit_date"].dt.date

        features = extract_message_features(df)
        trends = analyse_message_trends(df)

        return jsonify({
            "message_features": features,
            "trends": (
                trends.to_dict(orient="records") if not trends.empty else []
            ),
        })
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Productivity
# ---------------------------------------------------------------------------

@app.route("/api/repositories/<int:repo_id>/productivity", methods=["GET"])
@require_api_key
@limiter.limit("30 per minute")
def get_productivity(repo_id: int):
    """Return productivity indicators and trends."""
    session = get_session(DB_PATH)
    try:
        commit_dicts = _get_commit_dicts(session, repo_id)
        if not commit_dicts:
            return jsonify({"error": "No commits found"}), 404

        df = aggregate_commits(commit_dicts)
        if df.empty:
            return jsonify({"error": "No commits found"}), 404

        if "date" not in df.columns and "commit_date" in df.columns:
            df["date"] = df["commit_date"].dt.date

        indicators = compute_productivity_indicators(df)
        over_time = compute_productivity_over_time(df, freq="W")

        return jsonify({
            "indicators": indicators,
            "over_time": (
                over_time.to_dict(orient="records") if not over_time.empty else []
            ),
        })
    finally:
        session.close()


# ---------------------------------------------------------------------------
# AI code classification (train: admin required; predict: auth required)
# ---------------------------------------------------------------------------

@app.route("/api/classify/train", methods=["POST"])
@require_api_key
@admin_required
@limiter.limit("5 per minute")
def train_classifier():
    """Train the AI-code classifier. Admin only.

    Body: { "samples": ["code1", "code2", ...], "labels": [0, 1, ...] }
    Label: 1 = AI-generated, 0 = human-written.
    """
    try:
        data = _get_json_body()
        samples = data.get("samples", [])
        labels = data.get("labels", [])

        if not isinstance(samples, list) or not isinstance(labels, list):
            return jsonify({"error": "samples and labels must be lists"}), 400
        if not samples or not labels or len(samples) != len(labels):
            return jsonify(
                {"error": "samples and labels must be non-empty and equal length"}
            ), 400

        # Validate labels are 0/1 before training
        invalid = [l for l in labels if l not in (0, 1)]
        if invalid:
            return jsonify({"error": "labels must be 0 or 1"}), 400

        classifier = CodeClassifier()
        metrics = classifier.fit(samples, labels)

        return jsonify({
            "message": "Classifier trained successfully",
            "metrics": metrics,
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Classifier training failed")
        return jsonify({"error": "Classifier training failed"}), 500


@app.route("/api/classify/predict", methods=["POST"])
@require_api_key
@limiter.limit("30 per minute")
def predict_code():
    """Predict whether a code sample is AI-generated or human-written.

    Body: { "code": "source code string", "repo_id": int, "file_path": "string" }
    """
    try:
        data = _get_json_body()
        code = data.get("code", "")

        if not isinstance(code, str) or not code.strip():
            return jsonify({"error": "code is required"}), 400

        classifier = CodeClassifier()
        try:
            model_path = os.getenv("CODEDNA_CLASSIFIER_MODEL_PATH")
            vectorizer_path = os.getenv("CODEDNA_VECTORIZER_PATH")
            if model_path:
                classifier = CodeClassifier.load(model_path, vectorizer_path)
            else:
                return jsonify({"error": "Classifier not trained yet"}), 400
        except FileNotFoundError:
            return jsonify({"error": "Classifier not trained yet"}), 400
        except Exception:
            return jsonify({"error": "Classifier not trained yet"}), 400

        results = classifier.predict([code])
        # Store classification result if repo context available (Fix B11)
        repo_id = data.get("repo_id")
        if repo_id:
            try:
                repo_id_int = int(repo_id)
            except (ValueError, TypeError):
                repo_id_int = None
            if repo_id_int is not None:
                session = get_session(DB_PATH)
                try:
                    db_result = ClassificationResult(
                        repo_id=repo_id_int,
                        file_path=_sanitize_file_path(data.get("file_path", "")),
                        is_ai_generated=results[0]["is_ai_generated"],
                        confidence=results[0]["confidence"],
                        model_version="tfidf-rf-v1",
                    )
                    session.add(db_result)
                    session.commit()
                except Exception:
                    session.rollback()
                finally:
                    session.close()

        return jsonify(results[0])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Classification prediction failed")
        return jsonify({"error": "Classification failed"}), 500


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

@app.route("/api/dashboard/<int:repo_id>", methods=["GET"])
@require_api_key
@limiter.limit("30 per minute")
def dashboard(repo_id: int):
    """Return all dashboard data for a repository in one call."""
    session = get_session(DB_PATH)
    try:
        repo = session.query(Repository).filter_by(id=repo_id).first()
        if not repo:
            return jsonify({"error": "Repository not found"}), 404

        commit_dicts = _get_commit_dicts(session, repo_id)
        if not commit_dicts:
            return jsonify({"error": "No commits found"}), 404

        df = aggregate_commits(commit_dicts)
        if df.empty:
            return jsonify({"error": "No commits found"}), 404

        if "date" not in df.columns and "commit_date" in df.columns:
            df["date"] = df["commit_date"].dt.date

        # Fix B1: convert date keys to strings for JSON serialization
        timeline = df.groupby("date").size()
        timeline_dict = {str(k): int(v) for k, v in timeline.to_dict().items()}

        return jsonify({
            "repository": {
                "id": repo.id,
                "name": repo.repo_name,
                "owner": repo.owner,
                "description": repo.description,
                "language": repo.language,
            },
            "features": extract_features(df),
            "nlp": extract_message_features(df),
            "productivity": compute_productivity_indicators(df),
            "timeline": timeline_dict,
        })
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=False,
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
    )
