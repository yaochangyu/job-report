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

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from common.data_pipeline import T2_REPORT_DIR
from common.es_client import generated_now
from common.frontend_shell import FRONTEND_ASSETS, build_shell_html
from common.t1_reader import resolve_date_window
from tools.enrich_t1_events import enrich_t1_events
from tools.extract_raw_events import extract_raw_events

OUTPUT_DIR = Path(__file__).parent / "output"
ROOT_DIR = Path(__file__).parent
DATASET_DIR = ROOT_DIR / "pipeline"

REPORTS = [
    {
        "script": "builders/build_traffic_overview_t2.py",
        "title": "整體流量概覽",
        "subtitle": "Traffic Overview",
        "desc": "KPI 指標、每日流量趨勢、裝置與 OS 分佈",
        "path": "report/traffic-overview/index.html",
        "icon": "📊",
        "color": "#4361ee",
        "view_mode": "overview",
    },
    {
        "script": "builders/build_search_behavior_t2.py",
        "title": "搜尋行為分析",
        "subtitle": "Search Behavior",
        "desc": "AI vs 一般搜尋趨勢、搜尋結果頁分佈、快速篩選",
        "path": "report/search-behavior/index.html",
        "icon": "🔍",
        "color": "#7209b7",
        "view_mode": "search",
    },
    {
        "script": "builders/build_apply_conversion_t2.py",
        "title": "應徵轉換分析",
        "subtitle": "Apply Conversion",
        "desc": "應徵漏斗、每日趨勢、來源分佈、裝置分析",
        "path": "report/apply-conversion/index.html",
        "icon": "🎯",
        "color": "#f72585",
        "view_mode": "apply",
    },
    {
        "script": "builders/build_apply_journey_t2.py",
        "title": "應徵路徑分析",
        "subtitle": "Apply Journey",
        "desc": "使用者從進入網站到送出應徵的完整頁面路徑分析",
        "path": "report/apply-journey/index.html",
        "icon": "🗺️",
        "color": "#e76f51",
        "view_mode": "apply-journey",
    },
    {
        "script": "builders/build_feature_engagement_t2.py",
        "title": "功能互動分析",
        "subtitle": "Feature Engagement",
        "desc": "探索職缺/企業、身份辨識、產業 Tab、新聞互動",
        "path": "report/feature-engagement/index.html",
        "icon": "⚡",
        "color": "#06d6a0",
        "view_mode": "feature",
    },
    {
        "script": "builders/build_device_platform_t2.py",
        "title": "裝置與平台分析",
        "subtitle": "Device & Platform",
        "desc": "Mobile/Desktop 趨勢、OS 與瀏覽器分佈、裝置行為交叉",
        "path": "report/device-platform/index.html",
        "icon": "📱",
        "color": "#fb8500",
        "view_mode": "device",
    },
    {
        "script": "builders/build_page_ranking_t2.py",
        "title": "頁面流量排行",
        "subtitle": "Page Ranking",
        "desc": "featureId 排行 Top 20、功能類別佔比分析",
        "path": "report/page-ranking/index.html",
        "icon": "🏆",
        "color": "#118ab2",
        "view_mode": "ranking",
    },
    {
        "script": "builders/build_page_navigation_t2.py",
        "title": "頁面導航鏈路",
        "subtitle": "Page Navigation Flow",
        "desc": "頁面轉換路徑排行、各頁面來源/目標、初始進入分佈",
        "path": "report/page-navigation/index.html",
        "icon": "🔀",
        "color": "#8338ec",
        "view_mode": "navigation",
    },
    {
        "script": "builders/build_click_heatmap_t2.py",
        "title": "頁面點擊熱點",
        "subtitle": "Page Click Heatmap",
        "desc": "各頁面按鈕/連結的點擊次數排行",
        "path": "report/click-heatmap/index.html",
        "icon": "🔥",
        "color": "#e63946",
        "view_mode": "heatmap",
    },
    {
        "script": "builders/build_homepage_blocks_t2.py",
        "title": "首頁區塊點擊",
        "subtitle": "Homepage Blocks",
        "desc": "搜尋、身分類別、探索工作、探索企業各區塊每日點擊數",
        "path": "report/homepage-blocks/index.html",
        "icon": "🏠",
        "color": "#2ec4b6",
        "view_mode": "homepage-blocks",
    },
    {
        "script": "builders/build_apply_job_category_t2.py",
        "title": "應徵職類／產業",
        "subtitle": "Apply Job Category",
        "desc": "應徵者最常應徵的職類與產業 TOP 30 排行及每日趨勢",
        "path": "report/apply-job-category/index.html",
        "icon": "🏷️",
        "color": "#7c3aed",
        "view_mode": "apply-job-category",
    },
    {
        "script": "builders/build_apply_demographics_t2.py",
        "title": "應徵者性別／年齡",
        "subtitle": "Apply Demographics",
        "desc": "應徵者性別分佈、年齡層分佈與每日趨勢",
        "path": "report/apply-demographics/index.html",
        "icon": "👥",
        "color": "#10b981",
        "view_mode": "apply-demographics",
    },
    {
        "script": "builders/build_apply_demographics_category_t2.py",
        "title": "性別／年齡 × 職類／產業",
        "subtitle": "Demographics × Category",
        "desc": "性別、年齡層與職類、產業的交叉聚合分析 TOP 30",
        "path": "report/apply-demographics-category/index.html",
        "icon": "🔬",
        "color": "#8b5cf6",
        "view_mode": "apply-demographics-category",
    },
    {
        "script": "builders/build_homepage_blocks_t2.py",
        "title": "週期報表",
        "subtitle": "Period Report",
        "desc": "依月份、季度、年度瀏覽各類別聚合趨勢與明細報表",
        "path": "report/period-report/index.html",
        "icon": "📅",
        "color": "#0ea5e9",
        "view_mode": "period-report",
    },
]

