#!/usr/bin/env python3
"""
query_homepage_blocks.py
────────────────────────
從 ES 查詢首頁各區塊的每日點擊數，輸出 TSV 格式。

執行方式：
    uv run python query_homepage_blocks.py
    uv run python query_homepage_blocks.py --days 7
    uv run python query_homepage_blocks.py --from 2026-05-01 --to 2026-05-17
    uv run python query_homepage_blocks.py --output ./clicks.tsv
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from common.es_client import msearch, TW

# ── 區塊定義 ──────────────────────────────────────────────────────────────────

BLOCKS: list[dict] = [
    # 搜尋類別 — 搜尋
    {"block": "搜尋類別", "category": "搜尋",     "name": "職務 Tcode 選單",  "feature_id": "T-job-category"},
    {"block": "搜尋類別", "category": "搜尋",     "name": "地區 Tcode 選單",  "feature_id": "T-job-location"},
    {"block": "搜尋類別", "category": "搜尋",     "name": "關鍵字搜尋欄",     "feature_id": "search-general-keyword"},
    {"block": "搜尋類別", "category": "搜尋",     "name": "搜尋 BTN",         "feature_id": "search-general-submit"},
    # 搜尋類別 — AI 小精靈
    {"block": "搜尋類別", "category": "AI 小精靈", "name": "關鍵字搜尋欄",    "feature_id": "search-ai-keyword"},
    {"block": "搜尋類別", "category": "AI 小精靈", "name": "聽寫 BTN",        "feature_id": "search-ai-voice-input"},
    {"block": "搜尋類別", "category": "AI 小精靈", "name": "語音 BTN",        "feature_id": "search-ai-chat-mode"},
    {"block": "搜尋類別", "category": "AI 小精靈", "name": "送出 BTN",        "feature_id": "search-ai-submit"},
    # 身分類別
    {"block": "身分類別", "category": "", "name": "專屬推薦／猜你喜歡", "feature_id": "identify-personal"},
    {"block": "身分類別", "category": "", "name": "上班族",             "feature_id": "identify-worker"},
    {"block": "身分類別", "category": "", "name": "學生／實習",         "feature_id": "identify-student"},
    {"block": "身分類別", "category": "", "name": "新鮮人",             "feature_id": "identify-fresh"},
    {"block": "身分類別", "category": "", "name": "中高階",             "feature_id": "identify-senior"},
    {"block": "身分類別", "category": "", "name": "二度就業",           "feature_id": "identify-returning"},
    # 探索工作 — Tab
    {"block": "探索工作", "category": "Tab", "name": "專屬推薦 AI 推薦",          "feature_id": "identify-personal-tab-1"},
    {"block": "探索工作", "category": "Tab", "name": "專屬推薦 最新工作",          "feature_id": "identify-personal-tab-2"},
    {"block": "探索工作", "category": "Tab", "name": "專屬推薦 熱門工作",          "feature_id": "identify-personal-tab-3"},
    {"block": "探索工作", "category": "Tab", "name": "上班族 全職工作",            "feature_id": "identify-worker-tab-1"},
    {"block": "探索工作", "category": "Tab", "name": "上班族 知名企業",            "feature_id": "identify-worker-tab-2"},
    {"block": "探索工作", "category": "Tab", "name": "上班族 外商企業",            "feature_id": "identify-worker-tab-3"},
    {"block": "探索工作", "category": "Tab", "name": "學生／實習 學生實習",        "feature_id": "identify-student-tab-1"},
    {"block": "探索工作", "category": "Tab", "name": "學生／實習 工讀",            "feature_id": "identify-student-tab-2"},
    {"block": "探索工作", "category": "Tab", "name": "學生／實習 研替",            "feature_id": "identify-student-tab-3"},
    {"block": "探索工作", "category": "Tab", "name": "新鮮人 新鮮人",              "feature_id": "identify-fresh-tab-1"},
    {"block": "探索工作", "category": "Tab", "name": "新鮮人 應屆畢業生",          "feature_id": "identify-fresh-tab-2"},
    {"block": "探索工作", "category": "Tab", "name": "新鮮人 無經驗可",            "feature_id": "identify-fresh-tab-3"},
    {"block": "探索工作", "category": "Tab", "name": "中高階 中高階",              "feature_id": "identify-senior-tab-1"},
    {"block": "探索工作", "category": "Tab", "name": "中高階 高薪機會",            "feature_id": "identify-senior-tab-2"},
    {"block": "探索工作", "category": "Tab", "name": "中高階 知名企業",            "feature_id": "identify-senior-tab-3"},
    {"block": "探索工作", "category": "Tab", "name": "二度就業 二度就業",          "feature_id": "identify-returning-tab-1"},
    {"block": "探索工作", "category": "Tab", "name": "二度就業 兼職",              "feature_id": "identify-returning-tab-2"},
    {"block": "探索工作", "category": "Tab", "name": "二度就業 幸福企業",          "feature_id": "identify-returning-tab-3"},
    # 探索工作 — 職缺
    {"block": "探索工作", "category": "職缺", "name": "非廣告職缺",     "feature_id": "explore-jobs-organic"},
    {"block": "探索工作", "category": "職缺", "name": "非廣告職缺廠商", "feature_id": "explore-jobs-organic-corp"},
    # 探索工作 — 分頁
    {"block": "探索工作", "category": "分頁", "name": "上一頁",   "feature_id": "explore-jobs-prev"},
    {"block": "探索工作", "category": "分頁", "name": "下一頁",   "feature_id": "explore-jobs-next"},
    {"block": "探索工作", "category": "分頁", "name": "更多工作", "feature_id": "explore-jobs-more"},
    # 探索企業 — Tab
    {"block": "探索企業", "category": "Tab", "name": "餐飲／住宿服務",             "feature_id": "explore-company-hospitality"},
    {"block": "探索企業", "category": "Tab", "name": "一般傳統製造",               "feature_id": "explore-company-manufacturing"},
    {"block": "探索企業", "category": "Tab", "name": "醫療照護／環境衛生",         "feature_id": "explore-company-healthcare"},
    {"block": "探索企業", "category": "Tab", "name": "電子科技／資訊／軟體／半導體", "feature_id": "explore-company-tech"},
    {"block": "探索企業", "category": "Tab", "name": "教育／出版／藝文相關",       "feature_id": "explore-company-education"},
    {"block": "探索企業", "category": "Tab", "name": "批發／零售",                 "feature_id": "explore-company-retail"},
    {"block": "探索企業", "category": "Tab", "name": "一般服務業",                 "feature_id": "explore-company-service"},
    # 探索企業 — 職缺
    {"block": "探索企業", "category": "職缺", "name": "廠商",       "feature_id": "explore-company-corp"},
    {"block": "探索企業", "category": "職缺", "name": "左邊廠商職缺", "feature_id": "explore-company-job-1"},
    {"block": "探索企業", "category": "職缺", "name": "右邊廠商職缺", "feature_id": "explore-company-job-2"},
    {"block": "探索企業", "category": "職缺", "name": "更多工作",   "feature_id": "explore-company-job-more"},
    # 探索企業 — 分頁
    {"block": "探索企業", "category": "分頁", "name": "上一頁",   "feature_id": "explore-company-prev"},
    {"block": "探索企業", "category": "分頁", "name": "下一頁",   "feature_id": "explore-company-next"},
    {"block": "探索企業", "category": "分頁", "name": "更多公司", "feature_id": "explore-company-more"},
]

ALL_FEATURE_IDS = [b["feature_id"] for b in BLOCKS]


# ── 日期工具 ──────────────────────────────────────────────────────────────────

def _iter_dates(date_from: str, date_to: str) -> list[str]:
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    result: list[str] = []
    current = start
    while current <= end:
        result.append(current.isoformat())
        current += timedelta(days=1)
    return result


# ── ES 查詢 ───────────────────────────────────────────────────────────────────

def query_daily_clicks(date_from: str, date_to: str) -> dict[str, dict[str, int]]:
    """回傳 { '2026-05-01': { 'identify-personal': 100, ... }, ... }"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {
                "gte": date_from + "T00:00:00+08:00",
                "lte": date_to   + "T23:59:59+08:00",
            }}},
            {"term": {"system": "jobbank-web"}},
            {"term": {"eventType": "click"}},
            {"terms": {"featureId": ALL_FEATURE_IDS}},
        ]}},
        "aggs": {
            "daily": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
                "aggs": {
                    "by_feature": {
                        "terms": {
                            "field": "featureId",
                            "size": len(ALL_FEATURE_IDS) + 10,
                        }
                    }
                },
            }
        },
    }

    r = msearch(body)
    result: dict[str, dict[str, int]] = {}
    for day_bucket in r["aggregations"]["daily"]["buckets"]:
        day = day_bucket["key_as_string"][:10]
        result[day] = {
            feat["key"]: feat["doc_count"]
            for feat in day_bucket["by_feature"]["buckets"]
        }
    return result


