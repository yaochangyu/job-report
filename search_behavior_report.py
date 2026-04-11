#!/usr/bin/env python3
"""
search_behavior_report.py
─────────────────────────
Dashboard 2：搜尋行為分析（Search Behavior）
從 Elasticsearch 查詢 jobbank-web 的搜尋行為數據，產生 HTML 圖表報告。

執行方式：
    uv run python search_behavior_report.py
    uv run python search_behavior_report.py --days 7
    uv run python search_behavior_report.py --from 2026-04-01 --to 2026-04-10
    uv run python search_behavior_report.py --output /tmp/report
    uv run python search_behavior_report.py --from 2026-04-01 --to 2026-04-10 --from-store
"""

from datetime import datetime
from pathlib import Path

from common.es_client import msearch, parse_args, resolve_time_range, generated_now, TW
from common.chart_helpers import js_labels, js_values, palette_array, table_rows_ranked
from common.html_template import html_start, html_end, kpi_card, chart_card, table_card
from common.store import init_db, load_daily_range

OUTPUT_DIR = Path(__file__).parent / "output" / "search-behavior"
REPORT = "search-behavior"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}

# ── 搜尋 featureId 分類 ───────────────────────────────────────────────────────

GENERAL_SEARCH_IDS = ["search-general-keyword", "search-general-submit", "search-general"]
AI_SEARCH_IDS = ["search-ai-keyword", "search-ai-submit", "search-ai",
                 "search-ai-voice-input", "search-ai-chat-mode"]
QUICK_FILTER_IDS = ["T-job-location", "T-job-category"]
SEARCH_PAGE_IDS = ["search-job-page", "search-corp-page", "search-gig-page", "search-intern-page"]


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_search_overview(time_from: str, time_to: str) -> dict:
    """各搜尋類型總量。"""
    all_ids = SEARCH_PAGE_IDS + GENERAL_SEARCH_IDS + AI_SEARCH_IDS + QUICK_FILTER_IDS
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": all_ids}},
        ]}},
        "aggs": {
            "by_feature": {
                "terms": {"field": "featureId", "size": 50}
            }
        },
    }
    r = msearch(body)
    counts = {b["key"]: b["doc_count"] for b in r["aggregations"]["by_feature"]["buckets"]}

    search_page_total = sum(counts.get(f, 0) for f in SEARCH_PAGE_IDS)
    general_total = sum(counts.get(f, 0) for f in GENERAL_SEARCH_IDS)
    ai_total = sum(counts.get(f, 0) for f in AI_SEARCH_IDS)
    quick_total = sum(counts.get(f, 0) for f in QUICK_FILTER_IDS)

    return {
        "counts": counts,
        "search_page_total": search_page_total,
        "general_total": general_total,
        "ai_total": ai_total,
        "quick_total": quick_total,
    }


def query_daily_search_trend(time_from: str, time_to: str) -> list[dict]:
    """每日 AI 搜尋 vs 一般搜尋趨勢。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": GENERAL_SEARCH_IDS + AI_SEARCH_IDS}},
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
                    "general": {"filter": {"terms": {"featureId": GENERAL_SEARCH_IDS}}},
                    "ai": {"filter": {"terms": {"featureId": AI_SEARCH_IDS}}},
                },
            }
        },
    }
    r = msearch(body)
    result = []
    for bucket in r["aggregations"]["daily"]["buckets"]:
        g = bucket["general"]["doc_count"]
        a = bucket["ai"]["doc_count"]
        total = g + a
        result.append({
            "date": bucket["key_as_string"][:10],
            "general": g,
            "ai": a,
            "ai_pct": round(a / total * 100, 1) if total else 0,
        })
    return result


def query_search_page_dist(time_from: str, time_to: str) -> list[dict]:
    """搜尋結果頁分佈（job/corp/gig/intern）。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": SEARCH_PAGE_IDS}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 10}}
        },
    }
    r = msearch(body)
    label_map = {
        "search-job-page": "正職",
        "search-corp-page": "企業",
        "search-gig-page": "兼差",
        "search-intern-page": "實習",
    }
    return [
        {"name": label_map.get(b["key"], b["key"]), "count": b["doc_count"]}
        for b in r["aggregations"]["by_feature"]["buckets"]
    ]


