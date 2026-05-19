#!/usr/bin/env python3
"""
build_page_ranking_t2.py
───────────────────────
從 T1 raw parquet 產出 page-ranking 的 T2 day-keyed report parquet。
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

CATEGORY_MAP = {
    "job-page": "頁面瀏覽", "search-job-page": "頁面瀏覽", "home-page": "頁面瀏覽",
    "job-pair-page": "頁面瀏覽", "job-preview-page": "頁面瀏覽", "corp-page": "頁面瀏覽",
    "corp-preview-new-page": "頁面瀏覽", "welcome-page": "頁面瀏覽",
    "search-corp-page": "頁面瀏覽", "search-gig-page": "頁面瀏覽", "search-intern-page": "頁面瀏覽",
    "apply-job": "應徵",
    "search-general-keyword": "搜尋", "search-general-submit": "搜尋", "search-general": "搜尋",
    "search-ai-keyword": "AI 搜尋", "search-ai-submit": "AI 搜尋", "search-ai": "AI 搜尋",
    "search-ai-voice-input": "AI 搜尋", "search-ai-chat-mode": "AI 搜尋",
    "T-job-location": "快速篩選", "T-job-category": "快速篩選",
    "explore-jobs-organic": "探索功能", "explore-jobs-organic-corp": "探索功能",
    "explore-company-corp": "探索功能", "explore-company-job1": "探索功能",
    "explore-company-job2": "探索功能", "explore-company-job-more": "探索功能",
    "explore-company-manufacturing": "探索功能", "explore-company-service": "探索功能",
    "explore-company-next": "探索功能",
    "identify-returning": "身份辨識", "identify-student": "身份辨識",
    "identify-worker": "身份辨識", "identify-professional": "身份辨識",
    "identify-senior": "身份辨識", "identify-fresh": "身份辨識", "identify-personal": "身份辨識",
    "news-card-1": "新聞", "news-card-2": "新聞", "news-card-3": "新聞",
    "news-card-4": "新聞", "news-workplace": "新聞", "news-industry": "新聞",
    "company-select-job": "企業互動",
}

REPORT_NAME = "page-ranking"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
FEATURES_FILE = "features.parquet"
CATEGORIES_FILE = "categories.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 page-ranking 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def build_page_ranking_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "system", "feature_id", "event_type"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["feature_id"].notna()].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        feature_base = day_df.assign(
            is_view=day_df["event_type"].eq("view"),
            is_click=day_df["event_type"].eq("click"),
        )
        features = (
            feature_base.groupby("feature_id", as_index=False)
            .agg(
                total=("feature_id", "size"),
                views=("is_view", "sum"),
                clicks=("is_click", "sum"),
            )
            .sort_values(["total", "feature_id"], ascending=[False, True])
            .rename(columns={"feature_id": "featureId"})
        )
        features["ctr"] = ((features["clicks"] / features["total"].where(features["total"] != 0, 1)) * 100).round(2)
        features["category"] = features["featureId"].map(CATEGORY_MAP).fillna("其他")
        features.to_parquet(output_dir / FEATURES_FILE, index=False)

        categories = (
            features.groupby("category", as_index=False)["total"]
            .sum()
            .rename(columns={"category": "name", "total": "count"})
            .sort_values(["count", "name"], ascending=[False, True])
        )
        categories.to_parquet(output_dir / CATEGORIES_FILE, index=False)

        top1 = features.iloc[0] if not features.empty else None
        pd.DataFrame([{
            "date": target_date,
            "total_events": int(features["total"].sum()),
            "total_features": int(len(features)),
            "top_feature_id": top1["featureId"] if top1 is not None else "",
            "top_feature_total": int(top1["total"]) if top1 is not None else 0,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "features": rel(FEATURES_FILE),
                "categories": rel(CATEGORIES_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_page_ranking_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
