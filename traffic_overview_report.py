#!/usr/bin/env python3
"""
traffic_overview_report.py
──────────────────────────
Dashboard 1：整體流量概覽（Traffic Overview）
從 Elasticsearch 查詢 jobbank-web 的整體流量數據，產生 HTML 圖表報告。

執行方式：
    uv run python traffic_overview_report.py
    uv run python traffic_overview_report.py --days 7
    uv run python traffic_overview_report.py --from 2026-04-01 --to 2026-04-10
    uv run python traffic_overview_report.py --output /tmp/report
    uv run python traffic_overview_report.py --from 2026-04-01 --to 2026-04-10 --from-store
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from common.es_client import (
    ES_INDEX,
    msearch,
    parse_args,
    resolve_time_range,
    generated_now,
    TW,
)
from common.chart_helpers import (
    PALETTE,
    js_labels,
    js_values,
    palette_array,
)
from common.html_template import (
    html_start,
    html_end,
    kpi_card,
    chart_card,
    table_card,
)
from common.store import init_db, load_daily_range, parse_date_range

OUTPUT_DIR = Path(__file__).parent / "output" / "traffic-overview"
REPORT = "traffic-overview"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_kpi(time_from: str, time_to: str) -> dict:
    """KPI：總事件數、View/Click/Apply 數、Unique Sessions。"""
    body = {
        "size": 0,
        "track_total_hits": True,
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
                    SYSTEM_FILTER,
                ]
            }
        },
        "aggs": {
            "by_event_type": {
                "terms": {"field": "eventType", "size": 10}
            },
            "apply_count": {
                "filter": {"term": {"action": "apply"}}
            },
            "unique_sessions": {
                "cardinality": {"field": "sessionId", "precision_threshold": 40000}
            },
        },
    }
    r = msearch(body)
    total = r["hits"]["total"]["value"]

    event_types = {b["key"]: b["doc_count"] for b in r["aggregations"]["by_event_type"]["buckets"]}
    views = event_types.get("view", 0)
    clicks = event_types.get("click", 0)
    applies = r["aggregations"]["apply_count"]["doc_count"]
    sessions = r["aggregations"]["unique_sessions"]["value"]

    return {
        "total": total,
        "views": views,
        "clicks": clicks,
        "applies": applies,
        "sessions": sessions,
        "click_rate": clicks / total * 100 if total else 0,
        "apply_rate": applies / views * 100 if views else 0,
    }


def query_daily_trend(time_from: str, time_to: str) -> list[dict]:
    """每日流量趨勢：view/click/apply + unique sessions。"""
    body = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
                    SYSTEM_FILTER,
                ]
            }
        },
        "aggs": {
            "daily": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
                "aggs": {
                    "by_event_type": {
                        "terms": {"field": "eventType", "size": 10}
                    },
                    "apply_count": {
                        "filter": {"term": {"action": "apply"}}
                    },
                    "unique_sessions": {
                        "cardinality": {"field": "sessionId", "precision_threshold": 40000}
                    },
                },
            }
        },
    }
    r = msearch(body)
    result = []
    for bucket in r["aggregations"]["daily"]["buckets"]:
        date_str = bucket["key_as_string"][:10]
        et = {b["key"]: b["doc_count"] for b in bucket["by_event_type"]["buckets"]}
        result.append({
            "date": date_str,
            "views": et.get("view", 0),
            "clicks": et.get("click", 0),
            "applies": bucket["apply_count"]["doc_count"],
            "sessions": bucket["unique_sessions"]["value"],
        })
    return result


def query_hourly_distribution(time_from: str, time_to: str) -> list[dict]:
    """每小時流量分佈（台灣時區）。"""
    body = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
                    SYSTEM_FILTER,
                ]
            }
        },
        "aggs": {
            "hourly": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "hour",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
            }
        },
    }
    r = msearch(body)

    # 累加每個小時的事件數，再算平均
    hour_totals = [0] * 24
    hour_days = [0] * 24
    for bucket in r["aggregations"]["hourly"]["buckets"]:
        h = int(bucket["key_as_string"][11:13])
        hour_totals[h] += bucket["doc_count"]
        hour_days[h] += 1

    return [
        {"hour": h, "avg": round(hour_totals[h] / hour_days[h]) if hour_days[h] else 0}
        for h in range(24)
    ]


def query_device_distribution(time_from: str, time_to: str) -> dict:
    """裝置 / OS / 瀏覽器分佈。"""
    body = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
                    SYSTEM_FILTER,
                ]
            }
        },
        "aggs": {
            "device_type": {
                "terms": {"field": "deviceType", "size": 10}
            },
            "os": {
                "terms": {"field": "os", "size": 20}
            },
            "browser": {
                "terms": {"field": "browser", "size": 10}
            },
        },
    }
    r = msearch(body)
    return {
        "device_type": [
            {"name": b["key"], "count": b["doc_count"]}
            for b in r["aggregations"]["device_type"]["buckets"]
        ],
        "os": [
            {"name": b["key"], "count": b["doc_count"]}
            for b in r["aggregations"]["os"]["buckets"]
        ],
        "browser": [
            {"name": b["key"], "count": b["doc_count"]}
            for b in r["aggregations"]["browser"]["buckets"]
        ],
    }


# ── Store 讀取與合併 ──────────────────────────────────────────────────────────

def _date_range(time_from: str, time_to: str) -> tuple[str, str]:
    """從時間字串取出 YYYY-MM-DD 日期區間。"""
    d_from = time_from[:10]
    d_to = time_to[:10] if time_to.lower() != "now" else datetime.now(TW).strftime("%Y-%m-%d")
    return d_from, d_to


def _load_kpi(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_kpi")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_kpi [{date_from}～{date_to}]")
    total   = sum(r["data"]["total"]   for r in rows)
    views   = sum(r["data"]["views"]   for r in rows)
    clicks  = sum(r["data"]["clicks"]  for r in rows)
    applies = sum(r["data"]["applies"] for r in rows)
    sessions = sum(r["data"]["sessions"] for r in rows)
    return {
        "total": total, "views": views, "clicks": clicks, "applies": applies,
        "sessions": sessions,
        "sessions_approx": len(rows) > 1,
        "click_rate": clicks / total * 100 if total else 0,
        "apply_rate": applies / views * 100 if views else 0,
    }


def _load_daily_trend(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_daily_trend")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_daily_trend")
    result = []
    for r in rows:
        result.extend(r["data"])
    return sorted(result, key=lambda x: x["date"])


def _load_hourly(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_hourly_distribution")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_hourly_distribution")
    totals = [0] * 24
    for r in rows:
        for item in r["data"]:
            totals[item["hour"]] += item["avg"]
    return [{"hour": h, "avg": c} for h, c in enumerate(totals)]


def _load_device(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_device_distribution")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_device_distribution")
    merged: dict[str, dict[str, int]] = {}
    for r in rows:
        for k, lst in r["data"].items():
            if k not in merged:
                merged[k] = {}
            for item in lst:
                merged[k][item["name"]] = merged[k].get(item["name"], 0) + item["count"]
    return {k: sorted([{"name": n, "count": c} for n, c in v.items()], key=lambda x: -x["count"])
            for k, v in merged.items()}


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    kpi: dict,
    daily: list[dict],
    hourly: list[dict],
    device: dict,
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []

    # ── head
    parts.append(html_start("整體流量概覽 — Traffic Overview", time_from, time_to, gen_at))

    # ── KPI
    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("總事件數", f"{kpi['total']:,}", "View + Click", "#4361ee"))
    parts.append(kpi_card("View", f"{kpi['views']:,}", f"佔 {kpi['views']/kpi['total']*100:.1f}%" if kpi['total'] else "0%", "#118ab2"))
    parts.append(kpi_card("Click", f"{kpi['clicks']:,}", f"佔 {kpi['clicks']/kpi['total']*100:.1f}%" if kpi['total'] else "0%", "#7209b7"))
    parts.append(kpi_card("Apply", f"{kpi['applies']:,}", f"轉換率 {kpi['apply_rate']:.2f}%（Apply / Job Page View）", "#f72585"))
    parts.append(kpi_card("Unique Sessions", f"{kpi['sessions']:,}", "依 sessionId 去重 ＊" if kpi.get("sessions_approx") else "依 sessionId 去重", "#06d6a0"))
    parts.append(kpi_card("Click Rate", f"{kpi['click_rate']:.2f}%", "Click / 總事件數", "#fb8500"))
    parts.append(kpi_card("Apply Rate", f"{kpi['apply_rate']:.2f}%", "Apply / 總事件數中的 View", "#e63946"))
    parts.append('  </div>')

    # ── 每日流量趨勢
    dates = [d["date"] for d in daily]
    views_data = [d["views"] for d in daily]
    clicks_data = [d["clicks"] for d in daily]
    applies_data = [d["applies"] for d in daily]
    sessions_data = [d["sessions"] for d in daily]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("每日流量趨勢", "View / Click / Apply（右 Y 軸）+ Unique Sessions", "dailyTrend"))
    parts.append('  </div>')

    # ── 每小時分佈
    hour_labels = [f"{h:02d}" for h in range(24)]
    hour_values = [h["avg"] for h in hourly]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("每小時流量分佈", "平均事件數（台灣時區 0-23 時）", "hourlyDist"))
    parts.append('  </div>')

    # ── 裝置分佈
    dt = device["device_type"]
    dt_labels = [d["name"] for d in dt]
    dt_values = [d["count"] for d in dt]

    os_data = device["os"]
    os_total = sum(d["count"] for d in os_data)

    browser_data = device["browser"]
    br_total = sum(d["count"] for d in browser_data)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("裝置分佈", "Mobile vs Desktop", "devicePie"))
    parts.append(chart_card("OS 分佈", f"Top {len(os_data)} 作業系統", "osPie"))
    parts.append('  </div>')

    # ── OS 表格
    os_thead = "<tr><th>#</th><th>OS</th><th>事件數</th><th>佔比</th></tr>"
    os_tbody = ""
    for i, d in enumerate(os_data, 1):
        pct = d["count"] / os_total * 100 if os_total else 0
        os_tbody += f'<tr><td class="rank">{i}</td><td>{d["name"]}</td><td>{d["count"]:,}</td><td class="pct">{pct:.1f}%</td></tr>'
    parts.append(table_card("OS 詳細數據", f"共 {os_total:,} 筆", os_thead, os_tbody))

    # ── 瀏覽器表格
    br_thead = "<tr><th>#</th><th>瀏覽器</th><th>事件數</th><th>佔比</th></tr>"
    br_tbody = ""
    for i, d in enumerate(browser_data, 1):
        pct = d["count"] / br_total * 100 if br_total else 0
        br_tbody += f'<tr><td class="rank">{i}</td><td>{d["name"]}</td><td>{d["count"]:,}</td><td class="pct">{pct:.1f}%</td></tr>'
    parts.append(table_card("瀏覽器 Top 10", f"共 {br_total:,} 筆", br_thead, br_tbody))

    # ── Chart.js scripts
    parts.append(f"""
