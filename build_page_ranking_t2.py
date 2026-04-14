#!/usr/bin/env python3
"""
build_page_ranking_t2.py
───────────────────────
從 T1 raw parquet 產出 page-ranking 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window
from page_ranking_report import CATEGORY_MAP

REPORT_NAME = "page-ranking"
SUMMARY_FILE = "summary.parquet"
FEATURES_FILE = "features.parquet"
CATEGORIES_FILE = "categories.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 page-ranking 的 T2 parquet")
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


def build_page_ranking_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    columns = ["system", "feature_id", "event_type"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["feature_id"].notna()].copy()

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_base = df.assign(
        is_view=df["event_type"].eq("view"),
        is_click=df["event_type"].eq("click"),
    )
    features = (
        feature_base.groupby("feature_id", as_index=False)
        .agg(
            total=("feature_id", "size"),
            views=("is_view", "sum"),
            clicks=("is_click", "sum"),
        )
        .sort_values(["total", "feature_id"], ascending=[False, True])
    )
    features = features.rename(columns={"feature_id": "featureId"})
    features["ctr"] = ((features["clicks"] / features["total"].where(features["total"] != 0, 1)) * 100).round(2)
    features["category"] = features["featureId"].map(CATEGORY_MAP).fillna("其他")
    features.to_parquet(output_dir / FEATURES_FILE, index=False)

    categories = (
        features.groupby("category", as_index=False)["total"]
        .sum()
        .rename(columns={"category": "name", "total": "count"})
        .sort_values(["count", "name"], ascending=[False, True])
    )
    categories.to_parquet(output_dir / CATEGORIES_FILE, index=False)

    top1 = features.iloc[0] if not features.empty else None
    summary = pd.DataFrame([{
        "total_events": int(features["total"].sum()),
        "total_features": int(len(features)),
        "top_feature_id": top1["featureId"] if top1 is not None else "",
        "top_feature_total": int(top1["total"]) if top1 is not None else 0,
    }])
    summary.to_parquet(output_dir / SUMMARY_FILE, index=False)

    _update_t2_manifest(
        date_from,
        date_to,
        output_dir,
        files={
            "summary": str((output_dir / SUMMARY_FILE).relative_to(output_dir.parents[2])),
            "features": str((output_dir / FEATURES_FILE).relative_to(output_dir.parents[2])),
            "categories": str((output_dir / CATEGORIES_FILE).relative_to(output_dir.parents[2])),
        },
        rows=len(df),
    )
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_page_ranking_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
