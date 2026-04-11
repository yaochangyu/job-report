"""
parquet_schema.py
─────────────────
DuckDB-WASM 單頁報表使用的 Parquet dataset 定義。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    logical_type: str
    nullable: bool
    description: str


SCHEMA_VERSION = 1
DATASET_ROOT = Path(__file__).parent.parent / "dataset"
EVENTS_DIR = DATASET_ROOT / "events"
MANIFEST_FILE = DATASET_ROOT / "manifest.json"

PARTITION_COLUMNS = ("date",)
SORT_COLUMNS = ("date", "occurred_at", "feature_id", "event_type")
COMPRESSION = "zstd"
ROW_GROUP_SIZE = 100_000

EVENT_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("date", "date", False, "台灣時區日期，作為 Parquet partition key。"),
    ColumnSpec("hour", "tinyint", False, "台灣時區小時（0-23）。"),
    ColumnSpec("occurred_at", "timestamp", False, "事件發生時間（ISO 8601，含時區）。"),
    ColumnSpec("system", "string", False, "系統名稱，預設為 jobbank-web。"),
    ColumnSpec("event_type", "string", True, "事件型別，例如 view、click。"),
    ColumnSpec("action", "string", True, "動作類型，例如 apply。"),
    ColumnSpec("session_id", "string", True, "sessionId，供去重與訪客分析。"),
    ColumnSpec("feature_id", "string", True, "featureId。"),
    ColumnSpec("page_path", "string", True, "從 pageUrl 正規化出的 path。"),
    ColumnSpec("previous_page_path", "string", True, "從 previousPageUrl 正規化出的 path。"),
    ColumnSpec("device_type", "string", True, "裝置類型，例如 mobile、desktop。"),
    ColumnSpec("os", "string", True, "作業系統。"),
    ColumnSpec("browser", "string", True, "瀏覽器。"),
    ColumnSpec("source", "string", True, "metadata.source。"),
    ColumnSpec("category_tab", "string", True, "metadata.categoryTab。"),
    ColumnSpec("identity_type", "string", True, "metadata.identityType。"),
    ColumnSpec("industry_tab", "string", True, "metadata.industryTab。"),
)

OPTIONAL_DERIVED_TABLES = (
    "daily_kpi",
    "daily_feature",
    "daily_page_navigation",
)


def event_column_names() -> list[str]:
    return [column.name for column in EVENT_COLUMNS]


def schema_summary() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_root": str(DATASET_ROOT),
        "events_dir": str(EVENTS_DIR),
        "manifest_file": str(MANIFEST_FILE),
        "partition_columns": list(PARTITION_COLUMNS),
        "sort_columns": list(SORT_COLUMNS),
        "compression": COMPRESSION,
        "row_group_size": ROW_GROUP_SIZE,
        "event_columns": [
            {
                "name": column.name,
                "logical_type": column.logical_type,
                "nullable": column.nullable,
                "description": column.description,
            }
            for column in EVENT_COLUMNS
        ],
        "optional_derived_tables": list(OPTIONAL_DERIVED_TABLES),
    }
