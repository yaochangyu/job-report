#!/usr/bin/env python3
"""
click_heatmap_report.py
────────────────────────
Dashboard 8：頁面點擊熱點分析（Page Click Heatmap）
在實際頁面截圖上疊加點擊次數 badge，呈現 Clarity 風格的點擊熱點圖。

執行方式：
    uv run python click_heatmap_report.py
    uv run python click_heatmap_report.py --days 7
    uv run python click_heatmap_report.py --from 2026-04-01 --to 2026-04-10
    uv run python click_heatmap_report.py --output /tmp/report
"""

import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from common.es_client import msearch, parse_args, resolve_time_range, generated_now

CONFIG_PATH = Path(__file__).parent / "click_heatmap_config.json"
OUTPUT_DIR = Path(__file__).parent / "output" / "click-heatmap"

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}

# runtime_mappings：從 pageUrl 提取路徑
_PAGE_PATH_SCRIPT = """
    String url = params._source.get('pageUrl');
    if (url == null || url == '') { emit('(empty)'); return; }
    int start = url.indexOf('//');
    if (start >= 0) url = url.substring(start + 2);
    int slash = url.indexOf('/');
    url = slash >= 0 ? url.substring(slash) : '/';
    int qmark = url.indexOf('?');
    if (qmark >= 0) url = url.substring(0, qmark);
    if (url == '' || url == null) url = '/';
    emit(url.length() > 80 ? url.substring(0, 80) : url);
"""

RUNTIME_MAPPINGS = {
    "page_path": {
        "type": "keyword",
        "script": {"source": _PAGE_PATH_SCRIPT, "lang": "painless"},
    }
}


# ── 截圖 ────────────────────────────────────────────────────────────────────

def take_screenshot(page_config: dict, output_dir: Path) -> tuple[Path, int, int]:
    """用 Playwright 截取頁面截圖，回傳 (截圖路徑, 寬, 高)。"""
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    safe_name = page_config["page_path"].strip("/").replace("/", "_") or "home"
    screenshot_path = screenshots_dir / f"{safe_name}.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            ignore_https_errors=True,
            locale="zh-TW",
        )
        page = context.new_page()
        vp = page_config.get("viewport", {"width": 1440, "height": 900})
        page.set_viewport_size(vp)
        page.goto(page_config["url"], wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # 關閉常見彈窗（含蓋板廣告）
        close_selectors = [
            "button:has-text('稍後再說')",
            "button:has-text('關閉')",
            "button:has-text('我知道了')",
            "button:has-text('×')",
            "button:has-text('✕')",
            "[class*='close']",
            "[aria-label='close']",
            "[aria-label='關閉']",
        ]
        for selector in close_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=500):
                    btn.click()
                    page.wait_for_timeout(300)
            except Exception:
                pass

        # 移除蓋板廣告（position:fixed 且面積 > 視窗 50% 的 overlay）
        page.evaluate("""() => {
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            const minArea = vw * vh * 0.5;
            const candidates = document.querySelectorAll('*');
            for (const el of candidates) {
                const style = window.getComputedStyle(el);
                if (style.position !== 'fixed' && style.position !== 'absolute') continue;
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                const rect = el.getBoundingClientRect();
                if (rect.width * rect.height >= minArea) {
                    // 先找內部關閉按鈕
                    const closeBtn = el.querySelector(
                        'button, [role="button"], [class*="close"], [aria-label="close"]'
                    );
                    if (closeBtn) {
                        closeBtn.click();
                    } else {
                        el.remove();
                    }
                }
            }
        }""")
        page.wait_for_timeout(500)

        page.screenshot(
            path=str(screenshot_path),
            full_page=page_config.get("full_page", True),
        )

        # 取得截圖的實際尺寸
        img_width = vp["width"]
        img_height = page.evaluate("() => document.body.scrollHeight")

        browser.close()

    return screenshot_path, img_width, img_height


# ── ES 查詢 ──────────────────────────────────────────────────────────────────

