#!/usr/bin/env python3
"""
category_tab_report.py
─────────────────────
從 Elasticsearch（透過 Grafana Proxy）查詢 metadata.categoryTab 分佈，
並產生 HTML 圖表報告。

執行方式：
    python3 category_tab_report.py
    python3 category_tab_report.py --days 1
    python3 category_tab_report.py --from "2026-04-01" --to "2026-04-10"
    python3 category_tab_report.py --output /tmp/report
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 設定 ──────────────────────────────────────────────────────────────────────
GRAFANA_URL      = "https://grafana.web.internal"
GRAFANA_USER     = "esodev"
GRAFANA_PASSWORD = "2KqHmF6x"
DATASOURCE_UID   = "af55vm1ovng1sb"
ES_INDEX         = "operation-logs"
OUTPUT_DIR = Path(__file__).parent

EXPLORE_FEATURES = [
    "explore-jobs-organic",
    "explore-jobs-organic-corp",
]

# ── Grafana _msearch ──────────────────────────────────────────────────────────

def msearch(index: str, body: dict) -> dict:
    url = f"{GRAFANA_URL}/api/datasources/proxy/uid/{DATASOURCE_UID}/_msearch"
    ndjson = (
        json.dumps({"index": index}) + "\n" +
        json.dumps(body) + "\n"
    ).encode("utf-8")

    token = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=ndjson,
        headers={
            "Content-Type": "application/x-ndjson",
            "Authorization": f"Basic {token}",
        },
        method="POST",
    )

    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())


# ── 查詢邏輯 ──────────────────────────────────────────────────────────────────

def query_category_tab(time_from: str, time_to: str) -> dict[str, list[dict]]:
    """
    回傳 { featureId: [ {tab, count}, ... ] }
    """
    body = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
                    {"terms": {"featureId": EXPLORE_FEATURES}},
                ]
            }
        },
        "aggs": {
            "by_feature": {
                "terms": {"field": "featureId", "size": 20},
                "aggs": {
                    "category_tab": {
                        "terms": {
                            "script": {
                                "source": (
                                    "def meta = params._source.get('metadata'); "
                                    "if (meta != null) { return meta.get('categoryTab'); } "
                                    "return null;"
                                ),
                                "lang": "painless",
                            },
                            "size": 50,
                            "missing": "(無)",
                        }
                    }
                },
            }
        },
    }

    resp = msearch(ES_INDEX, body)
    r = resp["responses"][0]
    if "error" in r:
        print(f"[ERROR] ES 回傳錯誤：{r['error']['reason']}", file=sys.stderr)
        sys.exit(1)

    result: dict[str, list[dict]] = {}
    for feature_bucket in r["aggregations"]["by_feature"]["buckets"]:
        feature_id = feature_bucket["key"]
        tabs = [
            {"tab": b["key"], "count": b["doc_count"]}
            for b in feature_bucket["category_tab"]["buckets"]
            if b["key"] != "(無)"
        ]
        tabs.sort(key=lambda x: x["count"], reverse=True)
        result[feature_id] = tabs

    # 確保 EXPLORE_FEATURES 順序一致
    return {fid: result.get(fid, []) for fid in EXPLORE_FEATURES}


def query_total_docs(time_from: str, time_to: str) -> int:
    body = {
        "size": 0,
        "query": {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
    }
    resp = msearch(ES_INDEX, body)
    return resp["responses"][0]["hits"]["total"]["value"]


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

PALETTE = [
    "#4361ee","#7209b7","#f72585","#06d6a0","#fb8500",
    "#118ab2","#3a86ff","#8338ec","#ff006e","#ffbe0b",
    "#80b918","#00b4d8","#e63946","#457b9d",
]


def _js_array(data: list[dict], key: str) -> str:
    vals = [json.dumps(d[key], ensure_ascii=False) for d in data]
    return "[" + ", ".join(vals) + "]"


def _palette_array(n: int) -> str:
    colors = [PALETTE[i % len(PALETTE)] for i in range(n)]
    return "[" + ", ".join(f'"{c}"' for c in colors) + "]"


def _table_rows(data: list[dict], total: int) -> str:
    rows = []
    for i, d in enumerate(data, 1):
        pct = d["count"] / total * 100 if total else 0
        rows.append(f"""
        <tr>
          <td class="rank">{i}</td>
          <td>{d['tab']}</td>
          <td>{d['count']:,}</td>
          <td class="bar-cell">
            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>
          </td>
          <td class="pct">{pct:.1f}%</td>
        </tr>""")
    return "".join(rows)


def generate_html(
    data: dict[str, list[dict]],
    time_from: str,
    time_to: str,
    generated_at: str,
) -> str:
    organic      = data.get("explore-jobs-organic", [])
    corp         = data.get("explore-jobs-organic-corp", [])
    total_org    = sum(d["count"] for d in organic)
    total_corp   = sum(d["count"] for d in corp)
    ai_org       = next((d["count"] for d in organic if d["tab"] == "AI 推薦"), 0)
    ai_corp      = next((d["count"] for d in corp    if d["tab"] == "AI 推薦"), 0)
    ai_org_pct   = f"{ai_org / total_org * 100:.1f}" if total_org else "0"
    ai_corp_pct  = f"{ai_corp / total_corp * 100:.1f}" if total_corp else "0"
    tab_kinds    = len({d["tab"] for d in organic})
    other_org    = total_org - ai_org
    other_corp   = total_corp - ai_corp

    organic_labels = _js_array(organic, "tab")
    organic_counts = _js_array(organic, "count")
    organic_colors = _palette_array(len(organic))

    corp_labels = _js_array(corp, "tab")
    corp_counts = _js_array(corp, "count")
    corp_colors = _palette_array(len(corp))

    table_rows = _table_rows(organic, total_org)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>探索職缺 — CategoryTab 分析報告</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
      background: #f0f2f5; color: #1a1a2e; min-height: 100vh;
    }}
    header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff; padding: 36px 48px 28px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    header h1 {{ font-size: 1.8rem; font-weight: 700; }}
    header p  {{ margin-top: 6px; font-size: 0.9rem; opacity: 0.65; }}
    .badge {{
      display: inline-block; margin-top: 12px;
      background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
      border-radius: 20px; padding: 4px 14px; font-size: 0.8rem;
    }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 36px 24px 60px; }}
    .kpi-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; margin-bottom: 36px;
    }}
    .kpi-card {{
      background: #fff; border-radius: 14px; padding: 24px 20px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-top: 4px solid var(--accent);
    }}
    .kpi-card .label {{ font-size: 0.78rem; color: #888; text-transform: uppercase; letter-spacing: 0.8px; }}
    .kpi-card .value {{ font-size: 2rem; font-weight: 800; color: var(--accent); margin-top: 6px; }}
    .kpi-card .sub   {{ font-size: 0.8rem; color: #aaa; margin-top: 4px; }}
    .chart-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
      gap: 24px; margin-bottom: 28px;
    }}
    .card {{
      background: #fff; border-radius: 14px; padding: 28px 24px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    }}
    .card h2 {{ font-size: 1rem; font-weight: 700; color: #333; margin-bottom: 4px; }}
    .card .subtitle {{ font-size: 0.8rem; color: #999; margin-bottom: 20px; }}
    .chart-wrap {{ position: relative; height: 320px; }}
    .chart-wrap-tall {{ position: relative; height: 380px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    thead th {{
      background: #f7f8fa; padding: 10px 14px; text-align: left;
      font-weight: 600; color: #555; border-bottom: 2px solid #e8e8e8;
    }}
    tbody tr:nth-child(odd) {{ background: #fafafa; }}
    tbody tr:hover {{ background: #f0f4ff; }}
    tbody td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }}
    .rank {{ color: #bbb; font-weight: 700; font-size: 0.85rem; }}
    .bar-cell {{ width: 160px; }}
    .bar-bg {{ background: #eef0f4; border-radius: 4px; height: 8px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 4px; background: linear-gradient(90deg, #4361ee, #7209b7); }}
    .pct {{ color: #4361ee; font-weight: 700; }}
    footer {{ text-align: center; font-size: 0.78rem; color: #bbb; padding: 24px 0 12px; }}
  </style>
</head>
<body>
<header>
  <h1>🔍 探索職缺 — CategoryTab 點擊分析</h1>
  <p>資料來源：{ES_INDEX}（Elasticsearch） · 查詢區間：{time_from} ～ {time_to}</p>
  <span class="badge">⏱ 產生時間：{generated_at}</span>
</header>
<main>
  <div class="kpi-grid">
    <div class="kpi-card" style="--accent:#4361ee">
      <div class="label">explore-jobs-organic 總點擊</div>
      <div class="value">{total_org:,}</div>
      <div class="sub">一般求職者探索頁</div>
    </div>
    <div class="kpi-card" style="--accent:#7209b7">
      <div class="label">explore-jobs-organic-corp 總點擊</div>
      <div class="value">{total_corp:,}</div>
      <div class="sub">企業端探索頁</div>
    </div>
    <div class="kpi-card" style="--accent:#f72585">
      <div class="label">AI 推薦佔比（一般）</div>
      <div class="value">{ai_org_pct}%</div>
      <div class="sub">{ai_org:,} / {total_org:,} 次</div>
    </div>
    <div class="kpi-card" style="--accent:#06d6a0">
      <div class="label">AI 推薦佔比（企業端）</div>
      <div class="value">{ai_corp_pct}%</div>
      <div class="sub">{ai_corp:,} / {total_corp:,} 次</div>
    </div>
    <div class="kpi-card" style="--accent:#fb8500">
      <div class="label">categoryTab 種類數</div>
      <div class="value">{tab_kinds}</div>
      <div class="sub">一般探索頁共 {tab_kinds} 種 Tab</div>
    </div>
  </div>

  <div class="chart-grid">
    <div class="card">
      <h2>explore-jobs-organic — CategoryTab 分佈</h2>
      <div class="subtitle">一般求職者（Doughnut）</div>
      <div class="chart-wrap"><canvas id="donut1"></canvas></div>
    </div>
    <div class="card">
      <h2>explore-jobs-organic-corp — CategoryTab 分佈</h2>
      <div class="subtitle">企業端（Doughnut）</div>
      <div class="chart-wrap"><canvas id="donut2"></canvas></div>
    </div>
  </div>

  <div class="chart-grid">
    <div class="card">
      <h2>一般求職者 — 各 Tab 點擊次數</h2>
      <div class="subtitle">explore-jobs-organic（橫向 Bar）</div>
      <div class="chart-wrap-tall"><canvas id="bar1"></canvas></div>
    </div>
    <div class="card">
      <h2>AI 推薦 佔比比較</h2>
      <div class="subtitle">一般 vs 企業端（堆疊 Bar）</div>
      <div class="chart-wrap"><canvas id="bar2"></canvas></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:24px">
    <h2>詳細數據 — explore-jobs-organic</h2>
    <div class="subtitle">各 CategoryTab 點擊次數與比例</div>
    <table>
      <thead>
        <tr><th>#</th><th>CategoryTab</th><th>點擊次數</th><th class="bar-cell">佔比</th><th>佔比 %</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</main>
<footer>Generated {generated_at} · {ES_INDEX} · explore-jobs-organic</footer>

<script>
  const totalOrg  = {total_org};
  const totalCorp = {total_corp};
  const palette   = {json.dumps(PALETTE)};

  new Chart(document.getElementById('donut1'), {{
    type: 'doughnut',
    data: {{
      labels: {organic_labels},
      datasets: [{{ data: {organic_counts}, backgroundColor: {organic_colors}, borderWidth: 2, borderColor: '#fff' }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/totalOrg*100).toFixed(1)}}%）` }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('donut2'), {{
    type: 'doughnut',
    data: {{
      labels: {corp_labels},
      datasets: [{{ data: {corp_counts}, backgroundColor: {corp_colors}, borderWidth: 2, borderColor: '#fff' }}]
    }},
    options: {{
      cutout: '62%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 10 }} }},
        tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}} 次（${{(ctx.parsed/totalCorp*100).toFixed(1)}}%）` }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('bar1'), {{
    type: 'bar',
    data: {{
      labels: {organic_labels},
      datasets: [{{ label: '點擊次數', data: {organic_counts}, backgroundColor: {organic_colors}, borderRadius: 6, borderSkipped: false }}]
    }},
    options: {{
      indexAxis: 'y',
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.parsed.x.toLocaleString()}} 次（${{(ctx.parsed.x/totalOrg*100).toFixed(1)}}%）` }} }}
      }},
      scales: {{
        x: {{ grid: {{ color: '#f0f0f0' }} }},
        y: {{ ticks: {{ font: {{ size: 12 }} }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('bar2'), {{
    type: 'bar',
    data: {{
      labels: ['explore-jobs-organic\\n（一般）', 'explore-jobs-organic-corp\\n（企業端）'],
      datasets: [
        {{ label: 'AI 推薦', data: [{ai_org}, {ai_corp}], backgroundColor: ['#4361ee','#7209b7'], borderRadius: 8, borderSkipped: false }},
        {{ label: '其他 Tab', data: [{other_org}, {other_corp}], backgroundColor: ['rgba(67,97,238,0.2)','rgba(114,9,183,0.2)'], borderRadius: 8, borderSkipped: false }}
      ]
    }},
    options: {{
      plugins: {{
        legend: {{ position: 'bottom' }},
        tooltip: {{
          callbacks: {{
            label: ctx => {{
              const t = [totalOrg, totalCorp][ctx.dataIndex];
              return ` ${{ctx.dataset.label}}：${{ctx.parsed.y.toLocaleString()}} 次（${{(ctx.parsed.y/t*100).toFixed(1)}}%）`;
            }}
          }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        y: {{ grid: {{ color: '#f0f0f0' }} }}
      }}
    }}
  }});
</script>
</body>
</html>"""


