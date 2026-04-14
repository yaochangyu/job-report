#!/usr/bin/env python3
"""
build_apply_conversion_t2.py
───────────────────────────
從 T1 raw parquet 產出 apply-conversion 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import iter_dates, load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "apply-conversion"
KPI_FILE = "kpi.parquet"
SOURCE_FILE = "source.parquet"
DAILY_FILE = "daily.parquet"
FUNNEL_FILE = "funnel.parquet"
DEVICE_FILE = "device.parquet"
OS_FILE = "os.parquet"
HOURLY_FILE = "hourly.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 apply-conversion 的 T2 parquet")
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


def _count_by_value(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        frame[column]
        .fillna("unknown")
        .value_counts(dropna=False)
        .rename_axis("name")
        .reset_index(name="count")
        .sort_values(["count", "name"], ascending=[False, True])
    )


def build_apply_conversion_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    columns = ["date", "hour", "system", "action", "feature_id", "event_type", "device_type", "os", "source"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web")].copy()

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    is_apply = df["action"].eq("apply")
    is_job_view = df["feature_id"].eq("job-page") & df["event_type"].eq("view")
    applies = int(is_apply.sum())
    job_views = int(is_job_view.sum())
    kpi = pd.DataFrame([{
        "applies": applies,
        "job_views": job_views,
        "conversion_rate": applies / job_views * 100 if job_views else 0,
    }])
    kpi.to_parquet(output_dir / KPI_FILE, index=False)

    source_dist = _count_by_value(df[is_apply], "source")
    source_dist.to_parquet(output_dir / SOURCE_FILE, index=False)

    daily_base = df.assign(
        is_apply=is_apply,
        is_job_view=is_job_view,
    )
    daily = (
        daily_base.groupby("date", as_index=False)
        .agg(applies=("is_apply", "sum"), job_views=("is_job_view", "sum"))
        .sort_values("date")
    )
    daily["conv_rate"] = ((daily["applies"] / daily["job_views"].where(daily["job_views"] != 0, 1)) * 100).round(2)
    daily.to_parquet(output_dir / DAILY_FILE, index=False)

    funnel = pd.DataFrame([
        {"name": "首頁瀏覽", "count": int((df["feature_id"].eq("home-page") & df["event_type"].eq("view")).sum())},
        {"name": "搜尋結果頁瀏覽", "count": int((df["feature_id"].eq("search-job-page") & df["event_type"].eq("view")).sum())},
        {"name": "職缺詳情頁瀏覽", "count": job_views},
        {"name": "應徵送出", "count": applies},
    ])
    funnel.to_parquet(output_dir / FUNNEL_FILE, index=False)

    apply_df = df[is_apply].copy()
    device_dist = _count_by_value(apply_df, "device_type")
    device_dist.to_parquet(output_dir / DEVICE_FILE, index=False)

    os_dist = _count_by_value(apply_df, "os")
    os_dist.to_parquet(output_dir / OS_FILE, index=False)

    day_count = max(len(iter_dates(date_from, date_to)), 1)
    hourly = (
        apply_df.groupby("hour", as_index=False)
        .size()
        .rename(columns={"size": "total"})
        .sort_values("hour")
    )
    full_hours = pd.DataFrame({"hour": list(range(24))})
    hourly = full_hours.merge(hourly, on="hour", how="left").fillna({"total": 0})
    hourly["avg"] = (hourly["total"] / day_count).round().astype(int)
    hourly[["hour", "avg"]].to_parquet(output_dir / HOURLY_FILE, index=False)

    _update_t2_manifest(
        date_from,
        date_to,
        output_dir,
        files={
            "kpi": str((output_dir / KPI_FILE).relative_to(output_dir.parents[2])),
            "source": str((output_dir / SOURCE_FILE).relative_to(output_dir.parents[2])),
            "daily": str((output_dir / DAILY_FILE).relative_to(output_dir.parents[2])),
            "funnel": str((output_dir / FUNNEL_FILE).relative_to(output_dir.parents[2])),
            "device": str((output_dir / DEVICE_FILE).relative_to(output_dir.parents[2])),
            "os": str((output_dir / OS_FILE).relative_to(output_dir.parents[2])),
            "hourly": str((output_dir / HOURLY_FILE).relative_to(output_dir.parents[2])),
        },
        rows=len(df),
    )
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_apply_conversion_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
