#!/usr/bin/env python3
"""
extract_events.py
─────────────────
從 Elasticsearch 擷取原始事件，依日期輸出為 Parquet dataset。

執行方式：
    uv run python extract_events.py --date 2026-04-10
    uv run python extract_events.py --from 2026-04-01 --to 2026-04-10
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from common.es_client import TW, es_search
from common.parquet_dataset import normalize_event, update_manifest, write_events_partition

SOURCE_FIELDS = [
    "@timestamp",
    "system",
    "eventType",
    "action",
    "sessionId",
    "featureId",
    "pageUrl",
    "previousPageUrl",
    "deviceType",
    "os",
    "browser",
    "metadata",
]

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="從 ES 擷取原始事件並輸出 Parquet")
    parser.add_argument("--date", default=None, help="指定單日，例如 2026-04-10")
    parser.add_argument("--from", dest="date_from", default=None, help="起始日期，例如 2026-04-01")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期，例如 2026-04-10")
    parser.add_argument("--page-size", type=int, default=2000, help="每次向 ES 擷取的筆數")
    return parser.parse_args()


def iter_dates(start: date, end: date) -> list[str]:
    values: list[str] = []
    current = start
    while current <= end:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def resolve_target_dates(args: argparse.Namespace) -> list[str]:
    if args.date:
        return [args.date]
    if args.date_from and args.date_to:
        return iter_dates(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to))
    today = datetime.now(TW).date()
    return [today.isoformat()]


def fetch_events_for_date(target_date: str, page_size: int) -> list[dict]:
    time_from = f"{target_date}T00:00:00+08:00"
    next_day = (date.fromisoformat(target_date) + timedelta(days=1)).isoformat()
    time_to = f"{next_day}T00:00:00+08:00"

    rows: list[dict] = []
    search_after = None

    while True:
        body = {
            "size": page_size,
            "_source": SOURCE_FIELDS,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": time_from, "lt": time_to}}},
                        SYSTEM_FILTER,
                    ]
                }
            },
            "sort": [
                {"@timestamp": "asc"},
                {"_id": "asc"},
            ],
        }
        if search_after is not None:
            body["search_after"] = search_after

        response = es_search(body)
        hits = response["hits"]["hits"]
        if not hits:
            break

        rows.extend(normalize_event(hit["_source"]) for hit in hits)
        search_after = hits[-1]["sort"]

        if len(hits) < page_size:
            break

    return rows


def main() -> None:
    args = parse_args()
    target_dates = resolve_target_dates(args)

    for target_date in target_dates:
        print(f"[INFO] 擷取 {target_date} 的原始事件...")
        rows = fetch_events_for_date(target_date, args.page_size)
        file_path = write_events_partition(target_date, rows)
        update_manifest(target_date, len(rows))
        print(f"[OK] {target_date}：{len(rows):,} 筆 → {file_path}")


if __name__ == "__main__":
    main()
