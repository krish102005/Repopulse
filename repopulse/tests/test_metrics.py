from repopulse.metrics import (
    commit_churn_by_file_extension,
    commit_frequency,
    issue_resolution_times,
    language_breakdown,
    pr_merge_times,
    top_contributors,
)


def make_commit(login, date):
    return {
        "author": {"login": login},
        "commit": {"author": {"date": date}},
    }


def test_commit_frequency_by_week_buckets_correctly():
    commits = [
        make_commit("alice", "2025-01-06T10:00:00Z"),  # W02
        make_commit("bob", "2025-01-07T10:00:00Z"),  # same week
        make_commit("alice", "2025-01-15T10:00:00Z"),  # W03
    ]
    freq = commit_frequency(commits, granularity="week")
    assert freq == {"2025-W02": 2, "2025-W03": 1}


def test_commit_frequency_by_day():
    commits = [make_commit("alice", "2025-01-06T10:00:00Z"), make_commit("alice", "2025-01-06T18:00:00Z")]
    freq = commit_frequency(commits, granularity="day")
    assert freq == {"2025-01-06": 2}


def test_commit_frequency_skips_missing_dates():
    assert commit_frequency([{"author": {}, "commit": {}}]) == {}


def test_top_contributors_counts_and_orders():
    commits = [make_commit("alice", "2025-01-06T10:00:00Z")] * 3 + [make_commit("bob", "2025-01-06T10:00:00Z")]
    result = top_contributors(commits, n=2)
    assert result == [("alice", 3), ("bob", 1)]


def test_top_contributors_falls_back_to_commit_author_name():
    commits = [{"author": None, "commit": {"author": {"name": "Ghost User", "date": "2025-01-06T10:00:00Z"}}}]
    result = top_contributors(commits)
    assert result == [("Ghost User", 1)]


def test_pr_merge_times_handles_no_merged_prs():
    stats = pr_merge_times([{"merged_at": None, "created_at": "2025-01-01T00:00:00Z"}])
    assert stats == {"count": 0, "avg_hours": None, "median_hours": None}


def test_pr_merge_times_computes_hours():
    pulls = [
        {"created_at": "2025-01-01T00:00:00Z", "merged_at": "2025-01-01T02:00:00Z"},
        {"created_at": "2025-01-02T00:00:00Z", "merged_at": "2025-01-02T06:00:00Z"},
    ]
    stats = pr_merge_times(pulls)
    assert stats["count"] == 2
    assert stats["avg_hours"] == 4.0
    assert stats["median_hours"] == 4.0


def test_issue_resolution_times_ignores_pull_requests():
    issues = [
        {"created_at": "2025-01-01T00:00:00Z", "closed_at": "2025-01-01T05:00:00Z"},
        {"created_at": "2025-01-01T00:00:00Z", "closed_at": "2025-01-01T09:00:00Z", "pull_request": {}},
    ]
    stats = issue_resolution_times(issues)
    assert stats["count"] == 1
    assert stats["avg_hours"] == 5.0


def test_language_breakdown_percentages_sum_to_100():
    result = language_breakdown({"Python": 300, "JavaScript": 100})
    assert result == {"Python": 75.0, "JavaScript": 25.0}


def test_language_breakdown_handles_empty():
    assert language_breakdown({}) == {}


def test_commit_churn_by_file_extension():
    commits = [
        {"files": [{"filename": "app.py", "changes": 10}, {"filename": "README.md", "changes": 3}]},
        {"files": [{"filename": "utils.py", "changes": 5}, {"filename": "Makefile", "changes": 2}]},
    ]
    churn = commit_churn_by_file_extension(commits)
    assert churn["py"] == 15
    assert churn["md"] == 3
    assert churn["(no ext)"] == 2
