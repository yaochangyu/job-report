#!/usr/bin/env python3
"""
run_all.py
──────────
一鍵執行三層資料管線，並產生 output/index.html 導覽頁面。

執行方式：
    uv run python run_all.py
    uv run python run_all.py --days 7
    uv run python run_all.py --from 2026-04-01 --to 2026-04-10
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from common.data_pipeline import T1_RAW_MANIFEST_PATH
from common.es_client import generated_now, parse_args
from common.frontend_shell import FRONTEND_ASSETS, build_shell_html
from common.t1_reader import resolve_date_window
from extract_raw_events import extract_raw_events

OUTPUT_DIR = Path(__file__).parent / "output"
ROOT_DIR = Path(__file__).parent
DATASET_DIR = ROOT_DIR / "dataset"

REPORTS = [
    {
        "script": "run_traffic_overview_pipeline.py",
        "title": "整體流量概覽",
        "subtitle": "Traffic Overview",
        "desc": "KPI 指標、每日流量趨勢、每小時分佈、裝置與 OS 分佈",
        "path": "traffic-overview/index.html",
        "icon": "📊",
        "color": "#4361ee",
        "view_mode": "overview",
    },
    {
        "script": "run_search_behavior_pipeline.py",
        "title": "搜尋行為分析",
        "subtitle": "Search Behavior",
        "desc": "AI vs 一般搜尋趨勢、搜尋結果頁分佈、AI 互動方式、快速篩選",
        "path": "search-behavior/index.html",
        "icon": "🔍",
        "color": "#7209b7",
        "view_mode": "search",
    },
    {
        "script": "run_apply_conversion_pipeline.py",
        "title": "應徵轉換分析",
        "subtitle": "Apply Conversion",
        "desc": "應徵漏斗、每日趨勢、來源分佈、裝置與時段分析",
        "path": "apply-conversion/index.html",
        "icon": "🎯",
        "color": "#f72585",
        "view_mode": "apply",
    },
    {
        "script": "run_feature_engagement_pipeline.py",
        "title": "功能互動分析",
        "subtitle": "Feature Engagement",
        "desc": "探索職缺/企業、身份辨識、產業 Tab、新聞互動",
        "path": "feature-engagement/index.html",
        "icon": "⚡",
        "color": "#06d6a0",
        "view_mode": "feature",
    },
    {
        "script": "run_device_platform_pipeline.py",
        "title": "裝置與平台分析",
        "subtitle": "Device & Platform",
        "desc": "Mobile/Desktop 趨勢、OS 與瀏覽器分佈、裝置行為交叉",
        "path": "device-platform/index.html",
        "icon": "📱",
        "color": "#fb8500",
        "view_mode": "device",
    },
    {
        "script": "run_page_ranking_pipeline.py",
        "title": "頁面流量排行",
        "subtitle": "Page Ranking",
        "desc": "featureId 排行 Top 20、功能類別佔比分析",
        "path": "page-ranking/index.html",
        "icon": "🏆",
        "color": "#118ab2",
        "view_mode": "ranking",
    },
    {
        "script": "run_page_navigation_pipeline.py",
        "title": "頁面導航鏈路",
        "subtitle": "Page Navigation Flow",
        "desc": "頁面轉換路徑排行、各頁面來源/目標、初始進入分佈",
        "path": "page-navigation/index.html",
        "icon": "🔀",
        "color": "#8338ec",
        "view_mode": "navigation",
    },
    {
        "script": "run_click_heatmap_pipeline.py",
        "title": "頁面點擊熱點",
        "subtitle": "Page Click Heatmap",
        "desc": "Clarity 風格截圖疊加，呈現各頁面按鈕/連結的點擊次數",
        "path": "click-heatmap/index.html",
        "icon": "🔥",
        "color": "#e63946",
        "view_mode": "heatmap",
    },
]


def _get_git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def copy_frontend_bundle(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset_name in FRONTEND_ASSETS:
        shutil.copy2(ROOT_DIR / asset_name, output_dir / asset_name)

    dataset_output = output_dir / "dataset"
    dataset_output.mkdir(parents=True, exist_ok=True)

    # app.js needs manifest.json to discover datasetRoot; read dates from T1 manifest
    available_dates: list[str] = []
    if T1_RAW_MANIFEST_PATH.exists():
        raw = json.loads(T1_RAW_MANIFEST_PATH.read_text(encoding="utf-8"))
        available_dates = raw.get("available_dates", [])
    (dataset_output / "manifest.json").write_text(
        json.dumps(
            {
                "available_dates": sorted(available_dates),
                "generated_at": generated_now(),
                "branch": _get_git_branch(),
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    # Copy only T2 report parquet files — all dashboards read T2, T1 raw is not deployed
    report_src = DATASET_DIR / "report"
    if report_src.exists():
        report_dst = dataset_output / "report"
        if report_dst.exists():
            shutil.rmtree(report_dst)
        shutil.copytree(report_src, report_dst)


def build_shell_pages(output_dir: Path, reports: list[dict]) -> None:
    (output_dir / "index.html").write_text(
        build_shell_html(".", "overview"),
        encoding="utf-8",
    )

    for report in reports:
        page_file = output_dir / report["path"]
        page_file.parent.mkdir(parents=True, exist_ok=True)
        asset_prefix = Path(os.path.relpath(output_dir, page_file.parent)).as_posix()
        page_file.write_text(
            build_shell_html(asset_prefix, report["view_mode"]),
            encoding="utf-8",
        )


def run_report(script: str, extra_args: list[str]) -> tuple[bool, float]:
    """執行單一報告腳本，回傳（成功與否, 耗時秒數）。"""
    cmd = [sys.executable, script] + extra_args
    start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start
    return result.returncode == 0, round(elapsed, 1)


def main() -> None:
    args = parse_args("一鍵執行所有報告並產生導覽頁面")
    date_from, date_to = resolve_date_window(args.days, args.time_from, args.time_to)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    extra_args = ["--from", date_from, "--to", date_to, "--skip-extract"]

    print(f"[INFO] 查詢區間：{date_from} ～ {date_to}")
    print("[INFO] 先同步 T1 raw 資料（優先重用本地快取）...")
    extract_raw_events(date_from, date_to, keep_existing=True)
    print(f"[INFO] 開始執行 {len(REPORTS)} 份報告...\n")

    results = []
    total_start = time.time()

    for report in REPORTS:
        print(f"{'─'*60}")
        print(f"[{report['icon']}] {report['title']} ({report['subtitle']})")
        ok, elapsed = run_report(report["script"], extra_args)
        status = "✓ 完成" if ok else "✗ 失敗"
        print(f"  → {status}（耗時 {elapsed}s）")
        results.append({**report, "ok": ok, "elapsed": elapsed})

    total_elapsed = round(time.time() - total_start, 1)
    ok_count = sum(1 for r in results if r["ok"])

    print(f"\n{'═'*60}")
    print(f"[完成] {ok_count}/{len(REPORTS)} 份報告成功，共耗時 {total_elapsed}s")

    copy_frontend_bundle(OUTPUT_DIR)
    build_shell_pages(OUTPUT_DIR, REPORTS)
    print(f"[OK] 前端殼已產生：{OUTPUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
