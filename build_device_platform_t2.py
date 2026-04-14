#!/usr/bin/env python3
"""
build_device_platform_t2.py
──────────────────────────
從 T1 raw parquet 產出 device-platform 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "device-platform"
SUMMARY_FILE = "summary.parquet"
DEVICE_TOTAL_FILE = "device_total.parquet"
DAILY_FILE = "daily.parquet"
OS_FILE = "os.parquet"
BROWSER_FILE = "browser.parquet"
DEVICE_BEHAVIOR_FILE = "device_behavior.parquet"
OS_BEHAVIOR_FILE = "os_behavior.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 device-platform 的 T2 parquet")
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


def _count_by_value(frame: pd.DataFrame, column: str, alias: str) -> pd.DataFrame:
    return (
        frame[column]
        .fillna("unknown")
        .value_counts(dropna=False)
        .rename_axis(alias)
        .reset_index(name="count")
        .sort_values(["count", alias], ascending=[False, True])
    )


def build_device_platform_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    columns = ["date", "system", "device_type", "event_type", "action", "feature_id", "os", "browser"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web")].copy()

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    device_total = _count_by_value(df, "device_type", "device")
    device_total.to_parquet(output_dir / DEVICE_TOTAL_FILE, index=False)

    daily_base = df.assign(
        is_mobile=df["device_type"].eq("mobile"),
        is_desktop=df["device_type"].eq("desktop"),
    )
    daily = (
        daily_base.groupby("date", as_index=False)
        .agg(mobile=("is_mobile", "sum"), desktop=("is_desktop", "sum"))
        .sort_values("date")
    )
    daily_total = daily["mobile"] + daily["desktop"]
    daily["mobile_pct"] = ((daily["mobile"] / daily_total.where(daily_total != 0, 1)) * 100).round(1)
    daily.to_parquet(output_dir / DAILY_FILE, index=False)

    os_dist = _count_by_value(df, "os", "name")
    os_dist.to_parquet(output_dir / OS_FILE, index=False)

    browser_dist = _count_by_value(df, "browser", "name")
    browser_dist.to_parquet(output_dir / BROWSER_FILE, index=False)

    device_behavior_base = df.assign(
        is_view=df["event_type"].eq("view"),
        is_click=df["event_type"].eq("click"),
        is_apply=df["action"].eq("apply"),
        is_job_view=df["feature_id"].eq("job-page") & df["event_type"].eq("view"),
    )
    device_behavior = (
        device_behavior_base.groupby("device_type", as_index=False)
        .agg(
            total=("device_type", "size"),
            views=("is_view", "sum"),
            clicks=("is_click", "sum"),
            applies=("is_apply", "sum"),
            job_views=("is_job_view", "sum"),
        )
        .rename(columns={"device_type": "device"})
        .sort_values(["total", "device"], ascending=[False, True])
    )
    device_behavior["apply_rate"] = (
        (device_behavior["applies"] / device_behavior["job_views"].where(device_behavior["job_views"] != 0, 1)) * 100
    ).round(2)
    device_behavior = device_behavior.drop(columns=["job_views"])
    device_behavior.to_parquet(output_dir / DEVICE_BEHAVIOR_FILE, index=False)

    os_behavior_base = df.assign(
        is_view=df["event_type"].eq("view"),
        is_click=df["event_type"].eq("click"),
        is_apply=df["action"].eq("apply"),
    )
    os_behavior = (
        os_behavior_base.groupby("os", as_index=False)
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

    summary = pd.DataFrame([{
        "mobile_total": int(device_total.loc[device_total["device"].eq("mobile"), "count"].sum()),
        "desktop_total": int(device_total.loc[device_total["device"].eq("desktop"), "count"].sum()),
        "os_count": int(len(os_dist)),
        "browser_count": int(len(browser_dist)),
    }])
    summary.to_parquet(output_dir / SUMMARY_FILE, index=False)

    _update_t2_manifest(
        date_from,
        date_to,
        output_dir,
        files={
            "summary": str((output_dir / SUMMARY_FILE).relative_to(output_dir.parents[2])),
            "device_total": str((output_dir / DEVICE_TOTAL_FILE).relative_to(output_dir.parents[2])),
            "daily": str((output_dir / DAILY_FILE).relative_to(output_dir.parents[2])),
            "os": str((output_dir / OS_FILE).relative_to(output_dir.parents[2])),
            "browser": str((output_dir / BROWSER_FILE).relative_to(output_dir.parents[2])),
            "device_behavior": str((output_dir / DEVICE_BEHAVIOR_FILE).relative_to(output_dir.parents[2])),
            "os_behavior": str((output_dir / OS_BEHAVIOR_FILE).relative_to(output_dir.parents[2])),
        },
        rows=len(df),
    )
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_device_platform_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
