#!/usr/bin/env python3
"""
enrich_t1_events.py
────────────────────
讀取 T0 純原始事件，批次查 Solr（sex_i/birth_dt）與 Matching ES（職類/產業），
寫入 T1 enriched parquet（dataset/t1-enrich/）。

只對 action=apply 事件補強；其他事件的 sex_i/birth_dt/job_positions/company_industries 為 null。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from common.data_pipeline import (
    T1_ENRICH_MANIFEST_PATH,
    ensure_pipeline_directories,
    t0_raw_date_dir,
    t1_enrich_date_dir,
)
from common.es_client import generated_now
from common.job_metadata import fetch_job_metadata
from common.raw_events import (
    T1_ENRICH_EVENT_FIELDS,
    T1_ENRICH_EVENT_SCHEMA,
    T1_ENRICH_SCHEMA_VERSION,
)
from common.raw_events import normalize_url_path
from common.resume_metadata import fetch_resume_metadata
from common.t1_reader import iter_dates, resolve_date_window

PARQUET_FILE_NAME = "events.parquet"
PARQUET_COMPRESSION = "zstd"
PARQUET_ROW_GROUP_SIZE = 100000


def _enrich_one_date(target_date: str) -> dict[str, Any] | None:
    t0_path = t0_raw_date_dir(target_date) / PARQUET_FILE_NAME
    if not t0_path.exists():
        print(f"[WARN] T0 parquet 不存在：{t0_path}")
        return None

    print(f"[T1] 補強 {target_date} ...")
    df = pd.read_parquet(t0_path)

    apply_mask = df["action"] == "apply"
    apply_df = df[apply_mask]

    # Solr: sex_i, birth_dt
    resume_meta: dict[str, dict] = {}
    all_user_ids = apply_df["user_id"].dropna().unique().tolist()
    if all_user_ids:
        print(f"  查詢 {len(all_user_ids):,} 個 user_id (Solr)...")
        resume_meta = fetch_resume_metadata(all_user_ids)
        print(f"  命中 {len(resume_meta):,} 個")

    # Matching ES: job_positions, company_industries
    job_meta: dict[str, dict] = {}
    all_job_ids = apply_df["job_id"].dropna().unique().tolist()
    if all_job_ids:
        print(f"  查詢 {len(all_job_ids):,} 個 job_id (Matching ES)...")
        job_meta = fetch_job_metadata(all_job_ids)
        print(f"  命中 {len(job_meta):,} 個")

    df = df.copy()

    # URL 正規化（所有事件）
    df["page_path"] = df["page_url"].map(normalize_url_path)
    df["previous_page_path"] = df["previous_page_url"].map(normalize_url_path)

    # 補強欄位（全部先設 None，再對 apply 事件填值）
    df["sex_i"] = None
    df["birth_dt"] = None
    df["job_positions"] = None
    df["company_industries"] = None

    if resume_meta:
        df.loc[apply_mask, "sex_i"] = df.loc[apply_mask, "user_id"].map(
            lambda u: resume_meta.get(str(u), {}).get("sex_i") if pd.notna(u) else None
        )
        df.loc[apply_mask, "birth_dt"] = df.loc[apply_mask, "user_id"].map(
            lambda u: resume_meta.get(str(u), {}).get("birth_dt") if pd.notna(u) else None
        )

    if job_meta:
        df.loc[apply_mask, "job_positions"] = df.loc[apply_mask, "job_id"].map(
            lambda j: job_meta.get(str(j), {}).get("job_positions") if pd.notna(j) else None
        )
        df.loc[apply_mask, "company_industries"] = df.loc[apply_mask, "job_id"].map(
            lambda j: job_meta.get(str(j), {}).get("company_industries") if pd.notna(j) else None
        )

    # 寫入 T1 parquet
    output_path = t1_enrich_date_dir(target_date) / PARQUET_FILE_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _safe_tolist(series: pd.Series) -> list:
        vals = series.tolist()
        return [None if isinstance(v, float) and pd.isna(v) else v for v in vals]

    data = {
        field: _safe_tolist(df[field]) if field in df.columns else [None] * len(df)
        for field in T1_ENRICH_EVENT_FIELDS
    }
    table = pa.Table.from_pydict(data, schema=T1_ENRICH_EVENT_SCHEMA)
    pq.write_table(
        table,
        output_path,
        compression=PARQUET_COMPRESSION,
        row_group_size=PARQUET_ROW_GROUP_SIZE,
    )

    row_count = len(df)
    print(f"  → {row_count:,} 筆：{output_path}")
    return {
        "path": str(output_path.relative_to(output_path.parents[2])),
        "rows": row_count,
        "status": "generated",
    }


def enrich_t1_events(date_from: str, date_to: str, keep_existing: bool = False) -> dict[str, dict[str, Any]]:
    """補強指定日期區間的 T1 enriched parquet。"""
    ensure_pipeline_directories()
    results: dict[str, dict[str, Any]] = {}

    for target_date in iter_dates(date_from, date_to):
        output_path = t1_enrich_date_dir(target_date) / PARQUET_FILE_NAME
        if keep_existing and output_path.exists():
            print(f"[SKIP] {target_date} 已存在：{output_path}")
            results[target_date] = {
                "path": str(output_path.relative_to(output_path.parents[2])),
                "rows": None,
                "status": "skipped",
            }
            continue

        info = _enrich_one_date(target_date)
        if info:
            results[target_date] = info

    _write_manifest(results)
    return results


def _write_manifest(results: dict[str, dict[str, Any]]) -> None:
    existing: dict[str, Any] = {}
    if T1_ENRICH_MANIFEST_PATH.exists():
        try:
            existing = json.loads(T1_ENRICH_MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    merged_dates: dict[str, Any] = dict(existing.get("dates", {}))
    merged_dates.update(results)

    manifest = {
        "schema_version": T1_ENRICH_SCHEMA_VERSION,
        "tier": "t1-enrich",
        "description": "T0 + Solr（sex_i/birth_dt）+ Matching ES（職類/產業）補強後的事件 parquet。",
        "partition_rule": "date=YYYY-MM-DD",
        "compression": PARQUET_COMPRESSION,
        "row_group_size": PARQUET_ROW_GROUP_SIZE,
        "available_dates": sorted(merged_dates.keys()),
        "dates": merged_dates,
        "updated_at": generated_now(),
    }
    T1_ENRICH_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="補強 T1 enriched 事件 parquet")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--days", type=int, help="補強最近 N 天（含今天）")
    group.add_argument("--from", dest="date_from", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", help="結束日期 YYYY-MM-DD")
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="若指定日期 T1 parquet 已存在則跳過。",
    )
    args = parser.parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    results = enrich_t1_events(date_from, date_to, keep_existing=args.keep_existing)
    print(f"[OK] T1 manifest 已更新：{T1_ENRICH_MANIFEST_PATH}")
    print(f"[OK] 完成日期：{', '.join(sorted(results))}")


if __name__ == "__main__":
    main()
