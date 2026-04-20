# job-report

1111人力銀行前端行為分析報告系統。從 Elasticsearch 抽取使用者事件，經三層資料管線處理，產出可部署至 GitHub Pages 的靜態分析報表。

## 架構概覽

```
Elasticsearch (operation-logs)
        │
        ▼  extract_raw_events.py
dataset/raw/date=YYYY-MM-DD/events.parquet      ← T1 原始事件
        │
        ▼  build_*_t2.py
dataset/report/<報表名>/range=from_to/*.parquet  ← T2 聚合結果
        │
        ▼  render_*_t3.py
output/<報表名>/index.html                        ← T3 靜態報表頁
```

所有報表輸出至 `output/`，透過 `deploy.sh` 推送至 GitHub Pages。頁面本身是前端殼（空 HTML），`app.js` 啟動後以 HTTP 抓取同目錄下的 Parquet 檔，由 DuckDB-WASM 在瀏覽器動態查詢渲染，無需後端服務。

## 報表清單

| # | 報表 | 說明 |
|---|------|------|
| 1 | Traffic Overview | KPI 指標、每日流量趨勢、每小時分佈、裝置與 OS 分佈 |
| 2 | Search Behavior | AI vs 一般搜尋趨勢、搜尋結果頁分佈、AI 互動方式 |
| 3 | Apply Conversion | 應徵漏斗、每日趨勢、來源分佈、裝置與時段分析 |
| 4 | Feature Engagement | 探索職缺/企業、身份辨識、產業 Tab、新聞互動 |
| 5 | Device & Platform | Mobile/Desktop 趨勢、OS 與瀏覽器分佈 |
| 6 | Page Ranking | featureId 排行 Top 20、功能類別佔比 |
| 7 | Page Navigation Flow | 頁面轉換路徑排行、各頁面來源/目標 |
| 8 | Page Click Heatmap | 截圖疊加點擊次數，呈現各頁面按鈕點擊熱點 |

## 資料管線詳細說明

### T1 — 原始事件

從 Elasticsearch index `operation-logs`（filter: `system=jobbank-web`）抽取原始事件，以 `search_after` 分批查詢（每批 5000 筆），按日存成 Parquet（zstd 壓縮）。

**存放位置：**
```
dataset/raw/
  date=2025-01-01/events.parquet
  date=2025-01-02/events.parquet
  ...
dataset/manifest/t1-raw-manifest.json
```

**欄位：**

| 欄位 | 說明 |
|------|------|
| `date` / `hour` / `occurred_at` | 台灣時區事件時間 |
| `event_type` / `action` | 事件種類（view / click / apply…） |
| `session_id` / `anonymous_id` / `user_id` / `client_id` | 身份識別 |
| `feature_id` / `feature_name` / `feature_type` | 觸發的功能元件 |
| `page_path` / `previous_page_path` | 正規化後的頁面路徑 |
| `device_type` / `os` / `browser` | 裝置資訊 |
| `source` / `category_tab` / `identity_type` / `industry_tab` | 來自 ES `metadata` 的額外維度 |

### T2 — 聚合結果

每份報表各自的 `build_*_t2.py` 讀取 T1 Parquet，依報表需求計算聚合，輸出多個主題的 Parquet 檔。

**存放位置：**
```
dataset/report/
  traffic-overview/
    range=2025-01-01_2025-01-31/
      kpi.parquet
      daily.parquet
      hourly.parquet
      device_type.parquet
      os.parquet
      browser.parquet
  search-behavior/range=.../...
  apply-conversion/range=.../...
  （各報表同理）
```

### T3 — 報表頁（前端殼 + DuckDB-WASM）

`render_*_t3.py` 讀取 T2 Parquet 產生中間 HTML，但 `run_all.py` 最後會呼叫 `build_shell_pages()` 將輸出覆蓋為前端殼。實際部署的 `index.html` 是空殼，資料在瀏覽器端由 `app.js` 透過 DuckDB-WASM 以 HTTP 動態讀取 Parquet 並渲染圖表。

**存放位置：**
```
output/
  index.html
  traffic-overview/index.html
  search-behavior/index.html
  apply-conversion/index.html
  feature-engagement/index.html
  device-platform/index.html
  page-ranking/index.html
  page-navigation/index.html
  click-heatmap/index.html
    screenshots/
```