# ── 主程式 ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="產生 metadata.categoryTab 分析報告")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days",  type=int, default=None, help="查詢近 N 天（預設：當日）")
    group.add_argument("--from",  dest="time_from", default=None, help="起始時間，例如 2026-04-01")
    parser.add_argument("--to",   dest="time_to",   default=None, help="結束時間，例如 2026-04-10（搭配 --from 使用）")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help=f"輸出目錄（預設：{OUTPUT_DIR}）")
    return parser.parse_args()


def resolve_time_range(args: argparse.Namespace) -> tuple[str, str]:
    if args.time_from:
        time_from = args.time_from if "T" in args.time_from else args.time_from + "T00:00:00Z"
        time_to   = (args.time_to + "T23:59:59Z") if args.time_to else "now"
    elif args.days:
        time_from = f"now-{args.days}d"
        time_to   = "now"
    else:
        # 預設：當日 00:00 ～ now
        today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
        time_from = today + "T00:00:00+08:00"
        time_to   = "now"
    return time_from, time_to


def main() -> None:
    args = parse_args()
    time_from, time_to = resolve_time_range(args)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 查詢區間：{time_from} ～ {time_to}")
    print(f"[INFO] 輸出目錄：{output_dir}")

    print("[INFO] 查詢 categoryTab 分佈...")
    data = query_category_tab(time_from, time_to)

    for fid, tabs in data.items():
        total = sum(t["count"] for t in tabs)
        print(f"\n  {fid}（共 {total:,} 次）")
        for t in tabs:
            pct = t["count"] / total * 100 if total else 0
            print(f"    {t['tab']:12s}  {t['count']:6,}  ({pct:.1f}%)")

    generated_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +08:00")
    html = generate_html(data, time_from, time_to, generated_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
