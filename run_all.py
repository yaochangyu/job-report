#!/usr/bin/env python3
"""
run_all.py
──────────
一鍵執行三層資料管線，並產生 output/index.html 導覽頁面。

執行方式：
    uv run python run_all.py
    uv run python run_all.py --days 7
    uv run python run_all.py --from 2026-04-01 --to 2026-04-10
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path
from common.es_client import parse_args, generated_now
from common.t1_reader import resolve_date_window
from extract_raw_events import extract_raw_events

OUTPUT_DIR = Path(__file__).parent / "output"

REPORTS = [
    {
        "script": "run_traffic_overview_pipeline.py",
        "title": "整體流量概覽",
        "subtitle": "Traffic Overview",
        "desc": "KPI 指標、每日流量趨勢、每小時分佈、裝置與 OS 分佈",
        "path": "traffic-overview/index.html",
        "icon": "📊",
        "color": "#4361ee",
    },
    {
        "script": "run_search_behavior_pipeline.py",
        "title": "搜尋行為分析",
        "subtitle": "Search Behavior",
        "desc": "AI vs 一般搜尋趨勢、搜尋結果頁分佈、AI 互動方式、快速篩選",
        "path": "search-behavior/index.html",
        "icon": "🔍",
        "color": "#7209b7",
    },
    {
        "script": "run_apply_conversion_pipeline.py",
        "title": "應徵轉換分析",
        "subtitle": "Apply Conversion",
        "desc": "應徵漏斗、每日趨勢、來源分佈、裝置與時段分析",
        "path": "apply-conversion/index.html",
        "icon": "🎯",
        "color": "#f72585",
    },
    {
        "script": "run_feature_engagement_pipeline.py",
        "title": "功能互動分析",
        "subtitle": "Feature Engagement",
        "desc": "探索職缺/企業、身份辨識、產業 Tab、新聞互動",
        "path": "feature-engagement/index.html",
        "icon": "⚡",
        "color": "#06d6a0",
    },
    {
        "script": "run_device_platform_pipeline.py",
        "title": "裝置與平台分析",
        "subtitle": "Device & Platform",
        "desc": "Mobile/Desktop 趨勢、OS 與瀏覽器分佈、裝置行為交叉",
        "path": "device-platform/index.html",
        "icon": "📱",
        "color": "#fb8500",
    },
    {
        "script": "run_page_ranking_pipeline.py",
        "title": "頁面流量排行",
        "subtitle": "Page Ranking",
        "desc": "featureId 排行 Top 20、功能類別佔比分析",
        "path": "page-ranking/index.html",
        "icon": "🏆",
        "color": "#118ab2",
    },
    {
        "script": "run_page_navigation_pipeline.py",
        "title": "頁面導航鏈路",
        "subtitle": "Page Navigation Flow",
        "desc": "頁面轉換路徑排行、各頁面來源/目標、初始進入分佈",
        "path": "page-navigation/index.html",
        "icon": "🔀",
        "color": "#8338ec",
    },
    {
        "script": "run_click_heatmap_pipeline.py",
        "title": "頁面點擊熱點",
        "subtitle": "Page Click Heatmap",
        "desc": "Clarity 風格截圖疊加，呈現各頁面按鈕/連結的點擊次數",
        "path": "click-heatmap/index.html",
        "icon": "🔥",
        "color": "#e63946",
    },
]


def build_nav_html(results: list[dict], time_from: str, time_to: str, gen_at: str) -> str:
    """產生 output/index.html 導覽頁面。"""
    cards_html = ""
    for r in results:
        status_badge = ""
        if r["ok"]:
            status_badge = '<span class="badge ok">✓ 完成</span>'
        else:
            status_badge = f'<span class="badge err">✗ 失敗</span>'

        link_attr = f'href="{r["path"]}"' if r["ok"] else 'href="#" onclick="return false"'
        card_style = "" if r["ok"] else "opacity:0.6"

        cards_html += f"""
    <a {link_attr} class="report-card" style="--accent:{r['color']};{card_style}" target="_blank">
      <div class="card-icon">{r['icon']}</div>
      <div class="card-body">
        <div class="card-title">{r['title']}</div>
        <div class="card-subtitle">{r['subtitle']}</div>
        <div class="card-desc">{r['desc']}</div>
      </div>
      {status_badge}
    </a>"""

    ok_count = sum(1 for r in results if r["ok"])
    total = len(results)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>jobbank-web 數據報告導覽</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
      background: #f0f2f5; color: #1a1a2e; min-height: 100vh;
    }}
    header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff; padding: 48px 48px 36px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    header h1 {{ font-size: 2rem; font-weight: 800; letter-spacing: -0.5px; }}
    header .meta {{ margin-top: 8px; font-size: 0.9rem; opacity: 0.65; }}
    .badge-row {{ margin-top: 14px; display: flex; gap: 10px; flex-wrap: wrap; }}
    .pill {{
      display: inline-block;
      background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
      border-radius: 20px; padding: 4px 14px; font-size: 0.82rem;
    }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 40px 24px 60px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }}
    .report-card {{
      display: flex; align-items: flex-start; gap: 16px;
      background: #fff; border-radius: 16px; padding: 24px 20px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.07);
      border-left: 5px solid var(--accent);
      text-decoration: none; color: inherit;
      transition: transform 0.15s, box-shadow 0.15s;
      position: relative;
    }}
    .report-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.12); }}
    .card-icon {{ font-size: 2.2rem; flex-shrink: 0; margin-top: 2px; }}
    .card-body {{ flex: 1; }}
    .card-title {{ font-size: 1.1rem; font-weight: 700; color: var(--accent); }}
    .card-subtitle {{ font-size: 0.78rem; color: #aaa; margin-top: 2px; letter-spacing: 0.5px; }}
    .card-desc {{ font-size: 0.85rem; color: #666; margin-top: 8px; line-height: 1.5; }}
    .badge {{ position: absolute; top: 14px; right: 16px; font-size: 0.75rem; padding: 3px 10px; border-radius: 12px; }}
    .badge.ok {{ background: #e8f9f2; color: #1a8a5a; border: 1px solid #b7e7d3; }}
    .badge.err {{ background: #fdecea; color: #c0392b; border: 1px solid #f5b7b1; }}
    footer {{ text-align: center; font-size: 0.78rem; color: #bbb; padding: 24px 0 12px; }}
  </style>
</head>
<body>
<header>
  <h1>📈 jobbank-web 數據報告</h1>
  <div class="meta">資料來源：operation-logs（Elasticsearch）· 查詢區間：{time_from} ～ {time_to}</div>
  <div class="badge-row">
    <span class="pill">共 {total} 份報告</span>
    <span class="pill">✓ {ok_count} 份完成</span>
    <span class="pill">產生時間：{gen_at}</span>
  </div>
</header>
<main>
  <div class="grid">
    {cards_html}
  </div>
</main>
<footer>Generated {gen_at} · operation-logs</footer>
</body>
</html>"""


