#!/usr/bin/env python3
"""
page_navigation_report.py
──────────────────────────
Dashboard 7：頁面導航鏈路分析（Page Navigation Flow）
從 Elasticsearch 查詢 jobbank-web 的原始 view 事件，依 session 還原完整頁面導航鏈路，
產生 HTML 圖表報告。

執行方式：
    uv run python page_navigation_report.py
    uv run python page_navigation_report.py --days 7
    uv run python page_navigation_report.py --from 2026-04-01 --to 2026-04-10
    uv run python page_navigation_report.py --output /tmp/report
    uv run python page_navigation_report.py --from 2026-04-01 --to 2026-04-10 --from-store
"""

from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from common.chart_helpers import js_labels, js_values, palette_array
from common.es_client import generated_now, msearch, parse_args, resolve_time_range, TW
from common.html_template import chart_card, html_end, html_start, kpi_card, table_card
from common.parquet_dataset import normalize_path, parse_event_timestamp
from common.store import init_db, load_daily_range

OUTPUT_DIR = Path(__file__).parent / "output" / "page-navigation"
REPORT = "page-navigation"
PAGE_SIZE = 2_000

SYSTEM_FILTER = {"term": {"system": "jobbank-web"}}
SOURCE_FIELDS = ["@timestamp", "@timestamp_ms", "eventType", "sessionId", "pageUrl"]


def _fetch_view_events(time_from: str, time_to: str) -> list[dict]:
    rows: list[dict] = []
    search_after = None

    while True:
        body = {
            "size": PAGE_SIZE,
            "_source": SOURCE_FIELDS,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}},
                        SYSTEM_FILTER,
                        {"term": {"eventType": "view"}},
                        {"exists": {"field": "sessionId"}},
                        {"exists": {"field": "pageUrl"}},
                    ]
                }
            },
            "sort": [
                {"@timestamp_ms": "asc"},
            ],
        }
        if search_after is not None:
            body["search_after"] = search_after

        response = msearch(body)
        hits = response["hits"]["hits"]
        if not hits:
            break

        for hit in hits:
            source = hit["_source"]
            rows.append(
                {
                    "session_id": source.get("sessionId"),
                    "occurred_at": parse_event_timestamp(source["@timestamp"]),
                    "page_path": normalize_path(source.get("pageUrl"), default="/"),
                }
            )

        search_after = hits[-1]["sort"]
        if len(hits) < PAGE_SIZE:
            break

    return rows


def _build_session_chains(events: list[dict]) -> list[dict]:
    grouped: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for item in events:
        session_id = item["session_id"]
        page_path = item["page_path"]
        if session_id and page_path:
            grouped[session_id].append((item["occurred_at"], page_path))

    chains: list[dict] = []
    for session_id, items in grouped.items():
        items.sort(key=lambda entry: (entry[0], entry[1]))
        deduped_paths: list[str] = []
        last_page = None
        for _, page_path in items:
            if page_path == last_page:
                continue
            deduped_paths.append(page_path)
            last_page = page_path

        if len(deduped_paths) < 2:
            continue

        chains.append(
            {
                "session_id": session_id,
                "steps": len(deduped_paths),
                "entry_page": deduped_paths[0],
                "chain": " -> ".join(deduped_paths),
            }
        )

    return chains


@lru_cache(maxsize=8)
def _navigation_snapshot(time_from: str, time_to: str) -> dict:
    events = _fetch_view_events(time_from, time_to)
    chains = _build_session_chains(events)

    ranking_map: dict[str, dict] = {}
    step_totals: dict[int, int] = defaultdict(int)
    entry_totals: dict[str, int] = defaultdict(int)
    total_steps = 0

    for item in chains:
        chain = item["chain"]
        ranking = ranking_map.setdefault(
            chain,
            {"name": chain, "count": 0, "steps": item["steps"]},
        )
        ranking["count"] += 1
        ranking["steps"] = max(ranking["steps"], item["steps"])
        step_totals[item["steps"]] += 1
        entry_totals[item["entry_page"]] += 1
        total_steps += item["steps"]

    ranking_rows = sorted(
        ranking_map.values(),
        key=lambda row: (-row["count"], -row["steps"], row["name"]),
    )
    step_rows = [
        {"name": str(step), "count": count}
        for step, count in sorted(step_totals.items(), key=lambda item: item[0])
    ]
    entry_rows = sorted(
        [{"name": name, "count": count} for name, count in entry_totals.items()],
        key=lambda row: (-row["count"], row["name"]),
    )

    total_sessions = sum(row["count"] for row in ranking_rows)
    max_steps = max((row["steps"] for row in ranking_rows), default=0)
    avg_steps = total_steps / total_sessions if total_sessions else 0

    return {
        "kpi": {
            "sessions": total_sessions,
            "unique_chains": len(ranking_rows),
            "avg_steps": round(avg_steps, 2),
            "max_steps": max_steps,
        },
        "ranking": ranking_rows,
        "steps": step_rows,
        "entry_pages": entry_rows,
    }


