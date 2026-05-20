from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import APPLY_CONVERSION_ROWS, EXPECTED_APPLY_CONVERSION


def test_apply_conversion_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, APPLY_CONVERSION_ROWS)

    from builders.build_apply_conversion_t2 import build_apply_conversion_t2

    dirs = build_apply_conversion_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    assert list(df.columns) == ["date", "applies", "job_views"]
    row = df.iloc[0]
    assert int(row["applies"])   == EXPECTED_APPLY_CONVERSION["applies"]
    assert int(row["job_views"]) == EXPECTED_APPLY_CONVERSION["job_views"]


def test_apply_conversion_source_and_funnel(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, APPLY_CONVERSION_ROWS)

    from builders.build_apply_conversion_t2 import build_apply_conversion_t2

    dirs = build_apply_conversion_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]

    for fname in ("source.parquet", "funnel.parquet"):
        df = pd.read_parquet(out / fname)
        assert len(df) > 0, f"{fname} is empty"
        assert "count" in df.columns
