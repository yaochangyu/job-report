from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import EXPECTED_PAGE_NAVIGATION, PAGE_NAVIGATION_ROWS


def test_page_navigation_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, PAGE_NAVIGATION_ROWS)

    from builders.build_page_navigation_t2 import build_page_navigation_t2

    dirs = build_page_navigation_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    for key, expected in EXPECTED_PAGE_NAVIGATION.items():
        assert int(row[key]) == expected, f"{key}: got {row[key]}, want {expected}"


def test_page_navigation_nav_pairs(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, PAGE_NAVIGATION_ROWS)

    from builders.build_page_navigation_t2 import build_page_navigation_t2

    dirs = build_page_navigation_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "nav_pairs.parquet")

    assert set(["from", "to", "count"]).issubset(df.columns)
    assert len(df) > 0
    assert df["count"].sum() > 0


def test_page_navigation_extra_files(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, PAGE_NAVIGATION_ROWS)

    from builders.build_page_navigation_t2 import build_page_navigation_t2

    dirs = build_page_navigation_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]

    for fname in ("entry_pages.parquet", "page_sources.parquet", "page_destinations.parquet"):
        df = pd.read_parquet(out / fname)
        assert len(df) > 0, f"{fname} is empty"
