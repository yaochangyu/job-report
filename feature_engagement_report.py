#!/usr/bin/env python3
"""
feature_engagement_report.py
─────────────────────────────
Dashboard 4：功能互動分析（Feature Engagement）
從 Elasticsearch 查詢 jobbank-web 的各功能模組使用數據，產生 HTML 圖表報告。

執行方式：
    uv run python feature_engagement_report.py
    uv run python feature_engagement_report.py --days 7
    uv run python feature_engagement_report.py --from 2026-04-01 --to 2026-04-10
    uv run python feature_engagement_report.py --output /tmp/report
"""

from pathlib import Path

from common.es_client import msearch, parse_args, resolve_time_range, generated_now
from common.chart_helpers import js_labels, js_values, palette_array, table_rows_ranked
from common.html_template import html_start, html_end, kpi_card, chart_card, table_card

OUTPUT_DIR = Path(__file__).parent / "output" / "feature-engagement"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}

EXPLORE_JOB_IDS = ["explore-jobs-organic", "explore-jobs-organic-corp"]
EXPLORE_CORP_IDS = [
    "explore-company-corp", "explore-company-job1", "explore-company-job2",
    "explore-company-job-more", "explore-company-manufacturing",
    "explore-company-service", "explore-company-next",
]
IDENTITY_IDS = [
    "identify-returning", "identify-student", "identify-worker",
    "identify-professional", "identify-senior", "identify-fresh", "identify-personal",
]
NEWS_IDS = ["news-card-1", "news-card-2", "news-card-3", "news-card-4",
            "news-workplace", "news-industry"]


# ── 查詢邏輯 ─────────────────────────────────────────────────────────────────

def query_explore_jobs(time_from: str, time_to: str) -> dict:
    """探索職缺：featureId 分佈 + categoryTab + identityType。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": EXPLORE_JOB_IDS}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 10}},
            "by_category_tab": {
                "terms": {
                    "script": {
                        "source": "doc.containsKey('metadata.categoryTab') && doc['metadata.categoryTab'].size() > 0 ? doc['metadata.categoryTab'].value : 'unknown'",
                        "lang": "painless",
                    },
                    "size": 20,
                }
            },
            "by_identity_type": {
                "terms": {
                    "script": {
                        "source": "doc.containsKey('metadata.identityType') && doc['metadata.identityType'].size() > 0 ? doc['metadata.identityType'].value : 'unknown'",
                        "lang": "painless",
                    },
                    "size": 20,
                }
            },
            "daily": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Taipei",
                    "min_doc_count": 0,
                },
                "aggs": {
                    "organic": {"filter": {"term": {"featureId": "explore-jobs-organic"}}},
                    "corp": {"filter": {"term": {"featureId": "explore-jobs-organic-corp"}}},
                },
            },
        },
    }
    r = msearch(body)
    agg = r["aggregations"]
    return {
        "features": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_feature"]["buckets"]],
        "category_tabs": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_category_tab"]["buckets"]],
        "identity_types": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_identity_type"]["buckets"]],
        "daily": [
            {
                "date": b["key_as_string"][:10],
                "organic": b["organic"]["doc_count"],
                "corp": b["corp"]["doc_count"],
            }
            for b in agg["daily"]["buckets"]
        ],
    }


def query_explore_corp(time_from: str, time_to: str) -> dict:
    """探索企業：featureId 分佈 + industryTab。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": EXPLORE_CORP_IDS}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 10}},
            "by_industry_tab": {
                "terms": {
                    "script": {
                        "source": "doc.containsKey('metadata.industryTab') && doc['metadata.industryTab'].size() > 0 ? doc['metadata.industryTab'].value : 'unknown'",
                        "lang": "painless",
                    },
                    "size": 20,
                }
            },
        },
    }
    r = msearch(body)
    agg = r["aggregations"]
    return {
        "features": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_feature"]["buckets"]],
        "industry_tabs": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_industry_tab"]["buckets"]],
    }


def query_identity(time_from: str, time_to: str) -> dict:
    """身份辨識分析。"""
    all_identity_ids = IDENTITY_IDS + [f"{i}-tab" for i in IDENTITY_IDS]
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"bool": {"should": [
                {"terms": {"featureId": IDENTITY_IDS}},
                {"prefix": {"featureId": "identify-"}},
            ]}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 30}},
        },
    }
    r = msearch(body)
    buckets = r["aggregations"]["by_feature"]["buckets"]
    # 只取主身份（不含 -tab-N）
    main_ids = {b["key"]: b["doc_count"] for b in buckets if b["key"] in IDENTITY_IDS}
    return {
        "main": [{"name": k.replace("identify-", ""), "count": v}
                 for k, v in sorted(main_ids.items(), key=lambda x: -x[1])],
        "all_buckets": [{"name": b["key"], "count": b["doc_count"]} for b in buckets],
    }


