#!/usr/bin/env python3
"""
build_click_heatmap_t2.py
────────────────────────
從 T1 raw parquet 產出 click-heatmap 的 T2 day-keyed report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

CONFIG_PATH = Path(__file__).parent / "click_heatmap_config.json"

from common.data_pipeline import (
    ensure_pipeline_directories,
    t2_report_date_dir,
    update_t2_manifest_dates,
)
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "click-heatmap"
DAILY_SUMMARY_FILE = "daily_summary.parquet"
CLICK_COUNTS_FILE = "click_counts.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 click-heatmap 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def build_click_heatmap_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    target_pages = [page["page_path"] for page in config["pages"]]

    columns = ["date", "system", "event_type", "page_path", "feature_id"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    if "feature_name" not in df.columns:
        df["feature_name"] = ""
    df = df[
        df["system"].eq("jobbank-web")
        & df["event_type"].eq("click")
        & df["page_path"].isin(target_pages)
        & df["feature_id"].notna()
    ].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        click_counts = (
            day_df.groupby(["page_path", "feature_id"], as_index=False)
            .agg(
                count=("feature_id", "size"),
                feature_name=("feature_name", lambda values: next((v for v in values if isinstance(v, str) and v), "")),
            )
            .sort_values(["page_path", "count", "feature_id"], ascending=[True, False, True])
        )
        click_counts.to_parquet(output_dir / CLICK_COUNTS_FILE, index=False)

        feature_totals = click_counts.groupby("feature_id")["count"].sum()
        top_feature = feature_totals.idxmax() if not feature_totals.empty else ""
        top_count = int(feature_totals.max()) if not feature_totals.empty else 0
        pd.DataFrame([{
            "date": target_date,
            "total_clicks": int(click_counts["count"].sum()),
            "feature_count": int(click_counts["feature_id"].nunique()),
            "top_feature_id": top_feature,
            "top_count": top_count,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "click_counts": rel(CLICK_COUNTS_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_click_heatmap_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
