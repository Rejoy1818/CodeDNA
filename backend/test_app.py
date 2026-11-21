"""Tests for the Flask application endpoints."""

import os
import tempfile

import pytest
from unittest.mock import MagicMock, patch

# Configure environment before importing app (which creates the DB engine at import time)
_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmpdb.close()
os.environ["CODEDNA_DB"] = f"sqlite:///{_tmpdb.name}"
os.environ["API_KEYS"] = "test-key:admin,user-key:user"
os.environ["RATELIMIT_STORAGE_URL"] = "memory://"

# Reset the database module's singleton engine so app.py creates one with our URL
import database  # noqa: E402
database._engine = None  # noqa: E402

from app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_collect_repository_no_auth(client):
    response = client.post(
        "/api/repositories/collect", json={"owner": "o", "repo": "r"}
    )
    assert response.status_code == 401


def test_collect_repository_invalid_input(client):
    headers = {"X-API-Key": "test-key"}
    response = client.post(
        "/api/repositories/collect", json={}, headers=headers
    )
    assert response.status_code == 400


def test_list_repositories_no_auth(client):
    response = client.get("/api/repositories")
    assert response.status_code == 401


def test_classify_train_no_auth(client):
    response = client.post(
        "/api/classify/train", json={"samples": ["a"], "labels": [0]}
    )
    assert response.status_code == 401


def test_classify_train_user_not_admin(client):
    headers = {"X-API-Key": "user-key"}
    response = client.post(
        "/api/classify/train",
        json={"samples": ["a", "b"], "labels": [0, 1]},
        headers=headers,
    )
    assert response.status_code == 403


def test_classify_predict_no_auth(client):
    response = client.post(
        "/api/classify/predict", json={"code": "x"}
    )
    assert response.status_code == 401


def test_classify_predict_no_model(client):
    headers = {"X-API-Key": "test-key"}
    response = client.post(
        "/api/classify/predict",
        json={"code": "def foo():\n    pass\n"},
        headers=headers,
    )
    assert response.status_code == 400


def test_endpoints_require_auth(client):
    """All protected endpoints return 401 without an API key."""
    protected = [
        ("GET", "/api/repositories"),
        ("GET", "/api/repositories/1/features"),
        ("GET", "/api/repositories/1/anomalies"),
        ("GET", "/api/repositories/1/nlp"),
        ("GET", "/api/repositories/1/productivity"),
        ("GET", "/api/dashboard/1"),
        ("POST", "/api/classify/train"),
        ("POST", "/api/classify/predict"),
    ]
    for method, path in protected:
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path, json={})
        assert response.status_code == 401, f"{method} {path} should require auth"


@patch("app.get_github_client")
def test_collect_repository_success(mock_get_client, client):
    mock_client = MagicMock()
    mock_client.collect_repository_data.return_value = {
        "repository": {
            "name": "react",
            "owner": "facebook",
            "description": "A JavaScript library",
            "language": "JavaScript",
        },
        "commits": [
            {
                "sha": "abc123",
                "author_name": "Alice",
                "author_email": "alice@x.com",
                "commit_date": "2024-01-01T10:00:00Z",
                "message": "Initial commit",
                "additions": 10,
                "deletions": 5,
                "total_changes": 15,
            }
        ],
        "commit_count": 1,
    }
    mock_get_client.return_value = mock_client

    headers = {"X-API-Key": "test-key"}
    response = client.post(
        "/api/repositories/collect",
        json={"owner": "facebook", "repo": "react"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["commit_count"] == 1
    assert data["repository"]["name"] == "react"