LEGACY_SHELL_REDIRECTS = [
    {
        "legacy_path": "report/monthly-report/index.html",
        "target_path": "report/period-report/index.html",
        "view_mode": "period-report",
    },
]


def _get_git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def _collect_t2_available_dates(dataset_dir: Path) -> list[str]:
    """掃描 T2 report 目錄，回傳所有 date= 分區日期的聯集。"""
    report_dir = T2_REPORT_DIR
    if not report_dir.exists():
        return []
    dates: set[str] = set()
    for report in report_dir.iterdir():
        if not report.is_dir():
            continue
        for part in report.iterdir():
            if part.is_dir() and part.name.startswith("date="):
                dates.add(part.name[5:])
    return sorted(dates)


def _collect_t2_available_periods(dataset_dir: Path) -> dict:
    """掃描所有 report 類別目錄，回傳 monthly/quarterly/yearly 各自的聯集。"""
    report_dir = T2_REPORT_DIR
    if not report_dir.exists():
        return {"available_months": [], "available_quarters": [], "available_years": []}
    months, quarters, years = set(), set(), set()
    for category in report_dir.iterdir():
        if not category.is_dir():
            continue
        for part in category.iterdir():
            if not part.is_dir():
                continue
            if part.name.startswith("monthly="):
                months.add(part.name[8:])
            elif part.name.startswith("quarterly="):
                quarters.add(part.name[10:])
            elif part.name.startswith("yearly="):
                years.add(part.name[7:])
    return {
        "available_months": sorted(months, reverse=True),
        "available_quarters": sorted(quarters, reverse=True),
        "available_years": sorted(years, reverse=True),
    }