def query_page_clicks(page_path: str, time_from: str, time_to: str) -> list[dict]:
    """查詢指定頁面路徑的 featureId 點擊數。"""
    body = {
        "size": 0,
        "runtime_mappings": RUNTIME_MAPPINGS,
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
            SYSTEM_FILTER,
            {"term": {"eventType": "click"}},
            {"term": {"page_path": page_path}},
        ]}},
        "aggs": {
            "by_feature": {
                "terms": {"field": "featureId", "size": 100},
                "aggs": {
                    "sample": {
                        "top_hits": {"size": 1, "_source": ["featureName"]}
                    }
                },
            }
        },
    }
    r = msearch(body)
    results = []
    for b in r["aggregations"]["by_feature"]["buckets"]:
        fname = ""
        if b["sample"]["hits"]["hits"]:
            fname = b["sample"]["hits"]["hits"][0]["_source"].get("featureName", "")
        results.append({
            "feature_id": b["key"],
            "feature_name": fname,
            "count": b["doc_count"],
        })
    return results


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

HEATMAP_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC",
                   "Noto Sans TC", sans-serif;
      background: #1a1a2e; color: #fff; min-height: 100vh;
    }
    header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff; padding: 36px 48px 28px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    header h1 { font-size: 1.8rem; font-weight: 700; }
    header p  { margin-top: 6px; font-size: 0.9rem; opacity: 0.65; }
    .badge-header {
      display: inline-block; margin-top: 12px;
      background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
      border-radius: 20px; padding: 4px 14px; font-size: 0.8rem;
    }

    /* Tab 切換 */
    .tab-bar {
      display: flex; gap: 0; background: #16213e;
      border-bottom: 2px solid #0f3460; padding: 0 48px;
    }
    .tab-btn {
      padding: 12px 28px; cursor: pointer; border: none;
      background: transparent; color: #8899aa; font-size: 0.95rem;
      font-weight: 600; transition: all 0.2s;
    }
    .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.05); }
    .tab-btn.active {
      color: #4cc9f0; border-bottom: 3px solid #4cc9f0;
      background: rgba(76,201,240,0.08);
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* 截圖容器 */
    .heatmap-container {
      position: relative; display: inline-block;
      margin: 24px auto; max-width: 100%;
    }
    .heatmap-container img {
      display: block; max-width: 100%; height: auto;
    }

    /* 點擊 Badge */
    .click-badge {
      position: absolute; z-index: 10;
      min-width: 36px; height: 22px; line-height: 22px;
      padding: 0 6px;
      border-radius: 11px;
      font-size: 11px; font-weight: 700;
      color: #fff; text-align: center;
      pointer-events: auto; cursor: default;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
      transform: translate(-50%, -100%);
      white-space: nowrap;
      transition: transform 0.15s;
    }
    .click-badge:hover {
      transform: translate(-50%, -100%) scale(1.3);
      z-index: 100;
    }
    .click-badge .tooltip {
      display: none; position: absolute;
      bottom: 28px; left: 50%; transform: translateX(-50%);
      background: #1a1a2e; color: #fff; padding: 8px 12px;
      border-radius: 8px; font-size: 12px; font-weight: 400;
      white-space: nowrap; min-width: 160px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.15);
    }
    .click-badge:hover .tooltip { display: block; }
    .tooltip-fid { color: #4cc9f0; font-weight: 600; }
    .tooltip-fname { color: #aaa; }

    /* 熱度色階 */
    .heat-high   { background: rgba(239,68,68,0.9); }
    .heat-medium { background: rgba(251,146,60,0.9); }
    .heat-low    { background: rgba(59,130,246,0.85); }
    .heat-cold   { background: rgba(107,114,128,0.8); }

    /* 未對應表格 */
    .unmatched-section {
      max-width: 1200px; margin: 24px auto; padding: 0 24px;
    }
    .unmatched-section h2 {
      font-size: 1.1rem; margin-bottom: 12px; color: #ccc;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    thead th {
      background: #16213e; padding: 10px 14px; text-align: left;
      font-weight: 600; color: #8899aa; border-bottom: 2px solid #0f3460;
    }
    tbody tr:nth-child(odd) { background: rgba(255,255,255,0.03); }
    tbody tr:hover { background: rgba(76,201,240,0.08); }
    tbody td { padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #ccc; }
    .rank { color: #555; font-weight: 700; }
    .count-cell { font-weight: 700; color: #4cc9f0; }
    .bar-bg { background: #2a2a3e; border-radius: 4px; height: 8px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #4361ee, #7209b7); }

    footer {
      text-align: center; font-size: 0.78rem; color: #555;
      padding: 24px 0 12px;
    }
    .center-wrap { text-align: center; }
    .legend {
      display: inline-flex; gap: 16px; margin: 16px 48px;
      font-size: 0.85rem; color: #aaa;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; }
    .legend-dot {
      width: 12px; height: 12px; border-radius: 50%;
    }
"""


def _heat_class(count: int, max_count: int) -> str:
    """根據點擊數決定熱度等級。"""
    if max_count == 0:
        return "heat-cold"
    ratio = count / max_count
    if ratio >= 0.5:
        return "heat-high"
    if ratio >= 0.2:
        return "heat-medium"
    if ratio >= 0.05:
        return "heat-low"
    return "heat-cold"


def _format_count(n: int) -> str:
    """格式化大數字。"""
    if n >= 10000:
        return f"{n/1000:.1f}K"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)


def generate_html(
    pages_data: list[dict],
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    """產生完整 HTML 報告。"""
    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>頁面點擊熱點分析 — Page Click Heatmap</title>
  <style>{HEATMAP_CSS}</style>
</head>
<body>
<header>
  <h1>頁面點擊熱點分析 — Page Click Heatmap</h1>
  <p>資料來源：operation-logs（Elasticsearch） · 查詢區間：{time_from} ～ {time_to}</p>
  <span class="badge-header">產生時間：{gen_at}</span>
</header>
""")

    # Tab bar
    parts.append('<div class="tab-bar">')
    for i, pd in enumerate(pages_data):
        active = " active" if i == 0 else ""
        parts.append(
            f'  <button class="tab-btn{active}" onclick="switchTab({i})">'
            f'{pd["page_name"]}</button>'
        )
    parts.append("</div>")

    # Legend
    parts.append("""
<div class="center-wrap">
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:rgba(239,68,68,0.9)"></div>高 (≥50%)</div>
    <div class="legend-item"><div class="legend-dot" style="background:rgba(251,146,60,0.9)"></div>中 (≥20%)</div>
    <div class="legend-item"><div class="legend-dot" style="background:rgba(59,130,246,0.85)"></div>低 (≥5%)</div>
    <div class="legend-item"><div class="legend-dot" style="background:rgba(107,114,128,0.8)"></div>極低 (<5%)</div>
  </div>
</div>
""")

    # 每個頁面的 Tab Content
    for i, pd in enumerate(pages_data):
        active = " active" if i == 0 else ""
        parts.append(f'<div class="tab-content{active}" id="tab-{i}">')

        # 截圖 + Badge 疊加
        screenshot_b64 = pd.get("screenshot_b64", "")
        parts.append('  <div class="center-wrap">')
        parts.append('    <div class="heatmap-container">')
        parts.append(
            f'      <img src="data:image/png;base64,{screenshot_b64}" '
            f'alt="{pd["page_name"]}" />'
        )

        # Badge 疊加
        click_data = pd.get("click_data", [])
        elements = pd.get("elements", [])
        max_count = max((c["count"] for c in click_data), default=0)

        # 建立 feature_id → click count 的 dict
        click_map = {c["feature_id"]: c for c in click_data}

        img_w = pd.get("img_width", 1440)
        img_h = pd.get("img_height", 5000)

        matched_fids = set()
        for el in elements:
            fid = el.get("feature_id", "")
            if not fid or fid not in click_map:
                continue
            matched_fids.add(fid)
            cd = click_map[fid]
            heat = _heat_class(cd["count"], max_count)
            display_count = _format_count(cd["count"])
            # Badge 定位在元素的右上角，使用百分比座標
            pct_x = (el["x"] + el["width"]) / img_w * 100
            pct_y = el["y"] / img_h * 100
            parts.append(
                f'      <div class="click-badge {heat}" '
                f'style="left:{pct_x:.2f}%;top:{pct_y:.2f}%">'
                f'{display_count}'
                f'<div class="tooltip">'
                f'<div class="tooltip-fid">{fid}</div>'
                f'<div class="tooltip-fname">{cd["feature_name"]}</div>'
                f'<div>{cd["count"]:,} clicks</div>'
                f'</div></div>'
            )

        parts.append("    </div>")
        parts.append("  </div>")

        # 未對應的 featureId 表格
        unmatched = [c for c in click_data if c["feature_id"] not in matched_fids]
        if unmatched:
            total = sum(c["count"] for c in unmatched)
            parts.append('  <div class="unmatched-section">')
            parts.append(f'    <h2>未對應元素的點擊數據（共 {len(unmatched)} 項，{total:,} clicks）</h2>')
            parts.append("    <table><thead><tr>")
            parts.append(
                "<th>#</th><th>featureId</th><th>featureName</th>"
                "<th>點擊數</th><th>視覺</th></tr></thead><tbody>"
            )
            all_total = sum(c["count"] for c in click_data)
            for j, c in enumerate(unmatched, 1):
                pct = c["count"] / all_total * 100 if all_total else 0
                parts.append(
                    f'<tr><td class="rank">{j}</td>'
                    f'<td>{c["feature_id"]}</td>'
                    f'<td>{c["feature_name"]}</td>'
                    f'<td class="count-cell">{c["count"]:,}</td>'
                    f'<td style="width:120px"><div class="bar-bg">'
                    f'<div class="bar-fill" style="width:{pct:.1f}%"></div>'
                    f'</div></td></tr>'
                )
            parts.append("</tbody></table></div>")

        parts.append("</div>")

    # Tab 切換 JS
    parts.append("""
<script>
function switchTab(idx) {
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', i === idx);
  });
  document.querySelectorAll('.tab-content').forEach((c, i) => {
    c.classList.toggle('active', i === idx);
  });
}
</script>
""")

    parts.append(f'<footer>Generated {gen_at} · operation-logs</footer>')
    parts.append("</body></html>")
    return "".join(parts)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args("Dashboard 8：頁面點擊熱點分析")
    time_from, time_to = resolve_time_range(args)
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 查詢區間：{time_from} ～ {time_to}")
    print(f"[INFO] 輸出目錄：{output_dir}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pages_data = []

    for page_config in config["pages"]:
        page_name = page_config["page_name"]
        page_path = page_config["page_path"]

        print(f"\n[INFO] 處理頁面：{page_name} ({page_path})")

        # 截圖
        print("  截圖中...")
        screenshot_path, img_w, img_h = take_screenshot(page_config, output_dir)
        screenshot_b64 = base64.b64encode(
            screenshot_path.read_bytes()
        ).decode()
        print(f"  截圖完成：{screenshot_path}（{img_w}x{img_h}）")

        # 查詢 ES
        print("  查詢 ES 點擊數據...")
        click_data = query_page_clicks(page_path, time_from, time_to)
        total_clicks = sum(c["count"] for c in click_data)
        print(f"  共 {total_clicks:,} clicks，{len(click_data)} 個 featureId")

        # 篩選有 feature_id 對應的元素
        elements_with_fid = [
            el for el in page_config.get("elements", [])
            if el.get("feature_id")
        ]

        pages_data.append({
            "page_name": page_name,
            "page_path": page_path,
            "screenshot_b64": screenshot_b64,
            "click_data": click_data,
            "elements": elements_with_fid,
            "img_width": img_w,
            "img_height": img_h,
        })

    gen_at = generated_now()
    html = generate_html(pages_data, time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
