#!/usr/bin/env python3
"""
device_platform_report.py
──────────────────────────
Dashboard 5：裝置與平台分析（Device & Platform）
從 Elasticsearch 查詢 jobbank-web 的裝置/平台使用數據，產生 HTML 圖表報告。

執行方式：
    uv run python device_platform_report.py
    uv run python device_platform_report.py --days 7
    uv run python device_platform_report.py --from 2026-04-01 --to 2026-04-10
    uv run python device_platform_report.py --output /tmp/report
    uv run python device_platform_report.py --from 2026-04-01 --to 2026-04-10 --from-store
"""

from datetime import datetime
from pathlib import Path

from common.es_client import msearch, parse_args, resolve_time_range, generated_now, TW
from common.chart_helpers import js_labels, js_values, palette_array, table_rows_ranked
from common.html_template import html_start, html_end, kpi_card, chart_card, table_card
from common.store import init_db, load_daily_range

OUTPUT_DIR = Path(__file__).parent / "output" / "device-platform"
REPORT = "device-platform"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_device_daily(time_from: str, time_to: str) -> dict:
    """裝置每日趨勢 + 總體分佈。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "device_total": {"terms": {"field": "deviceType", "size": 10}},
            "daily": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
                "aggs": {
                    "mobile": {"filter": {"term": {"deviceType": "mobile"}}},
                    "desktop": {"filter": {"term": {"deviceType": "desktop"}}},
                },
            },
        },
    }
    r = msearch(body)
    agg = r["aggregations"]
    device_total = {b["key"]: b["doc_count"] for b in agg["device_total"]["buckets"]}
    daily = []
    for bucket in agg["daily"]["buckets"]:
        m = bucket["mobile"]["doc_count"]
        d = bucket["desktop"]["doc_count"]
        total = m + d
        daily.append({
            "date": bucket["key_as_string"][:10],
            "mobile": m,
            "desktop": d,
            "mobile_pct": round(m / total * 100, 1) if total else 0,
        })
    return {"total": device_total, "daily": daily}


def query_os_browser(time_from: str, time_to: str) -> dict:
    """OS 與瀏覽器分佈。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "os": {"terms": {"field": "os", "size": 15}},
            "browser": {"terms": {"field": "browser", "size": 10}},
        },
    }
    r = msearch(body)
    agg = r["aggregations"]
    return {
        "os": [{"name": b["key"], "count": b["doc_count"]} for b in agg["os"]["buckets"]],
        "browser": [{"name": b["key"], "count": b["doc_count"]} for b in agg["browser"]["buckets"]],
    }


def query_device_behavior(time_from: str, time_to: str) -> dict:
    """裝置 × 行為交叉分析（view / click / apply）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "by_device": {
                "terms": {"field": "deviceType", "size": 5},
                "aggs": {
                    "views":  {"filter": {"term": {"eventType": "view"}}},
                    "clicks": {"filter": {"term": {"eventType": "click"}}},
                    "applies": {"filter": {"term": {"action": "apply"}}},
                    "job_views": {"filter": {"bool": {"must": [
                        {"term": {"featureId": "job-page"}},
                        {"term": {"eventType": "view"}},
                    ]}}},
                },
            }
        },
    }
    r = msearch(body)
    result = []
    for b in r["aggregations"]["by_device"]["buckets"]:
        total = b["doc_count"]
        applies = b["applies"]["doc_count"]
        job_views = b["job_views"]["doc_count"]
        result.append({
            "device": b["key"],
            "total": total,
            "views": b["views"]["doc_count"],
            "clicks": b["clicks"]["doc_count"],
            "applies": applies,
            "apply_rate": round(applies / job_views * 100, 2) if job_views else 0,
        })
    return result


def query_os_behavior(time_from: str, time_to: str) -> list[dict]:
    """OS × 行為交叉分析。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "by_os": {
                "terms": {"field": "os", "size": 10},
                "aggs": {
                    "views":  {"filter": {"term": {"eventType": "view"}}},
                    "clicks": {"filter": {"term": {"eventType": "click"}}},
                    "applies": {"filter": {"term": {"action": "apply"}}},
                },
            }
        },
    }
    r = msearch(body)
    result = []
    for b in r["aggregations"]["by_os"]["buckets"]:
        result.append({
            "os": b["key"],
            "total": b["doc_count"],
            "views": b["views"]["doc_count"],
            "clicks": b["clicks"]["doc_count"],
            "applies": b["applies"]["doc_count"],
        })
    return result


