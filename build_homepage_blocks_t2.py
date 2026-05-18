#!/usr/bin/env python3
"""
build_homepage_blocks_t2.py
────────────────────────────
從 T1 raw parquet 產出首頁區塊點擊的 T2 day-keyed report parquet。

執行方式：
    uv run python build_homepage_blocks_t2.py
    uv run python build_homepage_blocks_t2.py --days 7
    uv run python build_homepage_blocks_t2.py --from 2026-05-01 --to 2026-05-17
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common.data_pipeline import (
    ensure_pipeline_directories,
    t2_report_date_dir,
    update_t2_manifest_dates,
)
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window
from query_homepage_blocks import ALL_FEATURE_IDS

REPORT_NAME = "homepage-blocks"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
FEATURE_COUNTS_FILE = "feature_counts.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 homepage-blocks 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def build_homepage_blocks_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()

    columns = ["date", "system", "event_type", "feature_id"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[
        df["system"].eq("jobbank-web")
        & df["feature_id"].isin(ALL_FEATURE_IDS)
    ].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        feature_counts = (
            day_df.groupby(["event_type", "feature_id"], as_index=False)
            .agg(count=("feature_id", "size"))
            .assign(date=target_date)
            .sort_values(["event_type", "count", "feature_id"], ascending=[True, False, True])
        )
        feature_counts.to_parquet(output_dir / FEATURE_COUNTS_FILE, index=False)

        total_clicks = int(feature_counts[feature_counts["event_type"].eq("click")]["count"].sum())
        total_views = int(feature_counts[feature_counts["event_type"].eq("view")]["count"].sum())
        click_rows = feature_counts[feature_counts["event_type"].eq("click")]
        top_feature = click_rows.iloc[0]["feature_id"] if not click_rows.empty else ""
        top_count = int(click_rows.iloc[0]["count"]) if not click_rows.empty else 0
        pd.DataFrame([{
            "date": target_date,
            "total_clicks": total_clicks,
            "total_views": total_views,
            "feature_count": int(feature_counts["feature_id"].nunique()),
            "top_feature_id": top_feature,
            "top_count": top_count,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "feature_counts": rel(FEATURE_COUNTS_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    print(f"[INFO] 查詢區間：{date_from} ～ {date_to}")
    dirs = build_homepage_blocks_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(dirs)} 個日期分區：{REPORT_NAME}")


if __name__ == "__main__":
    main()
