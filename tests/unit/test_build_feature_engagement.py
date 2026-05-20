from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import EXPECTED_FEATURE_ENGAGEMENT, FEATURE_ENGAGEMENT_ROWS


def test_feature_engagement_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, FEATURE_ENGAGEMENT_ROWS)

    from builders.build_feature_engagement_t2 import build_feature_engagement_t2

    dirs = build_feature_engagement_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    for key, expected in EXPECTED_FEATURE_ENGAGEMENT.items():
        assert int(row[key]) == expected, f"{key}: got {row[key]}, want {expected}"


def test_feature_engagement_detail_files(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, FEATURE_ENGAGEMENT_ROWS)

    from builders.build_feature_engagement_t2 import build_feature_engagement_t2

    dirs = build_feature_engagement_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]

    for fname in (
        "explore_jobs_features.parquet",
        "explore_corp_features.parquet",
        "identity_main.parquet",
        "news_features.parquet",
    ):
        df = pd.read_parquet(out / fname)
        assert "name" in df.columns
        assert "count" in df.columns
