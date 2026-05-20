#!/usr/bin/env python3
"""
build_period_summary.py
━━━━━━━━━━━━━━━━━━━━━━━
對所有 10 個 T2 報表類別，預計算月報、季報、年報聚合 parquet。

目錄結構：
  dataset/report/{category}/
    date=YYYY-MM-DD/...          ← 現有日報（不動）
    monthly=YYYY-MM/
      period_summary.parquet    ← 趨勢（period=YYYY-MM-DD）
      [breakdown].parquet
    quarterly=YYYY-QN/
      period_summary.parquet    ← 趨勢（period=YYYY-MM）
      [breakdown].parquet
    yearly=YYYY/
      period_summary.parquet    ← 趨勢（period=YYYY-MM）
      [breakdown].parquet

執行方式：
    uv run python builders/build_period_summary.py
    uv run python builders/build_period_summary.py --days 30
    uv run python builders/build_period_summary.py --from 2026-05-01 --to 2026-05-17
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from common.data_pipeline import T2_REPORT_DIR


# ──────────────────────────────────────────────────────────────────────
# post-agg hooks（需在 CATEGORY_CONFIG 前定義）
# ──────────────────────────────────────────────────────────────────────

def _recalculate_ctr(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ctr"] = df.apply(
        lambda r: round(r["clicks"] / r["views"], 4) if r.get("views", 0) > 0 else 0.0,
        axis=1,
    )
    return df


# ──────────────────────────────────────────────────────────────────────
# 各類別設定
# summary_cols: daily_summary.parquet 中可加總的數值欄位（排除文字欄位）
# breakdowns:   {輸出檔名: config}
# ──────────────────────────────────────────────────────────────────────

CATEGORY_CONFIG: dict[str, dict] = {
    "traffic-overview": {
        "summary_cols": ["total", "views", "clicks", "applies", "sessions"],
        "breakdowns": {},
    },
    "search-behavior": {
        "summary_cols": [
            "general_click", "general_view",
            "ai_click", "ai_view",
            "quick_click", "quick_view",
            "search_page_click", "search_page_view",
        ],
        "breakdowns": {
            "feature_counts.parquet": {
                "group_cols": ["event_type", "feature_id"],
                "agg": {"count": ("count", "sum"), "feature_name": ("feature_name", "first")},
                "top_n": None,
                "top_by": "count",
            },
        },
    },
    "apply-conversion": {
        "summary_cols": ["applies", "job_views"],
        "breakdowns": {
            "source.parquet": {
                "group_cols": ["name"],
                "agg": {"count": ("count", "sum")},
                "top_n": None,
                "top_by": "count",
            },
            "funnel.parquet": {
                "group_cols": ["name"],
                "agg": {"count": ("count", "sum")},
                "top_n": None,
                "top_by": "count",
            },
        },
    },
    "apply-journey": {
        "summary_cols": ["applies", "apply_sessions", "total_steps"],
        "breakdowns": {
            "path_ranking.parquet": {
                "group_cols": ["path", "step_count"],
                "agg": {"count": ("count", "sum")},
                "top_n": 30,
                "top_by": "count",
            },
            "entry_page.parquet": {
                "group_cols": ["name"],
                "agg": {"count": ("count", "sum")},
                "top_n": None,
                "top_by": "count",
            },
        },
    },
    "feature-engagement": {
        "summary_cols": [
            "explore_jobs_click", "explore_jobs_view",
            "explore_corp_click", "explore_corp_view",
            "identity_click", "identity_view",
            "news_click", "news_view",
        ],
        "breakdowns": {},
    },
    "device-platform": {
        "summary_cols": ["mobile", "desktop"],
        "breakdowns": {},
    },
    "page-ranking": {
        "summary_cols": ["total_events", "total_features"],
        "breakdowns": {
            "features.parquet": {
                "group_cols": ["featureId"],
                "agg": {
                    "total": ("total", "sum"),
                    "views": ("views", "sum"),
                    "clicks": ("clicks", "sum"),
                    "feature_name": ("feature_name", "first"),
                    "category": ("category", "first"),
                },
                "top_n": 50,
                "top_by": "total",
                "post_agg": _recalculate_ctr,
            },
            "categories.parquet": {
                "group_cols": ["name"],
                "agg": {"count": ("count", "sum")},
                "top_n": None,
                "top_by": "count",
            },
        },
    },
    "page-navigation": {
        "summary_cols": ["nav_click", "nav_view", "entry_click", "entry_view"],
        "breakdowns": {
            "nav_pairs.parquet": {
                "group_cols": ["event_type", "from", "to"],
                "agg": {"count": ("count", "sum"), "label": ("label", "first")},
                "top_n": 30,
                "top_by": "count",
            },
            "entry_pages.parquet": {
                "group_cols": ["event_type", "name"],
                "agg": {"count": ("count", "sum")},
                "top_n": None,
                "top_by": "count",
            },
        },
    },
    "click-heatmap": {
        "summary_cols": ["total_clicks"],
        "breakdowns": {
            "click_counts.parquet": {
                "group_cols": ["page_path", "feature_id"],
                "agg": {"count": ("count", "sum"), "feature_name": ("feature_name", "first")},
                "top_n": 50,
                "top_by": "count",
            },
        },
    },
    "homepage-blocks": {
        "summary_cols": ["total_clicks", "total_views"],
        "breakdowns": {
            "feature_counts.parquet": {
                "group_cols": ["event_type", "feature_id"],
                "agg": {"count": ("count", "sum"), "feature_name": ("feature_name", "first")},
                "top_n": None,
                "top_by": "count",
            },
        },
    },
}


# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────

def _quarter_label(month: str) -> str:
    y, m = month.split("-")
    q = (int(m) - 1) // 3 + 1
    return f"{y}-Q{q}"


def _parse_date_range(args: argparse.Namespace) -> tuple[str, str] | None:
    if args.days:
        to_dt = date.today()
        from_dt = to_dt - timedelta(days=int(args.days) - 1)
        return str(from_dt), str(to_dt)
    if args.from_date or args.to_date:
        return args.from_date or "0000-01-01", args.to_date or "9999-12-31"
    return None


def _iter_date_dirs(report_dir: Path, date_range: tuple[str, str] | None):
    for part in sorted(report_dir.iterdir()):
        if not part.is_dir() or not part.name.startswith("date="):
            continue
        d = part.name[5:]
        if date_range and not (date_range[0] <= d <= date_range[1]):
            continue
        yield d, part


def _load_daily_summaries(report_dir: Path, date_range: tuple[str, str] | None) -> pd.DataFrame:
    frames = []
    for _d, part in _iter_date_dirs(report_dir, date_range):
        f = part / "daily_summary.parquet"
        if f.exists():
            frames.append(pd.read_parquet(f))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _load_breakdown_file(report_dir: Path, filename: str, date_range: tuple[str, str] | None) -> pd.DataFrame:
    frames = []
    for d, part in _iter_date_dirs(report_dir, date_range):
        f = part / filename
        if not f.exists():
            continue
        df = pd.read_parquet(f)
        if "date" not in df.columns:
            df["date"] = d
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────
# period_summary.parquet
# ──────────────────────────────────────────────────────────────────────

def _write_period_summary(
    df: pd.DataFrame,
    report_dir: Path,
    summary_cols: list[str],
) -> dict:
    num_cols = [c for c in summary_cols if c in df.columns]
    base = df[["date"] + num_cols].copy()
    base["month"] = base["date"].str[:7]
    base["quarter"] = base["month"].map(_quarter_label)
    base["year"] = base["date"].str[:4]

    result: dict[str, list[str]] = {"months": [], "quarters": [], "years": []}

    for month, mdf in base.groupby("month"):
        out_dir = report_dir / f"monthly={month}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (
            mdf[["date"] + num_cols]
            .rename(columns={"date": "period"})
            .to_parquet(out_dir / "period_summary.parquet", index=False)
        )
        result["months"].append(str(month))

    for quarter, qdf in base.groupby("quarter"):
        out_dir = report_dir / f"quarterly={quarter}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (
            qdf.groupby("month")[num_cols].sum()
            .reset_index()
            .rename(columns={"month": "period"})
            .to_parquet(out_dir / "period_summary.parquet", index=False)
        )
        result["quarters"].append(str(quarter))

    for year, ydf in base.groupby("year"):
        out_dir = report_dir / f"yearly={year}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (
            ydf.groupby("month")[num_cols].sum()
            .reset_index()
            .rename(columns={"month": "period"})
            .to_parquet(out_dir / "period_summary.parquet", index=False)
        )
        result["years"].append(str(year))

    return result


# ──────────────────────────────────────────────────────────────────────
# breakdown parquets
# ──────────────────────────────────────────────────────────────────────

def _apply_top_n(
    result: pd.DataFrame,
    group_cols: list[str],
    top_by: str,
    top_n: int,
    ref_df: pd.DataFrame,
) -> pd.DataFrame:
    """依 ref_df 全期加總排名，取 Top N key，filter result。"""
    totals = ref_df.groupby(group_cols)[top_by].sum().reset_index()
    top_keys = totals.nlargest(top_n, top_by)[group_cols]
    return result.merge(top_keys, on=group_cols)


def _write_breakdown(
    df: pd.DataFrame,
    report_dir: Path,
    filename: str,
    group_cols: list[str],
    agg: dict,
    top_n: int | None,
    top_by: str,
    post_agg=None,
) -> None:
    if df.empty:
        return

    df = df.copy()
    df["month"] = df["date"].str[:7]
    df["quarter"] = df["month"].map(_quarter_label)
    df["year"] = df["date"].str[:4]

    # 月報：日粒度（period=YYYY-MM-DD）
    for month, mdf in df.groupby("month"):
        out_dir = report_dir / f"monthly={month}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = mdf.groupby(["date"] + group_cols, as_index=False).agg(**agg)
        result = result.rename(columns={"date": "period"})
        if top_n:
            result = _apply_top_n(result, group_cols, top_by, top_n, ref_df=mdf)
        if post_agg:
            result = post_agg(result)
        result.to_parquet(out_dir / filename, index=False)

    # 季報：月粒度（period=YYYY-MM）
    for quarter, qdf in df.groupby("quarter"):
        out_dir = report_dir / f"quarterly={quarter}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = qdf.groupby(["month"] + group_cols, as_index=False).agg(**agg)
        result = result.rename(columns={"month": "period"})
        if top_n:
            result = _apply_top_n(result, group_cols, top_by, top_n, ref_df=qdf)
        if post_agg:
            result = post_agg(result)
        result.to_parquet(out_dir / filename, index=False)

    # 年報：月粒度（period=YYYY-MM）
    for year, ydf in df.groupby("year"):
        out_dir = report_dir / f"yearly={year}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = ydf.groupby(["month"] + group_cols, as_index=False).agg(**agg)
        result = result.rename(columns={"month": "period"})
        if top_n:
            result = _apply_top_n(result, group_cols, top_by, top_n, ref_df=ydf)
        if post_agg:
            result = post_agg(result)
        result.to_parquet(out_dir / filename, index=False)


# ──────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────

def build_all(date_range: tuple[str, str] | None = None) -> dict:
    all_months: set[str] = set()
    all_quarters: set[str] = set()
    all_years: set[str] = set()

    for category, config in CATEGORY_CONFIG.items():
        report_dir = T2_REPORT_DIR / category
        if not report_dir.exists():
            print(f"[WARN] 找不到目錄，跳過：{category}")
            continue

        print(f"\n[INFO] 處理 {category}...")

        df = _load_daily_summaries(report_dir, None)  # 必須讀全部日期才能產生正確的週期聚合
        if df.empty:
            print("  [WARN] 無日報資料，跳過。")
            continue

        res = _write_period_summary(df, report_dir, config["summary_cols"])
        all_months.update(res["months"])
        all_quarters.update(res["quarters"])
        all_years.update(res["years"])
        print(f"  period_summary: {len(res['months'])} 月, {len(res['quarters'])} 季, {len(res['years'])} 年")

        for filename, bd in config["breakdowns"].items():
            bdf = _load_breakdown_file(report_dir, filename, None)
            if bdf.empty:
                print(f"  [WARN] {filename} 無資料，跳過。")
                continue
            _write_breakdown(
                bdf, report_dir, filename,
                group_cols=bd["group_cols"],
                agg=bd["agg"],
                top_n=bd.get("top_n"),
                top_by=bd.get("top_by", "count"),
                post_agg=bd.get("post_agg"),
            )
            print(f"  {filename}: OK")

    return {
        "months": sorted(all_months),
        "quarters": sorted(all_quarters),
        "years": sorted(all_years),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="建立所有類別的週期聚合 parquet")
    parser.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD")
    parser.add_argument("--days", type=int, metavar="N")
    args = parser.parse_args()

    date_range = _parse_date_range(args)
    if date_range:
        print(f"[INFO] 日期範圍：{date_range[0]} ~ {date_range[1]}")
    else:
        print("[INFO] 處理所有日期")

    result = build_all(date_range)
    print(f"\n[完成] 月：{result['months']}")
    print(f"[完成] 季：{result['quarters']}")
    print(f"[完成] 年：{result['years']}")


if __name__ == "__main__":
    main()
