"""Thin wrapper around the GitHub REST API v3.

Handles: auth headers, Link-header pagination, basic rate-limit awareness,
and transparent caching via SqliteCache so repeated CLI runs are cheap.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from .cache import SqliteCache
from .config import Settings


class GitHubAPIError(RuntimeError):
    """Raised for non-recoverable GitHub API failures (auth, 404, etc.)."""


class RateLimitError(GitHubAPIError):
    """Raised when the API rate limit is exhausted and cannot be waited out."""


class GitHubClient:
    def __init__(self, settings: Settings, cache: SqliteCache | None = None, use_cache: bool = True):
        self.settings = settings
        self.use_cache = use_cache
        self.cache = cache or SqliteCache(settings.cache_db, settings.cache_ttl_seconds)
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "RepoPulse/0.1"}
        if settings.token:
            headers["Authorization"] = f"Bearer {settings.token}"
        self.session.headers.update(headers)

    # -- low-level ---------------------------------------------------
    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(0, reset - int(time.time()))
            raise RateLimitError(
                f"GitHub API rate limit exhausted. Resets in {wait}s. "
                "Pass --token or set GITHUB_TOKEN for a higher limit."
            )
        if resp.status_code == 404:
            raise GitHubAPIError(f"Not found: {url}. Check the owner/repo name.")
        if resp.status_code == 401:
            raise GitHubAPIError("Authentication failed. Check your GitHub token.")
        resp.raise_for_status()
        return resp

    def _paginated_get(self, url: str, params: dict | None = None, max_pages: int = 20) -> list[dict]:
        cache_key = f"GET:{url}:{params}"
        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        results: list[Any] = []
        page_params = dict(params or {})
        page_params.setdefault("per_page", 100)
        next_url: str | None = url
        pages_fetched = 0

        while next_url and pages_fetched < max_pages:
            resp = self._get(next_url, params=page_params if pages_fetched == 0 else None)
            data = resp.json()
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
            next_url = resp.links.get("next", {}).get("url")
            pages_fetched += 1

        if self.use_cache:
            self.cache.set(cache_key, results)
        return results

    # -- high-level endpoints -----------------------------------------
    def get_repo(self, owner: str, repo: str) -> dict:
        url = f"{self.settings.api_base}/repos/{owner}/{repo}"
        result = self._paginated_get(url, max_pages=1)
        return result[0] if result else {}

    def list_commits(
        self, owner: str, repo: str, since: str | None = None, until: str | None = None
    ) -> list[dict]:
        url = f"{self.settings.api_base}/repos/{owner}/{repo}/commits"
        params = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self._paginated_get(url, params=params)

    def list_pulls(self, owner: str, repo: str, state: str = "closed") -> list[dict]:
        url = f"{self.settings.api_base}/repos/{owner}/{repo}/pulls"
        return self._paginated_get(url, params={"state": state, "sort": "created", "direction": "desc"})

    def list_issues(self, owner: str, repo: str, state: str = "closed") -> list[dict]:
        """Note: GitHub's /issues endpoint also returns PRs; callers should
        filter out entries containing a 'pull_request' key if they want
        issues only."""
        url = f"{self.settings.api_base}/repos/{owner}/{repo}/issues"
        return self._paginated_get(url, params={"state": state, "sort": "created", "direction": "desc"})

    def get_languages(self, owner: str, repo: str) -> dict:
        url = f"{self.settings.api_base}/repos/{owner}/{repo}/languages"
        result = self._paginated_get(url, max_pages=1)
        return result[0] if result else {}