<script>
  // ── 每日流量趨勢（Dual Y-Axis）
  new Chart(document.getElementById('dailyTrend'), {{
    type: 'line',
    data: {{
      labels: {js_labels(dates)},
      datasets: [
        {{
          label: 'View',
          data: {js_values(views_data)},
          borderColor: '#118ab2', backgroundColor: 'rgba(17,138,178,0.1)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: 'Click',
          data: {js_values(clicks_data)},
          borderColor: '#7209b7', backgroundColor: 'rgba(114,9,183,0.1)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: 'Apply',
          data: {js_values(applies_data)},
          borderColor: '#f72585', backgroundColor: 'rgba(247,37,133,0.1)',
          fill: true, tension: 0.3, yAxisID: 'y1'
        }},
        {{
          label: 'Unique Sessions',
          data: {js_values(sessions_data)},
          borderColor: '#06d6a0', borderDash: [6,3],
          fill: false, tension: 0.3, yAxisID: 'y'
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y:  {{ position: 'left',  grid: {{ color: '#f0f0f0' }}, title: {{ display: true, text: '事件數' }} }},
        y1: {{ position: 'right', grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'Apply 數' }} }}
      }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});

  // ── 每小時分佈
  new Chart(document.getElementById('hourlyDist'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(hour_labels)},
      datasets: [{{
        label: '平均事件數',
        data: {js_values(hour_values)},
        backgroundColor: {palette_array(24)},
        borderRadius: 4
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ display: false }}, title: {{ display: true, text: '小時（台灣時區）' }} }},
        y: {{ grid: {{ color: '#f0f0f0' }}, title: {{ display: true, text: '平均事件數' }} }}
      }}
    }}
  }});

  // ── 裝置分佈 Doughnut
  new Chart(document.getElementById('devicePie'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(dt_labels)},
      datasets: [{{
        data: {js_values(dt_values)},
        backgroundColor: {palette_array(len(dt))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {sum(dt_values)};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── OS 分佈 Doughnut
  const osLabels = {js_labels([d["name"] for d in os_data])};
  const osValues = {js_values([d["count"] for d in os_data])};
  new Chart(document.getElementById('osPie'), {{
    type: 'doughnut',
    data: {{
      labels: osLabels,
      datasets: [{{
        data: osValues,
        backgroundColor: {palette_array(len(os_data))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {os_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});
</script>
""")

    parts.append(html_end(gen_at))
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 1：整體流量概覽")
    time_from, time_to = resolve_time_range(args)
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 查詢區間：{time_from} ～ {time_to}")
    print(f"[INFO] 輸出目錄：{output_dir}")
    source = "store.db" if args.from_store else "ES"
    print(f"[INFO] 資料來源：{source}")

    if args.from_store:
        init_db()
        date_from, date_to = parse_date_range(time_from, time_to)
        print("[INFO] 讀取 KPI...")
        kpi = _load_kpi(date_from, date_to)
        print("[INFO] 讀取每日趨勢...")
        daily = _load_daily_trend(date_from, date_to)
        print("[INFO] 讀取每小時分佈...")
        hourly = _load_hourly(date_from, date_to)
        print("[INFO] 讀取裝置分佈...")
        device = _load_device(date_from, date_to)
    else:
        print("[INFO] 查詢 KPI...")
        kpi = query_kpi(time_from, time_to)
        print("[INFO] 查詢每日趨勢...")
        daily = query_daily_trend(time_from, time_to)
        print("[INFO] 查詢每小時分佈...")
        hourly = query_hourly_distribution(time_from, time_to)
        print("[INFO] 查詢裝置分佈...")
        device = query_device_distribution(time_from, time_to)

    print(f"  總事件 {kpi['total']:,} / View {kpi['views']:,} / Click {kpi['clicks']:,} / Apply {kpi['applies']:,} / Sessions {kpi['sessions']:,}")

    gen_at = generated_now()
    html = generate_html(kpi, daily, hourly, device, time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()

