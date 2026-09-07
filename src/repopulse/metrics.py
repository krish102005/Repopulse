"""Pure functions that turn raw GitHub API payloads into metrics.

Kept free of any network/IO calls so they're trivial to unit test with
small hand-built fixtures.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean, median


def _parse_iso(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def commit_frequency(commits: list[dict], granularity: str = "week") -> dict[str, int]:
    """Bucket commits by ISO week ('YYYY-Www') or day ('YYYY-MM-DD')."""
    buckets: Counter[str] = Counter()
    for c in commits:
        date_str = c.get("commit", {}).get("author", {}).get("date")
        if not date_str:
            continue
        dt = _parse_iso(date_str)
        if granularity == "day":
            key = dt.strftime("%Y-%m-%d")
        else:
            iso_year, iso_week, _ = dt.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
        buckets[key] += 1
    return dict(sorted(buckets.items()))


def top_contributors(commits: list[dict], n: int = 10) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for c in commits:
        author = c.get("author") or {}
        login = author.get("login") if author else None
        if not login:
            login = c.get("commit", {}).get("author", {}).get("name", "unknown")
        counts[login] += 1
    return counts.most_common(n)


def pr_merge_times(pulls: list[dict]) -> dict[str, float | None]:
    """Average/median hours from PR creation to merge, for merged PRs only."""
    hours: list[float] = []
    for p in pulls:
        if not p.get("merged_at"):
            continue
        created = _parse_iso(p["created_at"])
        merged = _parse_iso(p["merged_at"])
        hours.append((merged - created).total_seconds() / 3600)
    if not hours:
        return {"count": 0, "avg_hours": None, "median_hours": None}
    return {
        "count": len(hours),
        "avg_hours": round(mean(hours), 2),
        "median_hours": round(median(hours), 2),
    }


def issue_resolution_times(issues: list[dict]) -> dict[str, float | None]:
    """Average/median hours from issue creation to close. Filters out PRs,
    which GitHub's /issues endpoint also includes."""
    hours: list[float] = []
    for i in issues:
        if "pull_request" in i:
            continue
        if not i.get("closed_at"):
            continue
        created = _parse_iso(i["created_at"])
        closed = _parse_iso(i["closed_at"])
        hours.append((closed - created).total_seconds() / 3600)
    if not hours:
        return {"count": 0, "avg_hours": None, "median_hours": None}
    return {
        "count": len(hours),
        "avg_hours": round(mean(hours), 2),
        "median_hours": round(median(hours), 2),
    }


def language_breakdown(languages: dict[str, int]) -> dict[str, float]:
    """Convert raw byte counts per language into rounded percentages."""
    total = sum(languages.values())
    if total == 0:
        return {}
    return {lang: round(100 * bytes_ / total, 1) for lang, bytes_ in sorted(
        languages.items(), key=lambda kv: kv[1], reverse=True
    )}


def commit_churn_by_file_extension(commits_with_files: list[dict]) -> dict[str, int]:
    """Given commit detail payloads (each with a 'files' list containing
    'filename' and 'changes'), sum changed lines per file extension."""
    churn: defaultdict[str, int] = defaultdict(int)
    for commit in commits_with_files:
        for f in commit.get("files", []):
            filename = f.get("filename", "")
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "(no ext)"
            churn[ext] += f.get("changes", 0)
    return dict(sorted(churn.items(), key=lambda kv: kv[1], reverse=True))
