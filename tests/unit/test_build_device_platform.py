from __future__ import annotations

import pandas as pd

from tests.unit.conftest import TEST_DATE, write_t1
from tests.unit.fixture_data import DEVICE_PLATFORM_ROWS, EXPECTED_DEVICE_PLATFORM


def test_device_platform_daily_summary(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, DEVICE_PLATFORM_ROWS)

    from builders.build_device_platform_t2 import build_device_platform_t2

    dirs = build_device_platform_t2(TEST_DATE, TEST_DATE)
    assert len(dirs) == 1

    df = pd.read_parquet(dirs[0] / "daily_summary.parquet")
    assert set(["date", "mobile", "desktop"]).issubset(df.columns)
    row = df.iloc[0]
    assert int(row["mobile"])  == EXPECTED_DEVICE_PLATFORM["mobile"]
    assert int(row["desktop"]) == EXPECTED_DEVICE_PLATFORM["desktop"]


def test_device_platform_extra_files(patch_dirs):
    t1_dir, t2_dir = patch_dirs
    write_t1(t1_dir, DEVICE_PLATFORM_ROWS)

    from builders.build_device_platform_t2 import build_device_platform_t2

    dirs = build_device_platform_t2(TEST_DATE, TEST_DATE)
    out = dirs[0]

    for fname in ("os.parquet", "browser.parquet", "device_behavior.parquet", "os_behavior.parquet"):
        df = pd.read_parquet(out / fname)
        assert len(df) > 0, f"{fname} is empty"