## 環境需求

- Python 3.12+（建議使用 [uv](https://github.com/astral-sh/uv) 管理環境）
- 可存取 `https://grafana.web.internal`（內部 Grafana/ES proxy）

安裝依賴：
```bash
uv sync
```

主要套件：`pandas`、`pyarrow`、`playwright`

## 使用方式

### 一鍵執行所有報表

```bash
# 最近 7 天（預設）
uv run python run_all.py

# 指定天數
uv run python run_all.py --days 30

# 指定日期區間
uv run python run_all.py --from 2025-01-01 --to 2025-01-31
```

`run_all.py` 會：
1. 同步 T1 raw 資料（已存在則跳過，不重複抓）
2. 依序執行 8 份報表的完整管線
3. 產生 `output/index.html` 導覽頁面

### 分步執行

```bash
# Step 1：抽取 T1
uv run python extract_raw_events.py --days 7
uv run python extract_raw_events.py --from 2025-01-01 --to 2025-01-31
uv run python extract_raw_events.py --days 7 --keep-existing  # 已存在則跳過

# Step 2：建立 T2（以 traffic-overview 為例）
uv run python build_traffic_overview_t2.py --days 7

# Step 3：渲染 T3 HTML
uv run python render_traffic_overview_t3.py --days 7

# 或一步到位執行單一報表的完整管線
uv run python run_traffic_overview_pipeline.py --days 7
```

### 部署至 GitHub Pages

```bash
# 部署至根目錄
bash deploy.sh

# 部署至版本子目錄（保留舊版）
bash deploy.sh 7 v1-2
```

部署後網址：
- 根目錄：`https://yaochangyu.github.io/job-report/`
- 版本目錄：`https://yaochangyu.github.io/job-report/v1-2/`

## 專案結構

```
├── common/
│   ├── data_pipeline.py     # T1/T2/T3 路徑與契約定義
│   ├── es_client.py         # Grafana _msearch 封裝
│   ├── raw_events.py        # T1 欄位契約與正規化
│   ├── t1_reader.py         # T1 Parquet 讀取工具
│   ├── frontend_shell.py    # 前端殼 HTML 模板
│   ├── html_template.py     # HTML header/footer/style
│   └── chart_helpers.py     # Chart.js 輔助函式
│
├── extract_raw_events.py    # T1 抽取
├── build_*_t2.py            # T2 聚合（各報表）
├── render_*_t3.py           # T3 渲染（各報表）
├── run_*_pipeline.py        # 各報表完整管線（T1→T2→T3）
├── run_all.py               # 一鍵執行所有報表
│
├── *_report.py              # 各報表的查詢與 HTML 產生邏輯
├── click_heatmap_discover.py # 自動探索頁面可點擊元素
├── click_heatmap_config.json # featureId → 元素位置對應表
│
├── app.js                   # 前端殼啟動邏輯
├── app.css                  # 前端殼樣式
├── dashboard-renderers.js   # 各 dashboard 前端 renderer
├── query-definitions.js     # DuckDB 前端查詢定義
├── site-manifest.json       # 站點資產與資料集 manifest
│
├── deploy.sh                # 一鍵部署至 GitHub Pages
├── output/                  # T3 輸出（報表靜態頁面）
├── dataset/                 # T1/T2 資料（本地快取，不進版控）
└── .archive/                # 已完成的設計計畫文件
```

## Click Heatmap 特殊設定

Dashboard 8 需要頁面截圖才能疊加熱點。

**更新截圖：**
```bash
uv run python click_heatmap_discover.py --page /
uv run python click_heatmap_discover.py --page /job/search
```

`click_heatmap_config.json` 記錄各頁面的 `featureId` → 元素位置對應關係，截圖存於 `output/click-heatmap/screenshots/`。

## 資料說明

- 資料來源：Elasticsearch index `operation-logs`，透過內部 Grafana proxy 存取
- 時區：所有時間統一轉為台灣時間（UTC+8）
- `dataset/` 目錄不進版控（`.gitignore` 排除），需在本機重新抓取
