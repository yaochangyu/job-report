#!/usr/bin/env python3
"""
build_device_platform_t2.py
──────────────────────────
從 T1 raw parquet 產出 device-platform 的 T2 day-keyed report parquet。
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

REPORT_NAME = "device-platform"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
OS_FILE = "os.parquet"
BROWSER_FILE = "browser.parquet"
DEVICE_BEHAVIOR_FILE = "device_behavior.parquet"
OS_BEHAVIOR_FILE = "os_behavior.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 device-platform 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def _count_by_value(frame: pd.DataFrame, column: str, alias: str) -> pd.DataFrame:
    return (
        frame[column]
        .fillna("unknown")
        .value_counts(dropna=False)
        .rename_axis(alias)
        .reset_index(name="count")
        .sort_values(["count", alias], ascending=[False, True])
    )


def build_device_platform_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "system", "device_type", "event_type", "action", "feature_id", "feature_name", "os", "browser"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web")].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        mobile = int((day_df["device_type"] == "mobile").sum())
        desktop = int((day_df["device_type"] == "desktop").sum())
        pd.DataFrame([{
            "date": target_date,
            "mobile": mobile,
            "desktop": desktop,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        _count_by_value(day_df, "os", "name").to_parquet(output_dir / OS_FILE, index=False)
        _count_by_value(day_df, "browser", "name").to_parquet(output_dir / BROWSER_FILE, index=False)

        behavior_base = day_df.assign(
            is_view=day_df["event_type"].eq("view"),
            is_click=day_df["event_type"].eq("click"),
            is_apply=day_df["action"].eq("apply"),
        )
        device_behavior = (
            behavior_base.groupby("device_type", as_index=False)
            .agg(
                total=("device_type", "size"),
                views=("is_view", "sum"),
                clicks=("is_click", "sum"),
                applies=("is_apply", "sum"),
            )
            .rename(columns={"device_type": "device"})
            .sort_values(["total", "device"], ascending=[False, True])
        )
        device_behavior.to_parquet(output_dir / DEVICE_BEHAVIOR_FILE, index=False)

        os_behavior = (
            behavior_base.groupby("os", as_index=False)
            .agg(
                total=("os", "size"),
                views=("is_view", "sum"),
                clicks=("is_click", "sum"),
                applies=("is_apply", "sum"),
            )
            .fillna({"os": "unknown"})
            .sort_values(["total", "os"], ascending=[False, True])
        )
        os_behavior.to_parquet(output_dir / OS_BEHAVIOR_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "os": rel(OS_FILE),
                "browser": rel(BROWSER_FILE),
                "device_behavior": rel(DEVICE_BEHAVIOR_FILE),
                "os_behavior": rel(OS_BEHAVIOR_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_device_platform_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
