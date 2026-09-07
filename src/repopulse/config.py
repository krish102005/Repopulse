"""Configuration loading for RepoPulse.

Reads a GitHub token from the environment (or a .env file, if python-dotenv
is available) so the CLI can make authenticated requests and get the higher
rate limit (5,000/hr vs 60/hr unauthenticated).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is an optional convenience
    pass

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_CACHE_DB = os.path.expanduser("~/.repopulse/cache.sqlite3")
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour


@dataclass(frozen=True)
class Settings:
    token: str | None
    api_base: str = GITHUB_API_BASE
    cache_db: str = DEFAULT_CACHE_DB
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS


def load_settings(token_override: str | None = None) -> Settings:
    """Build a Settings object, preferring an explicit CLI --token over env vars."""
    token = token_override or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    return Settings(token=token)
