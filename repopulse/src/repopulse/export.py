"""Export computed metrics to files the user (or a spreadsheet) can consume."""
from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd


def to_json(data: dict[str, Any], path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def to_csv(commit_freq: dict[str, int], top_contribs: list[tuple[str, int]], path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    freq_df = pd.DataFrame(list(commit_freq.items()), columns=["period", "commits"])
    freq_df.to_csv(path, index=False)
    return path


def to_excel(
    commit_freq: dict[str, int],
    top_contribs: list[tuple[str, int]],
    pr_stats: dict,
    issue_stats: dict,
    languages: dict[str, float],
    path: str,
) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(list(commit_freq.items()), columns=["period", "commits"]).to_excel(
            writer, sheet_name="Commit Frequency", index=False
        )
        pd.DataFrame(top_contribs, columns=["contributor", "commits"]).to_excel(
            writer, sheet_name="Top Contributors", index=False
        )
        pd.DataFrame([pr_stats]).to_excel(writer, sheet_name="PR Merge Time", index=False)
        pd.DataFrame([issue_stats]).to_excel(writer, sheet_name="Issue Resolution", index=False)
        pd.DataFrame(list(languages.items()), columns=["language", "percent"]).to_excel(
            writer, sheet_name="Languages", index=False
        )
    return path


def plot_commit_frequency(commit_freq: dict[str, int], path: str, repo_name: str = "") -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    periods = list(commit_freq.keys())
    counts = list(commit_freq.values())

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(periods, counts, color="#1F3864")
    ax.set_title(f"Commit frequency{f' — {repo_name}' if repo_name else ''}")
    ax.set_xlabel("Period")
    ax.set_ylabel("Commits")
    step = max(1, len(periods) // 15)
    ax.set_xticks(periods[::step])
    ax.set_xticklabels(periods[::step], rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