def run_report(script: str, extra_args: list[str]) -> tuple[bool, float]:
    """執行單一報告腳本，回傳（成功與否, 耗時秒數）。"""
    cmd = [sys.executable, script] + extra_args
    start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start
    return result.returncode == 0, round(elapsed, 1)


def main() -> None:
    args = parse_args("一鍵執行所有報告並產生導覽頁面")
    date_from, date_to = resolve_date_window(args.days, args.time_from, args.time_to)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    extra_args = ["--from", date_from, "--to", date_to, "--skip-extract"]

    print(f"[INFO] 查詢區間：{date_from} ～ {date_to}")
    print("[INFO] 先同步 T1 raw 資料（優先重用本地快取）...")
    extract_raw_events(date_from, date_to, keep_existing=True)
    print(f"[INFO] 開始執行 {len(REPORTS)} 份報告...\n")

    results = []
    total_start = time.time()

    for report in REPORTS:
        print(f"{'─'*60}")
        print(f"[{report['icon']}] {report['title']} ({report['subtitle']})")
        ok, elapsed = run_report(report["script"], extra_args)
        status = "✓ 完成" if ok else "✗ 失敗"
        print(f"  → {status}（耗時 {elapsed}s）")
        results.append({**report, "ok": ok, "elapsed": elapsed})

    total_elapsed = round(time.time() - total_start, 1)
    ok_count = sum(1 for r in results if r["ok"])

    print(f"\n{'═'*60}")
    print(f"[完成] {ok_count}/{len(REPORTS)} 份報告成功，共耗時 {total_elapsed}s")

    # 產生導覽頁面
    gen_at = generated_now()
    nav_html = build_nav_html(results, date_from, date_to, gen_at)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    nav_file = OUTPUT_DIR / "index.html"
    nav_file.write_text(nav_html, encoding="utf-8")
    print(f"[OK] 導覽頁面已產生：{nav_file}")


if __name__ == "__main__":
    main()
