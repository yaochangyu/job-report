#!/usr/bin/env python3
"""
page_ranking_report.py
──────────────────────
Dashboard 6：頁面流量排行（Page Ranking）
從 Elasticsearch 查詢 jobbank-web 各 featureId 的流量排行，產生 HTML 圖表報告。

執行方式：
    uv run python page_ranking_report.py
    uv run python page_ranking_report.py --days 7
    uv run python page_ranking_report.py --from 2026-04-01 --to 2026-04-10
    uv run python page_ranking_report.py --output /tmp/report
    uv run python page_ranking_report.py --from 2026-04-01 --to 2026-04-10 --from-store
"""

from datetime import datetime
from pathlib import Path

from common.es_client import msearch, parse_args, resolve_time_range, generated_now, TW
from common.chart_helpers import js_labels, js_values, palette_array, table_rows_ranked
from common.html_template import html_start, html_end, kpi_card, chart_card, table_card
from common.store import init_db, load_daily_range

OUTPUT_DIR = Path(__file__).parent / "output" / "page-ranking"
REPORT = "page-ranking"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}

# featureId 分類
CATEGORY_MAP = {
    "job-page": "頁面瀏覽",
    "search-job-page": "頁面瀏覽",
    "home-page": "頁面瀏覽",
    "job-pair-page": "頁面瀏覽",
    "job-preview-page": "頁面瀏覽",
    "corp-page": "頁面瀏覽",
    "corp-preview-new-page": "頁面瀏覽",
    "welcome-page": "頁面瀏覽",
    "search-corp-page": "頁面瀏覽",
    "search-gig-page": "頁面瀏覽",
    "search-intern-page": "頁面瀏覽",
    "apply-job": "應徵",
    "search-general-keyword": "搜尋",
    "search-general-submit": "搜尋",
    "search-general": "搜尋",
    "search-ai-keyword": "AI 搜尋",
    "search-ai-submit": "AI 搜尋",
    "search-ai": "AI 搜尋",
    "search-ai-voice-input": "AI 搜尋",
    "search-ai-chat-mode": "AI 搜尋",
    "T-job-location": "快速篩選",
    "T-job-category": "快速篩選",
    "explore-jobs-organic": "探索功能",
    "explore-jobs-organic-corp": "探索功能",
    "explore-company-corp": "探索功能",
    "explore-company-job1": "探索功能",
    "explore-company-job2": "探索功能",
    "explore-company-job-more": "探索功能",
    "explore-company-manufacturing": "探索功能",
    "explore-company-service": "探索功能",
    "explore-company-next": "探索功能",
    "identify-returning": "身份辨識",
    "identify-student": "身份辨識",
    "identify-worker": "身份辨識",
    "identify-professional": "身份辨識",
    "identify-senior": "身份辨識",
    "identify-fresh": "身份辨識",
    "identify-personal": "身份辨識",
    "news-card-1": "新聞",
    "news-card-2": "新聞",
    "news-card-3": "新聞",
    "news-card-4": "新聞",
    "news-workplace": "新聞",
    "news-industry": "新聞",
    "company-select-job": "企業互動",
}

