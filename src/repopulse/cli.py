"""RepoPulse CLI.

Usage:
    repopulse analyze octocat/Hello-World
    repopulse analyze psf/requests --since 2025-01-01 --export xlsx --plot
"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .cache import SqliteCache
from .config import load_settings
from .export import plot_commit_frequency, to_csv, to_excel, to_json
from .github_client import GitHubAPIError, GitHubClient
from .metrics import (
    commit_frequency,
    issue_resolution_times,
    language_breakdown,
    pr_merge_times,
    top_contributors,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repopulse", description="GitHub repo health analyzer")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a GitHub repository")
    analyze.add_argument("repo", help="owner/repo, e.g. psf/requests")
    analyze.add_argument("--since", help="ISO date, only include commits after this (YYYY-MM-DD)")
    analyze.add_argument("--until", help="ISO date, only include commits before this (YYYY-MM-DD)")
    analyze.add_argument("--top", type=int, default=10, help="Number of top contributors to show")
    analyze.add_argument(
        "--export", choices=["csv", "xlsx", "json", "all"], default=None,
        help="Export results to a file in the given format(s)",
    )
    analyze.add_argument("--output-dir", default="./repopulse-output", help="Where to write exports")
    analyze.add_argument("--plot", action="store_true", help="Save a commit-frequency chart PNG")
    analyze.add_argument("--token", help="GitHub token (overrides GITHUB_TOKEN env var)")
    analyze.add_argument("--no-cache", action="store_true", help="Bypass the local response cache")

    return parser


def _fmt_since(since: str | None) -> str | None:
    return f"{since}T00:00:00Z" if since else None


def _fmt_until(until: str | None) -> str | None:
    return f"{until}T23:59:59Z" if until else None


def run_analyze(args: argparse.Namespace) -> int:
    if "/" not in args.repo:
        print("Error: repo must be in 'owner/repo' format", file=sys.stderr)
        return 2
    owner, repo = args.repo.split("/", 1)

    settings = load_settings(token_override=args.token)
    cache = SqliteCache(settings.cache_db, settings.cache_ttl_seconds)
    client = GitHubClient(settings, cache=cache, use_cache=not args.no_cache)

    try:
        print(f"Fetching data for {owner}/{repo} ...")
        commits = client.list_commits(owner, repo, since=_fmt_since(args.since), until=_fmt_until(args.until))
        pulls = client.list_pulls(owner, repo, state="closed")
        issues = client.list_issues(owner, repo, state="closed")
        languages = client.get_languages(owner, repo)
    except GitHubAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    freq = commit_frequency(commits, granularity="week")
    contributors = top_contributors(commits, n=args.top)
    pr_stats = pr_merge_times(pulls)
    issue_stats = issue_resolution_times(issues)
    lang_pct = language_breakdown(languages)

    print(f"\n=== {owner}/{repo} — Engineering Health Summary ===")
    print(f"Commits analyzed: {len(commits)}")
    print(f"Closed PRs analyzed: {len(pulls)}  (merged: {pr_stats['count']})")
    print(f"Closed issues analyzed: {issue_stats['count']}")
    print("\nTop contributors:")
    for login, count in contributors:
        print(f"  {login:<25} {count} commits")
    print("\nPR merge time:")
    print(f"  avg: {pr_stats['avg_hours']} hrs   median: {pr_stats['median_hours']} hrs")
    print("\nIssue resolution time:")
    print(f"  avg: {issue_stats['avg_hours']} hrs   median: {issue_stats['median_hours']} hrs")
    print("\nLanguage breakdown:")
    for lang, pct in list(lang_pct.items())[:8]:
        print(f"  {lang:<15} {pct}%")

    if args.export:
        formats = ["csv", "xlsx", "json"] if args.export == "all" else [args.export]
        for fmt in formats:
            path = f"{args.output_dir}/{owner}_{repo}.{fmt}"
            if fmt == "csv":
                to_csv(freq, contributors, path)
            elif fmt == "xlsx":
                to_excel(freq, contributors, pr_stats, issue_stats, lang_pct, path)
            elif fmt == "json":
                to_json(
                    {
                        "repo": f"{owner}/{repo}",
                        "commit_frequency": freq,
                        "top_contributors": contributors,
                        "pr_merge_time": pr_stats,
                        "issue_resolution_time": issue_stats,
                        "languages": lang_pct,
                    },
                    path,
                )
            print(f"\nExported: {path}")

    if args.plot:
        chart_path = f"{args.output_dir}/{owner}_{repo}_commit_frequency.png"
        plot_commit_frequency(freq, chart_path, repo_name=f"{owner}/{repo}")
        print(f"Chart saved: {chart_path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return run_analyze(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
