#!/usr/bin/env python3
"""
page_navigation_report.py
──────────────────────────
Dashboard 7：頁面導航鏈路分析（Page Navigation Flow）
從 Elasticsearch 查詢 jobbank-web 的頁面間導航數據，產生 HTML 圖表報告。

執行方式：
    uv run python page_navigation_report.py
    uv run python page_navigation_report.py --days 7
    uv run python page_navigation_report.py --from 2026-04-01 --to 2026-04-10
    uv run python page_navigation_report.py --output /tmp/report
"""

from pathlib import Path

from common.es_client import msearch, parse_args, resolve_time_range, generated_now
from common.chart_helpers import js_labels, js_values, palette_array, table_rows_ranked
from common.html_template import html_start, html_end, kpi_card, chart_card, table_card

OUTPUT_DIR = Path(__file__).parent / "output" / "page-navigation"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_nav_pairs(time_from: str, time_to: str, size: int = 30) -> list[dict]:
    """previousPageName → pageName 轉換路徑排行（過濾空 previousPageName）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"exists": {"field": "previousPageName"}},
            {"bool": {"must_not": {"term": {"previousPageName": ""}}}},
        ]}},
        "aggs": {
            "by_prev": {
                "terms": {"field": "previousPageName", "size": 20},
                "aggs": {
                    "by_curr": {
                        "terms": {"field": "pageName", "size": 5}
                    }
                },
            }
        },
    }
    r = msearch(body)
    pairs = []
    for prev_b in r["aggregations"]["by_prev"]["buckets"]:
        prev = prev_b["key"]
        for curr_b in prev_b["by_curr"]["buckets"]:
            curr = curr_b["key"]
            pairs.append({
                "from": prev,
                "to": curr,
                "count": curr_b["doc_count"],
                "label": f"{prev} → {curr}",
            })
    # 按次數排序，取 Top size
    pairs.sort(key=lambda x: -x["count"])
    return pairs[:size]


def query_entry_pages(time_from: str, time_to: str) -> list[dict]:
    """初始進入頁面分佈（previousPageName 為空的事件）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"bool": {"should": [
                {"bool": {"must_not": {"exists": {"field": "previousPageName"}}}},
                {"term": {"previousPageName": ""}},
            ]}},
        ]}},
        "aggs": {
            "by_page": {"terms": {"field": "pageName", "size": 15}}
        },
    }
    r = msearch(body)
    return [
        {"name": b["key"], "count": b["doc_count"]}
        for b in r["aggregations"]["by_page"]["buckets"]
    ]


