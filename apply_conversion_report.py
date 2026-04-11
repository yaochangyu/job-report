#!/usr/bin/env python3
"""
apply_conversion_report.py
──────────────────────────
Dashboard 3：應徵轉換分析（Apply Conversion）
從 Elasticsearch 查詢 jobbank-web 的應徵行為數據，產生 HTML 圖表報告。

執行方式：
    uv run python apply_conversion_report.py
    uv run python apply_conversion_report.py --days 7
    uv run python apply_conversion_report.py --from 2026-04-01 --to 2026-04-10
    uv run python apply_conversion_report.py --output /tmp/report
    uv run python apply_conversion_report.py --from 2026-04-01 --to 2026-04-10 --from-store
"""

from datetime import datetime
from pathlib import Path

from common.es_client import msearch, parse_args, resolve_time_range, generated_now, TW
from common.chart_helpers import js_labels, js_values, palette_array, table_rows_ranked
from common.html_template import html_start, html_end, kpi_card, chart_card, table_card
from common.store import init_db, load_daily_range

OUTPUT_DIR = Path(__file__).parent / "output" / "apply-conversion"
REPORT = "apply-conversion"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_apply_kpi(time_from: str, time_to: str) -> dict:
    """應徵 KPI：總應徵數、Job Page View、轉換率、來源分佈。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "apply_count": {"filter": {"term": {"action": "apply"}}},
            "job_page_view": {"filter": {"bool": {"must": [
                {"term": {"featureId": "job-page"}},
                {"term": {"eventType": "view"}},
            ]}}},
        },
    }
    r = msearch(body)
    applies = r["aggregations"]["apply_count"]["doc_count"]
    job_views = r["aggregations"]["job_page_view"]["doc_count"]
    return {
        "applies": applies,
        "job_views": job_views,
        "conversion_rate": applies / job_views * 100 if job_views else 0,
    }


def query_apply_source(time_from: str, time_to: str) -> list[dict]:
    """應徵來源分佈（metadata.source 需用 script）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"term": {"action": "apply"}},
        ]}},
        "aggs": {
            "by_source": {
                "terms": {
                    "script": {
                        "source": "doc.containsKey('metadata.source') && doc['metadata.source'].size() > 0 ? doc['metadata.source'].value : 'unknown'",
                        "lang": "painless",
                    },
                    "size": 10,
                }
            }
        },
    }
    r = msearch(body)
    return [
        {"name": b["key"], "count": b["doc_count"]}
        for b in r["aggregations"]["by_source"]["buckets"]
    ]


def query_apply_daily_trend(time_from: str, time_to: str) -> list[dict]:
    """每日 apply + job-page view 趨勢。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "daily": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
                "aggs": {
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
    for bucket in r["aggregations"]["daily"]["buckets"]:
        applies = bucket["applies"]["doc_count"]
        job_views = bucket["job_views"]["doc_count"]
        result.append({
            "date": bucket["key_as_string"][:10],
            "applies": applies,
            "job_views": job_views,
            "conv_rate": round(applies / job_views * 100, 2) if job_views else 0,
        })
    return result


def query_funnel(time_from: str, time_to: str) -> list[dict]:
    """轉換漏斗：home-page → search-job-page → job-page → apply-job。"""
    funnel_features = ["home-page", "search-job-page", "job-page"]
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "home_page": {"filter": {"bool": {"must": [
                {"term": {"featureId": "home-page"}},
                {"term": {"eventType": "view"}},
            ]}}},
            "search_page": {"filter": {"bool": {"must": [
                {"term": {"featureId": "search-job-page"}},
                {"term": {"eventType": "view"}},
            ]}}},
            "job_page": {"filter": {"bool": {"must": [
                {"term": {"featureId": "job-page"}},
                {"term": {"eventType": "view"}},
            ]}}},
            "apply": {"filter": {"term": {"action": "apply"}}},
        },
    }
    r = msearch(body)
    agg = r["aggregations"]
    steps = [
        {"name": "首頁瀏覽", "count": agg["home_page"]["doc_count"]},
        {"name": "搜尋結果頁瀏覽", "count": agg["search_page"]["doc_count"]},
        {"name": "職缺詳情頁瀏覽", "count": agg["job_page"]["doc_count"]},
        {"name": "應徵送出", "count": agg["apply"]["doc_count"]},
    ]
    return steps


def query_apply_device(time_from: str, time_to: str) -> dict:
    """應徵裝置/OS 分佈。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"term": {"action": "apply"}},
        ]}},
        "aggs": {
            "device_type": {"terms": {"field": "deviceType", "size": 10}},
            "os": {"terms": {"field": "os", "size": 10}},
        },
    }
    r = msearch(body)
    return {
        "device": [{"name": b["key"], "count": b["doc_count"]}
                   for b in r["aggregations"]["device_type"]["buckets"]],
        "os": [{"name": b["key"], "count": b["doc_count"]}
               for b in r["aggregations"]["os"]["buckets"]],
    }


