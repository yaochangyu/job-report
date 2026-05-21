#!/usr/bin/env python3
"""
build_apply_demographics_t2.py
───────────────────────────────
從 T1 apply 事件 user_id JOIN core6 Solr 取得應徵者性別／年齡，
產出 apply-demographics 的 T2 day-keyed parquet。

性別映射：sex_i = 1 → 男, 2 → 女, 其他/None → 未知
年齡計算：以事件日期為基準（避免補跑歷史資料時年齡漂移）
年齡層：<25, 25-29, 30-34, 35-39, 40-44, 45-49, 50+
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
from common.resume_metadata import fetch_resume_metadata
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window

REPORT_NAME = "apply-demographics"

DAILY_SUMMARY_FILE       = "daily_summary.parquet"
GENDER_FILE              = "gender.parquet"
AGE_GROUPS_FILE          = "age_groups.parquet"
GENDER_DAILY_FILE        = "gender_daily.parquet"
AGE_GROUPS_DAILY_FILE    = "age_groups_daily.parquet"

SEX_MAP = {1: "男", 2: "女"}
AGE_GROUP_BINS   = [0, 25, 30, 35, 40, 45, 50, 200]
AGE_GROUP_LABELS = ["<25", "25-29", "30-34", "35-39", "40-44", "45-49", "50+"]


def _age_from_birth_dt(birth_dt: str | None, event_date: str) -> int | None:
    """從 birth_dt（ISO 8601 或 YYYY-MM-DD）計算整數年齡；無法解析時回傳 None。"""
    if not birth_dt:
        return None
    try:
        bd_str = str(birth_dt)[:10]
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


def build_apply_demographics_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()

    columns = ["date", "system", "action", "user_id"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["action"].eq("apply")].copy()

    if df.empty:
        print("[WARN] 無 apply 事件資料")
        return []

    all_user_ids = df["user_id"].dropna().unique().tolist()
    print(f"  查詢 {len(all_user_ids):,} 個唯一 user_id ...")
    meta = fetch_resume_metadata(all_user_ids)
    hit_count = len(meta)
    total_ids = len(all_user_ids)
    coverage = f"{hit_count/total_ids:.1%}" if total_ids else "—"
    print(f"  命中 {hit_count:,} 個（{coverage} 覆蓋率）")

    df["sex_i"]    = df["user_id"].map(lambda u: meta.get(str(u), {}).get("sex_i"))
    df["birth_dt"] = df["user_id"].map(lambda u: meta.get(str(u), {}).get("birth_dt"))
    df["gender"]   = df["sex_i"].map(lambda s: SEX_MAP.get(s, "未知"))

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        day_df = day_df.copy()
        day_df["age"] = day_df["birth_dt"].map(lambda b: _age_from_birth_dt(b, target_date))
        day_df["age_group"] = day_df["age"].map(_age_group)

        total = len(day_df)
        with_meta = int(day_df["user_id"].map(lambda u: str(u) in meta).sum())

        # daily_summary
        pd.DataFrame([{
            "date": target_date,
            "total_applies": total,
            "applies_with_metadata": with_meta,
            "coverage_rate": round(with_meta / total, 4) if total else 0.0,
        }]).to_parquet(output_dir / DAILY_SUMMARY_FILE, index=False)

        # gender 全區間聚合（當日）
        (
            day_df.groupby("gender", observed=True)
            .size()
            .reset_index(name="count")
            .rename(columns={"gender": "gender"})
        ).to_parquet(output_dir / GENDER_FILE, index=False)

        # age_groups 全區間聚合（當日）
        (
            day_df.groupby("age_group", observed=True)
            .size()
            .reset_index(name="count")
        ).to_parquet(output_dir / AGE_GROUPS_FILE, index=False)

        # gender_daily（當日）
        pd.DataFrame([{
            "date": target_date,
            "gender": row["gender"],
            "count": row["count"],
        } for _, row in (
            day_df.groupby("gender", observed=True).size().reset_index(name="count")
        ).iterrows()]).to_parquet(output_dir / GENDER_DAILY_FILE, index=False)

        # age_groups_daily（當日）
        pd.DataFrame([{
            "date": target_date,
            "age_group": row["age_group"],
            "count": row["count"],
        } for _, row in (
            day_df.groupby("age_group", observed=True).size().reset_index(name="count")
        ).iterrows()]).to_parquet(output_dir / AGE_GROUPS_DAILY_FILE, index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary":    rel(DAILY_SUMMARY_FILE),
                "gender":           rel(GENDER_FILE),
                "age_groups":       rel(AGE_GROUPS_FILE),
                "gender_daily":     rel(GENDER_DAILY_FILE),
                "age_groups_daily": rel(AGE_GROUPS_DAILY_FILE),
            },
            "rows": total,
        }
        output_dirs.append(output_dir)
        print(f"  [{target_date}] {total:,} applies → {output_dir}")

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="建立 apply-demographics T2 parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    args = parser.parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_apply_demographics_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
