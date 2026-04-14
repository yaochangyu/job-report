#!/usr/bin/env python3
"""
build_page_navigation_t2.py
──────────────────────────
從 T1 raw parquet 產出 page-navigation 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "page-navigation"
ENTRY_MARKER = "_entry_"
SUMMARY_FILE = "summary.parquet"
NAV_PAIRS_FILE = "nav_pairs.parquet"
ENTRY_PAGES_FILE = "entry_pages.parquet"
PAGE_SOURCES_FILE = "page_sources.parquet"
PAGE_DESTINATIONS_FILE = "page_destinations.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 page-navigation 的 T2 parquet")
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


def build_page_navigation_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    columns = ["system", "page_path", "previous_page_path"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web")].copy()
    df["page_path"] = df["page_path"].fillna("/")
    df["previous_page_path"] = df["previous_page_path"].fillna(ENTRY_MARKER)

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    pair_counts = (
        df.groupby(["previous_page_path", "page_path"], as_index=False)
        .size()
        .rename(columns={"size": "count", "previous_page_path": "from", "page_path": "to"})
        .sort_values(["count", "from", "to"], ascending=[False, True, True])
    )
    nav_pairs = pair_counts[pair_counts["from"].ne(ENTRY_MARKER)].head(30).copy()
    nav_pairs["label"] = nav_pairs["from"] + " → " + nav_pairs["to"]
    nav_pairs.to_parquet(output_dir / NAV_PAIRS_FILE, index=False)

    entry_pages = (
        pair_counts[pair_counts["from"].eq(ENTRY_MARKER)][["to", "count"]]
        .rename(columns={"to": "name"})
        .sort_values(["count", "name"], ascending=[False, True])
        .head(15)
    )
    entry_pages.to_parquet(output_dir / ENTRY_PAGES_FILE, index=False)

    page_sources = (
        pair_counts[pair_counts["from"].ne(ENTRY_MARKER)]
        .rename(columns={"to": "page", "from": "name"})
        .sort_values(["page", "count", "name"], ascending=[True, False, True])
    )
    page_sources["rank"] = page_sources.groupby("page").cumcount() + 1
    page_sources = page_sources[page_sources["rank"] <= 5]
    top_source_pages = (
        page_sources.groupby("page", as_index=False)["count"]
        .sum()
        .sort_values(["count", "page"], ascending=[False, True])
        .head(10)["page"]
        .tolist()
    )
    page_sources = page_sources[page_sources["page"].isin(top_source_pages)].copy()
    page_sources.to_parquet(output_dir / PAGE_SOURCES_FILE, index=False)

    page_destinations = (
        pair_counts[pair_counts["from"].ne(ENTRY_MARKER)]
        .rename(columns={"from": "page", "to": "name"})
        .sort_values(["page", "count", "name"], ascending=[True, False, True])
    )
    page_destinations["rank"] = page_destinations.groupby("page").cumcount() + 1
    page_destinations = page_destinations[page_destinations["rank"] <= 5]
    top_destination_pages = (
        page_destinations.groupby("page", as_index=False)["count"]
        .sum()
        .sort_values(["count", "page"], ascending=[False, True])
        .head(10)["page"]
        .tolist()
    )
    page_destinations = page_destinations[page_destinations["page"].isin(top_destination_pages)].copy()
    page_destinations.to_parquet(output_dir / PAGE_DESTINATIONS_FILE, index=False)

    summary = pd.DataFrame([{
        "total_nav": int(nav_pairs["count"].sum()),
        "entry_total": int(entry_pages["count"].sum()),
        "tracked_pages": int(page_sources["page"].nunique()),
    }])
    summary.to_parquet(output_dir / SUMMARY_FILE, index=False)

    _update_t2_manifest(
        date_from,
        date_to,
        output_dir,
        files={
            "summary": str((output_dir / SUMMARY_FILE).relative_to(output_dir.parents[2])),
            "nav_pairs": str((output_dir / NAV_PAIRS_FILE).relative_to(output_dir.parents[2])),
            "entry_pages": str((output_dir / ENTRY_PAGES_FILE).relative_to(output_dir.parents[2])),
            "page_sources": str((output_dir / PAGE_SOURCES_FILE).relative_to(output_dir.parents[2])),
            "page_destinations": str((output_dir / PAGE_DESTINATIONS_FILE).relative_to(output_dir.parents[2])),
        },
        rows=len(df),
    )
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_page_navigation_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
