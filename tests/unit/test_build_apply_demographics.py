from __future__ import annotations

import pandas as pd
import pytest

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import (
    APPLY_DEMOGRAPHICS_ROWS,
    EXPECTED_APPLY_DEMOGRAPHICS,
)


def test_daily_summary(patch_dirs):
    t1_dir, _ = patch_dirs
    write_t1(t1_dir, APPLY_DEMOGRAPHICS_ROWS)

    from builders.build_apply_demographics_t2 import build_apply_demographics_t2

    dirs = build_apply_demographics_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    assert int(row["total_applies"])         == EXPECTED_APPLY_DEMOGRAPHICS["total_applies"]
    assert int(row["applies_with_metadata"]) == EXPECTED_APPLY_DEMOGRAPHICS["applies_with_metadata"]
    assert float(row["coverage_rate"])       == pytest.approx(2 / 4, rel=1e-3)


def test_gender_dist(patch_dirs):
    t1_dir, _ = patch_dirs
    write_t1(t1_dir, APPLY_DEMOGRAPHICS_ROWS)

    from builders.build_apply_demographics_t2 import build_apply_demographics_t2

    dirs = build_apply_demographics_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "gender.parquet")
    assert set(df.columns) >= {"gender", "count"}

    gender_map = dict(zip(df["gender"], df["count"].astype(int)))
    expected = EXPECTED_APPLY_DEMOGRAPHICS["gender_counts"]
    for g, cnt in expected.items():
        assert gender_map.get(g, 0) == cnt, f"gender={g}: expected {cnt}, got {gender_map.get(g, 0)}"


def test_age_groups_dist(patch_dirs):
    t1_dir, _ = patch_dirs
    write_t1(t1_dir, APPLY_DEMOGRAPHICS_ROWS)

    from builders.build_apply_demographics_t2 import build_apply_demographics_t2

    dirs = build_apply_demographics_t2(TEST_DATE, TEST_DATE)
    df = pd.read_parquet(dirs[0] / "age_groups.parquet")
    assert set(df.columns) >= {"age_group", "count"}
    assert df["count"].sum() == EXPECTED_APPLY_DEMOGRAPHICS["total_applies"]


def test_daily_parquets_exist(patch_dirs):
    t1_dir, _ = patch_dirs
    write_t1(t1_dir, APPLY_DEMOGRAPHICS_ROWS)

    from builders.build_apply_demographics_t2 import build_apply_demographics_t2

    dirs = build_apply_demographics_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]
    for fname in ("gender_daily.parquet", "age_groups_daily.parquet"):
        df = pd.read_parquet(out / fname)
        assert len(df) > 0, f"{fname} should not be empty"
        assert "count" in df.columns
