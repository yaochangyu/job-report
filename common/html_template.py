"""
html_template.py
────────────────
HTML header / footer / CSS 共用模板。
"""

from common.es_client import ES_INDEX

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"

# ── 共用 CSS ─────────────────────────────────────────────────────────────────

COMMON_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
      background: #f0f2f5; color: #1a1a2e; min-height: 100vh;
    }
    header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff; padding: 36px 48px 28px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    header h1 { font-size: 1.8rem; font-weight: 700; }
    header p  { margin-top: 6px; font-size: 0.9rem; opacity: 0.65; }
    .badge {
      display: inline-block; margin-top: 12px;
      background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
      border-radius: 20px; padding: 4px 14px; font-size: 0.8rem;
    }
    main { max-width: 1200px; margin: 0 auto; padding: 36px 24px 60px; }
    .kpi-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; margin-bottom: 36px;
    }
    .kpi-card {
      background: #fff; border-radius: 14px; padding: 24px 20px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-top: 4px solid var(--accent);
    }
    .kpi-card .label { font-size: 0.78rem; color: #888; text-transform: uppercase; letter-spacing: 0.8px; }
    .kpi-card .value { font-size: 2rem; font-weight: 800; color: var(--accent); margin-top: 6px; }
    .kpi-card .sub   { font-size: 0.8rem; color: #aaa; margin-top: 4px; }
    .chart-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
      gap: 24px; margin-bottom: 28px;
    }
    .card {
      background: #fff; border-radius: 14px; padding: 28px 24px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    }
    .card h2 { font-size: 1rem; font-weight: 700; color: #333; margin-bottom: 4px; }
    .card .subtitle { font-size: 0.8rem; color: #999; margin-bottom: 20px; }
    .chart-wrap { position: relative; height: 320px; }
    .chart-wrap-tall { position: relative; height: 380px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    thead th {
      background: #f7f8fa; padding: 10px 14px; text-align: left;
      font-weight: 600; color: #555; border-bottom: 2px solid #e8e8e8;
    }
    tbody tr:nth-child(odd) { background: #fafafa; }
    tbody tr:hover { background: #f0f4ff; }
    tbody td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
    .rank { color: #bbb; font-weight: 700; font-size: 0.85rem; }
    .bar-cell { width: 160px; }
    .bar-bg { background: #eef0f4; border-radius: 4px; height: 8px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #4361ee, #7209b7); }
    .pct { color: #4361ee; font-weight: 700; }
    footer { text-align: center; font-size: 0.78rem; color: #bbb; padding: 24px 0 12px; }
"""


# ── 組合函式 ─────────────────────────────────────────────────────────────────

def html_start(title: str, time_from: str, time_to: str, generated_at: str) -> str:
    """產生 HTML 開頭：<!DOCTYPE> ~ <main> 前。"""
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <script src="{CHART_JS_CDN}"></script>
  <style>{COMMON_CSS}</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>資料來源：{ES_INDEX}（Elasticsearch） · 查詢區間：{time_from} ～ {time_to}</p>
  <span class="badge">產生時間：{generated_at}</span>
</header>
<main>
"""


def html_end(generated_at: str) -> str:
    """產生 HTML 結尾：</main> ~ </html>。"""
    return f"""
</main>
<footer>Generated {generated_at} · {ES_INDEX}</footer>
</body>
</html>"""


def kpi_card(label: str, value: str, sub: str, color: str) -> str:
    """產生單一 KPI 卡片 HTML。"""
    return f"""
    <div class="kpi-card" style="--accent:{color}">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      <div class="sub">{sub}</div>
    </div>"""


def chart_card(title: str, subtitle: str, canvas_id: str, tall: bool = False) -> str:
    """產生包含 canvas 的圖表卡片 HTML。"""
    wrap_class = "chart-wrap-tall" if tall else "chart-wrap"
    return f"""
  <div class="card">
    <h2>{title}</h2>
    <div class="subtitle">{subtitle}</div>
    <div class="{wrap_class}"><canvas id="{canvas_id}"></canvas></div>
  </div>"""


def table_card(title: str, subtitle: str, thead: str, tbody: str) -> str:
    """產生表格卡片 HTML。"""
    return f"""
  <div class="card" style="margin-bottom:24px">
    <h2>{title}</h2>
    <div class="subtitle">{subtitle}</div>
    <table>
      <thead>{thead}</thead>
      <tbody>{tbody}</tbody>
    </table>
  </div>"""
