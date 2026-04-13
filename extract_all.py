#!/usr/bin/env python3
"""
extract_all.py
──────────────
從 ES 抽取所有報告的聚合結果，存入 store.db。

執行方式：
    # 即時層：查詢距上次執行到現在（cron 每 10~60 分鐘）
    uv run python extract_all.py --mode interval

    # 即時層：手動指定區間
    uv run python extract_all.py --mode interval --from 2026-04-11T06:00:00+08:00 --to 2026-04-11T06:10:00+08:00

    # 日報層：昨天
    uv run python extract_all.py --mode daily --date yesterday

    # 日報層：指定日期
    uv run python extract_all.py --mode daily --date 2026-04-10

    # 日報層：補跑一段日期區間
    uv run python extract_all.py --mode daily --from 2026-04-01 --to 2026-04-10
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone, timedelta, date

from common.store import (
    init_db,
    save_interval,
    save_daily,
    get_meta,
    set_meta,
)

# ── 各報告 query 函式 ────────────────────────────────────────────────────────

from traffic_overview_report import (
    query_kpi,
    query_daily_trend,
    query_hourly_distribution,
    query_device_distribution,
)
from search_behavior_report import (
    query_search_overview,
    query_daily_search_trend,
    query_search_page_dist,
    query_ai_interaction,
    query_quick_filter,
)
from apply_conversion_report import (
    query_apply_kpi,
    query_apply_source,
    query_apply_daily_trend,
    query_funnel,
    query_apply_device,
    query_apply_hourly,
)
from feature_engagement_report import (
    query_explore_jobs,
    query_explore_corp,
    query_identity,
    query_news,
)
from device_platform_report import (
    query_device_daily,
    query_os_browser,
    query_device_behavior,
    query_os_behavior,
)
from page_ranking_report import (
    query_feature_ranking,
    query_category_summary,
)
from page_navigation_report import (
    query_chain_kpi,
    query_chain_ranking,
    query_chain_steps,
    query_entry_pages,
)
from click_heatmap_report import query_page_clicks

import json as _json
from pathlib import Path

_HEATMAP_CONFIG = Path(__file__).parent / "click_heatmap_config.json"

TW = timezone(timedelta(hours=8))
META_LAST_INTERVAL = "last_interval_run"
DEFAULT_INTERVAL_MINUTES = 10


# ── 查詢清單 ─────────────────────────────────────────────────────────────────

def _build_queries(time_from: str, time_to: str) -> list[tuple[str, str, callable]]:
    """回傳 [(report, query_name, callable)] 的清單。"""
    queries = [
        # traffic-overview
        ("traffic-overview", "query_kpi",                  lambda: query_kpi(time_from, time_to)),
        ("traffic-overview", "query_daily_trend",           lambda: query_daily_trend(time_from, time_to)),
        ("traffic-overview", "query_hourly_distribution",   lambda: query_hourly_distribution(time_from, time_to)),
        ("traffic-overview", "query_device_distribution",   lambda: query_device_distribution(time_from, time_to)),
        # search-behavior
        ("search-behavior",  "query_search_overview",       lambda: query_search_overview(time_from, time_to)),
        ("search-behavior",  "query_daily_search_trend",    lambda: query_daily_search_trend(time_from, time_to)),
        ("search-behavior",  "query_search_page_dist",      lambda: query_search_page_dist(time_from, time_to)),
        ("search-behavior",  "query_ai_interaction",        lambda: query_ai_interaction(time_from, time_to)),
        ("search-behavior",  "query_quick_filter",          lambda: query_quick_filter(time_from, time_to)),
        # apply-conversion
        ("apply-conversion", "query_apply_kpi",             lambda: query_apply_kpi(time_from, time_to)),
        ("apply-conversion", "query_apply_source",          lambda: query_apply_source(time_from, time_to)),
        ("apply-conversion", "query_apply_daily_trend",     lambda: query_apply_daily_trend(time_from, time_to)),
        ("apply-conversion", "query_funnel",                lambda: query_funnel(time_from, time_to)),
        ("apply-conversion", "query_apply_device",          lambda: query_apply_device(time_from, time_to)),
        ("apply-conversion", "query_apply_hourly",          lambda: query_apply_hourly(time_from, time_to)),
        # feature-engagement
        ("feature-engagement", "query_explore_jobs",        lambda: query_explore_jobs(time_from, time_to)),
        ("feature-engagement", "query_explore_corp",        lambda: query_explore_corp(time_from, time_to)),
        ("feature-engagement", "query_identity",            lambda: query_identity(time_from, time_to)),
        ("feature-engagement", "query_news",                lambda: query_news(time_from, time_to)),
        # device-platform
        ("device-platform",  "query_device_daily",          lambda: query_device_daily(time_from, time_to)),
        ("device-platform",  "query_os_browser",            lambda: query_os_browser(time_from, time_to)),
        ("device-platform",  "query_device_behavior",       lambda: query_device_behavior(time_from, time_to)),
        ("device-platform",  "query_os_behavior",           lambda: query_os_behavior(time_from, time_to)),
        # page-ranking（query_category_summary 依賴 query_feature_ranking 結果，特殊處理）
        ("page-ranking",     "query_feature_ranking",       lambda: query_feature_ranking(time_from, time_to)),
        # page-navigation
        ("page-navigation",  "query_chain_kpi",             lambda: query_chain_kpi(time_from, time_to)),
        ("page-navigation",  "query_chain_ranking",         lambda: query_chain_ranking(time_from, time_to)),
        ("page-navigation",  "query_chain_steps",           lambda: query_chain_steps(time_from, time_to)),
        ("page-navigation",  "query_entry_pages",           lambda: query_entry_pages(time_from, time_to)),
    ]

    # click-heatmap：每個頁面各一筆
    if _HEATMAP_CONFIG.exists():
        config = _json.loads(_HEATMAP_CONFIG.read_text(encoding="utf-8"))
        for page in config.get("pages", []):
            page_path = page["page_path"]
            safe = page_path.strip("/").replace("/", "_") or "home"
            queries.append((
                "click-heatmap",
                f"query_page_clicks_{safe}",
                (lambda pp: lambda: query_page_clicks(pp, time_from, time_to))(page_path),
            ))

    return queries


# ── 執行查詢並儲存 ────────────────────────────────────────────────────────────

def _run_queries(queries, save_fn) -> tuple[int, int]:
    """執行查詢清單，呼叫 save_fn 儲存。回傳 (成功數, 失敗數)。"""
    ok = fail = 0
    for report, query_name, fn in queries:
        result = None
        success = False
        try:
            result = fn()
            save_fn(report, query_name, result)
            print(f"  ✅ {report}/{query_name}")
            ok += 1
            success = True
        except Exception as e:
            print(f"  ❌ {report}/{query_name}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            fail += 1

        # page-ranking 特殊：query_category_summary 依賴 feature_ranking 結果
        if success and report == "page-ranking" and query_name == "query_feature_ranking":
            try:
                cat_data = query_category_summary(result)
                save_fn("page-ranking", "query_category_summary", cat_data)
                print(f"  ✅ page-ranking/query_category_summary")
                ok += 1
            except Exception as e:
                print(f"  ❌ page-ranking/query_category_summary: {e}", file=sys.stderr)
                fail += 1

    return ok, fail


# ── Interval 模式 ─────────────────────────────────────────────────────────────

def run_interval(time_from: str, time_to: str) -> None:
    print(f"\n[interval] {time_from} ～ {time_to}")
    queries = _build_queries(time_from, time_to)

    def save(report, query_name, data):
        save_interval(time_from, time_to, report, query_name, data)

    ok, fail = _run_queries(queries, save)
    set_meta(META_LAST_INTERVAL, time_to)
    print(f"\n[interval] 完成：{ok} 成功 / {fail} 失敗")
    if fail:
        sys.exit(1)


# ── Daily 模式 ────────────────────────────────────────────────────────────────

def run_daily(target_date: str) -> None:
    """target_date: YYYY-MM-DD"""
    time_from = f"{target_date}T00:00:00+08:00"
    time_to   = f"{target_date}T23:59:59+08:00"
    print(f"\n[daily] {target_date}")
    queries = _build_queries(time_from, time_to)

    def save(report, query_name, data):
        save_daily(target_date, report, query_name, data)

    ok, fail = _run_queries(queries, save)
    print(f"\n[daily] 完成：{ok} 成功 / {fail} 失敗")
    if fail:
        sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="從 ES 抽取資料存入 store.db")
    parser.add_argument("--mode", choices=["interval", "daily"], required=True,
                        help="interval：即時層  daily：日報層")
    parser.add_argument("--from", dest="time_from", default=None,
                        help="起始時間（interval: ISO8601；daily: YYYY-MM-DD）")
    parser.add_argument("--to", dest="time_to", default=None,
                        help="結束時間（interval: ISO8601；daily: YYYY-MM-DD）")
    parser.add_argument("--date", default=None,
                        help="daily 模式：指定日期（YYYY-MM-DD 或 yesterday）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()

    if args.mode == "interval":
        now = datetime.now(TW)
        if args.time_from and args.time_to:
            run_interval(args.time_from, args.time_to)
        else:
            last = get_meta(META_LAST_INTERVAL)
            if last:
                t_from = last
            else:
                t_from = (now - timedelta(minutes=DEFAULT_INTERVAL_MINUTES)).isoformat()
            run_interval(t_from, now.isoformat())

    elif args.mode == "daily":
        today = datetime.now(TW).date()
        yesterday = (today - timedelta(days=1)).isoformat()

        if args.time_from and args.time_to:
            # 補跑日期區間
            d = date.fromisoformat(args.time_from)
            end = date.fromisoformat(args.time_to)
            while d <= end:
                run_daily(d.isoformat())
                d += timedelta(days=1)
        elif args.date:
            target = yesterday if args.date == "yesterday" else args.date
            run_daily(target)
        else:
            run_daily(yesterday)


if __name__ == "__main__":
    main()
