#!/usr/bin/env python3
"""
build_period_summary.py
────────────────────────
從現有 homepage-blocks 日報 parquet 預算月報、季報、年報聚合 parquet。

目錄結構：
  dataset/report/homepage-blocks/
    date=YYYY-MM-DD/feature_counts.parquet      ← 現有日報（不動）
    monthly=YYYY-MM/feature_counts.parquet      ← 月報（period=YYYY-MM-DD 保留日粒度）
    quarterly=YYYY-Q{N}/feature_counts.parquet  ← 季報（period=YYYY-MM 月粒度）
    yearly=YYYY/feature_counts.parquet          ← 年報（period=YYYY-MM 月粒度）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from common.data_pipeline import T2_REPORT_DIR

REPORT_NAME = "homepage-blocks"
FEATURE_COUNTS_FILE = "feature_counts.parquet"


def _quarter_label(month: str) -> str:
    y, m = month.split("-")
    q = (int(m) - 1) // 3 + 1
    return f"{y}-Q{q}"


def load_all_daily(report_dir: Path) -> pd.DataFrame:
    frames = []
    for part in sorted(report_dir.iterdir()):
        if not part.is_dir() or not part.name.startswith("date="):
            continue
        f = part / FEATURE_COUNTS_FILE
        if f.exists():
            frames.append(pd.read_parquet(f))
    if not frames:
        return pd.DataFrame(columns=["date", "feature_id", "feature_name", "event_type", "count"])
    return pd.concat(frames, ignore_index=True)


def build_monthly(df: pd.DataFrame, report_dir: Path) -> list[str]:
    """月報：每月一個 parquet，period=YYYY-MM-DD（保留日粒度供前端畫趨勢）。"""
    df = df.copy()
    df["month"] = df["date"].str[:7]
    written = []
    for month, mdf in df.groupby("month"):
        out_dir = report_dir / f"monthly={month}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = (
            mdf.groupby(["date", "feature_id", "event_type"], as_index=False)
            .agg(count=("count", "sum"), feature_name=("feature_name", "first"))
            .rename(columns={"date": "period"})
            [["period", "feature_id", "feature_name", "event_type", "count"]]
            .sort_values(["event_type", "period", "count"], ascending=[True, True, False])
        )
        result.to_parquet(out_dir / FEATURE_COUNTS_FILE, index=False)
        written.append(str(month))
    return written


def build_quarterly(df: pd.DataFrame, report_dir: Path) -> list[str]:
    """季報：每季一個 parquet，period=YYYY-MM（月粒度）。"""
    df = df.copy()
    df["month"] = df["date"].str[:7]
    df["quarter"] = df["month"].map(_quarter_label)
    written = []
    for quarter, qdf in df.groupby("quarter"):
        out_dir = report_dir / f"quarterly={quarter}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = (
            qdf.groupby(["month", "feature_id", "event_type"], as_index=False)
            .agg(count=("count", "sum"), feature_name=("feature_name", "first"))
            .rename(columns={"month": "period"})
            [["period", "feature_id", "feature_name", "event_type", "count"]]
            .sort_values(["event_type", "period", "count"], ascending=[True, True, False])
        )
        result.to_parquet(out_dir / FEATURE_COUNTS_FILE, index=False)
        written.append(str(quarter))
    return written


def build_yearly(df: pd.DataFrame, report_dir: Path) -> list[str]:
    """年報：每年一個 parquet，period=YYYY-MM（月粒度）。"""
    df = df.copy()
    df["month"] = df["date"].str[:7]
    df["year"] = df["date"].str[:4]
    written = []
    for year, ydf in df.groupby("year"):
        out_dir = report_dir / f"yearly={year}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = (
            ydf.groupby(["month", "feature_id", "event_type"], as_index=False)
            .agg(count=("count", "sum"), feature_name=("feature_name", "first"))
            .rename(columns={"month": "period"})
            [["period", "feature_id", "feature_name", "event_type", "count"]]
            .sort_values(["event_type", "period", "count"], ascending=[True, True, False])
        )
        result.to_parquet(out_dir / FEATURE_COUNTS_FILE, index=False)
        written.append(str(year))
    return written


def build_period_summary() -> dict:
    report_dir = T2_REPORT_DIR / REPORT_NAME
    if not report_dir.exists():
        print(f"[ERROR] 找不到報表目錄：{report_dir}")
        sys.exit(1)

    print("[INFO] 讀取所有日報 parquet...")
    df = load_all_daily(report_dir)
    if df.empty:
        print("[WARN] 沒有任何日報資料，跳過。")
        return {"months": [], "quarters": [], "years": []}

    print(f"[INFO] 共 {len(df)} 筆，{df['date'].nunique()} 天，{df['feature_id'].nunique()} 個功能")

    months = build_monthly(df, report_dir)
    print(f"[OK] 月報：{len(months)} 個月 → {months}")

    quarters = build_quarterly(df, report_dir)
    print(f"[OK] 季報：{len(quarters)} 季 → {quarters}")

    years = build_yearly(df, report_dir)
    print(f"[OK] 年報：{len(years)} 年 → {years}")

    return {"months": months, "quarters": quarters, "years": years}


def main() -> None:
    build_period_summary()


if __name__ == "__main__":
    main()