def query_news(time_from: str, time_to: str) -> list[dict]:
    """新聞互動分析。"""
    body = {
        "size": 0,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"terms": {"featureId": NEWS_IDS}},
        ]}},
        "aggs": {
            "by_feature": {"terms": {"field": "featureId", "size": 10}},
            "by_category": {
                "terms": {
                    "script": {
                        "source": "doc.containsKey('metadata.categoryTab') && doc['metadata.categoryTab'].size() > 0 ? doc['metadata.categoryTab'].value : 'unknown'",
                        "lang": "painless",
                    },
                    "size": 10,
                }
            },
        },
    }
    r = msearch(body)
    agg = r["aggregations"]
    return {
        "features": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_feature"]["buckets"]],
        "categories": [{"name": b["key"], "count": b["doc_count"]} for b in agg["by_category"]["buckets"]],
    }


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

def generate_html(
    explore_jobs: dict,
    explore_corp: dict,
    identity: dict,
    news: dict,
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    parts = []
    parts.append(html_start("功能互動分析 — Feature Engagement", time_from, time_to, gen_at))

    # ── KPI
    ej_total = sum(d["count"] for d in explore_jobs["features"])
    ec_total = sum(d["count"] for d in explore_corp["features"])
    id_total = sum(d["count"] for d in identity["main"])
    news_total = sum(d["count"] for d in news["features"])

    parts.append('  <div class="kpi-grid">')
    parts.append(kpi_card("探索職缺", f"{ej_total:,}", "organic + corp", "#4361ee"))
    parts.append(kpi_card("探索企業", f"{ec_total:,}", "各企業探索入口", "#7209b7"))
    parts.append(kpi_card("身份辨識", f"{id_total:,}", "7 種身份類型", "#f72585"))
    parts.append(kpi_card("新聞互動", f"{news_total:,}", "news-card 點擊", "#06d6a0"))
    parts.append('  </div>')

    # ── 探索職缺
    cat_tabs = explore_jobs["category_tabs"]
    cat_names = [d["name"] for d in cat_tabs]
    cat_vals = [d["count"] for d in cat_tabs]
    cat_total = sum(cat_vals)

    id_types = explore_jobs["identity_types"]
    idt_names = [d["name"] for d in id_types]
    idt_vals = [d["count"] for d in id_types]
    idt_total = sum(idt_vals)

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("探索職缺 — categoryTab 分佈", "各 Tab 點擊分佈", "expJobCatTab"))
    parts.append(chart_card("探索職缺 — identityType 分佈", "使用者身份分佈", "expJobIdentity"))
    parts.append('  </div>')

    # ── 探索職缺每日趨勢
    ej_dates = [d["date"] for d in explore_jobs["daily"]]
    ej_organic = [d["organic"] for d in explore_jobs["daily"]]
    ej_corp = [d["corp"] for d in explore_jobs["daily"]]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("探索職缺每日趨勢", "organic vs corp-organic", "expJobDaily"))
    parts.append(chart_card("探索企業 — featureId 分佈", "各企業探索入口使用量", "expCorpFeature"))
    parts.append('  </div>')

    # ── 探索企業 industryTab
    ind_tabs = explore_corp["industry_tabs"]
    ind_names = [d["name"] for d in ind_tabs]
    ind_vals = [d["count"] for d in ind_tabs]
    ind_total = sum(ind_vals)

    ec_feat_names = [d["name"].replace("explore-company-", "") for d in explore_corp["features"]]
    ec_feat_vals = [d["count"] for d in explore_corp["features"]]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("探索企業 — industryTab 分佈", "各產業 Tab 點擊", "expCorpIndustry"))
    parts.append(chart_card("身份辨識 — 主身份分佈", "各身份入口點擊數", "identityMain"))
    parts.append('  </div>')

    # ── 新聞互動
    news_feat_names = [d["name"] for d in news["features"]]
    news_feat_vals = [d["count"] for d in news["features"]]
    news_cat_names = [d["name"] for d in news["categories"]]
    news_cat_vals = [d["count"] for d in news["categories"]]

    parts.append('  <div class="chart-grid">')
    parts.append(chart_card("新聞卡片點擊", "各位置點擊量", "newsFeature"))
    parts.append(chart_card("新聞分類分佈", "各新聞類別點擊數", "newsCat"))
    parts.append('  </div>')

    # ── identity table
    id_main = identity["main"]
    id_main_total = sum(d["count"] for d in id_main)
    id_thead = "<tr><th>#</th><th>身份</th><th>事件數</th><th>視覺</th><th>佔比</th></tr>"
    id_tbody = table_rows_ranked(id_main, "name", "count", id_main_total)
    parts.append(table_card("身份辨識詳細數據", f"共 {id_main_total:,} 筆", id_thead, id_tbody))

    # ── news table
    news_thead = "<tr><th>#</th><th>featureId</th><th>點擊數</th><th>視覺</th><th>佔比</th></tr>"
    news_tbody = table_rows_ranked(news["features"], "name", "count", news_total)
    parts.append(table_card("新聞互動詳細數據", f"共 {news_total:,} 筆", news_thead, news_tbody))

    id_main_names = [d["name"] for d in id_main]
    id_main_vals = [d["count"] for d in id_main]

    parts.append(f"""
<script>
  // ── 探索職缺 categoryTab Doughnut
  new Chart(document.getElementById('expJobCatTab'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(cat_names)},
      datasets: [{{
        data: {js_values(cat_vals)},
        backgroundColor: {palette_array(len(cat_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 8 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {cat_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}}（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── 探索職缺 identityType
  new Chart(document.getElementById('expJobIdentity'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(idt_names)},
      datasets: [{{
        data: {js_values(idt_vals)},
        backgroundColor: {palette_array(len(idt_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 8 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const t = {idt_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}}（${{(ctx.parsed/t*100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  // ── 探索職缺每日趨勢
  new Chart(document.getElementById('expJobDaily'), {{
    type: 'line',
    data: {{
      labels: {js_labels(ej_dates)},
      datasets: [
        {{
          label: 'explore-jobs-organic',
          data: {js_values(ej_organic)},
          borderColor: '#4361ee', backgroundColor: 'rgba(67,97,238,0.1)',
          fill: true, tension: 0.3
        }},
        {{
          label: 'explore-jobs-organic-corp',
          data: {js_values(ej_corp)},
          borderColor: '#f72585', backgroundColor: 'rgba(247,37,133,0.08)',
          fill: true, tension: 0.3
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{ y: {{ title: {{ display: true, text: 'Click 數' }} }} }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});

  // ── 探索企業 featureId Bar
  new Chart(document.getElementById('expCorpFeature'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(ec_feat_names)},
      datasets: [{{
        label: '事件數',
        data: {js_values(ec_feat_vals)},
        backgroundColor: {palette_array(len(ec_feat_vals))},
        borderRadius: 6
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ title: {{ display: true, text: '事件數' }} }}
      }}
    }}
  }});

  // ── 探索企業 industryTab
  new Chart(document.getElementById('expCorpIndustry'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(ind_names)},
      datasets: [{{
        label: '點擊數',
        data: {js_values(ind_vals)},
        backgroundColor: {palette_array(len(ind_vals))},
        borderRadius: 4
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: '點擊數' }} }},
        y: {{ grid: {{ display: false }} }}
      }}
    }}
  }});

  // ── 身份辨識 Bar
  new Chart(document.getElementById('identityMain'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(id_main_names)},
      datasets: [{{
        label: '點擊數',
        data: {js_values(id_main_vals)},
        backgroundColor: {palette_array(len(id_main_vals))},
        borderRadius: 6
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ title: {{ display: true, text: '點擊數' }} }}
      }}
    }}
  }});

  // ── 新聞卡片 Bar
  new Chart(document.getElementById('newsFeature'), {{
    type: 'bar',
    data: {{
      labels: {js_labels(news_feat_names)},
      datasets: [{{
        label: '點擊數',
        data: {js_values(news_feat_vals)},
        backgroundColor: {palette_array(len(news_feat_vals))},
        borderRadius: 6
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ title: {{ display: true, text: '點擊數' }} }}
      }}
    }}
  }});

  // ── 新聞分類 Doughnut
  new Chart(document.getElementById('newsCat'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels(news_cat_names)},
      datasets: [{{
        data: {js_values(news_cat_vals)},
        backgroundColor: {palette_array(len(news_cat_vals))},
        borderWidth: 2, borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 13 }}, padding: 10 }} }}
      }}
    }}
  }});
</script>
""")

    parts.append(html_end(gen_at))
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 4：功能互動分析")
    time_from, time_to = resolve_time_range(args)
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 查詢區間：{time_from} ～ {time_to}")
    print(f"[INFO] 輸出目錄：{output_dir}")

    print("[INFO] 查詢探索職缺...")
    explore_jobs = query_explore_jobs(time_from, time_to)

    print("[INFO] 查詢探索企業...")
    explore_corp = query_explore_corp(time_from, time_to)

    print("[INFO] 查詢身份辨識...")
    identity = query_identity(time_from, time_to)

    print("[INFO] 查詢新聞互動...")
    news = query_news(time_from, time_to)

    gen_at = generated_now()
    html = generate_html(explore_jobs, explore_corp, identity, news,
                         time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
