#!/usr/bin/env python3
"""
run_search_behavior_pipeline.py
──────────────────────────────
PoC：串接 search-behavior 的 extract → transform → render。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from build_search_behavior_t2 import build_search_behavior_t2
from common.t1_reader import resolve_date_window
from extract_raw_events import extract_raw_events
from render_search_behavior_t3 import render_search_behavior_t3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="執行 search-behavior 三層資料管線 PoC")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    parser.add_argument("--keep-existing", action="store_true", help="T1 已存在時跳過重抓")
    parser.add_argument("--skip-extract", action="store_true", help="略過 T1 extract，直接使用既有 raw parquet")
    parser.add_argument("--output", default=None, help="T3 HTML 輸出目錄")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    print(f"[PIPELINE] search-behavior：{date_from} ~ {date_to}")

    if args.skip_extract:
        print("[STEP] T1 extract")
        print("  → 已略過，直接使用既有 raw parquet")
    else:
        print("[STEP] T1 extract")
        extract_raw_events(date_from, date_to, keep_existing=args.keep_existing)

    print("[STEP] T2 transform")
    t2_dir = build_search_behavior_t2(date_from, date_to)
    print(f"  → {t2_dir}")

    print("[STEP] T3 render")
    output_dir = Path(args.output) if args.output else Path(__file__).parent / "output" / "search-behavior"
    out_file = render_search_behavior_t3(date_from, date_to, output_dir)
    print(f"  → {out_file}")


if __name__ == "__main__":
    main()
