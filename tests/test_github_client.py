from unittest.mock import MagicMock, patch

import pytest

from repopulse.config import Settings
from repopulse.github_client import GitHubAPIError, GitHubClient, RateLimitError


def make_settings(tmp_path):
    return Settings(token=None, cache_db=str(tmp_path / "cache.sqlite3"))


def make_response(json_data, status_code=200, links=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.links = links or {}
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


def test_get_repo_returns_single_dict(tmp_path):
    client = GitHubClient(make_settings(tmp_path), use_cache=False)
    with patch.object(client.session, "get", return_value=make_response({"name": "Hello-World"})):
        repo = client.get_repo("octocat", "Hello-World")
    assert repo["name"] == "Hello-World"


def test_list_commits_follows_pagination(tmp_path):
    client = GitHubClient(make_settings(tmp_path), use_cache=False)
    page1 = make_response([{"sha": "a"}], links={"next": {"url": "https://api.github.com/page2"}})
    page2 = make_response([{"sha": "b"}], links={})
    with patch.object(client.session, "get", side_effect=[page1, page2]):
        commits = client.list_commits("octocat", "Hello-World")
    assert [c["sha"] for c in commits] == ["a", "b"]


def test_404_raises_github_api_error(tmp_path):
    client = GitHubClient(make_settings(tmp_path), use_cache=False)
    with patch.object(client.session, "get", return_value=make_response({}, status_code=404)), pytest.raises(GitHubAPIError):
        client.get_repo("nope", "nope")


def test_rate_limit_raises_rate_limit_error(tmp_path):
    client = GitHubClient(make_settings(tmp_path), use_cache=False)
    resp = make_response(
        {}, status_code=403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9999999999"}
    )
    with patch.object(client.session, "get", return_value=resp), pytest.raises(RateLimitError):
        client.get_repo("octocat", "Hello-World")


def test_results_are_cached_between_calls(tmp_path):
    client = GitHubClient(make_settings(tmp_path), use_cache=True)
    resp = make_response([{"sha": "a"}])
    with patch.object(client.session, "get", return_value=resp) as mock_get:
        client.list_commits("octocat", "Hello-World")
        client.list_commits("octocat", "Hello-World")
    assert mock_get.call_count == 1  # second call served from cache
