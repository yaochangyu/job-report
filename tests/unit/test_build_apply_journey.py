from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import APPLY_JOURNEY_ROWS, EXPECTED_APPLY_JOURNEY


def test_apply_journey_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, APPLY_JOURNEY_ROWS)

    from builders.build_apply_journey_t2 import build_apply_journey_t2

    dirs = build_apply_journey_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    assert set(["date", "applies", "apply_sessions", "total_steps"]).issubset(df.columns)
    row = df.iloc[0]
    assert int(row["applies"])       == EXPECTED_APPLY_JOURNEY["applies"]
    assert int(row["apply_sessions"]) == EXPECTED_APPLY_JOURNEY["apply_sessions"]
    assert int(row["total_steps"])   == EXPECTED_APPLY_JOURNEY["total_steps"]


def test_apply_journey_extra_files(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, APPLY_JOURNEY_ROWS)

    from builders.build_apply_journey_t2 import build_apply_journey_t2

    dirs = build_apply_journey_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]

    path_df = pd.read_parquet(out / "path_ranking.parquet")
    assert set(["path", "step_count", "count"]).issubset(path_df.columns)
    assert len(path_df) == 2  # two distinct journeys

    for fname in ("entry_page.parquet", "step_distribution.parquet"):
        df = pd.read_parquet(out / fname)
        assert len(df) > 0, f"{fname} is empty"
