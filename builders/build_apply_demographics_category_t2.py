#!/usr/bin/env python3
"""
build_apply_demographics_category_t2.py
────────────────────────────────────────
從 T1 apply 事件同時讀取 demographics（sex_i/birth_dt）與
job metadata（job_positions/company_industries），
產出性別／年齡層 × 職類／產業的交叉聚合 T2 parquet。

性別映射：sex_i = 1 → 男, 2 → 女, 其他/None → 未知
年齡計算：以事件日期為基準
年齡層：<25, 25-29, 30-34, 35-39, 40-44, 45-49, 50+
TOP N：30
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from common.data_pipeline import (
    ensure_pipeline_directories,
    t2_report_date_dir,
    update_t2_manifest_dates,
)
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "apply-demographics-category"

DAILY_SUMMARY_FILE              = "daily_summary.parquet"
GENDER_JOB_POSITION_FILE        = "gender_job_position.parquet"
GENDER_COMPANY_INDUSTRY_FILE    = "gender_company_industry.parquet"
AGE_GROUP_JOB_POSITION_FILE     = "age_group_job_position.parquet"
AGE_GROUP_COMPANY_INDUSTRY_FILE = "age_group_company_industry.parquet"

TOP_N = 30

SEX_MAP = {1: "男", 2: "女"}
AGE_GROUP_BINS   = [0, 25, 30, 35, 40, 45, 50, 200]
AGE_GROUP_LABELS = ["<25", "25-29", "30-34", "35-39", "40-44", "45-49", "50+"]


def _age_from_birth_dt(birth_dt: str | None, event_date: str) -> int | None:
    if not birth_dt:
        return None
    try:
        bd_str = str(birth_dt)[:10].replace("/", "-")
        bd = date.fromisoformat(bd_str)
        ed = date.fromisoformat(event_date)
        age = ed.year - bd.year - ((ed.month, ed.day) < (bd.month, bd.day))
        return age if 0 < age < 120 else None
    except Exception:
        return None


def _age_group(age: int | None) -> str:
    if age is None:
        return "未知"
    for i in range(len(AGE_GROUP_BINS) - 1):
        if AGE_GROUP_BINS[i] <= age < AGE_GROUP_BINS[i + 1]:
            return AGE_GROUP_LABELS[i]
    return "未知"


def _cross_explode(df: pd.DataFrame, dim_col: str, cat_col: str, top_n: int) -> pd.DataFrame:
    """dim_col（gender/age_group）× cat_col（job_positions/company_industries）交叉計數，取 TOP N 個 cat。"""
    # 先展開 list 欄
    exploded = df[[dim_col, cat_col]].explode(cat_col).dropna(subset=[cat_col])
    exploded = exploded[exploded[cat_col].str.strip() != ""]

    # 找出整體 TOP N 類別
    top_cats = (
        exploded[cat_col].value_counts().head(top_n).index.tolist()
    )
    exploded = exploded[exploded[cat_col].isin(top_cats)]

    result = (
        exploded.groupby([dim_col, cat_col])
        .size()
        .reset_index(name="count")
        .rename(columns={cat_col: "category"})
    )
    return result


def build_apply_demographics_category_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()

    columns = [
        "date", "system", "action",
        "user_id", "sex_i", "birth_dt",
        "job_id", "job_positions", "company_industries",
    ]
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
            return list(v)  # numpy/pyarrow array → Python list
        except TypeError:
            return []

    df["job_positions"]       = df["job_positions"].map(_to_list)
    df["company_industries"]  = df["company_industries"].map(_to_list)

    total_rows = len(df)
    demo_hits = int(df["sex_i"].notna().sum())
    job_hits  = int(df["job_positions"].map(bool).sum())
    print(f"  demographics 覆蓋率：{demo_hits:,}/{total_rows:,}")
    print(f"  job_positions 覆蓋率：{job_hits:,}/{total_rows:,}")

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        day_df = day_df.copy()
        day_df["age"] = day_df["birth_dt"].map(
            lambda b: _age_from_birth_dt(b, target_date)
        )
        day_df["gender"]    = day_df["sex_i"].map(lambda s: SEX_MAP.get(s, "未知"))
        day_df["age_group"] = day_df["age"].map(_age_group)

        total        = len(day_df)
        coverage_demo = int(day_df["sex_i"].notna().sum())
        coverage_job  = int(day_df["job_positions"].map(bool).sum())

        # daily_summary
        pd.DataFrame([{
            "date":          target_date,
            "total_applies": total,
            "coverage_demo": coverage_demo,
            "coverage_job":  coverage_job,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        # 四張交叉表
        _cross_explode(day_df, "gender",    "job_positions",        TOP_N).to_parquet(
            output_dir / GENDER_JOB_POSITION_FILE, index=False
        )
        _cross_explode(day_df, "gender",    "company_industries",   TOP_N).to_parquet(
            output_dir / GENDER_COMPANY_INDUSTRY_FILE, index=False
        )
        _cross_explode(day_df, "age_group", "job_positions",        TOP_N).to_parquet(
            output_dir / AGE_GROUP_JOB_POSITION_FILE, index=False
        )
        _cross_explode(day_df, "age_group", "company_industries",   TOP_N).to_parquet(
            output_dir / AGE_GROUP_COMPANY_INDUSTRY_FILE, index=False
        )

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary":              rel(DAILY_SUMMARY_FILE),
                "gender_job_position":        rel(GENDER_JOB_POSITION_FILE),
                "gender_company_industry":    rel(GENDER_COMPANY_INDUSTRY_FILE),
                "age_group_job_position":     rel(AGE_GROUP_JOB_POSITION_FILE),
                "age_group_company_industry": rel(AGE_GROUP_COMPANY_INDUSTRY_FILE),
            },
            "rows": total,
        }
        output_dirs.append(output_dir)
        print(f"  [{target_date}] {total:,} applies → {output_dir}")

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="建立 apply-demographics-category T2 parquet"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    args = parser.parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_apply_demographics_category_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
