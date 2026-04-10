"""
chart_helpers.py
────────────────
Chart.js 輔助函式與色票常數。
"""

import json

# ── 色票 ─────────────────────────────────────────────────────────────────────

PALETTE = [
    "#4361ee", "#7209b7", "#f72585", "#06d6a0", "#fb8500",
    "#118ab2", "#3a86ff", "#8338ec", "#ff006e", "#ffbe0b",
    "#80b918", "#00b4d8", "#e63946", "#457b9d",
]


# ── JS 陣列產生 ──────────────────────────────────────────────────────────────

def js_array(data: list[dict], key: str) -> str:
    """將 list[dict] 中指定 key 轉為 JS 陣列字串。"""
    vals = [json.dumps(d[key], ensure_ascii=False) for d in data]
    return "[" + ", ".join(vals) + "]"


def js_labels(labels: list[str]) -> str:
    """將字串 list 轉為 JS 陣列字串。"""
    return "[" + ", ".join(json.dumps(l, ensure_ascii=False) for l in labels) + "]"


def js_values(values: list) -> str:
    """將數值 list 轉為 JS 陣列字串。"""
    return "[" + ", ".join(str(v) for v in values) + "]"


def palette_array(n: int) -> str:
    """產生 n 個顏色的 JS 陣列字串。"""
    colors = [PALETTE[i % len(PALETTE)] for i in range(n)]
    return "[" + ", ".join(f'"{c}"' for c in colors) + "]"


def palette_list(n: int) -> list[str]:
    """產生 n 個顏色的 Python list。"""
    return [PALETTE[i % len(PALETTE)] for i in range(n)]


# ── HTML 表格 ────────────────────────────────────────────────────────────────

def table_rows_ranked(data: list[dict], label_key: str, count_key: str, total: int) -> str:
    """產生帶排名、長條圖的表格 <tr> 列。"""
    rows = []
    for i, d in enumerate(data, 1):
        pct = d[count_key] / total * 100 if total else 0
        label = d[label_key]
        count = d[count_key]
        rows.append(f"""
        <tr>
          <td class="rank">{i}</td>
          <td>{label}</td>
          <td>{count:,}</td>
          <td class="bar-cell">
            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>
          </td>
          <td class="pct">{pct:.1f}%</td>
        </tr>""")
    return "".join(rows)
