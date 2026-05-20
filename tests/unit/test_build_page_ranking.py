from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import EXPECTED_PAGE_RANKING, PAGE_RANKING_ROWS


def test_page_ranking_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, PAGE_RANKING_ROWS)

    from builders.build_page_ranking_t2 import build_page_ranking_t2

    dirs = build_page_ranking_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    assert int(row["total_events"])   == EXPECTED_PAGE_RANKING["total_events"]
    assert int(row["total_features"]) == EXPECTED_PAGE_RANKING["total_features"]
    assert row["top_feature_id"]      == EXPECTED_PAGE_RANKING["top_feature_id"]


def test_page_ranking_features(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, PAGE_RANKING_ROWS)

    from builders.build_page_ranking_t2 import build_page_ranking_t2

    dirs = build_page_ranking_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "features.parquet")

    assert "featureId" in df.columns
    assert "total" in df.columns
    assert df["featureId"].isna().sum() == 0

    for fid, expected in EXPECTED_PAGE_RANKING["features"].items():
        row = df[df["featureId"] == fid].iloc[0]
        assert int(row["total"])  == expected["total"],  f"{fid} total"
        assert int(row["views"])  == expected["views"],  f"{fid} views"
        assert int(row["clicks"]) == expected["clicks"], f"{fid} clicks"


def test_page_ranking_categories_exist(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, PAGE_RANKING_ROWS)

    from builders.build_page_ranking_t2 import build_page_ranking_t2

    dirs = build_page_ranking_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "categories.parquet")
    assert len(df) > 0
    assert "name" in df.columns
    assert "count" in df.columns
