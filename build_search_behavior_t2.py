#!/usr/bin/env python3
"""
build_search_behavior_t2.py
──────────────────────────
從 T1 raw parquet 產出 search-behavior 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window
from search_behavior_report import AI_SEARCH_IDS, GENERAL_SEARCH_IDS, QUICK_FILTER_IDS, SEARCH_PAGE_IDS

REPORT_NAME = "search-behavior"
SUMMARY_FILE = "summary.parquet"
FEATURE_COUNTS_FILE = "feature_counts.parquet"
DAILY_TREND_FILE = "daily_trend.parquet"
SEARCH_PAGE_DIST_FILE = "search_page_dist.parquet"
AI_INTERACTION_FILE = "ai_interaction.parquet"
QUICK_OVERVIEW_FILE = "quick_overview.parquet"
QUICK_DAILY_FILE = "quick_daily.parquet"

SEARCH_PAGE_LABELS = {
    "search-job-page": "正職",
    "search-corp-page": "企業",
    "search-gig-page": "兼差",
    "search-intern-page": "實習",
}
AI_LABELS = {
    "search-ai-keyword": "AI 關鍵字",
    "search-ai-submit": "AI 送出",
    "search-ai": "AI 一般",
    "search-ai-voice-input": "語音輸入",
    "search-ai-chat-mode": "聊天模式",
}
QUICK_LABELS = {
    "T-job-location": "地區篩選",
    "T-job-category": "職類篩選",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 search-behavior 的 T2 parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    return parser.parse_args()


def _update_t2_manifest(date_from: str, date_to: str, output_dir: Path, files: dict[str, str], rows: int) -> None:
    manifest = {}
    if T2_REPORT_MANIFEST_PATH.exists():
        manifest = json.loads(T2_REPORT_MANIFEST_PATH.read_text(encoding="utf-8"))

    reports = manifest.setdefault("reports", {})
    report_manifest = reports.setdefault(REPORT_NAME, {"snapshots": {}})
    snapshot_key = f"{date_from}_{date_to}"
    report_manifest["snapshots"][snapshot_key] = {
        "date_from": date_from,
        "date_to": date_to,
        "root": str(output_dir.relative_to(output_dir.parents[2])),
        "files": files,
        "rows": rows,
        "updated_at": generated_now(),
    }
    report_manifest["available_snapshots"] = sorted(report_manifest["snapshots"].keys())

    manifest["tier"] = "t2-report"
    manifest["schema_version"] = 1
    manifest["updated_at"] = generated_now()
    T2_REPORT_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_search_behavior_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    feature_ids = SEARCH_PAGE_IDS + GENERAL_SEARCH_IDS + AI_SEARCH_IDS + QUICK_FILTER_IDS
    columns = ["date", "feature_id"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["feature_id"].isin(feature_ids)].copy()

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_counts = (
        df["feature_id"]
        .value_counts()
        .rename_axis("feature_id")
        .reset_index(name="count")
        .sort_values(["count", "feature_id"], ascending=[False, True])
    )
    feature_counts.to_parquet(output_dir / FEATURE_COUNTS_FILE, index=False)

    counts_map = dict(zip(feature_counts["feature_id"], feature_counts["count"]))
    summary = pd.DataFrame([{
        "search_page_total": sum(counts_map.get(fid, 0) for fid in SEARCH_PAGE_IDS),
        "general_total": sum(counts_map.get(fid, 0) for fid in GENERAL_SEARCH_IDS),
        "ai_total": sum(counts_map.get(fid, 0) for fid in AI_SEARCH_IDS),
        "quick_total": sum(counts_map.get(fid, 0) for fid in QUICK_FILTER_IDS),
    }])
    summary.to_parquet(output_dir / SUMMARY_FILE, index=False)

    trend_df = df[df["feature_id"].isin(GENERAL_SEARCH_IDS + AI_SEARCH_IDS)].copy()
    trend_df["is_general"] = trend_df["feature_id"].isin(GENERAL_SEARCH_IDS)
    trend_df["is_ai"] = trend_df["feature_id"].isin(AI_SEARCH_IDS)
    daily_trend = (
        trend_df.groupby("date", as_index=False)
        .agg(general=("is_general", "sum"), ai=("is_ai", "sum"))
        .sort_values("date")
    )
    total = daily_trend["general"] + daily_trend["ai"]
    daily_trend["ai_pct"] = ((daily_trend["ai"] / total.where(total != 0, 1)) * 100).round(1)
    daily_trend.to_parquet(output_dir / DAILY_TREND_FILE, index=False)

    search_page_dist = feature_counts[feature_counts["feature_id"].isin(SEARCH_PAGE_IDS)].copy()
    search_page_dist["name"] = search_page_dist["feature_id"].map(SEARCH_PAGE_LABELS).fillna(search_page_dist["feature_id"])
    search_page_dist[["name", "count"]].to_parquet(output_dir / SEARCH_PAGE_DIST_FILE, index=False)

    ai_interaction = feature_counts[feature_counts["feature_id"].isin(AI_SEARCH_IDS)].copy()
    ai_interaction["name"] = ai_interaction["feature_id"].map(AI_LABELS).fillna(ai_interaction["feature_id"])
    ai_interaction[["name", "count"]].to_parquet(output_dir / AI_INTERACTION_FILE, index=False)

    quick_overview = feature_counts[feature_counts["feature_id"].isin(QUICK_FILTER_IDS)].copy()
    quick_overview["name"] = quick_overview["feature_id"].map(QUICK_LABELS).fillna(quick_overview["feature_id"])
    quick_overview[["name", "count"]].to_parquet(output_dir / QUICK_OVERVIEW_FILE, index=False)

    quick_df = df[df["feature_id"].isin(QUICK_FILTER_IDS)].copy()
    quick_df["is_location"] = quick_df["feature_id"].eq("T-job-location")
    quick_df["is_category"] = quick_df["feature_id"].eq("T-job-category")
    quick_daily = (
        quick_df.groupby("date", as_index=False)
        .agg(location=("is_location", "sum"), category=("is_category", "sum"))
        .sort_values("date")
    )
    quick_daily.to_parquet(output_dir / QUICK_DAILY_FILE, index=False)

    _update_t2_manifest(
        date_from,
        date_to,
        output_dir,
        files={
            "summary": str((output_dir / SUMMARY_FILE).relative_to(output_dir.parents[2])),
            "feature_counts": str((output_dir / FEATURE_COUNTS_FILE).relative_to(output_dir.parents[2])),
            "daily_trend": str((output_dir / DAILY_TREND_FILE).relative_to(output_dir.parents[2])),
            "search_page_dist": str((output_dir / SEARCH_PAGE_DIST_FILE).relative_to(output_dir.parents[2])),
            "ai_interaction": str((output_dir / AI_INTERACTION_FILE).relative_to(output_dir.parents[2])),
            "quick_overview": str((output_dir / QUICK_OVERVIEW_FILE).relative_to(output_dir.parents[2])),
            "quick_daily": str((output_dir / QUICK_DAILY_FILE).relative_to(output_dir.parents[2])),
        },
        rows=len(df),
    )
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_search_behavior_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
