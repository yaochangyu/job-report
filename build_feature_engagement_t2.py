#!/usr/bin/env python3
"""
build_feature_engagement_t2.py
─────────────────────────────
從 T1 raw parquet 產出 feature-engagement 的 T2 report parquet。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common.data_pipeline import T2_REPORT_MANIFEST_PATH, ensure_pipeline_directories, t2_report_range_dir
from common.es_client import generated_now
from common.t1_reader import load_t1_raw_dataframe, resolve_date_window
from feature_engagement_report import EXPLORE_CORP_IDS, EXPLORE_JOB_IDS, IDENTITY_IDS, NEWS_IDS

REPORT_NAME = "feature-engagement"
EXPLORE_JOBS_FEATURES_FILE = "explore_jobs_features.parquet"
EXPLORE_JOBS_CATEGORY_TABS_FILE = "explore_jobs_category_tabs.parquet"
EXPLORE_JOBS_IDENTITY_TYPES_FILE = "explore_jobs_identity_types.parquet"
EXPLORE_JOBS_DAILY_FILE = "explore_jobs_daily.parquet"
EXPLORE_CORP_FEATURES_FILE = "explore_corp_features.parquet"
EXPLORE_CORP_INDUSTRY_TABS_FILE = "explore_corp_industry_tabs.parquet"
IDENTITY_MAIN_FILE = "identity_main.parquet"
IDENTITY_ALL_FILE = "identity_all.parquet"
NEWS_FEATURES_FILE = "news_features.parquet"
NEWS_CATEGORIES_FILE = "news_categories.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 feature-engagement 的 T2 parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="分析最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="結束日期 YYYY-MM-DD")
    return parser.parse_args()


def _update_t2_manifest(date_from: str, date_to: str, output_dir: Path, files: dict[str, str], rows: int) -> None:
    manifest = {}
    if T2_REPORT_MANIFEST_PATH.exists():
        manifest = json.loads(T2_REPORT_MANIFEST_PATH.read_text(encoding="utf-8"))

    reports = manifest.setdefault("reports", {})
    report_manifest = reports.setdefault(REPORT_NAME, {"snapshots": {}})
    snapshot_key = f"{date_from}_{date_to}"
    report_manifest["snapshots"][snapshot_key] = {
        "date_from": date_from,
        "date_to": date_to,
        "root": str(output_dir.relative_to(output_dir.parents[2])),
        "files": files,
        "rows": rows,
        "updated_at": generated_now(),
    }
    report_manifest["available_snapshots"] = sorted(report_manifest["snapshots"].keys())

    manifest["tier"] = "t2-report"
    manifest["schema_version"] = 1
    manifest["updated_at"] = generated_now()
    T2_REPORT_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _count_by_value(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        frame[column]
        .fillna("unknown")
        .value_counts(dropna=False)
        .rename_axis("name")
        .reset_index(name="count")
        .sort_values(["count", "name"], ascending=[False, True])
    )


def build_feature_engagement_t2(date_from: str, date_to: str) -> Path:
    ensure_pipeline_directories()
    columns = ["date", "system", "feature_id", "category_tab", "identity_type", "industry_tab"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web") & df["feature_id"].notna()].copy()

    output_dir = t2_report_range_dir(REPORT_NAME, date_from, date_to)
    output_dir.mkdir(parents=True, exist_ok=True)

    explore_jobs_df = df[df["feature_id"].isin(EXPLORE_JOB_IDS)].copy()
    _count_by_value(explore_jobs_df, "feature_id").to_parquet(output_dir / EXPLORE_JOBS_FEATURES_FILE, index=False)
    _count_by_value(explore_jobs_df, "category_tab").to_parquet(output_dir / EXPLORE_JOBS_CATEGORY_TABS_FILE, index=False)
    _count_by_value(explore_jobs_df, "identity_type").to_parquet(output_dir / EXPLORE_JOBS_IDENTITY_TYPES_FILE, index=False)
    explore_jobs_daily = (
        explore_jobs_df.assign(
            organic=explore_jobs_df["feature_id"].eq("explore-jobs-organic"),
            corp=explore_jobs_df["feature_id"].eq("explore-jobs-organic-corp"),
        )
        .groupby("date", as_index=False)
        .agg(organic=("organic", "sum"), corp=("corp", "sum"))
        .sort_values("date")
    )
    explore_jobs_daily.to_parquet(output_dir / EXPLORE_JOBS_DAILY_FILE, index=False)

    explore_corp_df = df[df["feature_id"].isin(EXPLORE_CORP_IDS)].copy()
    _count_by_value(explore_corp_df, "feature_id").to_parquet(output_dir / EXPLORE_CORP_FEATURES_FILE, index=False)
    _count_by_value(explore_corp_df, "industry_tab").to_parquet(output_dir / EXPLORE_CORP_INDUSTRY_TABS_FILE, index=False)

    identity_df = df[df["feature_id"].fillna("").str.startswith("identify-")].copy()
    identity_all = _count_by_value(identity_df, "feature_id")
    identity_all.to_parquet(output_dir / IDENTITY_ALL_FILE, index=False)
    identity_main = identity_all[identity_all["name"].isin(IDENTITY_IDS)].copy()
    identity_main["name"] = identity_main["name"].str.replace("identify-", "", regex=False)
    identity_main.to_parquet(output_dir / IDENTITY_MAIN_FILE, index=False)

    news_df = df[df["feature_id"].isin(NEWS_IDS)].copy()
    _count_by_value(news_df, "feature_id").to_parquet(output_dir / NEWS_FEATURES_FILE, index=False)
    _count_by_value(news_df, "category_tab").to_parquet(output_dir / NEWS_CATEGORIES_FILE, index=False)

    _update_t2_manifest(
        date_from,
        date_to,
        output_dir,
        files={
            "explore_jobs_features": str((output_dir / EXPLORE_JOBS_FEATURES_FILE).relative_to(output_dir.parents[2])),
            "explore_jobs_category_tabs": str((output_dir / EXPLORE_JOBS_CATEGORY_TABS_FILE).relative_to(output_dir.parents[2])),
            "explore_jobs_identity_types": str((output_dir / EXPLORE_JOBS_IDENTITY_TYPES_FILE).relative_to(output_dir.parents[2])),
            "explore_jobs_daily": str((output_dir / EXPLORE_JOBS_DAILY_FILE).relative_to(output_dir.parents[2])),
            "explore_corp_features": str((output_dir / EXPLORE_CORP_FEATURES_FILE).relative_to(output_dir.parents[2])),
            "explore_corp_industry_tabs": str((output_dir / EXPLORE_CORP_INDUSTRY_TABS_FILE).relative_to(output_dir.parents[2])),
            "identity_main": str((output_dir / IDENTITY_MAIN_FILE).relative_to(output_dir.parents[2])),
            "identity_all": str((output_dir / IDENTITY_ALL_FILE).relative_to(output_dir.parents[2])),
            "news_features": str((output_dir / NEWS_FEATURES_FILE).relative_to(output_dir.parents[2])),
            "news_categories": str((output_dir / NEWS_CATEGORIES_FILE).relative_to(output_dir.parents[2])),
        },
        rows=len(df),
    )
    return output_dir


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dir = build_feature_engagement_t2(date_from, date_to)
    print(f"[OK] 已產出 T2：{output_dir}")


if __name__ == "__main__":
    main()
