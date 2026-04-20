# job-report

1111人力銀行前端行為分析報告系統。從 Elasticsearch 抽取使用者事件，經三層資料管線處理，產出可部署至 GitHub Pages 的靜態分析報表。

## 架構概覽

```
Elasticsearch (operation-logs)
        │
        ▼  extract_raw_events.py
dataset/events/date=YYYY-MM-DD/events.parquet   ← T1 原始事件（僅本機）
        │
        ▼  build_*_t2.py
dataset/report/<報表名>/range=from_to/*.parquet  ← T2 聚合結果（部署至 GitHub Pages）
        │
        ▼  render_*_t3.py + build_shell_pages()
output/<報表名>/index.html                        ← T3 前端殼（空 HTML）
```

所有報表輸出至 `output/`，透過 `deploy.sh` 推送至 GitHub Pages。頁面本身是前端殼（空 HTML），`app.js` 啟動後以 HTTP 抓取 **T2 預聚合 Parquet**，由 DuckDB-WASM 在瀏覽器動態查詢渲染，無需後端服務。T1 原始事件體積龐大，**不部署**至 GitHub Pages。

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

從 Elasticsearch index `operation-logs`（filter: `system=jobbank-web`）抽取原始事件，以 `search_after` 分批查詢（每批 5000 筆），按日存成 Parquet（zstd 壓縮）。**僅存於本機**，不部署至 GitHub Pages。

**存放位置：**
```
dataset/events/
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

### T2 — 聚合結果（部署至 GitHub Pages）

每份報表各自的 `build_*_t2.py` 讀取 T1 Parquet，依報表需求計算聚合，輸出多個主題的 Parquet 檔。**這是瀏覽器端實際讀取的資料**，體積小（KB 級），DuckDB-WASM 可快速載入。

**存放位置：**
```
dataset/report/
  traffic-overview/
    range=2025-01-01_2025-01-31/
      kpi.parquet          # 單列 KPI（total/views/clicks/applies/sessions/rates）
      daily.parquet        # 每日彙總
      hourly.parquet       # 每小時平均
      device_type.parquet  # 裝置分佈（name, count）
      os.parquet           # OS 分佈
      browser.parquet      # 瀏覽器分佈
  search-behavior/range=.../
    summary.parquet        # 各搜尋類型總計
    feature_counts.parquet # featureId × count
    daily_trend.parquet    # 每日 general/ai 趨勢
    search_page_dist.parquet
    ai_interaction.parquet
    quick_overview.parquet
    quick_daily.parquet
  apply-conversion/range=.../
    kpi.parquet / source.parquet / daily.parquet
    funnel.parquet / device.parquet / os.parquet / hourly.parquet
  feature-engagement/range=.../
    explore_jobs_features.parquet / explore_jobs_category_tabs.parquet
    explore_jobs_identity_types.parquet / explore_jobs_daily.parquet
    explore_corp_features.parquet / explore_corp_industry_tabs.parquet
    identity_main.parquet / identity_all.parquet
    news_features.parquet / news_categories.parquet
  device-platform/range=.../
    summary.parquet / device_total.parquet / daily.parquet
    os.parquet / browser.parquet / device_behavior.parquet / os_behavior.parquet
  page-ranking/range=.../
    summary.parquet / features.parquet / categories.parquet
  page-navigation/range=.../
    summary.parquet / nav_pairs.parquet / entry_pages.parquet
    page_sources.parquet / page_destinations.parquet
  click-heatmap/range=.../
    click_counts.parquet   # page_path × feature_id × count
```

### T3 — 報表頁（前端殼 + DuckDB-WASM）

`render_*_t3.py` 產生中間 HTML，但 `run_all.py` 最後會呼叫 `build_shell_pages()` 將輸出覆蓋為前端殼（空白 HTML）。實際部署的 `index.html` 是空殼，資料在瀏覽器端由 `app.js` 動態處理：

1. 載入 `dataset/manifest.json` → 取得 `datasetRoot`（GitHub Pages 上的 dataset 根 URL）與可用日期列表
2. 初始化 DuckDB-WASM（從 CDN 下載 WASM binary，約 3–5 秒）
3. 依使用者選取的視角與日期區間，從 `dataset/report/<報表名>/range=<from>_<to>/` 並行 fetch T2 Parquet，以 `registerFileBuffer` 注入 DuckDB
4. 執行 SQL 查詢、渲染 Chart.js 圖表與表格

**存放位置：**
```
output/
  index.html
  app.js / app.css / query-definitions.js / dashboard-renderers.js
  dataset/
    manifest.json            # 可用日期清單（app.js 啟動時讀取）
    report/                  # T2 聚合 Parquet（各報表）
  traffic-overview/index.html
  search-behavior/index.html
  apply-conversion/index.html
  feature-engagement/index.html
  device-platform/index.html
  page-ranking/index.html
  page-navigation/index.html
  click-heatmap/index.html
```

> **注意**：T1 原始事件（`dataset/events/`）**不進入** `output/`，不部署至 GitHub Pages。

## 前端查詢策略

`query-definitions.js` 中每個 dashboard 直接讀取 T2 預聚合 Parquet，無 T1 fallback。`f.datasetRoot` 未設定時拋出錯誤（代表 manifest.json 載入失敗）。

| 視角 | 支援 pagePath 篩選 | 說明 |
|------|-------------------|------|
| overview / ranking | ✗ | T2 是跨所有頁面的整體聚合，無法 per-page 過濾 |
| navigation / heatmap | ✓ | T2 保留 page 維度，可用 pagePath 過濾 |
| 其他視角 | ✗ | 無 pagePath 欄位 |

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
1. 同步 T1 raw 資料至 `dataset/events/`（已存在則跳過，不重複抓）
2. 依序執行 8 份報表的完整管線（T1 → T2 → T3 shell）
3. 產生 `output/dataset/manifest.json`（日期清單，供 `app.js` 啟動用）
4. 複製 `dataset/report/` 至 `output/dataset/report/`（**僅 T2**，不含 T1 raw）
5. 產生 `output/index.html` 導覽頁面

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
├── app.js                   # 前端殼啟動邏輯（T2 路徑，registerFileBuffer 並行載入）
├── app.css                  # 前端殼樣式
├── dashboard-renderers.js   # 各 dashboard 前端 renderer
├── query-definitions.js     # DuckDB 前端查詢定義（T2/T1 雙路徑）
├── site-manifest.json       # 站點資產與資料集 manifest
│
├── deploy.sh                # 一鍵部署至 GitHub Pages
├── output/                  # T3 輸出（報表靜態頁面 + T2 Parquet）
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
- T1 原始事件不部署至 GitHub Pages，瀏覽器端只讀取 T2 聚合 Parquet
