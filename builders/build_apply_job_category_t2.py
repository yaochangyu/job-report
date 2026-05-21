#!/usr/bin/env python3
"""
build_apply_job_category_t2.py
──────────────────────────────
從 T1 apply 事件讀取 job_positions/company_industries（已在 T1 enrichment 階段補強），
產出 apply-job-category 的 T2 day-keyed parquet。
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from common.data_pipeline import (
    ensure_pipeline_directories,
    t2_report_date_dir,
    update_t2_manifest_dates,
)
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "apply-job-category"
DAILY_SUMMARY_FILE    = "daily_summary.parquet"
JOB_POSITION_TOP_FILE = "job_position_top.parquet"
COMPANY_INDUSTRY_TOP_FILE = "company_industry_top.parquet"
JOB_POSITION_DAILY_FILE   = "job_position_daily.parquet"
COMPANY_INDUSTRY_DAILY_FILE = "company_industry_daily.parquet"

TOP_N = 30
TREND_TOP_N = 10


def _explode_and_count(df: pd.DataFrame, col: str, top_n: int) -> pd.DataFrame:
    """explode list 欄位後聚合計數，回傳 TOP N。"""
    s = df[col].explode().dropna()
    s = s[s.str.strip() != ""]
    return (
        s.value_counts()
        .head(top_n)
        .rename_axis("name")
        .reset_index(name="count")
    )


def _explode_daily(df: pd.DataFrame, col: str, top_names: list[str]) -> pd.DataFrame:
    """每日 × 指定 TOP 名稱的交叉計數。"""
    exploded = df[["date", col]].explode(col).dropna(subset=[col])
    exploded = exploded[exploded[col].isin(top_names)]
    pivoted = (
        exploded.groupby(["date", col])
        .size()
        .reset_index(name="count")
        .rename(columns={col: "name"})
    )
    return pivoted


def build_apply_job_category_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()

    columns = ["date", "system", "action", "job_id", "job_positions", "company_industries"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["action"].eq("apply")].copy()

    if df.empty:
        print("[WARN] 無 apply 事件資料")
        return []

    def _to_list(v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        try:
            return list(v)
        except TypeError:
            return []

    df["job_positions"]      = df["job_positions"].map(_to_list)
    df["company_industries"] = df["company_industries"].map(_to_list)

    hit_count = int(df["job_id"].map(lambda j: bool(j)).sum())
    print(f"  job_positions 覆蓋 {hit_count:,} 筆 apply 事件")

    # 計算全區間 TOP N（供日趨勢使用）
    all_top_positions = _explode_and_count(df, "job_positions", TREND_TOP_N)["name"].tolist()
    all_top_industries = _explode_and_count(df, "company_industries", TREND_TOP_N)["name"].tolist()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        total = len(day_df)
        with_meta = int(day_df["job_positions"].map(lambda v: bool(v)).sum())

        pd.DataFrame([{
            "date": target_date,
            "total_applies": total,
            "applies_with_metadata": with_meta,
            "coverage_rate": round(with_meta / total, 4) if total else 0.0,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        _explode_and_count(day_df, "job_positions", TOP_N).to_parquet(
            output_dir / JOB_POSITION_TOP_FILE, index=False
        )
        _explode_and_count(day_df, "company_industries", TOP_N).to_parquet(
            output_dir / COMPANY_INDUSTRY_TOP_FILE, index=False
        )
        _explode_daily(day_df, "job_positions", all_top_positions).to_parquet(
            output_dir / JOB_POSITION_DAILY_FILE, index=False
        )
        _explode_daily(day_df, "company_industries", all_top_industries).to_parquet(
            output_dir / COMPANY_INDUSTRY_DAILY_FILE, index=False
        )

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary": rel(DAILY_SUMMARY_FILE),
                "job_position_top": rel(JOB_POSITION_TOP_FILE),
                "company_industry_top": rel(COMPANY_INDUSTRY_TOP_FILE),
                "job_position_daily": rel(JOB_POSITION_DAILY_FILE),
                "company_industry_daily": rel(COMPANY_INDUSTRY_DAILY_FILE),
            },
            "rows": total,
        }
        output_dirs.append(output_dir)
        print(f"  [{target_date}] {total:,} applies → {output_dir}")

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="建立 apply-job-category T2 parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    args = parser.parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_apply_job_category_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
