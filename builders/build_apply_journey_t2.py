#!/usr/bin/env python3
"""
build_apply_journey_t2.py
─────────────────────────
從 T1 raw 重建每個 session 的應徵路徑，產出 apply-journey 的 T2 day-keyed parquet。
"""

from __future__ import annotations

import argparse
import re
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

REPORT_NAME = "apply-journey"


def _normalize_page(page_path: str | None) -> str:
    if not page_path or pd.isna(page_path):
        return "unknown"
    path = str(page_path).rstrip("/")
    if path in ("", "/"):
        return "home-page"
    if re.match(r"^/search/job", path):
        return "search-job-page"
    if re.match(r"^/search/corp", path):
        return "search-corp-page"
    if re.match(r"^/search/gig", path):
        return "search-gig-page"
    if re.match(r"^/search/intern", path):
        return "search-intern-page"
    if re.match(r"^/job/\d", path):
        return "job-page"
    if re.match(r"^/job-pair", path):
        return "job-pair-page"
    if re.match(r"^/corp/\d", path):
        return "corp-page"
    parts = [p for p in path.lstrip("/").split("/") if p]
    return (parts[0] + "-page") if parts else "unknown"


def _dedup_consecutive(seq: list[str]) -> list[str]:
    result: list[str] = []
    for item in seq:
        if not result or result[-1] != item:
            result.append(item)
    return result


def _build_journeys(session_df: pd.DataFrame) -> list[tuple[str, int]]:
    """每個 session 的所有 apply 路徑，回傳 [(path_str, step_count), ...]。"""
    sorted_events = session_df.sort_values("occurred_at")
    names: list[str] = []
    for _, row in sorted_events.iterrows():
        names.append("apply" if row["action"] == "apply" else _normalize_page(row.get("page_path")))
    deduped = _dedup_consecutive(names)
    paths: list[tuple[str, int]] = []
    for i, name in enumerate(deduped):
        if name == "apply":
            seq = deduped[: i + 1]
            paths.append((" > ".join(seq), len(seq)))
    return paths


def build_apply_journey_t2(date_from: str, date_to: str) -> list[Path]:
    ensure_pipeline_directories()
    columns = ["date", "system", "session_id", "occurred_at", "page_path", "action"]
    df = load_t1_raw_dataframe(date_from, date_to, columns=columns)
    df = df[df["system"].eq("jobbank-web")].copy()

    dates_written: dict[str, dict] = {}
    output_dirs: list[Path] = []

    for target_date, day_df in df.groupby("date"):
        target_date = str(target_date)
        output_dir = t2_report_date_dir(REPORT_NAME, target_date)
        output_dir.mkdir(parents=True, exist_ok=True)

        apply_session_ids = set(day_df[day_df["action"] == "apply"]["session_id"].unique())
        apply_df = day_df[day_df["session_id"].isin(apply_session_ids)].copy()

        # 逐 session 還原應徵路徑
        all_journeys: list[tuple[str, int]] = []
        for _sid, sess_df in apply_df.groupby("session_id"):
            all_journeys.extend(_build_journeys(sess_df))

        applies = len(all_journeys)
        apply_sessions = len(apply_session_ids)
        total_steps = sum(s for _, s in all_journeys)

        # daily_summary
        pd.DataFrame([{
            "date": target_date,
            "applies": applies,
            "apply_sessions": apply_sessions,
            "total_steps": total_steps,
        }]).to_parquet(output_dir / "daily_summary.parquet", index=False)

        # path_ranking
        if all_journeys:
            path_df = pd.DataFrame(all_journeys, columns=["path", "step_count"])
            path_ranking = (
                path_df.groupby(["path", "step_count"], as_index=False)
                .size()
                .rename(columns={"size": "count"})
                .sort_values("count", ascending=False)
                .reset_index(drop=True)
            )
        else:
            path_ranking = pd.DataFrame(columns=["path", "step_count", "count"])
        path_ranking.to_parquet(output_dir / "path_ranking.parquet", index=False)

        # step_distribution
        if all_journeys:
            step_df = pd.DataFrame({"steps": [s for _, s in all_journeys]})
            step_dist = (
                step_df["steps"]
                .value_counts()
                .rename_axis("steps")
                .reset_index(name="count")
                .sort_values("steps")
            )
        else:
            step_dist = pd.DataFrame(columns=["steps", "count"])
        step_dist.to_parquet(output_dir / "step_distribution.parquet", index=False)

        # entry_page (first element in path)
        if all_journeys:
            entry_pages = [path.split(" > ")[0] for path, _ in all_journeys]
            entry_df = pd.DataFrame({"name": entry_pages})
            entry_ranking = (
                entry_df["name"]
                .value_counts()
                .rename_axis("name")
                .reset_index(name="count")
                .sort_values("count", ascending=False)
                .reset_index(drop=True)
            )
        else:
            entry_ranking = pd.DataFrame(columns=["name", "count"])
        entry_ranking.to_parquet(output_dir / "entry_page.parquet", index=False)

        rel = lambda f: str((output_dir / f).relative_to(output_dir.parents[2]))
        dates_written[target_date] = {
            "root": str(output_dir.relative_to(output_dir.parents[2])),
            "files": {
                "daily_summary":    rel("daily_summary.parquet"),
                "path_ranking":     rel("path_ranking.parquet"),
                "step_distribution": rel("step_distribution.parquet"),
                "entry_page":       rel("entry_page.parquet"),
            },
            "rows": len(apply_df),
        }
        output_dirs.append(output_dir)

    update_t2_manifest_dates(REPORT_NAME, dates_written)
    return output_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 apply-journey 的 T2 day-keyed parquet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None)
    group.add_argument("--from", dest="date_from", default=None)
    parser.add_argument("--to", dest="date_to", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    date_from, date_to = resolve_date_window(args.days, args.date_from, args.date_to)
    output_dirs = build_apply_journey_t2(date_from, date_to)
    print(f"[OK] 已產出 {len(output_dirs)} 個 T2 day-keyed 目錄")


if __name__ == "__main__":
    main()
