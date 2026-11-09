"""GitHub REST API data collection module for CodeDNA.

Fetches repository metadata and commit history using the GitHub REST API.
Supports authenticated requests, input validation, retry/backoff, and
pagination for repositories with large commit histories.
"""

import os
import time
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from urllib.parse import quote
import requests
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

# GitHub owner/repo naming rules: alphanumeric, hyphens, limited length
_OWNER_REPO_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?$")
MAX_OWNER_LEN = 39
MAX_REPO_LEN = 100


class GitHubAPI:
    """Client for the GitHub REST API v3."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None, username: Optional[str] = None):
        """Initialise the GitHub API client.

        Args:
            token: GitHub personal access token (optional, recommended).
            username: GitHub username for basic auth (optional).
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.username = username or os.getenv("GITHUB_USERNAME")
        self.session = requests.Session()

        # Configure retry/backoff for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        if self.token:
            self.session.headers.update(
                {"Authorization": f"token {self.token}"}
            )
        elif self.username:
            self.session.auth = HTTPBasicAuth(self.username, self.token or "")

        self.session.headers.update(
            {"Accept": "application/vnd.github.v3+json", "User-Agent": "CodeDNA-Project"}
        )

    def _validate_owner_repo(self, owner: str, repo: str) -> None:
        """Validate owner and repo names against GitHub naming rules.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Raises:
            ValueError: If names don't match GitHub naming rules.
        """
        if not owner or not repo:
            raise ValueError("owner and repo are required")
        if len(owner) > MAX_OWNER_LEN:
            raise ValueError(f"owner name too long (max {MAX_OWNER_LEN} chars)")
        if len(repo) > MAX_REPO_LEN:
            raise ValueError(f"repo name too long (max {MAX_REPO_LEN} chars)")
        if not _OWNER_REPO_RE.match(owner):
            raise ValueError("owner contains invalid characters")
        if not _OWNER_REPO_RE.match(repo):
            raise ValueError("repo contains invalid characters")

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Sleep if we are approaching GitHub API rate limits."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining and int(remaining) < 10:
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            sleep_for = max(reset_time - int(time.time()), 0) + 1
            logger.warning("Rate limit near. Sleeping for %d seconds.", sleep_for)
            time.sleep(sleep_for)

    def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a single repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary with repository metadata, or None on failure.
        """
        self._validate_owner_repo(owner, repo)
        url = f"{self.BASE_URL}/repos/{quote(owner)}/{quote(repo)}"
        try:
            response = self.session.get(url, timeout=30)
            self._handle_rate_limit(response)
            response.raise_for_status()
            data = response.json()
            return {
                "name": data.get("name"),
                "owner": data.get("owner", {}).get("login"),
                "description": data.get("description"),
                "language": data.get("language"),
                "created_at": data.get("created_at"),
            }
        except requests.RequestException as exc:
            logger.error("Failed to fetch repository %s/%s: %s", owner, repo, exc)
            return None

    def get_commits(
        self,
        owner: str,
        repo: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        max_commits: int = 500,
    ) -> List[Dict[str, Any]]:
        """Fetch commit history for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            since: ISO 8601 timestamp to filter commits after.
            until: ISO 8601 timestamp to filter commits before.
            author: GitHub username to filter by author.
            max_commits: Maximum number of commits to fetch (1-10000).

        Returns:
            List of commit dictionaries with normalised fields.

        Raises:
            ValueError: If max_commits is out of valid range.
        """
        self._validate_owner_repo(owner, repo)

        try:
            max_commits = int(max_commits)
        except (ValueError, TypeError):
            raise ValueError("max_commits must be a valid integer")

        if max_commits < 1 or max_commits > 10000:
            raise ValueError("max_commits must be between 1 and 10000")

        url = f"{self.BASE_URL}/repos/{quote(owner)}/{quote(repo)}/commits"
        params: Dict[str, Any] = {"per_page": 100}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if author:
            params["author"] = author

        commits: List[Dict[str, Any]] = []
        fetched = 0

        while fetched < max_commits:
            try:
                response = self.session.get(url, params=params, timeout=30)
                self._handle_rate_limit(response)
                response.raise_for_status()
                page = response.json()
            except requests.RequestException as exc:
                logger.error(
                    "Failed to fetch commits for %s/%s after retries: %s",
                    owner, repo, exc,
                )
                break

            if not page:
                break

            for item in page:
                if fetched >= max_commits:
                    break
                commit_info = self._normalise_commit(item)
                commits.append(commit_info)
                fetched += 1

            if "next" not in response.links:
                break
            url = response.links["next"]["url"]
            params = {}

        logger.info("Fetched %d commits from %s/%s", len(commits), owner, repo)
        return commits

    @staticmethod
    def _normalise_commit(item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise a raw GitHub commit API response into a flat dictionary."""
        commit = item.get("commit", {})
        author = commit.get("author", {})
        stats = item.get("stats", {}) or {}

        return {
            "sha": item.get("sha", ""),
            "author_name": author.get("name", ""),
            "author_email": author.get("email", ""),
            "commit_date": author.get("date", ""),
            "message": commit.get("message", ""),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0),
            "total_changes": stats.get("total", 0),
            "html_url": item.get("html_url", ""),
        }

    def collect_repository_data(
        self, owner: str, repo: str, max_commits: int = 500
    ) -> Dict[str, Any]:
        """Collect full repository data: metadata + commits.

        Args:
            owner: Repository owner.
            repo: Repository name.
            max_commits: Maximum number of commits to fetch.

        Returns:
            Dictionary containing repo metadata and list of commits.
        """
        metadata = self.get_repository(owner, repo)
        if metadata is None:
            return {"error": f"Could not fetch repository {owner}/{repo}"}

        commits = self.get_commits(owner, repo, max_commits=max_commits)
        return {
            "repository": metadata,
            "commits": commits,
            "commit_count": len(commits),
        }