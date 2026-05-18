#!/usr/bin/env python3
"""
build_page_navigation_t2.py
──────────────────────────
從 T1 raw parquet 產出 page-navigation 的 T2 day-keyed report parquet。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common.data_pipeline import (
    ensure_pipeline_directories,
    t2_report_date_dir,
    update_t2_manifest_dates,
)
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "page-navigation"
ENTRY_MARKER = "_entry_"
PAGE_RELATION_LIMIT = 5
DAILY_SUMMARY_FILE = "daily_summary.parquet"
NAV_PAIRS_FILE = "nav_pairs.parquet"
ENTRY_PAGES_FILE = "entry_pages.parquet"
PAGE_SOURCES_FILE = "page_sources.parquet"
PAGE_DESTINATIONS_FILE = "page_destinations.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 page-navigation 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def build_page_navigation_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "system", "event_type", "page_path", "previous_page_path"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["event_type"].eq("view")].copy()
    df["page_path"] = df["page_path"].fillna("/")
    df["previous_page_path"] = df["previous_page_path"].fillna(ENTRY_MARKER)

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        pair_counts = (
            day_df.groupby(["previous_page_path", "page_path"], as_index=False)
            .size()
            .rename(columns={"size": "count", "previous_page_path": "from", "page_path": "to"})
            .sort_values(["count", "from", "to"], ascending=[False, True, True])
        )

        nav_pairs = pair_counts[pair_counts["from"].ne(ENTRY_MARKER)].copy()
        nav_pairs["label"] = nav_pairs["from"] + " → " + nav_pairs["to"]
        nav_pairs.to_parquet(output_dir / NAV_PAIRS_FILE, index=False)

        entry_pages = (
            pair_counts[pair_counts["from"].eq(ENTRY_MARKER)][["to", "count"]]
            .rename(columns={"to": "name"})
            .sort_values(["count", "name"], ascending=[False, True])
        )
        entry_pages.to_parquet(output_dir / ENTRY_PAGES_FILE, index=False)

        page_sources = (
            pair_counts[pair_counts["from"].ne(ENTRY_MARKER)]
            .rename(columns={"to": "page", "from": "name"})
            .sort_values(["page", "count", "name"], ascending=[True, False, True])
        )
        page_sources["rank"] = page_sources.groupby("page").cumcount() + 1
        page_sources[page_sources["rank"] <= PAGE_RELATION_LIMIT].to_parquet(output_dir / PAGE_SOURCES_FILE, index=False)

        page_destinations = (
            pair_counts[pair_counts["from"].ne(ENTRY_MARKER)]
            .rename(columns={"from": "page", "to": "name"})
            .sort_values(["page", "count", "name"], ascending=[True, False, True])
        )
        page_destinations["rank"] = page_destinations.groupby("page").cumcount() + 1
        page_destinations[page_destinations["rank"] <= PAGE_RELATION_LIMIT].to_parquet(output_dir / PAGE_DESTINATIONS_FILE, index=False)

        pd.DataFrame([{
            "date": target_date,
            "nav_total": int(nav_pairs["count"].sum()),
            "entry_total": int(entry_pages["count"].sum()),
            "tracked_pages": int(page_sources["page"].nunique()),
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "nav_pairs": rel(NAV_PAIRS_FILE),
                "entry_pages": rel(ENTRY_PAGES_FILE),
                "page_sources": rel(PAGE_SOURCES_FILE),
                "page_destinations": rel(PAGE_DESTINATIONS_FILE),
            },
            "rows": len(day_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_page_navigation_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
