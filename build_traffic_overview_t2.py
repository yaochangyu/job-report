#!/usr/bin/env python3
"""
build_traffic_overview_t2.py
───────────────────────────
從 T1 raw parquet 產出 traffic-overview 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import (
    T2_REPORT_MANIFEST_PATH,
    ensure_pipeline_directories,
    t2_report_range_dir,
)
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "traffic-overview"
KPI_FILE = "kpi.parquet"
DAILY_FILE = "daily.parquet"
HOURLY_FILE = "hourly.parquet"
DEVICE_FILE = "device_type.parquet"
OS_FILE = "os.parquet"
BROWSER_FILE = "browser.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 traffic-overview 的 T2 parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    return parser.parse_args()


def _count_by_value(frame: pd.DataFrame, column: str, alias: str = "name") -> pd.DataFrame:
    counted = frame[column].fillna("unknown").value_counts(dropna=False).rename_axis(alias).reset_index(name="count")
    return counted


def build_traffic_overview_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    columns = [
        "date",
        "hour",
        "event_type",
        "action",
        "session_id",
        "device_type",
        "os",
        "browser",
    ]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = int(len(df))
    views = int((df["event_type"] == "view").sum())
    clicks = int((df["event_type"] == "click").sum())
    applies = int((df["action"] == "apply").sum())
    sessions = int(df["session_id"].dropna().nunique())
    kpi = pd.DataFrame([{
        "total": total,
        "views": views,
        "clicks": clicks,
        "applies": applies,
        "sessions": sessions,
        "click_rate": clicks / total * 100 if total else 0,
        "apply_rate": applies / views * 100 if views else 0,
    }])
    kpi.to_parquet(output_dir / KPI_FILE, index=False)

    daily_base = df.assign(
        is_view=df["event_type"].eq("view"),
        is_click=df["event_type"].eq("click"),
        is_apply=df["action"].eq("apply"),
    )
    daily = (
        daily_base.groupby("date", as_index=False)
        .agg(
            views=("is_view", "sum"),
            clicks=("is_click", "sum"),
            applies=("is_apply", "sum"),
            sessions=("session_id", "nunique"),
        )
        .sort_values("date")
    )
    daily.to_parquet(output_dir / DAILY_FILE, index=False)

    day_count = max(len(daily), 1)
    hourly = (
        df.groupby("hour", as_index=False)
        .size()
        .rename(columns={"size": "total"})
    )
    hourly["avg"] = (hourly["total"] / day_count).round().astype(int)
    hourly = hourly[["hour", "avg"]].sort_values("hour")
    hourly.to_parquet(output_dir / HOURLY_FILE, index=False)

    _count_by_value(df, "device_type").to_parquet(output_dir / DEVICE_FILE, index=False)
    _count_by_value(df, "os").to_parquet(output_dir / OS_FILE, index=False)
    _count_by_value(df, "browser").to_parquet(output_dir / BROWSER_FILE, index=False)

    _write_manifest(date_from, date_to, output_dir, total)
    return output_dir


def _write_manifest(date_from: str, date_to: str, output_dir: Path, total_rows: int) -> None:
    manifest = {}
    if T2_REPORT_MANIFEST_PATH.exists():
        manifest = json.loads(T2_REPORT_MANIFEST_PATH.read_text(encoding="utf-8"))

    reports = manifest.setdefault("reports", {})
    traffic_overview = reports.setdefault(REPORT_NAME, {"snapshots": {}})
    snapshot_key = f"{date_from}_{date_to}"
    traffic_overview["snapshots"][snapshot_key] = {
        "date_from": date_from,
        "date_to": date_to,
        "root": str(output_dir.relative_to(output_dir.parents[2])),
        "files": {
            "kpi": str((output_dir / KPI_FILE).relative_to(output_dir.parents[2])),
            "daily": str((output_dir / DAILY_FILE).relative_to(output_dir.parents[2])),
            "hourly": str((output_dir / HOURLY_FILE).relative_to(output_dir.parents[2])),
            "device_type": str((output_dir / DEVICE_FILE).relative_to(output_dir.parents[2])),
            "os": str((output_dir / OS_FILE).relative_to(output_dir.parents[2])),
            "browser": str((output_dir / BROWSER_FILE).relative_to(output_dir.parents[2])),
        },
        "rows": total_rows,
        "updated_at": generated_now(),
    }
    traffic_overview["available_snapshots"] = sorted(traffic_overview["snapshots"].keys())

    manifest["tier"] = "t2-report"
    manifest["schema_version"] = 1
    manifest["updated_at"] = generated_now()
    T2_REPORT_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_traffic_overview_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