def query_apply_hourly(time_from: str, time_to: str) -> list[int]:
    """每小時應徵分佈。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"term": {"action": "apply"}},
        ]}},
        "aggs": {
            "hourly": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "hour",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                }
            }
        },
    }
    r = msearch(body)
    hour_totals = [0] * 24
    hour_days = [0] * 24
    for bucket in r["aggregations"]["hourly"]["buckets"]:
        h = int(bucket["key_as_string"][11:13])
        hour_totals[h] += bucket["doc_count"]
        hour_days[h] += 1
    return [round(hour_totals[h] / hour_days[h]) if hour_days[h] else 0 for h in range(24)]


# ── Store 讀取與合併 ──────────────────────────────────────────────────────────

def _date_range(time_from: str, time_to: str) -> tuple[str, str]:
    """從時間字串取出 YYYY-MM-DD 日期區間。"""
    d_from = time_from[:10]
    d_to = time_to[:10] if time_to.lower() != "now" else datetime.now(TW).strftime("%Y-%m-%d")
    return d_from, d_to


def _load_apply_kpi(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_apply_kpi")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_apply_kpi [{date_from}～{date_to}]")
    applies = sum(r["data"]["applies"] for r in rows)
    job_views = sum(r["data"]["job_views"] for r in rows)
    return {
        "applies": applies,
        "job_views": job_views,
        "conversion_rate": applies / job_views * 100 if job_views else 0,
    }


def _load_apply_source(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_apply_source")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_apply_source [{date_from}～{date_to}]")
    totals: dict = {}
    for r in rows:
        for item in r["data"]:
            k = item["name"]
            totals[k] = totals.get(k, 0) + item["count"]
    return sorted([{"name": k, "count": v} for k, v in totals.items()], key=lambda x: -x["count"])


def _load_apply_daily_trend(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_apply_daily_trend")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_apply_daily_trend [{date_from}～{date_to}]")
    result = []
    for r in rows:
        result.extend(r["data"])
    return sorted(result, key=lambda x: x["date"])


def _load_funnel(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_funnel")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_funnel [{date_from}～{date_to}]")
    totals: dict = {}
    for r in rows:
        for item in r["data"]:
            k = item["name"]
            totals[k] = totals.get(k, 0) + item["count"]
    # 保持漏斗順序
    order = ["首頁瀏覽", "搜尋結果頁瀏覽", "職缺詳情頁瀏覽", "應徵送出"]
    return [{"name": n, "count": totals.get(n, 0)} for n in order if n in totals]


def _load_apply_device(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_apply_device")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_apply_device [{date_from}～{date_to}]")
    device_totals: dict = {}
    os_totals: dict = {}
    for r in rows:
        for item in r["data"]["device"]:
            k = item["name"]
            device_totals[k] = device_totals.get(k, 0) + item["count"]
        for item in r["data"]["os"]:
            k = item["name"]
            os_totals[k] = os_totals.get(k, 0) + item["count"]
    return {
        "device": sorted([{"name": k, "count": v} for k, v in device_totals.items()], key=lambda x: -x["count"]),
        "os": sorted([{"name": k, "count": v} for k, v in os_totals.items()], key=lambda x: -x["count"]),
    }


def _load_apply_hourly(date_from: str, date_to: str) -> list[int]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_apply_hourly")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_apply_hourly [{date_from}～{date_to}]")
    totals = [0] * 24
    for r in rows:
        for h, v in enumerate(r["data"]):
            totals[h] += v
    return totals


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    kpi: dict,
    source_dist: list[dict],
    daily: list[dict],
    funnel: list[dict],
    device: dict,
    hourly: list[int],
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []
    parts.append(html_start("應徵轉換分析 — Apply Conversion", time_from, time_to, gen_at))

    # ── KPI
    total_days = len([d for d in daily if d["applies"] > 0]) or 1
    avg_daily = kpi["applies"] / len(daily) if daily else 0

    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("總應徵數", f"{kpi['applies']:,}", "action=apply 事件數", "#f72585"))
    parts.append(kpi_card("每日平均應徵", f"{avg_daily:,.0f}", "區間內日平均", "#fb8500"))
    parts.append(kpi_card("職缺頁瀏覽", f"{kpi['job_views']:,}", "job-page view 事件數", "#118ab2"))
    parts.append(kpi_card("應徵轉換率", f"{kpi['conversion_rate']:.2f}%", "Apply / Job Page View", "#4361ee"))
    parts.append('  </div>')

    # ── 每日趨勢
    dates = [d["date"] for d in daily]
    daily_applies = [d["applies"] for d in daily]
    daily_job_views = [d["job_views"] for d in daily]
    daily_conv = [d["conv_rate"] for d in daily]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("應徵每日趨勢", "職缺頁瀏覽 + 應徵數（右 Y 軸）+ 轉換率（右 Y 軸）", "applyTrend", tall=True))
    parts.append(chart_card("轉換漏斗", "各環節事件數（非 session-based）", "funnelChart"))
    parts.append('  </div>')

    # ── 來源分佈
    src_names = [d["name"] for d in source_dist]
    src_vals = [d["count"] for d in source_dist]
    src_total = sum(src_vals)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("應徵來源分佈", "metadata.source 分佈", "sourcePie"))
    parts.append(chart_card("應徵裝置分佈", "mobile vs desktop", "deviceBar"))
    parts.append('  </div>')

    # ── 裝置 table
    dev_total = sum(d["count"] for d in device["device"])
    dev_thead = "<tr><th>#</th><th>裝置</th><th>應徵數</th><th>佔比</th></tr>"
    dev_tbody = ""
    for i, d in enumerate(device["device"], 1):
        pct = d["count"] / dev_total * 100 if dev_total else 0
        dev_tbody += f'<tr><td class="rank">{i}</td><td>{d["name"]}</td><td>{d["count"]:,}</td><td class="pct">{pct:.1f}%</td></tr>'
    parts.append(table_card("應徵裝置詳細", f"共 {dev_total:,} 筆", dev_thead, dev_tbody))

    # ── OS table
    os_total = sum(d["count"] for d in device["os"])
    os_thead = "<tr><th>#</th><th>OS</th><th>應徵數</th><th>佔比</th></tr>"
    os_tbody = ""
    for i, d in enumerate(device["os"], 1):
        pct = d["count"] / os_total * 100 if os_total else 0
        os_tbody += f'<tr><td class="rank">{i}</td><td>{d["name"]}</td><td>{d["count"]:,}</td><td class="pct">{pct:.1f}%</td></tr>'
    parts.append(table_card("應徵 OS 分佈", f"共 {os_total:,} 筆", os_thead, os_tbody))

    # ── 每小時應徵
    hour_labels = [f"{h:02d}" for h in range(24)]
    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("應徵時段分佈", "每小時平均應徵數（台灣時區）", "applyHourly"))
    parts.append('  </div>')

    # ── 來源 table
    src_thead = "<tr><th>#</th><th>來源</th><th>應徵數</th><th>視覺</th><th>佔比</th></tr>"
    src_tbody = table_rows_ranked(source_dist, "name", "count", src_total)
    parts.append(table_card("應徵來源詳細數據", f"共 {src_total:,} 筆", src_thead, src_tbody))

    # ── funnel values
    funnel_labels = [f["name"] for f in funnel]
    funnel_vals = [f["count"] for f in funnel]
    funnel_top = funnel_vals[0] if funnel_vals else 1

    dev_labels = [d["name"] for d in device["device"]]
    dev_vals = [d["count"] for d in device["device"]]

    parts.append(f"""