# ── Store 讀取與合併 ──────────────────────────────────────────────────────────

def _date_range(time_from: str, time_to: str) -> tuple[str, str]:
    """從時間字串取出 YYYY-MM-DD 日期區間。"""
    d_from = time_from[:10]
    d_to = time_to[:10] if time_to.lower() != "now" else datetime.now(TW).strftime("%Y-%m-%d")
    return d_from, d_to


def _load_device_daily(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_device_daily")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_device_daily [{date_from}～{date_to}]")
    total: dict = {}
    all_daily: list = []
    for r in rows:
        d = r["data"]
        for k, v in d["total"].items():
            total[k] = total.get(k, 0) + v
        all_daily.extend(d["daily"])
    return {"total": total, "daily": sorted(all_daily, key=lambda x: x["date"])}


def _load_os_browser(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_os_browser")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_os_browser [{date_from}～{date_to}]")
    os_totals: dict = {}
    browser_totals: dict = {}
    for r in rows:
        for item in r["data"]["os"]:
            k = item["name"]
            os_totals[k] = os_totals.get(k, 0) + item["count"]
        for item in r["data"]["browser"]:
            k = item["name"]
            browser_totals[k] = browser_totals.get(k, 0) + item["count"]
    return {
        "os": sorted([{"name": k, "count": v} for k, v in os_totals.items()], key=lambda x: -x["count"]),
        "browser": sorted([{"name": k, "count": v} for k, v in browser_totals.items()], key=lambda x: -x["count"]),
    }


def _load_device_behavior(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_device_behavior")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_device_behavior [{date_from}～{date_to}]")
    # 跨天各 device 的各行為加總
    merged: dict = {}
    for r in rows:
        for item in r["data"]:
            dev = item["device"]
            if dev not in merged:
                merged[dev] = {"total": 0, "views": 0, "clicks": 0, "applies": 0}
            merged[dev]["total"] += item["total"]
            merged[dev]["views"] += item["views"]
            merged[dev]["clicks"] += item["clicks"]
            merged[dev]["applies"] += item["applies"]
    return [
        {"device": dev, "apply_rate": 0, **vals}
        for dev, vals in sorted(merged.items(), key=lambda x: -x[1]["total"])
    ]


