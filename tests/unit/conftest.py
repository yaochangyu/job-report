from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

TEST_DATE = "2026-01-01"

T1_COLUMNS = [
    "date", "system", "event_type", "action", "session_id", "occurred_at",
    "feature_id", "feature_name", "device_type", "os", "browser",
    "source", "page_path", "previous_page_path", "category_tab", "identity_type",
    "user_id", "job_id",
    "sex_i", "birth_dt", "job_positions", "company_industries",
]

_DEFAULTS: dict = {
    "date": TEST_DATE,
    "system": "jobbank-web",
    "event_type": None,
    "action": None,
    "session_id": None,
    "occurred_at": "2026-01-01T10:00:00+08:00",
    "feature_id": None,
    "feature_name": None,
    "device_type": None,
    "os": None,
    "browser": None,
    "source": None,
    "page_path": None,
    "previous_page_path": None,
    "category_tab": None,
    "identity_type": None,
    "user_id": None,
    "job_id": None,
    "sex_i": None,
    "birth_dt": None,
    "job_positions": None,
    "company_industries": None,
}


def make_t1_events(rows: list[dict]) -> pd.DataFrame:
    filled = [{**_DEFAULTS, **row} for row in rows]
    return pd.DataFrame(filled, columns=T1_COLUMNS)


@pytest.fixture
def patch_dirs(monkeypatch, tmp_path):
    t1_dir = tmp_path / "raw"
    t2_dir = tmp_path / "report"
    manifest_dir = tmp_path / "manifest"
    t3_dir = tmp_path / "output"
    for d in (t1_dir, t2_dir, manifest_dir, t3_dir):
        d.mkdir()

    import common.data_pipeline as dp
    import common.t1_reader as t1r

    monkeypatch.setattr(dp, "T1_RAW_DIR", t1_dir)
    monkeypatch.setattr(dp, "T2_REPORT_DIR", t2_dir)
    monkeypatch.setattr(dp, "MANIFEST_DIR", manifest_dir)
    monkeypatch.setattr(dp, "T3_RENDER_DIR", t3_dir)
    monkeypatch.setattr(dp, "T2_REPORT_MANIFEST_PATH", manifest_dir / "t2-report-manifest.json")
    monkeypatch.setattr(t1r, "T1_RAW_DIR", t1_dir)

    return t1_dir, t2_dir


def write_t1(t1_dir: Path, rows: list[dict], date: str = TEST_DATE) -> None:
    date_dir = t1_dir / f"date={date}"
    date_dir.mkdir(parents=True, exist_ok=True)
    make_t1_events(rows).to_parquet(date_dir / "events.parquet", index=False)