<script>
  // ── 應徵每日趨勢
  new Chart(document.getElementById('applyTrend'), {{
    type: 'line',
    data: {{
      labels: {js_labels(dates)},
      datasets: [
        {{
          label: '職缺頁瀏覽',
          data: {js_values(daily_job_views)},
          borderColor: '#118ab2', backgroundColor: 'rgba(17,138,178,0.08)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: '應徵數',
          data: {js_values(daily_applies)},
          borderColor: '#f72585', backgroundColor: 'rgba(247,37,133,0.1)',
          fill: true, tension: 0.3, yAxisID: 'y1'
        }},
        {{
          label: '轉換率 %',
          data: {js_values(daily_conv)},
          borderColor: '#fb8500', borderDash: [6,3],
          fill: false, tension: 0.3, yAxisID: 'y1'
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y:  {{ position: 'left',  title: {{ display: true, text: '職缺頁瀏覽數' }} }},
        y1: {{ position: 'right', grid: {{ drawOnChartArea: false }},
               title: {{ display: true, text: '應徵數 / 轉換率 %' }} }}
      }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});

  // ── 漏斗圖（水平 Bar）
  new Chart(document.getElementById('funnelChart'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(funnel_labels)},
      datasets: [{{
        label: '事件數',
        data: {js_values(funnel_vals)},
        backgroundColor: {palette_array(len(funnel_vals))},
        borderRadius: 6
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const top = {funnel_top};
            const pct = top ? (ctx.parsed.x / top * 100).toFixed(1) : '0.0';
            return ` ${{ctx.parsed.x.toLocaleString()}} 次（相對首步驟 ${{pct}}%）`;
          }}
        }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: '事件數（非 session-based）' }} }},
        y: {{ grid: {{ display: false }} }}
      }}
    }}
  }});

  // ── 應徵來源 Doughnut
  new Chart(document.getElementById('sourcePie'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(src_names)},
      datasets: [{{
        data: {js_values(src_vals)},
        backgroundColor: {palette_array(len(src_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 13 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {src_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── 應徵裝置 Bar
  new Chart(document.getElementById('deviceBar'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(dev_labels)},
      datasets: [{{
        label: '應徵數',
        data: {js_values(dev_vals)},
        backgroundColor: {palette_array(len(dev_vals))},
        borderRadius: 6
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ title: {{ display: true, text: '應徵數' }} }}
      }}
    }}
  }});

  // ── 每小時應徵
  new Chart(document.getElementById('applyHourly'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(hour_labels)},
      datasets: [{{
        label: '平均應徵數',
        data: {js_values(hourly)},
        backgroundColor: {palette_array(24)},
        borderRadius: 4
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: '小時（台灣時區）' }} }},
        y: {{ title: {{ display: true, text: '平均應徵數' }} }}
      }}
    }}
  }});
