"""Tests for the data_collection module using mocked requests."""

from unittest.mock import MagicMock, patch

from data_collection import GitHubAPI


def test_github_api_default_base_url():
    client = GitHubAPI()
    assert client.BASE_URL == "https://api.github.com"


def test_get_repository_returns_metadata():
    client = GitHubAPI(token="test-token")
    mock_response = MagicMock()
    mock_response.headers = {"X-RateLimit-Remaining": "100"}
    mock_response.json.return_value = {
        "name": "react",
        "owner": {"login": "facebook"},
        "description": "A JavaScript library",
        "language": "JavaScript",
        "created_at": "2024-01-01T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.session, "get", return_value=mock_response) as mock_get:
        result = client.get_repository("facebook", "react")
        assert result["name"] == "react"
        assert result["owner"] == "facebook"
        assert result["language"] == "JavaScript"
        mock_get.assert_called_once()


def test_get_repository_invalid_owner():
    client = GitHubAPI()
    with patch.object(client, "_validate_owner_repo", side_effect=ValueError("bad")):
        try:
            client.get_repository("bad owner!", "repo")
        except ValueError:
            pass


def test_get_commits_pagination():
    client = GitHubAPI(token="test-token")

    page1 = MagicMock()
    page1.headers = {"X-RateLimit-Remaining": "100"}
    page1.json.return_value = [
        {"sha": "sha1", "commit": {"author": {"name": "a", "email": "a@x.com", "date": "2024-01-01T00:00:00Z"}}, "stats": {"additions": 1, "deletions": 0, "total": 1}, "html_url": "u1"},
    ]
    page1.links = {}
    page1.raise_for_status = MagicMock()

    with patch.object(client.session, "get", return_value=page1):
        commits = client.get_commits("owner", "repo", max_commits=1)
        assert len(commits) == 1
        assert commits[0]["sha"] == "sha1"


def test_normalise_commit():
    item = {
        "sha": "abc123",
        "commit": {
            "author": {"name": "Alice", "email": "alice@x.com", "date": "2024-01-01T10:00:00Z"},
            "message": "Fix bug",
        },
        "stats": {"additions": 10, "deletions": 5, "total": 15},
        "html_url": "https://github.com/o/r/commit/abc123",
    }
    result = GitHubAPI._normalise_commit(item)
    assert result["sha"] == "abc123"
    assert result["author_name"] == "Alice"
    assert result["message"] == "Fix bug"
    assert result["additions"] == 10
    assert result["deletions"] == 5
    assert result["total_changes"] == 15
