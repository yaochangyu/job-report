from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import EXPECTED_HOMEPAGE_BLOCKS, HOMEPAGE_BLOCKS_ROWS


def test_homepage_blocks_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, HOMEPAGE_BLOCKS_ROWS)

    from builders.build_homepage_blocks_t2 import build_homepage_blocks_t2

    dirs = build_homepage_blocks_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    assert set(["date", "total_clicks", "total_views", "feature_count"]).issubset(df.columns)
    row = df.iloc[0]
    assert int(row["total_clicks"])  == EXPECTED_HOMEPAGE_BLOCKS["total_clicks"]
    assert int(row["total_views"])   == EXPECTED_HOMEPAGE_BLOCKS["total_views"]
    assert int(row["feature_count"]) == EXPECTED_HOMEPAGE_BLOCKS["feature_count"]
    assert row["top_feature_id"]     == EXPECTED_HOMEPAGE_BLOCKS["top_feature_id"]
    assert int(row["top_count"])     == EXPECTED_HOMEPAGE_BLOCKS["top_count"]


def test_homepage_blocks_feature_counts(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, HOMEPAGE_BLOCKS_ROWS)

    from builders.build_homepage_blocks_t2 import build_homepage_blocks_t2

    dirs = build_homepage_blocks_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "feature_counts.parquet")

    assert set(["event_type", "feature_id", "count"]).issubset(df.columns)
    assert "unknown-feature" not in df["feature_id"].values

    click_df = df[df["event_type"] == "click"]
    assert int(click_df[click_df["feature_id"] == "identify-student"]["count"].iloc[0]) == 2
    assert int(click_df[click_df["feature_id"] == "explore-jobs-organic"]["count"].iloc[0]) == 1
