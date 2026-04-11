# jobbank-web 單頁分析報表

從 Elasticsearch（透過 Grafana proxy）擷取 `jobbank-web` 使用者行為事件，輸出為 Parquet dataset，並以 **DuckDB-WASM 單頁前端** 在瀏覽器端即時查詢與呈現。

---

## 架構概覽

```text
Elasticsearch
    │
    ▼
extract_events.py
    │
    └── dataset/
        ├── manifest.json
        └── events/date=YYYY-MM-DD/events.parquet
                │
                ▼
frontend/（DuckDB-WASM 單頁）
                │
                ▼
run_all.py
    │
    └── output/（可部署站台）
                │
                ▼
GitHub Pages
```

---

## 快速開始

```bash
# 安裝相依套件
uv sync

# 匯出指定日期區間的 Parquet dataset
uv run python extract_events.py --from 2026-04-01 --to 2026-04-07

# 組裝單頁網站到 output/
uv run python run_all.py

# 本機預覽
uv run python -m http.server 8000
# 開啟 http://127.0.0.1:8000/output/
```

---

## 主要指令

### 1. 匯出 Parquet dataset

```bash
# 單日
uv run python extract_events.py --date 2026-04-10

# 日期區間
uv run python extract_events.py --from 2026-04-01 --to 2026-04-10
```

輸出位置：

```text
dataset/
├── manifest.json
└── events/
    └── date=YYYY-MM-DD/
        └── events.parquet
```

### 2. 組裝單頁網站

```bash
uv run python run_all.py
uv run python run_all.py --output /tmp/job-report-site
```

`run_all.py` 會把：

- `frontend/` 複製到輸出目錄
- `dataset/` 複製到輸出目錄
- 產生 `site-manifest.json`

### 3. 部署到 GitHub Pages

```bash
# 預設匯出近 7 天資料後部署
bash deploy.sh

# 指定天數
bash deploy.sh 30
```

`deploy.sh` 目前流程：

1. 以 `extract_events.py` 匯出近 N 天 Parquet
2. 以 `run_all.py` 組裝單頁網站
3. 推送 `output/` 到 `gh-pages`

---

## Frontend 行為

單頁前端位於 `frontend/`，目前包含：

- `index.html`：單頁入口
- `app.css`：頁面樣式
- `app.js`：DuckDB-WASM 啟動、manifest 載入、資料集註冊
- `query-definitions.js`：查詢條件轉 DuckDB SQL
- `dashboard-renderers.js`：KPI、圖表、表格 renderer

支援的視角：

- `overview`
- `search`
- `apply`
- `feature`
- `device`
- `ranking`
- `navigation`
- `heatmap`

---

## Dataset 與 Schema

Parquet schema 由 `common/parquet_schema.py` 定義，主表為 `events`，核心欄位包含：

| 欄位 | 說明 |
|------|------|
| `date` | 台灣時區日期 |
| `hour` | 台灣時區小時 |
| `occurred_at` | 事件發生時間 |
| `event_type` | `view` / `click` |
| `action` | 例如 `apply` |
| `session_id` | session 去重用 |
| `feature_id` | 功能識別 |
| `page_path` | `pageUrl` 正規化路徑 |
| `previous_page_path` | `previousPageUrl` 正規化路徑 |
| `device_type` | 裝置類型 |
| `os` | 作業系統 |
| `browser` | 瀏覽器 |
| `source` | `metadata.source` |
| `category_tab` | `metadata.categoryTab` |
| `identity_type` | `metadata.identityType` |
| `industry_tab` | `metadata.industryTab` |

---

## 注意事項

- DuckDB-WASM 方案適合 **可公開資料**
- `manifest.json` 不存在時，前端會顯示尚未載入資料集
- 跨日 `unique session` 仍是近似值，前端不會自動解決 HyperLogLog 合併限制
- 點擊熱點若要完整疊圖，仍需搭配 `click_heatmap_config.json`

---

## 舊流程說明

以下檔案目前仍保留，但已不是主部署流程：

- `extract_all.py`
- `common/store.py`
- `*_report.py`
- `snapshot-refactor.plan.md`

這些檔案屬於舊的 **SQLite + 多頁靜態報表** 路線，現階段保留作為參考與回溯用途。

---

## 環境需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Playwright（目前專案仍保留）
- 可連線的 Grafana / Elasticsearch
