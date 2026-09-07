# RepoPulse

A command-line tool that analyzes a public GitHub repository's engineering
health: commit frequency, top contributors, PR merge time, issue resolution
time, and language breakdown — exported to CSV, Excel, or JSON, with an
optional chart.

```
$ repopulse analyze psf/requests --since 2025-01-01 --export xlsx --plot

Fetching data for psf/requests ...

=== psf/requests — Engineering Health Summary ===
Commits analyzed: 42
Closed PRs analyzed: 118  (merged: 96)
Closed issues analyzed: 73

Top contributors:
  nateprewitt              14 commits
  sigmavirus24             9 commits
  ...

PR merge time:
  avg: 38.4 hrs   median: 12.1 hrs

Issue resolution time:
  avg: 96.7 hrs   median: 44.0 hrs

Language breakdown:
  Python          98.2%
  Shell           1.1%
  ...

Exported: ./repopulse-output/psf_requests.xlsx
Chart saved: ./repopulse-output/psf_requests_commit_frequency.png
```

## Why

Recruiters and hiring managers can eyeball commit counts on GitHub, but
questions like "how fast does this team actually merge PRs?" or "who are the
real maintainers vs. one-off contributors?" require pulling and processing
data. RepoPulse automates that end to end: paginated API calls, caching,
metric computation, and export — in one CLI command.

## Features

- **Commit frequency** — weekly or daily commit counts
- **Top contributors** — ranked by commit count
- **PR merge time** — average & median hours from open to merge
- **Issue resolution time** — average & median hours from open to close
- **Language breakdown** — percentage of codebase per language
- **Exports** — CSV, Excel (multi-sheet), JSON, or all three
- **Chart** — commit-frequency bar chart saved as PNG
- **Caching** — SQLite-backed response cache (1 hr TTL) so repeat runs don't burn API quota
- **Rate-limit aware** — clear error message + reset time when the GitHub API quota is exhausted

## Installation

```bash
git clone https://github.com/<your-username>/repopulse.git
cd repopulse
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Usage

```bash
# Basic analysis, printed to the console
repopulse analyze octocat/Hello-World

# Filter by date range, export everything, save a chart
repopulse analyze psf/requests --since 2025-01-01 --until 2025-06-30 --export all --plot

# Use a token for the higher rate limit (5,000/hr vs 60/hr)
repopulse analyze torvalds/linux --token ghp_xxx
# or: export GITHUB_TOKEN=ghp_xxx   (or copy .env.example to .env and fill it in)
```

Run `repopulse analyze --help` for all options.

## Architecture

```
src/repopulse/
├── cli.py            # argparse CLI, orchestrates the pipeline
├── github_client.py  # GitHub REST API wrapper: auth, pagination, rate limits
├── cache.py           # SQLite response cache with TTL
├── metrics.py         # pure functions: raw API data -> metrics (fully unit-testable)
├── export.py          # CSV / Excel / JSON / PNG chart writers
└── config.py           # env/token loading
```

`metrics.py` has zero network or file I/O — every metric is a pure function
tested against small hand-built fixtures, so the test suite runs in
milliseconds with no live API calls. `github_client.py` is tested separately
with mocked HTTP responses covering pagination, 404s, and rate-limit errors.

## Testing

```bash
pytest --cov=repopulse --cov-report=term-missing
```

20 tests covering metric calculations, cache TTL behavior, and API client
pagination/error handling (mocked, no live network calls). Runs on Python
3.10–3.12 via GitHub Actions on every push (see `.github/workflows/ci.yml`).

## License

MIT — see [LICENSE](LICENSE).
