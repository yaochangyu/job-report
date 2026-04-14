#!/usr/bin/env python3
"""
render_apply_conversion_t3.py
────────────────────────────
從 T2 report parquet 讀取資料並產出 apply-conversion HTML。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from apply_conversion_report import OUTPUT_DIR, generate_html
from build_apply_conversion_t2 import (
    DAILY_FILE,
    DEVICE_FILE,
    FUNNEL_FILE,
    HOURLY_FILE,
    KPI_FILE,
    OS_FILE,
    REPORT_NAME,
    SOURCE_FILE,
)
from common.data_pipeline import t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import resolve_date_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="從 T2 產出 apply-conversion HTML")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    parser.add_argument("--output", default=None, help="自訂 HTML 輸出目錄")
    return parser.parse_args()


def _to_dict_list(path: Path) -> list[dict]:
    return pd.read_parquet(path).to_dict(orient="records")


def render_apply_conversion_t3(date_from: str, date_to: str, output_dir: Path) -> Path:
    snapshot_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    if not snapshot_dir.exists():
        raise FileNotFoundError(f"找不到 T2 snapshot：{snapshot_dir}")

    kpi = _to_dict_list(snapshot_dir / KPI_FILE)[0]
    source_dist = _to_dict_list(snapshot_dir / SOURCE_FILE)
    daily = _to_dict_list(snapshot_dir / DAILY_FILE)
    funnel = _to_dict_list(snapshot_dir / FUNNEL_FILE)
    device = {
        "device": _to_dict_list(snapshot_dir / DEVICE_FILE),
        "os": _to_dict_list(snapshot_dir / OS_FILE),
    }
    hourly_rows = _to_dict_list(snapshot_dir / HOURLY_FILE)
    hourly = [row["avg"] for row in sorted(hourly_rows, key=lambda row: row["hour"])]

    output_dir.mkdir(parents=True, exist_ok=True)
    html = generate_html(
        kpi,
        source_dist,
        daily,
        funnel,
        device,
        hourly,
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
    out_file = render_apply_conversion_t3(date_from, date_to, output_dir)
    print(f"[OK] 已產出 T3 HTML：{out_file}")


if __name__ == "__main__":
    main()
