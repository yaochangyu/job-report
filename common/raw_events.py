"""
raw_events.py
─────────────
T1 raw 事件資料的標準欄位契約與正規化工具。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import pyarrow as pa

from common.es_client import TW

RAW_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RawEventRecord:
    date: str
    hour: int
    occurred_at: str
    system: str
    event_type: str | None
    action: str | None
    session_id: str | None
    anonymous_id: str | None
    user_id: str | None
    client_id: str | None
    locale: str | None
    message_id: str | None
    feature_id: str | None
    feature_name: str | None
    feature_type: str | None
    page_url: str | None
    previous_page_url: str | None
    page_path: str | None
    previous_page_path: str | None
    device_type: str | None
    os: str | None
    browser: str | None
    source: str | None
    category_tab: str | None
    identity_type: str | None
    industry_tab: str | None
    job_id: str | None
    company_id: str | None


RAW_EVENT_FIELDS = tuple(field.name for field in RawEventRecord.__dataclass_fields__.values())

RAW_EVENT_SCHEMA = pa.schema([
    ("date", pa.string()),
    ("hour", pa.int8()),
    ("occurred_at", pa.string()),
    ("system", pa.string()),
    ("event_type", pa.string()),
    ("action", pa.string()),
    ("session_id", pa.string()),
    ("anonymous_id", pa.string()),
    ("user_id", pa.string()),
    ("client_id", pa.string()),
    ("locale", pa.string()),
    ("message_id", pa.string()),
    ("feature_id", pa.string()),
    ("feature_name", pa.string()),
    ("feature_type", pa.string()),
    ("page_url", pa.string()),
    ("previous_page_url", pa.string()),
    ("page_path", pa.string()),
    ("previous_page_path", pa.string()),
    ("device_type", pa.string()),
    ("os", pa.string()),
    ("browser", pa.string()),
    ("source", pa.string()),
    ("category_tab", pa.string()),
    ("identity_type", pa.string()),
    ("industry_tab", pa.string()),
    ("job_id", pa.string()),
    ("company_id", pa.string()),
])


def normalize_url_path(url: str | None) -> str | None:
    """將完整 URL 正規化為 path。"""

    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or "/"
    return path[:255]


def parse_occurred_at(value: str | None) -> datetime:
    """將 ES 時間欄位轉成台灣時區 datetime。"""

    if not value:
        raise ValueError("缺少 @timestamp")
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(TW)


def normalize_raw_event(source: dict[str, Any]) -> dict[str, Any]:
    """將 ES 原始 _source 正規化為 T1 raw schema。"""

    metadata = source.get("metadata") or {}
    occurred_at = parse_occurred_at(source.get("@timestamp"))
    page_url = source.get("pageUrl")
    previous_page_url = source.get("previousPageUrl")

    return {
        "date": occurred_at.date().isoformat(),
        "hour": occurred_at.hour,
        "occurred_at": occurred_at.isoformat(),
        "system": source.get("system") or "jobbank-web",
        "event_type": source.get("eventType"),
        "action": source.get("action"),
        "session_id": source.get("sessionId"),
        "anonymous_id": source.get("anonymousId"),
        "user_id": source.get("userId"),
        "client_id": source.get("clientId"),
        "locale": source.get("locale"),
        "message_id": source.get("messageId"),
        "feature_id": source.get("featureId"),
        "feature_name": source.get("featureName"),
        "feature_type": source.get("featureType"),
        "page_url": page_url,
        "previous_page_url": previous_page_url,
        "page_path": normalize_url_path(page_url),
        "previous_page_path": normalize_url_path(previous_page_url),
        "device_type": source.get("deviceType"),
        "os": source.get("os"),
        "browser": source.get("browser"),
        "source": metadata.get("source"),
        "category_tab": metadata.get("categoryTab"),
        "identity_type": metadata.get("identityType"),
        "industry_tab": metadata.get("industryTab"),
        "job_id": str(metadata["jobId"]) if metadata.get("jobId") is not None else None,
        "company_id": str(metadata["companyId"]) if metadata.get("companyId") is not None else None,
    }