def copy_frontend_bundle(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset_name in FRONTEND_ASSETS:
        shutil.copy2(ROOT_DIR / "frontend" / asset_name, output_dir / asset_name)

    dataset_output = output_dir / "dataset"
    dataset_output.mkdir(parents=True, exist_ok=True)

    # available_dates 從 T2 實際產出目錄掃描，確保與前端 fetch 路徑一致
    available_dates = _collect_t2_available_dates(DATASET_DIR)
    periods = _collect_t2_available_periods(DATASET_DIR)
    (dataset_output / "manifest.json").write_text(
        json.dumps(
            {
                "available_dates": available_dates,
                **periods,
                "generated_at": generated_now(),
                "branch": _get_git_branch(),
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    # Copy only T2 report parquet files — all dashboards read T2, T0/T1 raw is not deployed
    report_src = T2_REPORT_DIR
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

    for redirect in LEGACY_SHELL_REDIRECTS:
        legacy_file = output_dir / redirect["legacy_path"]
        legacy_file.parent.mkdir(parents=True, exist_ok=True)
        target_rel = Path(os.path.relpath(output_dir / redirect["target_path"], legacy_file.parent)).as_posix()
        legacy_file.write_text(
            f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Redirecting…</title>
  <script>
    const target = new URL("{target_rel}", window.location.href);
    target.search = window.location.search;
    target.hash = window.location.hash;
    if (target.searchParams.get("view") === "monthly-report" || !target.searchParams.get("view")) {{
      target.searchParams.set("view", "{redirect["view_mode"]}");
    }}
    window.location.replace(target.toString());
  </script>
</head>
<body></body>
</html>
""",
            encoding="utf-8",
        )


def run_report(script: str, extra_args: list[str]) -> tuple[bool, float]:
    """執行單一報告腳本，回傳（成功與否, 耗時秒數）。"""
    cmd = [sys.executable, script] + extra_args
    start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start
    return result.returncode == 0, round(elapsed, 1)


_ALL_STEPS = ("t0", "t1", "report", "html")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="一鍵執行所有報告並產生導覽頁面",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="查詢近 N 天（預設：當日）")
    group.add_argument("--from", dest="time_from", default=None, help="起始日期，例如 2026-04-01")
    parser.add_argument("--to", dest="time_to", default=None, help="結束日期，例如 2026-04-10")
    parser.add_argument(
        "--steps",
        default=",".join(_ALL_STEPS),
        help=(
            "指定要執行的階段，逗號分隔（預設：t0,t1,report,html）\n"
            "  t0     — 從 Elasticsearch 抽取純原始事件（→ pipeline/t0-raw/）\n"
            "  t1     — 補強 Solr/Matching ES metadata（→ pipeline/t1-enrich/）\n"
            "  report — 建立 T2 day-keyed parquet（→ pipeline/t2-report/）\n"
            "  html   — 產生 manifest 與 HTML shell（→ output/）\n"
            "範例：--steps report,html"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    steps = {s.strip() for s in args.steps.split(",")}
    unknown = steps - set(_ALL_STEPS)
    if unknown:
        raise SystemExit(f"[ERROR] 未知的 step：{', '.join(sorted(unknown))}。可用值：{', '.join(_ALL_STEPS)}")

    print(f"[INFO] 執行階段：{args.steps}")

    if steps & {"t0", "t1", "report"}:
        date_from, date_to = resolve_date_window(args.days, args.time_from, args.time_to)
        extra_args = ["--from", date_from, "--to", date_to]
        print(f"[INFO] 查詢區間：{date_from} ～ {date_to}")
    else:
        date_from = date_to = None
        extra_args = []

    if "t0" in steps:
        print("[INFO] 抽取 T0 純原始事件（優先重用本地快取）...")
        extract_raw_events(date_from, date_to, keep_existing=True)

    if "t1" in steps:
        print("[INFO] 補強 T1 enriched 事件（優先重用本地快取）...")
        enrich_t1_events(date_from, date_to, keep_existing=True)

    results = []
    total_start = time.time()

    if "report" in steps:
        print(f"[INFO] 開始執行 {len(REPORTS)} 份報告...\n")
        for report in REPORTS:
            print(f"{'─'*60}")
            print(f"[{report['icon']}] {report['title']} ({report['subtitle']})")
            ok, elapsed = run_report(report["script"], extra_args)
            status = "✓ 完成" if ok else "✗ 失敗"
            print(f"  → {status}（耗時 {elapsed}s）")
            results.append({**report, "ok": ok, "elapsed": elapsed})

        print(f"{'─'*60}")
        print("[📆] 週期彙總（Period Summary）")
        ok, elapsed = run_report("builders/build_period_summary.py", extra_args)
        print(f"  → {'✓ 完成' if ok else '✗ 失敗'}（耗時 {elapsed}s）")

    total_elapsed = round(time.time() - total_start, 1)

    if results:
        ok_count = sum(1 for r in results if r["ok"])
        print(f"\n{'═'*60}")
        print(f"[完成] {ok_count}/{len(REPORTS)} 份報告成功，共耗時 {total_elapsed}s")

    if "html" in steps:
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        copy_frontend_bundle(OUTPUT_DIR)
        build_shell_pages(OUTPUT_DIR, REPORTS)
        print(f"[OK] 前端殼已產生：{OUTPUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