# ── TSV 輸出 ──────────────────────────────────────────────────────────────────

def write_tsv(daily: dict[str, dict[str, int]], dates: list[str], output: Path) -> None:
    header = ["區塊", "分類", "名稱", "featureId"] + dates
    rows = [
        [
            b["block"],
            b["category"],
            b["name"],
            b["feature_id"],
        ] + [str(daily.get(d, {}).get(b["feature_id"], 0)) for d in dates]
        for b in BLOCKS
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        f.write("\t".join(header) + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")

    print(f"[OK] 輸出：{output}（{len(rows)} 筆，{len(dates)} 天）")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="從 ES 查詢首頁各區塊每日點擊數")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days",  type=int, default=None, metavar="N",    help="查詢近 N 天")
    group.add_argument("--from",  dest="date_from", default=None,         help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to",   dest="date_to",   default=None,         help="結束日期 YYYY-MM-DD")
    parser.add_argument("--output", default=None,                         help="輸出檔案路徑")
    return parser.parse_args()


def _resolve_date_range(args: argparse.Namespace) -> tuple[str, str]:
    if args.date_from:
        return args.date_from, args.date_to or args.date_from
    if args.days:
        today = datetime.now(TW).date()
        return (today - timedelta(days=args.days - 1)).isoformat(), today.isoformat()
    today = datetime.now(TW).date().isoformat()
    return today, today


def main() -> None:
    args = _parse_args()
    date_from, date_to = _resolve_date_range(args)
    dates = _iter_dates(date_from, date_to)

    slug_from = date_from.replace("-", "")
    slug_to   = date_to.replace("-", "")
    output_path = Path(args.output) if args.output else Path(
        f"homepage-clicks-daily-{slug_from}-{slug_to}.tsv"
    )

    print(f"[INFO] 查詢區間：{date_from} ～ {date_to}（{len(dates)} 天）")
    print(f"[INFO] featureId 數量：{len(ALL_FEATURE_IDS)}")

    daily = query_daily_clicks(date_from, date_to)
    write_tsv(daily, dates, output_path)


if __name__ == "__main__":
    main()