def query_ai_interaction(time_from: str, time_to: str) -> list[dict]:
    """AI 搜尋互動方式細分。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": AI_SEARCH_IDS}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 10}}
        },
    }
    r = msearch(body)
    label_map = {
        "search-ai-keyword": "AI 關鍵字",
        "search-ai-submit": "AI 送出",
        "search-ai": "AI 一般",
        "search-ai-voice-input": "語音輸入",
        "search-ai-chat-mode": "聊天模式",
    }
    return [
        {"name": label_map.get(b["key"], b["key"]), "count": b["doc_count"]}
        for b in r["aggregations"]["by_feature"]["buckets"]
    ]


def query_quick_filter(time_from: str, time_to: str) -> list[dict]:
    """快速篩選使用量。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": QUICK_FILTER_IDS}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 10}},
            "daily": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
                "aggs": {
                    "location": {"filter": {"term": {"featureId": "T-job-location"}}},
                    "category": {"filter": {"term": {"featureId": "T-job-category"}}},
                },
            },
        },
    }
    r = msearch(body)
    label_map = {
        "T-job-location": "地區篩選",
        "T-job-category": "職類篩選",
    }
    overview = [
        {"name": label_map.get(b["key"], b["key"]), "count": b["doc_count"]}
        for b in r["aggregations"]["by_feature"]["buckets"]
    ]
    daily = []
    for bucket in r["aggregations"]["daily"]["buckets"]:
        daily.append({
            "date": bucket["key_as_string"][:10],
            "location": bucket["location"]["doc_count"],
            "category": bucket["category"]["doc_count"],
        })
    return overview, daily


# ── Store 讀取與合併 ──────────────────────────────────────────────────────────

def _date_range(time_from: str, time_to: str) -> tuple[str, str]:
    """從時間字串取出 YYYY-MM-DD 日期區間。"""
    d_from = time_from[:10]
    d_to = time_to[:10] if time_to.lower() != "now" else datetime.now(TW).strftime("%Y-%m-%d")
    return d_from, d_to


def _load_search_overview(date_from: str, date_to: str) -> dict:
    rows = load_daily_range(date_from, date_to, REPORT, "query_search_overview")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_search_overview [{date_from}～{date_to}]")
    counts: dict = {}
    search_page_total = general_total = ai_total = quick_total = 0
    for r in rows:
        d = r["data"]
        for k, v in d["counts"].items():
            counts[k] = counts.get(k, 0) + v
        search_page_total += d["search_page_total"]
        general_total += d["general_total"]
        ai_total += d["ai_total"]
        quick_total += d["quick_total"]
    return {
        "counts": counts,
        "search_page_total": search_page_total,
        "general_total": general_total,
        "ai_total": ai_total,
        "quick_total": quick_total,
    }


def _load_daily_search_trend(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_daily_search_trend")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_daily_search_trend [{date_from}～{date_to}]")
    result = []
    for r in rows:
        result.extend(r["data"])
    return sorted(result, key=lambda x: x["date"])


def _load_search_page_dist(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_search_page_dist")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_search_page_dist [{date_from}～{date_to}]")
    totals: dict = {}
    for r in rows:
        for item in r["data"]:
            k = item["name"]
            totals[k] = totals.get(k, 0) + item["count"]
    return sorted([{"name": k, "count": v} for k, v in totals.items()], key=lambda x: -x["count"])


def _load_ai_interaction(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_ai_interaction")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_ai_interaction [{date_from}～{date_to}]")
    totals: dict = {}
    for r in rows:
        for item in r["data"]:
            k = item["name"]
            totals[k] = totals.get(k, 0) + item["count"]
    return sorted([{"name": k, "count": v} for k, v in totals.items()], key=lambda x: -x["count"])