CATEGORY_COLORS = {
    "頁面瀏覽": "#4361ee",
    "應徵": "#f72585",
    "搜尋": "#7209b7",
    "AI 搜尋": "#8338ec",
    "快速篩選": "#fb8500",
    "探索功能": "#06d6a0",
    "身份辨識": "#118ab2",
    "新聞": "#ffbe0b",
    "企業互動": "#80b918",
    "其他": "#888888",
}


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_feature_ranking(time_from: str, time_to: str) -> list[dict]:
    """各 featureId 的 view / click 數量。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
        ]}},
        "aggs": {
            "by_feature": {
                "terms": {"field": "featureId", "size": 100},
                "aggs": {
                    "views":  {"filter": {"term": {"eventType": "view"}}},
                    "clicks": {"filter": {"term": {"eventType": "click"}}},
                },
            }
        },
    }
    r = msearch(body)
    result = []
    for b in r["aggregations"]["by_feature"]["buckets"]:
        fid = b["key"]
        views = b["views"]["doc_count"]
        clicks = b["clicks"]["doc_count"]
        total = b["doc_count"]
        ctr = clicks / total * 100 if total else 0
        result.append({
            "featureId": fid,
            "total": total,
            "views": views,
            "clicks": clicks,
            "ctr": round(ctr, 2),
            "category": CATEGORY_MAP.get(fid, "其他"),
        })
    return sorted(result, key=lambda x: -x["total"])


def query_category_summary(features: list[dict]) -> list[dict]:
    """功能類別匯總。"""
    cat_totals: dict[str, int] = {}
    for f in features:
        cat = f["category"]
        cat_totals[cat] = cat_totals.get(cat, 0) + f["total"]
    return sorted(
        [{"name": k, "count": v} for k, v in cat_totals.items()],
        key=lambda x: -x["count"],
    )


# ── Store 讀取與合併 ──────────────────────────────────────────────────────────

def _date_range(time_from: str, time_to: str) -> tuple[str, str]:
    """從時間字串取出 YYYY-MM-DD 日期區間。"""
    d_from = time_from[:10]
    d_to = time_to[:10] if time_to.lower() != "now" else datetime.now(TW).strftime("%Y-%m-%d")
    return d_from, d_to


def _load_feature_ranking(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_feature_ranking")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_feature_ranking [{date_from}～{date_to}]")
    merged: dict = {}
    for r in rows:
        for item in r["data"]:
            fid = item["featureId"]
            if fid not in merged:
                merged[fid] = {"total": 0, "views": 0, "clicks": 0, "category": item["category"]}
            merged[fid]["total"] += item["total"]
            merged[fid]["views"] += item["views"]
            merged[fid]["clicks"] += item["clicks"]
    result = []
    for fid, d in merged.items():
        total = d["total"]
        clicks = d["clicks"]
        result.append({
            "featureId": fid,
            "total": total,
            "views": d["views"],
            "clicks": clicks,
            "ctr": round(clicks / total * 100, 2) if total else 0,
            "category": d["category"],
        })
    return sorted(result, key=lambda x: -x["total"])


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    features: list[dict],
    categories: list[dict],
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []
    parts.append(html_start("頁面流量排行 — Page Ranking", time_from, time_to, gen_at))

    total_events = sum(f["total"] for f in features)
    total_features = len(features)

    # ── KPI
    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("總事件數", f"{total_events:,}", "所有 featureId 合計", "#4361ee"))
    parts.append(kpi_card("功能數量", f"{total_features}", "不重複 featureId 數", "#7209b7"))
    if features:
        top1 = features[0]
        parts.append(kpi_card("Top 1 功能", top1["featureId"], f"{top1['total']:,} 次", "#f72585"))
    parts.append('  </div>')

    # ── Top 20 功能 Bar
    top20 = features[:20]
    t20_labels = [f["featureId"] for f in top20]
    t20_vals = [f["total"] for f in top20]
    t20_colors = [CATEGORY_COLORS.get(f["category"], "#888") for f in top20]

    # ── 類別佔比
    cat_names = [c["name"] for c in categories]
    cat_vals = [c["count"] for c in categories]
    cat_colors = [CATEGORY_COLORS.get(c["name"], "#888") for c in categories]
    cat_total = sum(cat_vals)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("Top 20 功能流量排行", "依總事件數排序（顏色代表類別）", "top20Bar", tall=True))
    parts.append(chart_card("功能類別佔比", "各功能類別事件數比例", "categoryPie"))
    parts.append('  </div>')

    # ── 完整功能表格
    feat_thead = "<tr><th>#</th><th>featureId</th><th>總計</th><th>View</th><th>Click</th><th>CTR</th><th>類別</th></tr>"
    feat_tbody = ""
    for i, f in enumerate(features, 1):
        feat_tbody += (
            f'<tr><td class="rank">{i}</td><td>{f["featureId"]}</td>'
            f'<td>{f["total"]:,}</td><td>{f["views"]:,}</td><td>{f["clicks"]:,}</td>'
            f'<td class="pct">{f["ctr"]:.2f}%</td><td>{f["category"]}</td></tr>'
        )
    parts.append(table_card("完整 featureId 排行", f"共 {total_features} 個功能 / {total_events:,} 筆事件",
                             feat_thead, feat_tbody))

    t20_color_str = "[" + ", ".join(f'"{c}"' for c in t20_colors) + "]"
    cat_color_str = "[" + ", ".join(f'"{c}"' for c in cat_colors) + "]"

    parts.append(f"""
<script>
  // ── Top 20 Bar (horizontal)
  new Chart(document.getElementById('top20Bar'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(t20_labels)},
      datasets: [{{
        label: '事件數',
        data: {js_values(t20_vals)},
        backgroundColor: {t20_color_str},
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

  // ── 功能類別 Doughnut
  new Chart(document.getElementById('categoryPie'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(cat_names)},
      datasets: [{{
        data: {js_values(cat_vals)},
        backgroundColor: {cat_color_str},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 13 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {cat_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}}（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
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
    args = parse_args("Dashboard 6：頁面流量排行")
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
        print("[INFO] 讀取功能排行...")
        features = _load_feature_ranking(date_from, date_to)
    else:
        print("[INFO] 查詢功能排行...")
        features = query_feature_ranking(time_from, time_to)

    print(f"  共 {len(features)} 個 featureId")

    categories = query_category_summary(features)

    gen_at = generated_now()
    html = generate_html(features, categories, time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
