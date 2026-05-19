#!/usr/bin/env python3
"""
extract_raw_events.py
────────────────────
從 Elasticsearch 抽取 T1 raw 事件資料，寫入本地 parquet。
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from common.data_pipeline import (
    T1_RAW_MANIFEST_PATH,
    ensure_pipeline_directories,
    t1_raw_date_dir,
)
from common.es_client import ES_INDEX, TW, generated_now, msearch
from common.raw_events import (
    RAW_EVENT_FIELDS,
    RAW_EVENT_SCHEMA,
    RAW_SCHEMA_VERSION,
    normalize_raw_event,
)

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}
SEARCH_BATCH_SIZE = 5000
PARQUET_FILE_NAME = "events.parquet"
PARQUET_COMPRESSION = "zstd"
PARQUET_ROW_GROUP_SIZE = 100000
SOURCE_FIELDS = [
    "@timestamp",
    "system",
    "eventType",
    "action",
    "sessionId",
    "anonymousId",
    "userId",
    "clientId",
    "locale",
    "messageId",
    "featureId",
    "featureName",
    "featureType",
    "pageUrl",
    "previousPageUrl",
    "deviceType",
    "os",
    "browser",
    "metadata",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抽取 T1 raw 事件 parquet")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--days", type=int, help="抽取最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", help="結束日期 YYYY-MM-DD")
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="若指定日期 parquet 已存在則跳過，不重抓。",
    )
    return parser.parse_args()


def resolve_dates(args: argparse.Namespace) -> list[str]:
    if args.days:
        today = datetime.now(TW).date()
        start = today - timedelta(days=args.days - 1)
        end = today
    else:
        start = date.fromisoformat(args.date_from)
        end = date.fromisoformat(args.date_to or args.date_from)
    if start > end:
        raise ValueError("--from 不可大於 --to")
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def build_search_body(target_date: str, search_after: list[Any] | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "size": SEARCH_BATCH_SIZE,
        "_source": SOURCE_FIELDS,
        "sort": [
            {"@timestamp": {"order": "asc"}},
            {"messageId": {"order": "asc", "missing": "_last"}},
        ],
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": f"{target_date}T00:00:00+08:00", "lte": f"{target_date}T23:59:59+08:00"}}},
                    SYSTEM_FILTER,
                ]
            }
        },
    }
    if search_after:
        body["search_after"] = search_after
    return body


def fetch_raw_events(target_date: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    search_after: list[Any] | None = None
    batch_count = 0

    while True:
        response = msearch(build_search_body(target_date, search_after), index=ES_INDEX)
        hits = response.get("hits", {}).get("hits", [])
        if not hits:
            break
        batch_count += 1
        for hit in hits:
            rows.append(normalize_raw_event(hit.get("_source", {})))
        search_after = hits[-1].get("sort")
        if batch_count % 10 == 0:
            print(f"    已抓取 {len(rows):,} 筆...")
        if len(hits) < SEARCH_BATCH_SIZE:
            break

    return rows


def write_daily_parquet(target_date: str, rows: list[dict[str, Any]]) -> Path:
    output_dir = t1_raw_date_dir(target_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / PARQUET_FILE_NAME
    data = {
        field: [row.get(field) for row in rows]
        for field in RAW_EVENT_FIELDS
    }
    table = pa.Table.from_pydict(data, schema=RAW_EVENT_SCHEMA)
    pq.write_table(
        table,
        parquet_path,
        compression=PARQUET_COMPRESSION,
        row_group_size=PARQUET_ROW_GROUP_SIZE,
    )
    return parquet_path


def write_manifest(results: dict[str, dict[str, Any]]) -> None:
    existing: dict[str, Any] = {}
    if T1_RAW_MANIFEST_PATH.exists():
        try:
            existing = json.loads(T1_RAW_MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    merged_dates: dict[str, Any] = dict(existing.get("dates", {}))
    merged_dates.update(results)

    manifest = {
        "schema_version": RAW_SCHEMA_VERSION,
        "tier": "t1-raw",
        "description": "從 Elasticsearch 匯出的標準化原始事件 parquet。",
        "source_index": ES_INDEX,
        "source_fields": SOURCE_FIELDS,
        "partition_rule": "date=YYYY-MM-DD",
        "compression": PARQUET_COMPRESSION,
        "row_group_size": PARQUET_ROW_GROUP_SIZE,
        "available_dates": sorted(merged_dates.keys()),
        "dates": merged_dates,
        "updated_at": generated_now(),
    }
    T1_RAW_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def extract_raw_events(date_from: str, date_to: str, keep_existing: bool = False) -> dict[str, dict[str, Any]]:
    """抽取指定日期區間的 T1 raw parquet。"""

    ensure_pipeline_directories()
    results: dict[str, dict[str, Any]] = {}

    for target_date in resolve_dates(argparse.Namespace(days=None, date_from=date_from, date_to=date_to)):
        output_path = t1_raw_date_dir(target_date) / PARQUET_FILE_NAME
        if keep_existing and output_path.exists():
            print(f"[SKIP] {target_date} 已存在：{output_path}")
            results[target_date] = {
                "path": str(output_path.relative_to(output_path.parents[2])),
                "rows": None,
                "status": "skipped",
            }
            continue

        print(f"[T1] 抽取 {target_date} ...")
        rows = fetch_raw_events(target_date)
        parquet_path = write_daily_parquet(target_date, rows)
        print(f"  → {len(rows):,} 筆：{parquet_path}")
        results[target_date] = {
            "path": str(parquet_path.relative_to(parquet_path.parents[2])),
            "rows": len(rows),
            "status": "generated",
        }

    write_manifest(results)
    return results


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args)
    results = extract_raw_events(date_from, date_to, keep_existing=args.keep_existing)
    print(f"[OK] T1 manifest 已更新：{T1_RAW_MANIFEST_PATH}")
    print(f"[OK] 完成日期：{', '.join(sorted(results))}")


def resolve_date_window(args: argparse.Namespace) -> tuple[str, str]:
    """將 CLI 參數轉為日期區間。"""

    dates = resolve_dates(args)
    return dates[0], dates[-1]


if __name__ == "__main__":
    main()
