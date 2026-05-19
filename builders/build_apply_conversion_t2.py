#!/usr/bin/env python3
"""
build_apply_conversion_t2.py
───────────────────────────
從 T1 raw parquet 產出 apply-conversion 的 T2 day-keyed report parquet。
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

REPORT_NAME = "apply-conversion"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
SOURCE_FILE = "source.parquet"
FUNNEL_FILE = "funnel.parquet"
DEVICE_FILE = "device.parquet"
OS_FILE = "os.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 apply-conversion 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def _count_by_value(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        frame[column]
        .fillna("unknown")
        .value_counts(dropna=False)
        .rename_axis("name")
        .reset_index(name="count")
        .sort_values(["count", "name"], ascending=[False, True])
    )


def build_apply_conversion_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "system", "action", "feature_id", "feature_name", "event_type", "device_type", "os", "source"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web")].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        is_apply = day_df["action"].eq("apply")
        is_job_view = day_df["feature_id"].eq("job-page") & day_df["event_type"].eq("view")
        applies = int(is_apply.sum())
        job_views = int(is_job_view.sum())

        pd.DataFrame([{
            "date": target_date,
            "applies": applies,
            "job_views": job_views,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        apply_df = day_df[is_apply].copy()
        _count_by_value(apply_df, "source").to_parquet(output_dir / SOURCE_FILE, index=False)
        _count_by_value(apply_df, "device_type").to_parquet(output_dir / DEVICE_FILE, index=False)
        _count_by_value(apply_df, "os").to_parquet(output_dir / OS_FILE, index=False)

        pd.DataFrame([
            {"name": "首頁瀏覽", "count": int((day_df["feature_id"].eq("home-page") & day_df["event_type"].eq("view")).sum())},
            {"name": "搜尋結果頁瀏覽", "count": int((day_df["feature_id"].eq("search-job-page") & day_df["event_type"].eq("view")).sum())},
            {"name": "職缺詳情頁瀏覽", "count": job_views},
            {"name": "應徵送出", "count": applies},
        ]).to_parquet(output_dir / FUNNEL_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "funnel": rel(FUNNEL_FILE),
                "device": rel(DEVICE_FILE),
                "os": rel(OS_FILE),
                "source": rel(SOURCE_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_apply_conversion_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
