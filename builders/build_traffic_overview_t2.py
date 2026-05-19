#!/usr/bin/env python3
"""
build_traffic_overview_t2.py
───────────────────────────
從 T1 raw parquet 產出 traffic-overview 的 T2 day-keyed report parquet。
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

REPORT_NAME = "traffic-overview"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
SESSION_IDS_FILE = "session_ids.parquet"
DEVICE_FILE = "device_type.parquet"
OS_FILE = "os.parquet"
BROWSER_FILE = "browser.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 traffic-overview 的 T2 day-keyed parquet")
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


def build_traffic_overview_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "event_type", "action", "session_id", "device_type", "os", "browser"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        total = int(len(day_df))
        views = int((day_df["event_type"] == "view").sum())
        clicks = int((day_df["event_type"] == "click").sum())
        applies = int((day_df["action"] == "apply").sum())
        sessions = int(day_df["session_id"].dropna().nunique())
        pd.DataFrame([{
            "date": target_date,
            "total": total,
            "views": views,
            "clicks": clicks,
            "applies": applies,
            "sessions": sessions,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        (
            day_df[["session_id"]]
            .dropna(subset=["session_id"])
            .drop_duplicates()
            .sort_values("session_id")
            .to_parquet(output_dir / SESSION_IDS_FILE, index=False)
        )
        _count_by_value(day_df, "device_type").to_parquet(output_dir / DEVICE_FILE, index=False)
        _count_by_value(day_df, "os").to_parquet(output_dir / OS_FILE, index=False)
        _count_by_value(day_df, "browser").to_parquet(output_dir / BROWSER_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "session_ids": rel(SESSION_IDS_FILE),
                "device_type": rel(DEVICE_FILE),
                "os": rel(OS_FILE),
                "browser": rel(BROWSER_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_traffic_overview_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
