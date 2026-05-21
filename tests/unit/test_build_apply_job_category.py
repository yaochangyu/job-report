from __future__ import annotations

import pandas as pd
import pytest

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import (
    APPLY_JOB_CATEGORY_ROWS,
    EXPECTED_APPLY_JOB_CATEGORY,
)


def _build(patch_dirs):
    t1_dir, _ = patch_dirs
    write_t1(t1_dir, APPLY_JOB_CATEGORY_ROWS)
    from builders.build_apply_job_category_t2 import build_apply_job_category_t2
    return build_apply_job_category_t2(TEST_DATE, TEST_DATE)


def test_returns_one_dir(patch_dirs):
    dirs = _build(patch_dirs)
    assert len(dirs) == 1


def test_all_parquets_exist(patch_dirs):
    dirs = _build(patch_dirs)
    out = dirs[0]
    for fname in (
        "daily_summary.parquet",
        "job_position_top.parquet",
        "company_industry_top.parquet",
        "job_position_daily.parquet",
        "company_industry_daily.parquet",
    ):
        assert (out / fname).exists(), f"{fname} not found"


def test_daily_summary(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    row = df.iloc[0]
    assert int(row["total_applies"])         == EXPECTED_APPLY_JOB_CATEGORY["total_applies"]
    assert int(row["applies_with_metadata"]) == EXPECTED_APPLY_JOB_CATEGORY["applies_with_metadata"]
    assert float(row["coverage_rate"])       == pytest.approx(EXPECTED_APPLY_JOB_CATEGORY["coverage_rate"])


def test_job_position_top_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "job_position_top.parquet")
    assert set(df.columns) >= {"name", "count"}
    assert len(df) > 0


def test_job_position_top_values(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "job_position_top.parquet")
    top = df.iloc[0]
    assert top["name"]        == EXPECTED_APPLY_JOB_CATEGORY["top_job_position"]
    assert int(top["count"])  == EXPECTED_APPLY_JOB_CATEGORY["top_job_position_count"]


def test_company_industry_top_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "company_industry_top.parquet")
    assert set(df.columns) >= {"name", "count"}
    assert len(df) > 0


def test_company_industry_top_values(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "company_industry_top.parquet")
    top = df.iloc[0]
    assert top["name"]       == EXPECTED_APPLY_JOB_CATEGORY["top_industry"]
    assert int(top["count"]) == EXPECTED_APPLY_JOB_CATEGORY["top_industry_count"]


def test_job_position_daily_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "job_position_daily.parquet")
    assert set(df.columns) >= {"date", "name", "count"}


def test_company_industry_daily_columns(patch_dirs):
    dirs = _build(patch_dirs)
    df = pd.read_parquet(dirs[0] / "company_industry_daily.parquet")
    assert set(df.columns) >= {"date", "name", "count"}
