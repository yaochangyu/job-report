#!/usr/bin/env python3
# DEPRECATED: 已退出主管線，由 build_*_t2.py 直接取代。待 day pipeline 穩定後清理。
"""
render_click_heatmap_t3.py
─────────────────────────
從 T2 report parquet 讀取資料並產出 click-heatmap HTML。
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import pandas as pd

from build_click_heatmap_t2 import CLICK_COUNTS_FILE, REPORT_NAME
from click_heatmap_report import CONFIG_PATH, OUTPUT_DIR, generate_html, take_screenshot
from common.data_pipeline import t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import resolve_date_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="從 T2 產出 click-heatmap HTML")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    parser.add_argument("--output", default=None, help="自訂 HTML 輸出目錄")
    return parser.parse_args()


def render_click_heatmap_t3(date_from: str, date_to: str, output_dir: Path) -> Path:
    snapshot_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    if not snapshot_dir.exists():
        raise FileNotFoundError(f"找不到 T2 snapshot：{snapshot_dir}")

    click_counts = pd.read_parquet(snapshot_dir / CLICK_COUNTS_FILE).to_dict(orient="records")
    click_by_page: dict[str, list[dict]] = {}
    for row in click_counts:
        click_by_page.setdefault(row["page_path"], []).append({
            "feature_id": row["feature_id"],
            "feature_name": row["feature_name"],
            "count": row["count"],
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pages_data = []
    for page_config in config["pages"]:
        screenshot_path, img_w, img_h = take_screenshot(page_config, output_dir)
        screenshot_b64 = base64.b64encode(screenshot_path.read_bytes()).decode()
        elements_with_fid = [el for el in page_config.get("elements", []) if el.get("feature_id")]
        pages_data.append({
            "page_name": page_config["page_name"],
            "page_path": page_config["page_path"],
            "screenshot_b64": screenshot_b64,
            "click_data": click_by_page.get(page_config["page_path"], []),
            "elements": elements_with_fid,
            "img_width": img_w,
            "img_height": img_h,
        })

    html = generate_html(
        pages_data,
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
    out_file = render_click_heatmap_t3(date_from, date_to, output_dir)
    print(f"[OK] 已產出 T3 HTML：{out_file}")


if __name__ == "__main__":
    main()
