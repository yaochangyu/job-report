"""
store.py
────────
SQLite 雙層儲存：即時層（snapshots_interval）＋ 日報層（snapshots_daily）。
"""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "store.db"

TW = timezone(timedelta(hours=8))


def parse_date_range(time_from: str, time_to: str) -> tuple[str, str]:
    """將 time_from / time_to 轉換為 YYYY-MM-DD 字串。

    支援：
    - Grafana 相對時間：now-Nd → 今天減 N 天
    - "now" → 今天
    - ISO 8601 datetime → 取前 10 字元
    - YYYY-MM-DD → 直接使用
    """
    def _to_date(s: str) -> str:
        if s.lower() == "now":
            return datetime.now(TW).strftime("%Y-%m-%d")
        m = re.match(r"now-(\d+)([dhm])$", s, re.IGNORECASE)
        if m:
            n, unit = int(m.group(1)), m.group(2).lower()
            delta = timedelta(days=n) if unit == "d" else timedelta(hours=n) if unit == "h" else timedelta(minutes=n)
            return (datetime.now(TW) - delta).strftime("%Y-%m-%d")
        return s[:10]

    return _to_date(time_from), _to_date(time_to)


# ── 初始化 ───────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS snapshots_interval (
    time_from  TEXT NOT NULL,
    time_to    TEXT NOT NULL,
    report     TEXT NOT NULL,
    query_name TEXT NOT NULL,
    data       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (time_from, time_to, report, query_name)
);

CREATE TABLE IF NOT EXISTS snapshots_daily (
    date       TEXT NOT NULL,
    report     TEXT NOT NULL,
    query_name TEXT NOT NULL,
    data       TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (date, report, query_name)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(db_path: Path | None = None) -> None:
    """建立資料表（若不存在）。可傳入自訂路徑，供測試使用。"""
    global DB_PATH
    if db_path:
        DB_PATH = db_path
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as con:
        con.executescript(DDL)


# ── 即時層 ───────────────────────────────────────────────────────────────────

def save_interval(
    time_from: str,
    time_to: str,
    report: str,
    query_name: str,
    data: dict | list,
) -> None:
    """寫入一筆即時聚合結果（UPSERT）。"""
    now = datetime.now(TW).isoformat()
    with _conn() as con:
        con.execute(
            """
            INSERT INTO snapshots_interval
                (time_from, time_to, report, query_name, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(time_from, time_to, report, query_name)
            DO UPDATE SET data = excluded.data, created_at = excluded.created_at
            """,
            (time_from, time_to, report, query_name, json.dumps(data, ensure_ascii=False), now),
        )


def load_interval(
    time_from: str,
    time_to: str,
    report: str,
    query_name: str,
) -> dict | list | None:
    """讀取一筆即時聚合結果，不存在則回傳 None。"""
    with _conn() as con:
        row = con.execute(
            """
            SELECT data FROM snapshots_interval
            WHERE time_from = ? AND time_to = ? AND report = ? AND query_name = ?
            """,
            (time_from, time_to, report, query_name),
        ).fetchone()
    return json.loads(row["data"]) if row else None


def load_intervals_in_range(
    time_from: str,
    time_to: str,
    report: str,
    query_name: str,
) -> list[dict]:
    """讀取時間範圍內所有即時區間，依 time_from 排序。"""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT time_from, time_to, data FROM snapshots_interval
            WHERE report = ? AND query_name = ?
              AND time_from >= ? AND time_to <= ?
            ORDER BY time_from
            """,
            (report, query_name, time_from, time_to),
        ).fetchall()
    return [
        {"time_from": r["time_from"], "time_to": r["time_to"], "data": json.loads(r["data"])}
        for r in rows
    ]


# ── 日報層 ───────────────────────────────────────────────────────────────────

def save_daily(
    date: str,
    report: str,
    query_name: str,
    data: dict | list,
) -> None:
    """寫入一筆日報聚合結果（UPSERT）。date 格式：YYYY-MM-DD。"""
    now = datetime.now(TW).isoformat()
    with _conn() as con:
        con.execute(
            """
            INSERT INTO snapshots_daily
                (date, report, query_name, data, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date, report, query_name)
            DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
            """,
            (date, report, query_name, json.dumps(data, ensure_ascii=False), now),
        )


def load_daily(
    date: str,
    report: str,
    query_name: str,
) -> dict | list | None:
    """讀取單日日報結果，不存在則回傳 None。"""
    with _conn() as con:
        row = con.execute(
            """
            SELECT data FROM snapshots_daily
            WHERE date = ? AND report = ? AND query_name = ?
            """,
            (date, report, query_name),
        ).fetchone()
    return json.loads(row["data"]) if row else None


def load_daily_range(
    date_from: str,
    date_to: str,
    report: str,
    query_name: str,
) -> list[dict]:
    """讀取日期區間內所有日報，依 date 排序。date 格式：YYYY-MM-DD。"""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT date, data FROM snapshots_daily
            WHERE report = ? AND query_name = ?
              AND date >= ? AND date <= ?
            ORDER BY date
            """,
            (report, query_name, date_from, date_to),
        ).fetchall()
    return [{"date": r["date"], "data": json.loads(r["data"])} for r in rows]


# ── Meta（上次執行時間等） ────────────────────────────────────────────────────

def get_meta(key: str) -> str | None:
    with _conn() as con:
        row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