def _load_os_behavior(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_os_behavior")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_os_behavior [{date_from}～{date_to}]")
    merged: dict = {}
    for r in rows:
        for item in r["data"]:
            os = item["os"]
            if os not in merged:
                merged[os] = {"total": 0, "views": 0, "clicks": 0, "applies": 0}
            merged[os]["total"] += item["total"]
            merged[os]["views"] += item["views"]
            merged[os]["clicks"] += item["clicks"]
            merged[os]["applies"] += item["applies"]
    return [
        {"os": os, **vals}
        for os, vals in sorted(merged.items(), key=lambda x: -x[1]["total"])
    ]


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    device_data: dict,
    os_browser: dict,
    device_behavior: list[dict],
    os_behavior: list[dict],
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []
    parts.append(html_start("裝置與平台分析 — Device & Platform", time_from, time_to, gen_at))

    # ── KPI
    mobile_total = device_data["total"].get("mobile", 0)
    desktop_total = device_data["total"].get("desktop", 0)
    grand_total = mobile_total + desktop_total
    mobile_pct = mobile_total / grand_total * 100 if grand_total else 0

    os_list = os_browser["os"]
    browser_list = os_browser["browser"]

    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("Mobile 事件數", f"{mobile_total:,}", f"佔 {mobile_pct:.1f}%", "#4361ee"))
    parts.append(kpi_card("Desktop 事件數", f"{desktop_total:,}", f"佔 {100-mobile_pct:.1f}%", "#118ab2"))
    parts.append(kpi_card("OS 種類", f"{len(os_list)}", "排名 Top 種", "#7209b7"))
    parts.append(kpi_card("瀏覽器種類", f"{len(browser_list)}", "排名 Top 種", "#f72585"))
    parts.append('  </div>')

    # ── 裝置每日趨勢
    d_dates = [d["date"] for d in device_data["daily"]]
    d_mobile = [d["mobile"] for d in device_data["daily"]]
    d_desktop = [d["desktop"] for d in device_data["daily"]]
    d_mobile_pct = [d["mobile_pct"] for d in device_data["daily"]]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("裝置類型每日趨勢", "mobile vs desktop 事件數 + mobile 佔比（右 Y 軸）", "deviceDaily", tall=True))
    parts.append(chart_card("OS 分佈", f"Top {len(os_list)} 作業系統", "osDist"))
    parts.append('  </div>')

    # ── 瀏覽器 horizontal bar
    br_names = [d["name"] for d in browser_list]
    br_vals = [d["count"] for d in browser_list]
    br_total = sum(br_vals)

    os_names = [d["name"] for d in os_list]
    os_vals = [d["count"] for d in os_list]
    os_total = sum(os_vals)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("瀏覽器分佈", f"Top {len(browser_list)} 瀏覽器", "browserBar"))
    parts.append(chart_card("裝置 × 行為（view/click/apply）", "各裝置事件量比較", "deviceBehavior"))
    parts.append('  </div>')

    # ── OS 表格
    os_thead = "<tr><th>#</th><th>OS</th><th>事件數</th><th>視覺</th><th>佔比</th></tr>"
    os_tbody = table_rows_ranked(os_list, "name", "count", os_total)
    parts.append(table_card("OS 詳細數據", f"共 {os_total:,} 筆", os_thead, os_tbody))

    # ── 瀏覽器表格
    br_thead = "<tr><th>#</th><th>瀏覽器</th><th>事件數</th><th>視覺</th><th>佔比</th></tr>"
    br_tbody = table_rows_ranked(browser_list, "name", "count", br_total)
    parts.append(table_card("瀏覽器詳細數據", f"共 {br_total:,} 筆", br_thead, br_tbody))

    # ── 裝置行為表格
    dev_beh_thead = "<tr><th>裝置</th><th>總事件</th><th>View</th><th>Click</th><th>Apply</th><th>Apply 轉換率</th></tr>"
    dev_beh_tbody = ""
    for d in device_behavior:
        dev_beh_tbody += (
            f'<tr><td>{d["device"]}</td><td>{d["total"]:,}</td>'
            f'<td>{d["views"]:,}</td><td>{d["clicks"]:,}</td>'
            f'<td>{d["applies"]:,}</td><td class="pct">{d["apply_rate"]:.2f}%</td></tr>'
        )
    parts.append(table_card("裝置 × 行為交叉分析", "各裝置 view/click/apply 分佈與應徵轉換率",
                             dev_beh_thead, dev_beh_tbody))

    # ── OS 行為表格
    os_beh_thead = "<tr><th>OS</th><th>總事件</th><th>View</th><th>Click</th><th>Apply</th></tr>"
    os_beh_tbody = ""
    for d in os_behavior:
        os_beh_tbody += (
            f'<tr><td>{d["os"]}</td><td>{d["total"]:,}</td>'
            f'<td>{d["views"]:,}</td><td>{d["clicks"]:,}</td>'
            f'<td>{d["applies"]:,}</td></tr>'
        )
    parts.append(table_card("OS × 行為交叉分析", "各 OS view/click/apply 分佈", os_beh_thead, os_beh_tbody))

    # ── 裝置行為 grouped bar
    db_devices = [d["device"] for d in device_behavior]
    db_views = [d["views"] for d in device_behavior]
    db_clicks = [d["clicks"] for d in device_behavior]
    db_applies = [d["applies"] for d in device_behavior]

    parts.append(f"""
<script>
  // ── 裝置每日趨勢
  new Chart(document.getElementById('deviceDaily'), {{
    type: 'line',
    data: {{
      labels: {js_labels(d_dates)},
      datasets: [
        {{
          label: 'Mobile',
          data: {js_values(d_mobile)},
          borderColor: '#4361ee', backgroundColor: 'rgba(67,97,238,0.1)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: 'Desktop',
          data: {js_values(d_desktop)},
          borderColor: '#118ab2', backgroundColor: 'rgba(17,138,178,0.08)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: 'Mobile 佔比 %',
          data: {js_values(d_mobile_pct)},
          borderColor: '#fb8500', borderDash: [6,3],
          fill: false, tension: 0.3, yAxisID: 'y1'
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y:  {{ position: 'left',  title: {{ display: true, text: '事件數' }} }},
        y1: {{ position: 'right', grid: {{ drawOnChartArea: false }},
               title: {{ display: true, text: 'Mobile 佔比 %' }}, min: 0, max: 100 }}
      }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});

  // ── OS 分佈 Doughnut
  new Chart(document.getElementById('osDist'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(os_names)},
      datasets: [{{
        data: {js_values(os_vals)},
        backgroundColor: {palette_array(len(os_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 8 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {os_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}}（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── 瀏覽器 Horizontal Bar
  new Chart(document.getElementById('browserBar'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(br_names)},
      datasets: [{{
        label: '事件數',
        data: {js_values(br_vals)},
        backgroundColor: {palette_array(len(br_vals))},
        borderRadius: 4
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: '事件數' }} }},
        y: {{ grid: {{ display: false }} }}
      }}
    }}
  }});

  // ── 裝置行為 Grouped Bar
  new Chart(document.getElementById('deviceBehavior'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(db_devices)},
      datasets: [
        {{
          label: 'View',
          data: {js_values(db_views)},
          backgroundColor: '#4361ee', borderRadius: 4
        }},
        {{
          label: 'Click',
          data: {js_values(db_clicks)},
          backgroundColor: '#7209b7', borderRadius: 4
        }},
        {{
          label: 'Apply',
          data: {js_values(db_applies)},
          backgroundColor: '#f72585', borderRadius: 4
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{ legend: {{ position: 'bottom' }} }},
      scales: {{
        y: {{ title: {{ display: true, text: '事件數' }} }}
      }}
    }}
  }});
</script>
""")

    parts.append(html_end(gen_at))
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 5：裝置與平台分析")
    time_from, time_to = resolve_time_range(args)
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 查詢區間：{time_from} ～ {time_to}")
    print(f"[INFO] 輸出目錄：{output_dir}")
    source = "store.db" if args.from_store else "ES"
    print(f"[INFO] 資料來源：{source}")

    if args.from_store:
        init_db()
        date_from, date_to = _date_range(time_from, time_to)
        print("[INFO] 讀取裝置每日趨勢...")
        device_data = _load_device_daily(date_from, date_to)
        print("[INFO] 讀取 OS / 瀏覽器分佈...")
        os_browser = _load_os_browser(date_from, date_to)
        print("[INFO] 讀取裝置行為交叉...")
        device_behavior = _load_device_behavior(date_from, date_to)
        print("[INFO] 讀取 OS 行為交叉...")
        os_behavior = _load_os_behavior(date_from, date_to)
    else:
        print("[INFO] 查詢裝置每日趨勢...")
        device_data = query_device_daily(time_from, time_to)
        print("[INFO] 查詢 OS / 瀏覽器分佈...")
        os_browser = query_os_browser(time_from, time_to)
        print("[INFO] 查詢裝置行為交叉...")
        device_behavior = query_device_behavior(time_from, time_to)
        print("[INFO] 查詢 OS 行為交叉...")
        os_behavior = query_os_behavior(time_from, time_to)

    gen_at = generated_now()
    html = generate_html(device_data, os_browser, device_behavior, os_behavior,
                         time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
