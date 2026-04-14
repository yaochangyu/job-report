"""
t1_reader.py
────────────
讀取 T1 raw parquet 的共用工具。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from common.data_pipeline import T1_RAW_DIR
from common.es_client import TW


def resolve_date_window(days: int | None = None, date_from: str | None = None, date_to: str | None = None) -> tuple[str, str]:
    """將 days / from / to 轉為日期區間。"""

    if days:
        today = datetime.now(TW).date()
        start = today - timedelta(days=days - 1)
        end = today
    elif date_from:
        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to or date_from)
    else:
        today = datetime.now(TW).date().isoformat()
        return today, today

    if start > end:
        raise ValueError("date_from 不可大於 date_to")
    return start.isoformat(), end.isoformat()


def iter_dates(date_from: str, date_to: str) -> list[str]:
    """列出日期區間內所有日期字串。"""

    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    values: list[str] = []
    current = start
    while current <= end:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def t1_raw_files(date_from: str, date_to: str) -> list[Path]:
    """取得指定日期區間的 T1 parquet 檔案。"""

    files = [
        T1_RAW_DIR / f"date={target_date}" / "events.parquet"
        for target_date in iter_dates(date_from, date_to)
    ]
    return [path for path in files if path.exists()]


def load_t1_raw_dataframe(date_from: str, date_to: str, columns: list[str] | None = None) -> pd.DataFrame:
    """讀取指定日期區間的 T1 raw parquet。"""

    files = t1_raw_files(date_from, date_to)
    if not files:
        raise FileNotFoundError(f"找不到 T1 raw parquet：{date_from} ~ {date_to}")
    frames = [pd.read_parquet(path, columns=columns) for path in files]
    return pd.concat(frames, ignore_index=True)
