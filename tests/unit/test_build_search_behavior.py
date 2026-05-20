from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import EXPECTED_SEARCH, SEARCH_ROWS


def test_search_behavior_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, SEARCH_ROWS)

    from builders.build_search_behavior_t2 import build_search_behavior_t2

    dirs = build_search_behavior_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    for key, expected in EXPECTED_SEARCH.items():
        assert int(row[key]) == expected, f"{key}: got {row[key]}, want {expected}"


def test_search_behavior_feature_counts(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, SEARCH_ROWS)

    from builders.build_search_behavior_t2 import build_search_behavior_t2

    dirs = build_search_behavior_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "feature_counts.parquet")

    assert "event_type" in df.columns
    assert "feature_id" in df.columns
    assert "count" in df.columns
    assert df["count"].sum() == len(SEARCH_ROWS)
