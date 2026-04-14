#!/usr/bin/env python3
"""
build_click_heatmap_t2.py
────────────────────────
從 T1 raw parquet 產出 click-heatmap 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from click_heatmap_report import CONFIG_PATH
from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "click-heatmap"
CLICK_COUNTS_FILE = "click_counts.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 click-heatmap 的 T2 parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    return parser.parse_args()


def _update_t2_manifest(date_from: str, date_to: str, output_dir: Path, rows: int) -> None:
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
        "files": {
            "click_counts": str((output_dir / CLICK_COUNTS_FILE).relative_to(output_dir.parents[2])),
        },
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


def build_click_heatmap_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    target_pages = [page["page_path"] for page in config["pages"]]

    columns = ["system", "event_type", "page_path", "feature_id", "feature_name"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[
        df["system"].eq("jobbank-web")
        & df["event_type"].eq("click")
        & df["page_path"].isin(target_pages)
        & df["feature_id"].notna()
    ].copy()

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    click_counts = (
        df.groupby(["page_path", "feature_id"], as_index=False)
        .agg(
            count=("feature_id", "size"),
            feature_name=("feature_name", lambda values: next((v for v in values if isinstance(v, str) and v), "")),
        )
        .sort_values(["page_path", "count", "feature_id"], ascending=[True, False, True])
    )
    click_counts.to_parquet(output_dir / CLICK_COUNTS_FILE, index=False)

    _update_t2_manifest(date_from, date_to, output_dir, len(df))
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_click_heatmap_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