def query_chain_kpi(time_from: str, time_to: str) -> dict:
    return _navigation_snapshot(time_from, time_to)["kpi"]


def query_chain_ranking(time_from: str, time_to: str, size: int | None = None) -> list[dict]:
    rows = _navigation_snapshot(time_from, time_to)["ranking"]
    return rows if size is None else rows[:size]


def query_chain_steps(time_from: str, time_to: str) -> list[dict]:
    return _navigation_snapshot(time_from, time_to)["steps"]


def query_entry_pages(time_from: str, time_to: str, size: int | None = None) -> list[dict]:
    rows = _navigation_snapshot(time_from, time_to)["entry_pages"]
    return rows if size is None else rows[:size]


def _date_range(time_from: str, time_to: str) -> tuple[str, str]:
    d_from = time_from[:10]
    d_to = time_to[:10] if time_to.lower() != "now" else datetime.now(TW).strftime("%Y-%m-%d")
    return d_from, d_to


def _load_chain_ranking(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_chain_ranking")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_chain_ranking [{date_from}～{date_to}]")

    merged: dict[str, dict] = {}
    for row in rows:
        for item in row["data"]:
            target = merged.setdefault(
                item["name"],
                {"name": item["name"], "count": 0, "steps": item["steps"]},
            )
            target["count"] += item["count"]
            target["steps"] = max(target["steps"], item["steps"])

    return sorted(merged.values(), key=lambda item: (-item["count"], -item["steps"], item["name"]))


def _load_chain_steps(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_chain_steps")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_chain_steps [{date_from}～{date_to}]")

    merged: dict[str, int] = defaultdict(int)
    for row in rows:
        for item in row["data"]:
            merged[item["name"]] += item["count"]

    return [
        {"name": name, "count": count}
        for name, count in sorted(merged.items(), key=lambda item: int(item[0]))
    ]


def _load_entry_pages(date_from: str, date_to: str) -> list[dict]:
    rows = load_daily_range(date_from, date_to, REPORT, "query_entry_pages")
    if not rows:
        raise RuntimeError(f"store.db 無資料：{REPORT}/query_entry_pages [{date_from}～{date_to}]")

    merged: dict[str, int] = defaultdict(int)
    for row in rows:
        for item in row["data"]:
            merged[item["name"]] += item["count"]

    return sorted(
        [{"name": name, "count": count} for name, count in merged.items()],
        key=lambda item: (-item["count"], item["name"]),
    )


def _kpi_from_ranking(ranking: list[dict]) -> dict:
    total_sessions = sum(item["count"] for item in ranking)
    total_steps = sum(item["count"] * item["steps"] for item in ranking)
    return {
        "sessions": total_sessions,
        "unique_chains": len(ranking),
        "avg_steps": round(total_steps / total_sessions, 2) if total_sessions else 0,
        "max_steps": max((item["steps"] for item in ranking), default=0),
    }


