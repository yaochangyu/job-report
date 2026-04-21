#!/usr/bin/env python3
# DEPRECATED: 已退出主管線，由 build_*_t2.py 直接取代。待 day pipeline 穩定後清理。
"""
render_feature_engagement_t3.py
──────────────────────────────
從 T2 report parquet 讀取資料並產出 feature-engagement HTML。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_feature_engagement_t2 import (
    EXPLORE_CORP_FEATURES_FILE,
    EXPLORE_CORP_INDUSTRY_TABS_FILE,
    EXPLORE_JOBS_CATEGORY_TABS_FILE,
    EXPLORE_JOBS_DAILY_FILE,
    EXPLORE_JOBS_FEATURES_FILE,
    EXPLORE_JOBS_IDENTITY_TYPES_FILE,
    IDENTITY_ALL_FILE,
    IDENTITY_MAIN_FILE,
    NEWS_CATEGORIES_FILE,
    NEWS_FEATURES_FILE,
    REPORT_NAME,
)
from common.data_pipeline import t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import resolve_date_window
from feature_engagement_report import OUTPUT_DIR, generate_html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="從 T2 產出 feature-engagement HTML")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    parser.add_argument("--output", default=None, help="自訂 HTML 輸出目錄")
    return parser.parse_args()


def _to_dict_list(path: Path) -> list[dict]:
    return pd.read_parquet(path).to_dict(orient="records")


def render_feature_engagement_t3(date_from: str, date_to: str, output_dir: Path) -> Path:
    snapshot_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    if not snapshot_dir.exists():
        raise FileNotFoundError(f"找不到 T2 snapshot：{snapshot_dir}")

    explore_jobs = {
        "features": _to_dict_list(snapshot_dir / EXPLORE_JOBS_FEATURES_FILE),
        "category_tabs": _to_dict_list(snapshot_dir / EXPLORE_JOBS_CATEGORY_TABS_FILE),
        "identity_types": _to_dict_list(snapshot_dir / EXPLORE_JOBS_IDENTITY_TYPES_FILE),
        "daily": _to_dict_list(snapshot_dir / EXPLORE_JOBS_DAILY_FILE),
    }
    explore_corp = {
        "features": _to_dict_list(snapshot_dir / EXPLORE_CORP_FEATURES_FILE),
        "industry_tabs": _to_dict_list(snapshot_dir / EXPLORE_CORP_INDUSTRY_TABS_FILE),
    }
    identity = {
        "main": _to_dict_list(snapshot_dir / IDENTITY_MAIN_FILE),
        "all_buckets": _to_dict_list(snapshot_dir / IDENTITY_ALL_FILE),
    }
    news = {
        "features": _to_dict_list(snapshot_dir / NEWS_FEATURES_FILE),
        "categories": _to_dict_list(snapshot_dir / NEWS_CATEGORIES_FILE),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    html = generate_html(
        explore_jobs,
        explore_corp,
        identity,
        news,
        f"{date_from}T00:00:00+08:00",
        f"{date_to}T23:59:59+08:00",
        generated_now(),
    )
    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    return out_file


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    out_file = render_feature_engagement_t3(date_from, date_to, output_dir)
    print(f"[OK] 已產出 T3 HTML：{out_file}")


if __name__ == "__main__":
    main()
