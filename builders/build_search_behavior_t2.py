#!/usr/bin/env python3
"""
build_search_behavior_t2.py
──────────────────────────
從 T1 raw parquet 產出 search-behavior 的 T2 day-keyed report parquet。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from common.data_pipeline import (
    ensure_pipeline_directories,
    t2_report_date_dir,
    update_t2_manifest_dates,
)
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

GENERAL_SEARCH_IDS = ["search-general-keyword", "search-general-submit", "search-general"]
AI_SEARCH_IDS = ["search-ai-keyword", "search-ai-submit", "search-ai",
                 "search-ai-voice-input", "search-ai-chat-mode"]
QUICK_FILTER_IDS = ["T-job-location", "T-job-category"]
SEARCH_PAGE_IDS = ["search-job-page", "search-corp-page", "search-gig-page", "search-intern-page"]

REPORT_NAME = "search-behavior"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
FEATURE_COUNTS_FILE = "feature_counts.parquet"
SEARCH_PAGE_DIST_FILE = "search_page_dist.parquet"

SEARCH_PAGE_LABELS = {
    "search-job-page": "正職",
    "search-corp-page": "企業",
    "search-gig-page": "兼差",
    "search-intern-page": "實習",
}

ALL_FEATURE_IDS = SEARCH_PAGE_IDS + GENERAL_SEARCH_IDS + AI_SEARCH_IDS + QUICK_FILTER_IDS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 search-behavior 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def build_search_behavior_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "event_type", "feature_id"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["feature_id"].isin(ALL_FEATURE_IDS)].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        def _sum(ids: list[str], et: str) -> int:
            return int(day_df[day_df["feature_id"].isin(ids) & day_df["event_type"].eq(et)].shape[0])

        pd.DataFrame([{
            "date": target_date,
            "general_click":     _sum(GENERAL_SEARCH_IDS, "click"),
            "general_view":      _sum(GENERAL_SEARCH_IDS, "view"),
            "ai_click":          _sum(AI_SEARCH_IDS, "click"),
            "ai_view":           _sum(AI_SEARCH_IDS, "view"),
            "quick_click":       _sum(QUICK_FILTER_IDS, "click"),
            "quick_view":        _sum(QUICK_FILTER_IDS, "view"),
            "search_page_click": _sum(SEARCH_PAGE_IDS, "click"),
            "search_page_view":  _sum(SEARCH_PAGE_IDS, "view"),
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        feature_counts = (
            day_df.groupby(["event_type", "feature_id"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values(["event_type", "count", "feature_id"], ascending=[True, False, True])
        )
        feature_counts.to_parquet(output_dir / FEATURE_COUNTS_FILE, index=False)

        search_page_dist = feature_counts[feature_counts["feature_id"].isin(SEARCH_PAGE_IDS)].copy()
        search_page_dist["name"] = search_page_dist["feature_id"].map(SEARCH_PAGE_LABELS).fillna(search_page_dist["feature_id"])
        search_page_dist[["event_type", "name", "count"]].to_parquet(output_dir / SEARCH_PAGE_DIST_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "feature_counts": rel(FEATURE_COUNTS_FILE),
                "search_page_dist": rel(SEARCH_PAGE_DIST_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_search_behavior_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