def query_page_sources(time_from: str, time_to: str) -> dict:
    """各頁面的 Top 來源（從哪來）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"exists": {"field": "previousPageName"}},
            {"bool": {"must_not": {"term": {"previousPageName": ""}}}},
        ]}},
        "aggs": {
            "by_page": {
                "terms": {"field": "pageName", "size": 10},
                "aggs": {
                    "top_sources": {
                        "terms": {"field": "previousPageName", "size": 5}
                    }
                },
            }
        },
    }
    r = msearch(body)
    result = {}
    for b in r["aggregations"]["by_page"]["buckets"]:
        result[b["key"]] = [
            {"name": s["key"], "count": s["doc_count"]}
            for s in b["top_sources"]["buckets"]
        ]
    return result


def query_page_destinations(time_from: str, time_to: str) -> dict:
    """各頁面的 Top 目標（往哪去）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"exists": {"field": "previousPageName"}},
            {"bool": {"must_not": {"term": {"previousPageName": ""}}}},
        ]}},
        "aggs": {
            "by_prev": {
                "terms": {"field": "previousPageName", "size": 10},
                "aggs": {
                    "top_dests": {
                        "terms": {"field": "pageName", "size": 5}
                    }
                },
            }
        },
    }
    r = msearch(body)
    result = {}
    for b in r["aggregations"]["by_prev"]["buckets"]:
        result[b["key"]] = [
            {"name": d["key"], "count": d["doc_count"]}
            for d in b["top_dests"]["buckets"]
        ]
    return result


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    nav_pairs: list[dict],
    entry_pages: list[dict],
    page_sources: dict,
    page_dests: dict,
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []
    parts.append(html_start("頁面導航鏈路分析 — Page Navigation Flow", time_from, time_to, gen_at))

    # ── KPI
    total_nav = sum(p["count"] for p in nav_pairs)
    entry_total = sum(p["count"] for p in entry_pages)

    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("導航轉換事件", f"{total_nav:,}", "Top 30 路徑合計", "#4361ee"))
    parts.append(kpi_card("初始進入事件", f"{entry_total:,}", "無 previousPageName", "#06d6a0"))
    parts.append(kpi_card("追蹤頁面數", f"{len(page_sources)}", "有導航記錄的頁面", "#7209b7"))
    parts.append('  </div>')

    # ── 初始進入頁面
    ep_names = [p["name"] for p in entry_pages]
    ep_vals = [p["count"] for p in entry_pages]
    ep_total = sum(ep_vals)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("初始進入頁面分佈", "無 previousPageName 的首次瀏覽分佈", "entryDist"))
    parts.append('  </div>')

    # ── Top 20 導航路徑 Bar
    top20_pairs = nav_pairs[:20]
    pair_labels = [p["label"] for p in top20_pairs]
    pair_vals = [p["count"] for p in top20_pairs]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("Top 20 頁面轉換路徑", "previousPageName → pageName 轉換次數", "navPairsBar", tall=True))
    parts.append('  </div>')

    # ── 各頁面 Top 來源 表格
    src_thead = "<tr><th>目標頁面</th><th>來源頁面</th><th>次數</th></tr>"
    src_tbody = ""
    for page, sources in list(page_sources.items())[:10]:
        for i, s in enumerate(sources):
            if i == 0:
                src_tbody += f'<tr><td rowspan="{len(sources)}" style="vertical-align:top;font-weight:600">{page}</td>'
            else:
                src_tbody += '<tr>'
            src_tbody += f'<td>{s["name"]}</td><td>{s["count"]:,}</td></tr>'
    parts.append(table_card("各頁面 Top 來源（從哪來）",
                             "每個頁面最常見的上一頁 Top 5", src_thead, src_tbody))

    # ── 各頁面 Top 目標 表格
    dst_thead = "<tr><th>來源頁面</th><th>目標頁面</th><th>次數</th></tr>"
    dst_tbody = ""
    for page, dests in list(page_dests.items())[:10]:
        for i, d in enumerate(dests):
            if i == 0:
                dst_tbody += f'<tr><td rowspan="{len(dests)}" style="vertical-align:top;font-weight:600">{page}</td>'
            else:
                dst_tbody += '<tr>'
            dst_tbody += f'<td>{d["name"]}</td><td>{d["count"]:,}</td></tr>'
    parts.append(table_card("各頁面 Top 目標（往哪去）",
                             "離開頁面後最常前往的下一頁 Top 5", dst_thead, dst_tbody))

    # ── 完整導航路徑表格
    pairs_thead = "<tr><th>#</th><th>上一頁</th><th>下一頁</th><th>次數</th></tr>"
    pairs_tbody = ""
    for i, p in enumerate(nav_pairs, 1):
        pairs_tbody += (
            f'<tr><td class="rank">{i}</td><td>{p["from"]}</td>'
            f'<td>{p["to"]}</td><td>{p["count"]:,}</td></tr>'
        )
    parts.append(table_card("完整頁面轉換路徑排行 Top 30",
                             "previousPageName → pageName 排行", pairs_thead, pairs_tbody))

    parts.append(f"""
<script>
  // ── 初始進入頁面 Doughnut
  new Chart(document.getElementById('entryDist'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(ep_names)},
      datasets: [{{
        data: {js_values(ep_vals)},
        backgroundColor: {palette_array(len(ep_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 8 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {ep_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}}（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── Top 20 導航路徑 Bar
  new Chart(document.getElementById('navPairsBar'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(pair_labels)},
      datasets: [{{
        label: '轉換次數',
        data: {js_values(pair_vals)},
        backgroundColor: {palette_array(len(pair_vals))},
        borderRadius: 4
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: '轉換次數' }} }},
        y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
      }}
    }}
  }});
</script>
""")

    parts.append(html_end(gen_at))
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 7：頁面導航鏈路分析")
    time_from, time_to = resolve_time_range(args)
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 查詢區間：{time_from} ～ {time_to}")
    print(f"[INFO] 輸出目錄：{output_dir}")

    print("[INFO] 查詢導航路徑排行...")
    nav_pairs = query_nav_pairs(time_from, time_to)

    print("[INFO] 查詢初始進入頁面...")
    entry_pages = query_entry_pages(time_from, time_to)

    print("[INFO] 查詢各頁面來源...")
    page_sources = query_page_sources(time_from, time_to)

    print("[INFO] 查詢各頁面目標...")
    page_dests = query_page_destinations(time_from, time_to)

    gen_at = generated_now()
    html = generate_html(nav_pairs, entry_pages, page_sources, page_dests,
                         time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
