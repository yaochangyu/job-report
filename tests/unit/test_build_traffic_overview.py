from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import EXPECTED_TRAFFIC, TRAFFIC_ROWS


def test_traffic_overview_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, TRAFFIC_ROWS)

    from builders.build_traffic_overview_t2 import build_traffic_overview_t2

    dirs = build_traffic_overview_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    out = dirs[0]
    df = pd.read_parquet(out / "daily_summary.parquet")

    assert list(df.columns) == ["date", "total", "views", "clicks", "applies", "sessions"]
    row = df.iloc[0]
    assert row["date"] == TEST_DATE
    assert int(row["total"])   == EXPECTED_TRAFFIC["total"]
    assert int(row["views"])   == EXPECTED_TRAFFIC["views"]
    assert int(row["clicks"])  == EXPECTED_TRAFFIC["clicks"]
    assert int(row["applies"]) == EXPECTED_TRAFFIC["applies"]
    assert int(row["sessions"]) == EXPECTED_TRAFFIC["sessions"]


def test_traffic_overview_breakdown_files_exist(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, TRAFFIC_ROWS)

    from builders.build_traffic_overview_t2 import build_traffic_overview_t2

    dirs = build_traffic_overview_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]

    for fname in ("device_type.parquet", "os.parquet", "browser.parquet"):
        df = pd.read_parquet(out / fname)
        assert len(df) > 0
        assert "name" in df.columns
        assert "count" in df.columns