</script>
""")

    parts.append(html_end(gen_at))
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 3：應徵轉換分析")
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
        print("[INFO] 讀取應徵 KPI...")
        kpi = _load_apply_kpi(date_from, date_to)
        print("[INFO] 讀取應徵來源...")
        source_dist = _load_apply_source(date_from, date_to)
        print("[INFO] 讀取每日趨勢...")
        daily = _load_apply_daily_trend(date_from, date_to)
        print("[INFO] 讀取轉換漏斗...")
        funnel = _load_funnel(date_from, date_to)
        print("[INFO] 讀取裝置分佈...")
        device = _load_apply_device(date_from, date_to)
        print("[INFO] 讀取每小時分佈...")
        hourly = _load_apply_hourly(date_from, date_to)
    else:
        print("[INFO] 查詢應徵 KPI...")
        kpi = query_apply_kpi(time_from, time_to)
        print("[INFO] 查詢應徵來源...")
        source_dist = query_apply_source(time_from, time_to)
        print("[INFO] 查詢每日趨勢...")
        daily = query_apply_daily_trend(time_from, time_to)
        print("[INFO] 查詢轉換漏斗...")
        funnel = query_funnel(time_from, time_to)
        print("[INFO] 查詢裝置分佈...")
        device = query_apply_device(time_from, time_to)
        print("[INFO] 查詢每小時分佈...")
        hourly = query_apply_hourly(time_from, time_to)

    gen_at = generated_now()
    html = generate_html(kpi, source_dist, daily, funnel, device, hourly,
                         time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
