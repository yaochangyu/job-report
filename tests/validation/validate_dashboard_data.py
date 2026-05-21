#!/usr/bin/env python3
"""
validate_dashboard_data.py
──────────────────────────
比對瀏覽器內 executeViewQueries() 的實際查詢結果，是否與 output/dataset/report
中的 T2 parquet 聚合結果一致。
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pandas as pd
from playwright.sync_api import sync_playwright

REPORT_ROOT = Path("output/dataset/report")
STATIC_ROOT = Path("output")
VALIDATION_VIEWS = ("feature", "device", "ranking", "heatmap", "navigation")
NAVIGATION_PAGE_LIMIT = 300
NAVIGATION_TRANSITION_LIMIT = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="驗證 dashboard JS 查詢結果是否與 T2 parquet 一致")
    parser.add_argument("--from", dest="date_from", required=True, help="起始日期，例如 2026-04-08")
    parser.add_argument("--to", dest="date_to", required=True, help="結束日期，例如 2026-04-13")
    parser.add_argument(
        "--views",
        nargs="+",
        choices=VALIDATION_VIEWS,
        default=list(VALIDATION_VIEWS),
        help="指定要驗證的 view",
    )
    return parser.parse_args()


def enumerate_dates(date_from: str, date_to: str) -> list[str]:
    return [str(d.date()) for d in pd.date_range(date_from, date_to, freq="D")]


def load_days(report_name: str, dates: list[str], filename: str) -> pd.DataFrame:
    frames = [
        pd.read_parquet(REPORT_ROOT / report_name / f"date={target_date}" / filename)
        for target_date in dates
    ]
    return pd.concat(frames, ignore_index=True)


def expected_feature(dates: list[str]) -> dict[str, Any]:
    frame = load_days("feature-engagement", dates, "daily_summary.parquet")
    return {
        "kpi": {
            "explore_jobs_click": int(frame["explore_jobs_click"].sum()),
            "explore_jobs_view":  int(frame["explore_jobs_view"].sum()),
            "explore_corp_click": int(frame["explore_corp_click"].sum()),
            "explore_corp_view":  int(frame["explore_corp_view"].sum()),
            "identity_click":     int(frame["identity_click"].sum()),
            "identity_view":      int(frame["identity_view"].sum()),
            "news_click":         int(frame["news_click"].sum()),
            "news_view":          int(frame["news_view"].sum()),
        }
    }


def expected_device(dates: list[str]) -> dict[str, Any]:
    summary = load_days("device-platform", dates, "daily_summary.parquet")
    os_frame = load_days("device-platform", dates, "os.parquet")
    browser_frame = load_days("device-platform", dates, "browser.parquet")
    return {
        "kpi": {
            "mobile_total": int(summary["mobile"].sum()),
            "desktop_total": int(summary["desktop"].sum()),
            "os_count": int(os_frame["name"].nunique()),
            "browser_count": int(browser_frame["name"].nunique()),
        }
    }


def expected_ranking(dates: list[str]) -> dict[str, Any]:
    features = load_days("page-ranking", dates, "features.parquet")
    aggregated = (
        features.groupby("featureId", as_index=False)
        .agg(
            total=("total", "sum"),
            views=("views", "sum"),
            clicks=("clicks", "sum"),
        )
        .sort_values(["total", "featureId"], ascending=[False, True])
    )
    top = aggregated.iloc[0]
    return {
        "kpi": {
            "total": int(aggregated["total"].sum()),
            "feature_count": int(aggregated["featureId"].nunique()),
            "top_feature": str(top["featureId"]),
            "top_count": int(top["total"]),
        },
        "ranking_len": int(len(aggregated)),
    }


def expected_heatmap(dates: list[str]) -> dict[str, Any]:
    clicks = load_days("click-heatmap", dates, "click_counts.parquet")
    aggregated = (
        clicks.groupby("feature_id", as_index=False)
        .agg(total=("count", "sum"))
        .sort_values(["total", "feature_id"], ascending=[False, True])
    )
    top = aggregated.iloc[0]
    return {
        "kpi": {
            "total_clicks": int(clicks["count"].sum()),
            "feature_count": int(aggregated["feature_id"].nunique()),
            "top_feature": str(top["feature_id"]),
            "top_count": int(top["total"]),
        }
    }


def expected_navigation(dates: list[str]) -> dict[str, Any]:
    summary = load_days("page-navigation", dates, "daily_summary.parquet")
    # 驗證固定以 pagePath="" 執行（摘要模式），page_sources/destinations 不載入
    # page_count 回退為 daily_summary 的 SUM(tracked_pages)
    return {
        "kpi": {
            "nav_click":   int(summary["nav_click"].sum()),
            "nav_view":    int(summary["nav_view"].sum()),
            "nav_total":   int(summary["nav_click"].sum() + summary["nav_view"].sum()),
            "entry_click": int(summary["entry_click"].sum()),
            "entry_view":  int(summary["entry_view"].sum()),
            "entry_total": int(summary["entry_click"].sum() + summary["entry_view"].sum()),
            "page_count":  int(summary["tracked_pages"].sum()),
        },
        "transition_ranking_len": NAVIGATION_TRANSITION_LIMIT,
    }


def build_expected(view: str, dates: list[str]) -> dict[str, Any]:
    builders = {
        "feature": expected_feature,
        "device": expected_device,
        "ranking": expected_ranking,
        "heatmap": expected_heatmap,
        "navigation": expected_navigation,
    }
    return builders[view](dates)


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, list) and value:
        return normalize_scalar(value[0])
    if isinstance(value, dict):
        return {key: normalize_scalar(current) for key, current in value.items()}
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, str)) or value is None:
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: normalize_scalar(value) for key, value in row.items()}


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def start_static_server() -> tuple[ThreadingHTTPServer, str]:
    handler = partial(QuietHTTPRequestHandler, directory=str(STATIC_ROOT.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def actual_outputs(base_url: str, dates: list[str], views: list[str]) -> dict[str, dict[str, Any]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(
            f"{base_url}/report/device-platform/?view=device&date_from={dates[0]}&date_to={dates[-1]}",
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        page.wait_for_timeout(1_000)
        result = page.evaluate(
            """
            async ({ baseUrl, dates, views }) => {
              const duckdb = await import("https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.30.0/+esm");
              const { executeViewQueries } = await import(baseUrl + "/query-definitions.js");
              const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
              const workerUrl = URL.createObjectURL(
                new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }),
              );
              const worker = new Worker(workerUrl);
              const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
              await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
              URL.revokeObjectURL(workerUrl);
              const conn = await db.connect();
              const datasetRoot = baseUrl + "/dataset/";
              const registerFile = async (alias, url) => {
                const resp = await fetch(url);
                if (!resp.ok) throw new Error(`${resp.status} ${url}`);
                await db.registerFileBuffer(alias, new Uint8Array(await resp.arrayBuffer()));
              };

              async function run(viewMode) {
                const result = await executeViewQueries(
                  conn,
                  {
                    viewMode,
                    dateFrom: dates[0],
                    dateTo: dates[dates.length - 1],
                    fetchDates: dates,
                    datasetRoot,
                    pagePath: "",
                  },
                  registerFile,
                );
                return Object.fromEntries(result.outputs.map(item => [item.name, item.rows]));
              }

              const output = {};
              for (const viewMode of views) {
                output[viewMode] = await run(viewMode);
              }

              await conn.close();
              await db.terminate();
              return output;
            }
            """,
            {"baseUrl": base_url, "dates": dates, "views": views},
        )
        browser.close()
        return result


def compare_view(view: str, expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    if "kpi" in expected:
        comparison["expected"] = expected["kpi"]
        comparison["actual"] = normalize_row(actual["kpi"][0])
    if view == "ranking":
        comparison["expected_ranking_len"] = expected["ranking_len"]
        comparison["actual_ranking_len"] = len(actual["ranking"])
    if view == "navigation":
        # pagePath="" 時不載入 page_sources/targets，只驗證 transition_ranking
        comparison["expected_transition_ranking_len"] = expected["transition_ranking_len"]
        comparison["actual_transition_ranking_len"] = len(actual["transition_ranking"])
    return comparison


def has_mismatch(comparison: dict[str, Any]) -> bool:
    if comparison.get("expected") != comparison.get("actual"):
        return True
    for key, value in comparison.items():
        if key.startswith("expected_"):
            actual_key = key.replace("expected_", "actual_", 1)
            if comparison.get(actual_key) != value:
                return True
    return False


def main() -> None:
    args = parse_args()
    dates = enumerate_dates(args.date_from, args.date_to)
    if not dates:
        raise SystemExit("日期區間不可為空")
    if not REPORT_ROOT.exists():
        raise SystemExit(f"找不到報表資料夾：{REPORT_ROOT}")
    if not STATIC_ROOT.exists():
        raise SystemExit(f"找不到輸出資料夾：{STATIC_ROOT}")

    server, base_url = start_static_server()
    try:
        actual = actual_outputs(base_url, dates, args.views)
    finally:
        server.shutdown()
        server.server_close()

    comparisons = {
        view: compare_view(view, build_expected(view, dates), actual[view])
        for view in args.views
    }
    failed = {view: data for view, data in comparisons.items() if has_mismatch(data)}

    print(json.dumps({
        "date_from": args.date_from,
        "date_to": args.date_to,
        "views": args.views,
        "comparisons": comparisons,
        "passed": not failed,
    }, ensure_ascii=False, indent=2))

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
