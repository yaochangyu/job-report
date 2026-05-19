#!/usr/bin/env python3
"""
build_feature_engagement_t2.py
─────────────────────────────
從 T1 raw parquet 產出 feature-engagement 的 T2 day-keyed report parquet。
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

EXPLORE_JOB_IDS = ["explore-jobs-organic", "explore-jobs-organic-corp"]
EXPLORE_CORP_IDS = [
    "explore-company-corp", "explore-company-job1", "explore-company-job2",
    "explore-company-job-more", "explore-company-manufacturing",
    "explore-company-service", "explore-company-next",
]
IDENTITY_IDS = [
    "identify-returning", "identify-student", "identify-worker",
    "identify-professional", "identify-senior", "identify-fresh", "identify-personal",
]
NEWS_IDS = ["news-card-1", "news-card-2", "news-card-3", "news-card-4",
            "news-workplace", "news-industry"]

REPORT_NAME = "feature-engagement"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
EXPLORE_JOBS_FEATURES_FILE = "explore_jobs_features.parquet"
EXPLORE_JOBS_CATEGORY_TABS_FILE = "explore_jobs_category_tabs.parquet"
EXPLORE_CORP_FEATURES_FILE = "explore_corp_features.parquet"
IDENTITY_MAIN_FILE = "identity_main.parquet"
IDENTITY_ALL_FILE = "identity_all.parquet"
NEWS_FEATURES_FILE = "news_features.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 feature-engagement 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def _count_by_value(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        frame.groupby(["event_type", column], as_index=False)
        .size()
        .rename(columns={column: "name", "size": "count"})
        .sort_values(["event_type", "count", "name"], ascending=[True, False, True])
    )


def build_feature_engagement_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "system", "event_type", "feature_id", "category_tab", "identity_type"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["feature_id"].notna()].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        explore_jobs_df = day_df[day_df["feature_id"].isin(EXPLORE_JOB_IDS)].copy()
        explore_corp_df = day_df[day_df["feature_id"].isin(EXPLORE_CORP_IDS)].copy()
        identity_df = day_df[day_df["feature_id"].fillna("").str.startswith("identify-")].copy()
        news_df = day_df[day_df["feature_id"].isin(NEWS_IDS)].copy()

        def _sum(frame: pd.DataFrame, et: str) -> int:
            return int((frame["event_type"] == et).sum())

        pd.DataFrame([{
            "date": target_date,
            "explore_jobs_click": _sum(explore_jobs_df, "click"),
            "explore_jobs_view":  _sum(explore_jobs_df, "view"),
            "explore_corp_click": _sum(explore_corp_df, "click"),
            "explore_corp_view":  _sum(explore_corp_df, "view"),
            "identity_click": _sum(identity_df, "click"),
            "identity_view":  _sum(identity_df, "view"),
            "news_click": _sum(news_df, "click"),
            "news_view":  _sum(news_df, "view"),
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        _count_by_value(explore_jobs_df, "feature_id").to_parquet(output_dir / EXPLORE_JOBS_FEATURES_FILE, index=False)
        _count_by_value(explore_jobs_df, "category_tab").to_parquet(output_dir / EXPLORE_JOBS_CATEGORY_TABS_FILE, index=False)
        _count_by_value(explore_corp_df, "feature_id").to_parquet(output_dir / EXPLORE_CORP_FEATURES_FILE, index=False)

        identity_all = _count_by_value(identity_df, "feature_id")
        identity_all.to_parquet(output_dir / IDENTITY_ALL_FILE, index=False)
        identity_main = identity_all[identity_all["name"].isin(IDENTITY_IDS)].copy()
        identity_main["name"] = identity_main["name"].str.replace("identify-", "", regex=False)
        identity_main.to_parquet(output_dir / IDENTITY_MAIN_FILE, index=False)

        _count_by_value(news_df, "feature_id").to_parquet(output_dir / NEWS_FEATURES_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "explore_jobs_features": rel(EXPLORE_JOBS_FEATURES_FILE),
                "explore_jobs_category_tabs": rel(EXPLORE_JOBS_CATEGORY_TABS_FILE),
                "explore_corp_features": rel(EXPLORE_CORP_FEATURES_FILE),
                "identity_main": rel(IDENTITY_MAIN_FILE),
                "identity_all": rel(IDENTITY_ALL_FILE),
                "news_features": rel(NEWS_FEATURES_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_feature_engagement_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
