"""
parquet_dataset.py
──────────────────
Parquet dataset 寫入與 manifest 維護工具。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pyarrow as pa
import pyarrow.parquet as pq

from common.es_client import TW, generated_now
from common.parquet_schema import (
    COMPRESSION,
    EVENT_COLUMNS,
    EVENTS_DIR,
    MANIFEST_FILE,
    PARTITION_COLUMNS,
    ROW_GROUP_SIZE,
    schema_summary,
)

ENTRY_MARKER = "_entry_"

_TYPE_MAP = {
    "date": pa.date32(),
    "tinyint": pa.int8(),
    "timestamp": pa.timestamp("us", tz="Asia/Taipei"),
    "string": pa.string(),
}


def arrow_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field(column.name, _TYPE_MAP[column.logical_type], nullable=column.nullable)
            for column in EVENT_COLUMNS
        ]
    )


def parse_event_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TW)


def normalize_path(value: str | None, default: str | None = None) -> str | None:
    if not value:
        return default
    parsed = urlparse(value)
    path = parsed.path or "/"
    return path[:255]


def normalize_event(source: dict) -> dict:
    occurred_at = parse_event_timestamp(source["@timestamp"])
    metadata = source.get("metadata") or {}
    return {
        "date": occurred_at.date(),
        "hour": occurred_at.hour,
        "occurred_at": occurred_at,
        "system": source.get("system") or "jobbank-web",
        "event_type": source.get("eventType"),
        "action": source.get("action"),
        "session_id": source.get("sessionId"),
        "feature_id": source.get("featureId"),
        "page_path": normalize_path(source.get("pageUrl"), default="/"),
        "previous_page_path": normalize_path(source.get("previousPageUrl"), default=ENTRY_MARKER),
        "device_type": source.get("deviceType"),
        "os": source.get("os"),
        "browser": source.get("browser"),
        "source": metadata.get("source"),
        "category_tab": metadata.get("categoryTab"),
        "identity_type": metadata.get("identityType"),
        "industry_tab": metadata.get("industryTab"),
    }


def dataset_relative_path(target_date: str) -> str:
    partition = f"{PARTITION_COLUMNS[0]}={target_date}"
    return f"events/{partition}/events.parquet"


def dataset_file_path(target_date: str) -> Path:
    return EVENTS_DIR / f"{PARTITION_COLUMNS[0]}={target_date}" / "events.parquet"


def write_events_partition(target_date: str, rows: list[dict]) -> Path:
    file_path = dataset_file_path(target_date)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(
        rows,
        key=lambda item: (
            item["date"],
            item["occurred_at"],
            item["feature_id"] or "",
            item["event_type"] or "",
        ),
    )
    if sorted_rows:
        table = pa.Table.from_pylist(sorted_rows, schema=arrow_schema())
    else:
        table = pa.Table.from_pylist([], schema=arrow_schema())
    pq.write_table(
        table,
        file_path,
        compression=COMPRESSION,
        row_group_size=ROW_GROUP_SIZE,
    )
    return file_path


def load_manifest() -> dict:
    if not MANIFEST_FILE.exists():
        return {
            "schema": schema_summary(),
            "available_dates": [],
            "dates": {},
            "updated_at": None,
        }
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_manifest(target_date: str, row_count: int) -> None:
    manifest = load_manifest()
    manifest["schema"] = schema_summary()
    manifest.setdefault("dates", {})
    manifest["dates"][target_date] = {
        "path": dataset_relative_path(target_date),
        "rows": row_count,
    }
    manifest["available_dates"] = sorted(manifest["dates"].keys())
    manifest["updated_at"] = generated_now()
    save_manifest(manifest)
