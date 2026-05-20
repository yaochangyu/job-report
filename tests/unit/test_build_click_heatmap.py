from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import CLICK_HEATMAP_ROWS, EXPECTED_CLICK_HEATMAP


def test_click_heatmap_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, CLICK_HEATMAP_ROWS)

    from builders.build_click_heatmap_t2 import build_click_heatmap_t2

    dirs = build_click_heatmap_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    assert set(["date", "total_clicks", "feature_count", "top_feature_id", "top_count"]).issubset(df.columns)
    row = df.iloc[0]
    assert int(row["total_clicks"])  == EXPECTED_CLICK_HEATMAP["total_clicks"]
    assert int(row["feature_count"]) == EXPECTED_CLICK_HEATMAP["feature_count"]
    assert row["top_feature_id"]     == EXPECTED_CLICK_HEATMAP["top_feature_id"]
    assert int(row["top_count"])     == EXPECTED_CLICK_HEATMAP["top_count"]


def test_click_heatmap_click_counts(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, CLICK_HEATMAP_ROWS)

    from builders.build_click_heatmap_t2 import build_click_heatmap_t2

    dirs = build_click_heatmap_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "click_counts.parquet")

    assert "feature_id" in df.columns
    assert "count" in df.columns
    assert df["feature_id"].isna().sum() == 0

    top = df.groupby("feature_id")["count"].sum()
    assert top["search-general-keyword"] == 2
    assert top["identify-student"] == 1
    assert top["search-ai-submit"] == 1