def _load_quick_filter(date_from: str, date_to: str) -> tuple[list[dict], list[dict]]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_quick_filter")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_quick_filter [{date_from}～{date_to}]")
    overview_totals: dict = {}
    all_daily: list = []
    for r in rows:
        for item in r["data"][0]:
            k = item["name"]
            overview_totals[k] = overview_totals.get(k, 0) + item["count"]
        all_daily.extend(r["data"][1])
    overview = sorted(
        [{"name": k, "count": v} for k, v in overview_totals.items()],
        key=lambda x: -x["count"],
    )
    daily = sorted(all_daily, key=lambda x: x["date"])
    return overview, daily


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    overview: dict,
    daily_trend: list[dict],
    search_page_dist: list[dict],
    ai_interaction: list[dict],
    quick_overview: list[dict],
    quick_daily: list[dict],
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []
    parts.append(html_start("搜尋行為分析 — Search Behavior", time_from, time_to, gen_at))

    # ── KPI
    total_search = (overview["search_page_total"] + overview["general_total"] +
                    overview["ai_total"] + overview["quick_total"])
    ai_ratio = (overview["ai_total"] / (overview["ai_total"] + overview["general_total"]) * 100
                if (overview["ai_total"] + overview["general_total"]) else 0)

    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("搜尋相關事件", f"{total_search:,}", "含搜尋頁、互動與篩選", "#4361ee"))
    parts.append(kpi_card("搜尋結果頁瀏覽", f"{overview['search_page_total']:,}", "job/corp/gig/intern", "#118ab2"))
    parts.append(kpi_card("一般搜尋互動", f"{overview['general_total']:,}", "keyword/submit/general", "#7209b7"))
    parts.append(kpi_card("AI 搜尋互動", f"{overview['ai_total']:,}", f"AI 佔搜尋互動 {ai_ratio:.1f}%", "#f72585"))
    parts.append(kpi_card("快速篩選", f"{overview['quick_total']:,}", "地區 / 職類篩選", "#fb8500"))
    parts.append('  </div>')

    # ── 搜尋功能總覽 Horizontal Bar
    category_labels = ["搜尋結果頁（view）", "一般搜尋互動（click）", "AI 搜尋互動（click）", "快速篩選（click）"]
    category_values = [
        overview["search_page_total"],
        overview["general_total"],
        overview["ai_total"],
        overview["quick_total"],
    ]
    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("搜尋功能使用量總覽", "各搜尋類型事件數比較", "searchOverview"))
    parts.append('  </div>')

    # ── AI vs 一般搜尋每日趨勢
    trend_dates = [d["date"] for d in daily_trend]
    trend_general = [d["general"] for d in daily_trend]
    trend_ai = [d["ai"] for d in daily_trend]
    trend_ai_pct = [d["ai_pct"] for d in daily_trend]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("AI vs 一般搜尋每日趨勢", "click 數量 + AI 佔比（右 Y 軸）", "aiVsGeneralTrend"))
    parts.append(chart_card("搜尋結果頁分佈", "job / corp / gig / intern 佔比", "searchPageDist"))
    parts.append('  </div>')

    # ── AI 互動方式 + 快速篩選
    ai_names = [d["name"] for d in ai_interaction]
    ai_vals = [d["count"] for d in ai_interaction]
    ai_total = sum(ai_vals)

    quick_names = [d["name"] for d in quick_overview]
    quick_vals = [d["count"] for d in quick_overview]

    sp_names = [d["name"] for d in search_page_dist]
    sp_vals = [d["count"] for d in search_page_dist]
    sp_total = sum(sp_vals)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("AI 搜尋互動方式", "各 AI 功能點擊分佈", "aiInteraction"))
    parts.append(chart_card("快速篩選使用", "地區篩選 vs 職類篩選每日趨勢", "quickFilterTrend"))
    parts.append('  </div>')

    # ── featureId 詳細表格
    all_features = sorted(overview["counts"].items(), key=lambda x: -x[1])
    feat_total = sum(v for _, v in all_features)
    feat_thead = "<tr><th>#</th><th>featureId</th><th>事件數</th><th>佔比</th><th>類別</th></tr>"
    feat_tbody = ""

    def classify(fid: str) -> str:
        if fid in SEARCH_PAGE_IDS:
            return "搜尋結果頁"
        if fid in GENERAL_SEARCH_IDS:
            return "一般搜尋"
        if fid in AI_SEARCH_IDS:
            return "AI 搜尋"
        if fid in QUICK_FILTER_IDS:
            return "快速篩選"
        return "其他"

    for i, (fid, cnt) in enumerate(all_features, 1):
        pct = cnt / feat_total * 100 if feat_total else 0
        feat_tbody += (
            f'<tr><td class="rank">{i}</td><td>{fid}</td>'
            f'<td>{cnt:,}</td><td class="pct">{pct:.1f}%</td>'
            f'<td>{classify(fid)}</td></tr>'
        )
    parts.append(table_card("搜尋功能 featureId 詳細數據", f"共 {feat_total:,} 筆", feat_thead, feat_tbody))

    # ── quick filter daily
    qd_dates = [d["date"] for d in quick_daily]
    qd_location = [d["location"] for d in quick_daily]
    qd_category = [d["category"] for d in quick_daily]

    parts.append(f"""
<script>
  // ── 搜尋功能總覽 Horizontal Bar
  new Chart(document.getElementById('searchOverview'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(category_labels)},
      datasets: [{{
        label: '事件數',
        data: {js_values(category_values)},
        backgroundColor: {palette_array(4)},
        borderRadius: 6
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ color: '#f0f0f0' }}, title: {{ display: true, text: '事件數' }} }},
        y: {{ grid: {{ display: false }} }}
      }}
    }}
  }});

  // ── AI vs 一般搜尋每日趨勢
  new Chart(document.getElementById('aiVsGeneralTrend'), {{
    type: 'line',
    data: {{
      labels: {js_labels(trend_dates)},
      datasets: [
        {{
          label: '一般搜尋',
          data: {js_values(trend_general)},
          borderColor: '#7209b7', backgroundColor: 'rgba(114,9,183,0.08)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: 'AI 搜尋',
          data: {js_values(trend_ai)},
          borderColor: '#f72585', backgroundColor: 'rgba(247,37,133,0.08)',
          fill: true, tension: 0.3, yAxisID: 'y'
        }},
        {{
          label: 'AI 佔比 %',
          data: {js_values(trend_ai_pct)},
          borderColor: '#fb8500', borderDash: [6,3],
          fill: false, tension: 0.3, yAxisID: 'y1'
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y:  {{ position: 'left',  title: {{ display: true, text: 'Click 數' }} }},
        y1: {{ position: 'right', grid: {{ drawOnChartArea: false }},
               title: {{ display: true, text: 'AI 佔比 %' }}, min: 0, max: 100 }}
      }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});

  // ── 搜尋結果頁分佈 Doughnut
  new Chart(document.getElementById('searchPageDist'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(sp_names)},
      datasets: [{{
        data: {js_values(sp_vals)},
        backgroundColor: {palette_array(len(sp_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 13 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {sp_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── AI 搜尋互動方式
  new Chart(document.getElementById('aiInteraction'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(ai_names)},
      datasets: [{{
        data: {js_values(ai_vals)},
        backgroundColor: {palette_array(len(ai_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 13 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {ai_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── 快速篩選每日趨勢
  new Chart(document.getElementById('quickFilterTrend'), {{
    type: 'line',
    data: {{
      labels: {js_labels(qd_dates)},
      datasets: [
        {{
          label: '地區篩選',
          data: {js_values(qd_location)},
          borderColor: '#118ab2', backgroundColor: 'rgba(17,138,178,0.1)',
          fill: true, tension: 0.3
        }},
        {{
          label: '職類篩選',
          data: {js_values(qd_category)},
          borderColor: '#fb8500', backgroundColor: 'rgba(251,133,0,0.1)',
          fill: true, tension: 0.3
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y: {{ title: {{ display: true, text: 'Click 數' }} }}
      }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});
</script>
""")

    parts.append(html_end(gen_at))
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 2：搜尋行為分析")
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
        print("[INFO] 讀取搜尋功能總覽...")
        overview = _load_search_overview(date_from, date_to)
        print("[INFO] 讀取 AI vs 一般搜尋每日趨勢...")
        daily_trend = _load_daily_search_trend(date_from, date_to)
        print("[INFO] 讀取搜尋結果頁分佈...")
        search_page_dist = _load_search_page_dist(date_from, date_to)
        print("[INFO] 讀取 AI 搜尋互動方式...")
        ai_interaction = _load_ai_interaction(date_from, date_to)
        print("[INFO] 讀取快速篩選...")
        quick_overview, quick_daily = _load_quick_filter(date_from, date_to)
    else:
        print("[INFO] 查詢搜尋功能總覽...")
        overview = query_search_overview(time_from, time_to)
        print("[INFO] 查詢 AI vs 一般搜尋每日趨勢...")
        daily_trend = query_daily_search_trend(time_from, time_to)
        print("[INFO] 查詢搜尋結果頁分佈...")
        search_page_dist = query_search_page_dist(time_from, time_to)
        print("[INFO] 查詢 AI 搜尋互動方式...")
        ai_interaction = query_ai_interaction(time_from, time_to)
        print("[INFO] 查詢快速篩選...")
        quick_overview, quick_daily = query_quick_filter(time_from, time_to)

    gen_at = generated_now()
    html = generate_html(
        overview, daily_trend, search_page_dist, ai_interaction,
        quick_overview, quick_daily, time_from, time_to, gen_at,
    )

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