def generate_html(
    chain_kpi: dict,
    chain_ranking: list[dict],
    chain_steps: list[dict],
    entry_pages: list[dict],
    time_from: str,
    time_to: str,
    gen_at: str,
) -> str:
    ranking_top20 = chain_ranking[:20]
    entry_top10 = entry_pages[:10]
    step_total = sum(item["count"] for item in chain_steps)

    ranking_thead = "<tr><th>#</th><th>完整鏈路</th><th>Sessions</th><th>步數</th></tr>"
    ranking_tbody = "".join(
        (
            f'<tr><td class="rank">{index}</td><td>{row["name"]}</td>'
            f'<td>{row["count"]:,}</td><td>{row["steps"]}</td></tr>'
        )
        for index, row in enumerate(chain_ranking[:30], 1)
    )

    entry_thead = "<tr><th>#</th><th>入口頁</th><th>Sessions</th></tr>"
    entry_tbody = "".join(
        f'<tr><td class="rank">{index}</td><td>{row["name"]}</td><td>{row["count"]:,}</td></tr>'
        for index, row in enumerate(entry_pages[:15], 1)
    )

    parts = [
        html_start("頁面導航鏈路分析 — Page Navigation Flow", time_from, time_to, gen_at),
        '  <div class="kpi-grid">',
        kpi_card("鏈路 Sessions", f'{chain_kpi["sessions"]:,}', "至少 2 步的 session", "#4361ee"),
        kpi_card("不重複鏈路", f'{chain_kpi["unique_chains"]:,}', "完整鏈路組合數", "#06d6a0"),
        kpi_card("平均步數", f'{chain_kpi["avg_steps"]:.2f}', "每條鏈路平均頁面步數", "#7209b7"),
        kpi_card("最長步數", f'{chain_kpi["max_steps"]:,}', "單一鏈路最大頁面步數", "#fb8500"),
        "  </div>",
        '  <div class="chart-grid">',
        chart_card("完整鏈路排行 Top 20", "依 session 重建後最常見的頁面導航鏈路", "chainRanking", tall=True),
        chart_card("鏈路步數分佈", "每條鏈路包含幾個不同頁面步驟", "chainSteps"),
        "  </div>",
        '  <div class="chart-grid">',
        chart_card("常見入口頁 Top 10", "完整鏈路的起始頁面分佈", "entryPages"),
        "  </div>",
        table_card("完整鏈路排行 Top 30", "完整 session 鏈路明細", ranking_thead, ranking_tbody),
        table_card("常見入口頁 Top 15", "完整鏈路的起始頁面統計", entry_thead, entry_tbody),
        f"""
<script>
  new Chart(document.getElementById('chainRanking'), {{
    type: 'bar',
    data: {{
      labels: {js_labels([row["name"] for row in ranking_top20])},
      datasets: [{{
        label: 'Sessions',
        data: {js_values([row["count"] for row in ranking_top20])},
        backgroundColor: {palette_array(len(ranking_top20))},
        borderRadius: 4
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Sessions' }} }},
        y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('chainSteps'), {{
    type: 'doughnut',
    data: {{
      labels: {js_labels([f'{row["name"]} 步' for row in chain_steps])},
      datasets: [{{
        data: {js_values([row["count"] for row in chain_steps])},
        backgroundColor: {palette_array(len(chain_steps))},
        borderWidth: 2,
        borderColor: '#fff'
      }}]
    }},
    options: {{
      cutout: '55%',
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 12 }}, padding: 8 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const total = {step_total};
            return ` ${{ctx.label}}：${{ctx.parsed.toLocaleString()}}（${{(ctx.parsed / total * 100).toFixed(1)}}%）`;
          }}
        }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('entryPages'), {{
    type: 'bar',
    data: {{
      labels: {js_labels([row["name"] for row in entry_top10])},
      datasets: [{{
        label: 'Sessions',
        data: {js_values([row["count"] for row in entry_top10])},
        backgroundColor: {palette_array(len(entry_top10))},
        borderRadius: 4
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        y: {{ title: {{ display: true, text: 'Sessions' }} }}
      }}
    }}
  }});
</script>
""",
        html_end(gen_at),
    ]
    return "".join(parts)


def main() -> None:
    args = parse_args("Dashboard 7：頁面導航鏈路分析")
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
        print("[INFO] 讀取完整鏈路排行...")
        chain_ranking = _load_chain_ranking(date_from, date_to)
        print("[INFO] 讀取鏈路步數分佈...")
        chain_steps = _load_chain_steps(date_from, date_to)
        print("[INFO] 讀取入口頁分佈...")
        entry_pages = _load_entry_pages(date_from, date_to)
        chain_kpi = _kpi_from_ranking(chain_ranking)
    else:
        print("[INFO] 查詢完整鏈路排行...")
        chain_ranking = query_chain_ranking(time_from, time_to, size=30)
        print("[INFO] 查詢鏈路步數分佈...")
        chain_steps = query_chain_steps(time_from, time_to)
        print("[INFO] 查詢入口頁分佈...")
        entry_pages = query_entry_pages(time_from, time_to, size=15)
        chain_kpi = query_chain_kpi(time_from, time_to)

    gen_at = generated_now()
    html = generate_html(chain_kpi, chain_ranking, chain_steps, entry_pages, time_from, time_to, gen_at)

    out_file = output_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"\n[OK] 報告已產生：{out_file}")


if __name__ == "__main__":
    main()
