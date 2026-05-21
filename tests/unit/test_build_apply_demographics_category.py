from __future__ import annotations

import pandas as pd
import pytest

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import (
    APPLY_DEMOGRAPHICS_CATEGORY_ROWS,
    EXPECTED_APPLY_DEMOGRAPHICS_CATEGORY,
)


def _build(patch_dirs):
    t1_dir, _ = patch_dirs
    write_t1(t1_dir, APPLY_DEMOGRAPHICS_CATEGORY_ROWS)
    from builders.build_apply_demographics_category_t2 import build_apply_demographics_category_t2
    return build_apply_demographics_category_t2(TEST_DATE, TEST_DATE)


def test_returns_one_dir(patch_dirs):
    dirs = _build(patch_dirs)
    assert len(dirs) == 1


def test_daily_summary(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    assert int(row["total_applies"]) == EXPECTED_APPLY_DEMOGRAPHICS_CATEGORY["total_applies"]
    assert int(row["coverage_demo"]) == EXPECTED_APPLY_DEMOGRAPHICS_CATEGORY["coverage_demo"]
    assert int(row["coverage_job"])  == EXPECTED_APPLY_DEMOGRAPHICS_CATEGORY["coverage_job"]


def test_gender_job_position_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "gender_job_position.parquet")
    assert set(df.columns) >= {"gender", "category", "count"}
    assert len(df) > 0


def test_gender_job_position_values(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "gender_job_position.parquet")
    expected = EXPECTED_APPLY_DEMOGRAPHICS_CATEGORY["gender_job_position_sample"]
    for gender, cats in expected.items():
        for cat, cnt in cats.items():
            row = df[(df["gender"] == gender) & (df["category"] == cat)]
            assert not row.empty, f"missing ({gender}, {cat})"
            assert int(row.iloc[0]["count"]) == cnt, f"({gender}, {cat}) count mismatch"


def test_age_group_job_position_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "age_group_job_position.parquet")
    assert set(df.columns) >= {"age_group", "category", "count"}
    assert len(df) > 0


def test_gender_company_industry_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "gender_company_industry.parquet")
    assert set(df.columns) >= {"gender", "category", "count"}
    assert len(df) > 0


def test_age_group_company_industry_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "age_group_company_industry.parquet")
    assert set(df.columns) >= {"age_group", "category", "count"}
    assert len(df) > 0


def test_all_parquets_exist(patch_dirs):
    dirs = _build(patch_dirs)
    out = dirs[0]
    for fname in (
        "daily_summary.parquet",
        "gender_job_position.parquet",
        "gender_company_industry.parquet",
        "age_group_job_position.parquet",
        "age_group_company_industry.parquet",
    ):
        assert (out / fname).exists(), f"{fname} not found"
