# job-report

1111人力銀行前端行為分析報告系統。從 Elasticsearch 抽取使用者事件，經三層資料管線處理，產出可部署至 GitHub Pages 的靜態分析報表。

**已部署網址：**
- 最新版：`https://yaochangyu.github.io/job-report/v1-3/`
- 根目錄：`https://yaochangyu.github.io/job-report/`

## 架構概覽

```
Elasticsearch (operation-logs)
        │
        ▼  extract_raw_events.py
dataset/t0-raw/date=YYYY-MM-DD/events.parquet       ← T0 純原始事件（僅本機，不可變）
        │
        ▼  enrich_t1_events.py（批次查 Solr + Matching ES）
dataset/t1-enrich/date=YYYY-MM-DD/events.parquet        ← T1 補強事件（僅本機）
        │
        ▼  builders/build_*_t2.py  （day-keyed，每天一個分區）
dataset/t2-report/<報表名>/date=YYYY-MM-DD/
    daily_summary.parquet                        ← 當日 KPI 摘要（一列）
    <detail>.parquet                             ← 各 view 必要明細（分佈/排行等）
        │
        ▼  build_shell_pages()
output/<報表名>/index.html                        ← T3 前端殼（空 HTML）
```

所有報表輸出至 `output/`，透過 `deploy.sh` 推送至 GitHub Pages。頁面本身是前端殼（空 HTML），`app.js` 依使用者選取的日期區間，**逐日 fetch T2 Parquet**，由 DuckDB-WASM 在瀏覽器即時跨天聚合渲染，無需後端服務。T0/T1 原始事件體積龐大，**不部署**至 GitHub Pages。

## 報表清單

| # | 報表 | 說明 |
|---|------|------|
| 1 | Traffic Overview | KPI 指標、每日流量趨勢、每小時分佈、裝置與 OS 分佈 |
| 2 | Search Behavior | AI vs 一般搜尋趨勢、搜尋結果頁分佈、AI 互動方式 |
| 3 | Apply Conversion | 應徵漏斗、每日趨勢、來源分佈、裝置與時段分析 |
| 4 | Apply Journey | 使用者從進站到送出應徵的完整頁面路徑排行與步驟分佈 |
| 5 | Feature Engagement | 探索職缺/企業、身份辨識、產業 Tab、新聞互動 |
| 6 | Device & Platform | Mobile/Desktop 趨勢、OS 與瀏覽器分佈 |
| 7 | Page Ranking | featureId 排行 Top 20、功能類別佔比 |
| 8 | Page Navigation Flow | 頁面轉換路徑排行、各頁面來源/目標 |
| 9 | Page Click Heatmap | 截圖疊加點擊次數，呈現各頁面按鈕點擊熱點 |
| 10 | Homepage Blocks | 搜尋、身分類別、探索工作、探索企業各區塊每日點擊數 |
| 11 | Apply Job Category | 應徵者最常應徵的職類與產業 TOP 30 排行及每日趨勢（JOIN Matching ES job metadata） |
| 12 | Apply Demographics | 應徵者性別分佈、年齡層分佈與每日趨勢（JOIN core6 Solr 履歷資料） |
| 13 | Period Report | 依月份、季度、年度瀏覽各類別聚合趨勢與明細報表，月報可切換日報明細 |

## 資料管線詳細說明

### T0 — 純原始事件

從 Elasticsearch index `operation-logs`（filter: `system=jobbank-web`）抽取原始事件，以 `search_after` 分批查詢（每批 5000 筆），按日存成 Parquet（zstd 壓縮）。**不可變、僅存於本機**，不部署至 GitHub Pages。

**存放位置：**
```
dataset/t0-raw/
  date=2025-01-01/events.parquet
  date=2025-01-02/events.parquet
  ...
dataset/manifest/t0-raw-manifest.json
```

**欄位：**

| 欄位 | 說明 |
|------|------|
| `date` / `hour` / `occurred_at` | 台灣時區事件時間 |
| `event_type` / `action` | 事件種類（view / click / apply…） |
| `session_id` / `anonymous_id` / `user_id` / `client_id` | 身份識別 |
| `feature_id` / `feature_name` / `feature_type` | 觸發的功能元件 |
| `page_url` / `previous_page_url` | ES 原始 URL |
| `device_type` / `os` / `browser` | 裝置資訊 |
| `source` / `category_tab` / `identity_type` / `industry_tab` | 來自 ES `metadata` 的額外維度 |
| `job_id` / `company_id` | 來自 ES `metadata.jobId` / `metadata.companyId`，apply 事件帶有職缺與公司 ID |

### T1 — 補強事件

讀取 T0 Parquet，對 `action=apply` 事件批次查詢外部服務，補入人口屬性與職缺 metadata，寫入 `dataset/t1-enrich/`。**僅存於本機**，不部署至 GitHub Pages。T2 builder 統一從 T1 讀取資料。

**存放位置：**
```
dataset/t1-enrich/
  date=2025-01-01/events.parquet
  date=2025-01-02/events.parquet
  ...
dataset/manifest/t1-enrich-manifest.json
```

**T1 在 T0 基礎上新增的欄位：**

| 欄位 | 來源 | 說明 |
|------|------|------|
| `page_path` / `previous_page_path` | T0 page_url 正規化 | 所有事件都有 |
| `sex_i` | core6 Solr | apply 事件；1=男, 2=女, null=查無資料 |
| `birth_dt` | core6 Solr | apply 事件；ISO 8601 UTC 格式（如 `1990-01-15T16:00:00Z`） |
| `job_positions` | Matching ES | apply 事件；`list[str]`，職類名稱 |
| `company_industries` | Matching ES | apply 事件；`list[str]`，產業名稱 |

非 apply 事件的 sex_i / birth_dt / job_positions / company_industries 皆為 `null`。

### T2 — 聚合結果（部署至 GitHub Pages）

每份報表各自的 `build_*_t2.py` 讀取 T1 Parquet，以 **day-keyed** 方式輸出：每個日期獨立一個 `date=YYYY-MM-DD/` 分區。**這是瀏覽器端實際讀取的資料**，體積小（KB 級），DuckDB-WASM 可快速載入。

前端依所選日期區間並行 fetch 所有日期的 Parquet，再以 DuckDB-WASM 跨天 `SUM` / `GROUP BY` 聚合。

**存放位置（每個日期分區內的檔案）：**
```
dataset/t2-report/
  traffic-overview/date=YYYY-MM-DD/
    daily_summary.parquet  # date, views, clicks, applies, sessions
    device_type.parquet    # name, count
    os.parquet             # name, count
    browser.parquet        # name, count
  search-behavior/date=YYYY-MM-DD/
    daily_summary.parquet  # date, general, ai, quick, search_page
    feature_counts.parquet # feature_id, count
    search_page_dist.parquet # name, count
  apply-conversion/date=YYYY-MM-DD/
    daily_summary.parquet  # date, applies, job_views
    funnel.parquet / device.parquet / os.parquet / source.parquet
  apply-journey/date=YYYY-MM-DD/
    daily_summary.parquet    # date, total_sessions, apply_sessions, apply_rate
    path_ranking.parquet     # path（頁面序列）× session_count
    step_distribution.parquet # step（第幾步）× count
    entry_page.parquet       # page_path × session_count（第一頁分佈）
  feature-engagement/date=YYYY-MM-DD/
    daily_summary.parquet  # date, explore_jobs, explore_corp, identity, news
    explore_jobs_features.parquet / explore_jobs_category_tabs.parquet
    explore_corp_features.parquet
    identity_main.parquet / identity_all.parquet / news_features.parquet
  device-platform/date=YYYY-MM-DD/
    daily_summary.parquet  # date, mobile, desktop
    os.parquet / browser.parquet / device_behavior.parquet / os_behavior.parquet
  page-ranking/date=YYYY-MM-DD/
    daily_summary.parquet  # date, total_events, total_features, top_feature_id, top_feature_total
    features.parquet / categories.parquet
  page-navigation/date=YYYY-MM-DD/
    daily_summary.parquet  # date, nav_total, entry_total, tracked_pages
    nav_pairs.parquet / entry_pages.parquet
    page_sources.parquet / page_destinations.parquet
  click-heatmap/date=YYYY-MM-DD/
    daily_summary.parquet  # date, total_clicks, feature_count, top_feature_id, top_count
    click_counts.parquet   # page_path × feature_id × count
  homepage-blocks/date=YYYY-MM-DD/
    daily_summary.parquet   # date, total_clicks, total_views, feature_count, top_feature_id, top_count
    feature_counts.parquet  # event_type × feature_id × feature_name × count × date
    click_counts.parquet    # feature_id × count × date（點擊熱點視角用）
  apply-job-category/date=YYYY-MM-DD/
    daily_summary.parquet         # date, total_applies, applies_with_metadata, coverage_rate
    job_position_top.parquet      # name（職類）× count，TOP 30
    company_industry_top.parquet  # name（產業）× count，TOP 30
    job_position_daily.parquet    # date × name × count（TOP 10 職類每日趨勢）
    company_industry_daily.parquet # date × name × count（TOP 10 產業每日趨勢）
  apply-demographics/date=YYYY-MM-DD/
    daily_summary.parquet         # date, total_applies, applies_with_metadata, coverage_rate
    gender.parquet                # gender（男/女/未知）× count
    age_groups.parquet            # age_group（<25/25-29/.../50+/未知）× count
    gender_daily.parquet          # date × gender × count
    age_groups_daily.parquet      # date × age_group × count
```

> **apply-job-category 資料來源**：apply 事件的 `job_positions` / `company_industries` 欄位在 T1 enrichment 階段已補強（Matching ES `search-jobs-v1-*`）。T2 builder 直接讀取，不重複查詢。只有現存職缺可以 JOIN，已下架職缺不計入（覆蓋率約 98%）。

> **apply-demographics 資料來源**：apply 事件的 `sex_i` / `birth_dt` 欄位在 T1 enrichment 階段已補強（core6 Solr）。年齡以**事件日期**為基準計算，分為 `<25 / 25-29 / 30-34 / 35-39 / 40-44 / 45-49 / 50+` 七個年齡層。尚未建立履歷的使用者為 `null`，歸為「未知」（覆蓋率約 71%）。

### T3 — 報表頁（前端殼 + DuckDB-WASM）

實際部署的 `index.html` 是空殼，資料在瀏覽器端由 `app.js` 動態處理：

1. 載入 `dataset/manifest.json` → 取得 `datasetRoot` 與 T2 可查日期列表（`available_dates`）
2. 初始化 DuckDB-WASM（從 CDN 下載 WASM binary，約 3–5 秒）
3. 使用者選取日期區間後，計算 `fetchDates`（與 `available_dates` 取交集），並行 fetch 每個日期的 T2 Parquet，以 `registerFileBuffer` 注入 DuckDB
4. 執行跨天 SQL 聚合（`SUM` / `GROUP BY date`）、渲染 Chart.js 圖表與表格
5. 若部分日期 404，顯示 warning banner「資料涵蓋 N 天（缺少：...）」，其餘日期仍正常查詢


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
  apply-journey/index.html
  feature-engagement/index.html
  device-platform/index.html
  page-ranking/index.html
  page-navigation/index.html
  click-heatmap/index.html
  homepage-blocks/index.html
  period-report/index.html
```

> **注意**：T0/T1 原始事件（`dataset/t0-raw/`、`dataset/t1-enrich/`）**不進入** `output/`，不部署至 GitHub Pages。

## 外部資料來源查詢方式

### T0 — operation-logs（Elasticsearch）

透過內部 Grafana Datasource Proxy 發送 `_msearch` 請求，以 `search_after` 分頁抽取，每批 5,000 筆：

```
POST https://grafana.web.internal/api/datasources/proxy/uid/{DATASOURCE_UID}/_msearch
Content-Type: application/x-ndjson

{"index": "operation-logs"}
{"query": {"bool": {"filter": [{"term": {"system": "jobbank-web"}}, {"range": {"@timestamp": {...}}}]}}, "size": 5000, "sort": [...], "search_after": [...]}
```

相關模組：`common/es_client.py`、`tools/extract_raw_events.py`

---

### T1 enrichment — Matching ES（search-jobs-v1-*）

apply 事件取出 `job_id`，批次送往 Matching ES 查詢職類與產業，同樣透過 Grafana Proxy，每批 500 筆：

```
POST https://grafana.web.internal/api/datasources/proxy/uid/{MATCHING_ES_UID}/_msearch
Content-Type: application/x-ndjson

{"index": "search-jobs-v1-*"}
{"size": 500, "_source": ["id", "jobPositionNames", "companyIndustryNames"], "query": {"terms": {"id": [job_id, ...]}}}
```

相關模組：`common/job_metadata.py`、`tools/enrich_t1_events.py`

---

### T1 enrichment — core6 Solr

apply 事件取出 `user_id`，批次送往 core6 Solr 查詢履歷基本資料，每批 200 筆：

```
GET http://solr.web.internal:8985/solr/core6/select
  ?q=talentNo_l:(id1 OR id2 OR ...)
  &fl=talentNo_l,sex_i,birth_dt
  &rows=200
  &wt=json
```

回傳標準 Solr JSON（`response.docs`），`sex_i`：1=男、2=女；`birth_dt`：ISO 8601 UTC 格式。

相關模組：`common/resume_metadata.py`、`tools/enrich_t1_events.py`

---

## 前端查詢策略

`query-definitions.js` 以 `f.fetchDates` 陣列驅動，每個視角的 plan 函式返回：
- `registerFiles`：所有需要 fetch 的 parquet（每天 × 每個角色）
- `buildQueries(loadedByRole)`：依實際載入成功的 aliases 動態建構 DuckDB SQL

跨天聚合範例：
```sql
-- KPI（SUM 所有天）
SELECT SUM(views), SUM(clicks) FROM read_parquet(['date1/daily_summary.parquet', ...])

-- 趨勢（GROUP BY date）
SELECT date, views, clicks FROM read_parquet([...]) ORDER BY date

-- 分佈（去重合算）
SELECT name, SUM(count) AS count FROM read_parquet([...]) GROUP BY name ORDER BY count DESC
```

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

`run_all.py` 會依序執行四個階段（`t0` → `t1` → `report` → `html`）：

| 階段     | 對應目錄              | 動作                                          |
|----------|-----------------------|-----------------------------------------------|
| `t0`     | `dataset/t0-raw/`        | 從 Elasticsearch 抽取純原始事件               |
| `t1`     | `dataset/t1-enrich/`         | 補強 Solr/Matching ES metadata（apply 事件）  |
| `report` | `dataset/t2-report/`     | 建立 T2 day-keyed parquet                     |
| `html`   | `output/`             | 產生 manifest 與 HTML shell                   |

### 指定執行階段

```bash
# T0/T1 已抓過，只跑 T2 + HTML
uv run python run_all.py --from 2025-01-01 --to 2025-01-31 --steps report,html

# T0 已抓，重跑 T1 補強（例如 Solr 掉線後補跑）
uv run python run_all.py --from 2025-01-01 --to 2025-01-31 --steps t1,report,html

# 只重新產 HTML（T2 不變）
uv run python run_all.py --steps html
```

### 分步執行

```bash
# Step 1：抽取 T0
uv run python tools/extract_raw_events.py --days 7
uv run python tools/extract_raw_events.py --from 2025-01-01 --to 2025-01-31
uv run python tools/extract_raw_events.py --days 7 --keep-existing  # 已存在則跳過

# Step 2：補強 T1（需 T0 先存在）
uv run python tools/enrich_t1_events.py --days 7
uv run python tools/enrich_t1_events.py --from 2025-01-01 --to 2025-01-31
uv run python tools/enrich_t1_events.py --days 7 --keep-existing  # 已存在則跳過

# Step 3：建立 T2（以 traffic-overview 為例）
uv run python builders/build_traffic_overview_t2.py --days 7
```

### 驗證 T2 資料正確性

```bash
uv run python tests/validation/validate_dashboard_data.py --from 2025-01-01 --to 2025-01-31
```

比對瀏覽器內 `executeViewQueries()` 的實際查詢結果是否與 `output/dataset/report` 中的 T2 parquet 聚合一致，驗證 `feature`、`device`、`ranking`、`heatmap`、`navigation` 五個 view 的 KPI。

### 部署至 GitHub Pages

```bash
# 部署至根目錄
bash deploy.sh

# 部署至版本子目錄（保留舊版）
bash deploy.sh 7 v1-3
```

部署後網址：
- 根目錄：`https://yaochangyu.github.io/job-report/`
- 版本目錄：`https://yaochangyu.github.io/job-report/v1-3/`

## 專案結構

```
├── builders/
│   ├── build_*_t2.py        # T2 day-keyed 聚合（各報表）
│   └── build_period_summary.py  # 月報/季報/年報聚合（planned）
│
├── common/
│   ├── data_pipeline.py     # T1/T2/T3 路徑與契約定義
│   ├── es_client.py         # Grafana _msearch 封裝
│   ├── job_metadata.py      # 批次查詢 search-jobs-v1-* 取職類/產業（Matching ES）
│   ├── resume_metadata.py   # 批次查詢 core6 Solr 取應徵者 sex_i/birth_dt
│   ├── raw_events.py        # T1 欄位契約與正規化
│   ├── t1_reader.py         # T1 Parquet 讀取工具
│   ├── frontend_shell.py    # 前端殼 HTML 模板
│   ├── html_template.py     # HTML header/footer/style
│   └── chart_helpers.py     # Chart.js 輔助函式
│
├── exporters/               # 資料匯出腳本
│
├── frontend/
│   ├── app.js               # 前端殼啟動邏輯
│   ├── app.css              # 前端殼樣式
│   ├── dashboard-renderers.js # 各 dashboard 前端 renderer
│   ├── query-definitions.js # DuckDB 前端查詢定義
│   └── site-manifest.json   # 站點資產與資料集 manifest
│
├── tools/
│   ├── extract_raw_events.py    # T1 抽取
│   ├── query_homepage_blocks.py # 首頁區塊點擊查詢
│   └── click_heatmap_discover.py # 自動探索頁面可點擊元素
│
├── run_all.py               # 一鍵執行所有報表
│
├── click_heatmap_config.json # featureId → 元素位置對應表
│
├── app.js                   # 前端殼啟動邏輯（T2 路徑，registerFileBuffer 並行載入）
├── app.css                  # 前端殼樣式
├── dashboard-renderers.js   # 各 dashboard 前端 renderer
├── query-definitions.js     # DuckDB 前端查詢定義（純 T2，無 fallback）
├── site-manifest.json       # 站點資產與資料集 manifest
│
├── deploy.sh                # 一鍵部署至 GitHub Pages
├── tests/
│   └── validation/
│       └── validate_dashboard_data.py # Dashboard 查詢結果與 T2 parquet 一致性驗證
├── output/                  # T3 輸出（報表靜態頁面 + T2 Parquet）
├── dataset/                 # T1/T2 資料（本地快取，不進版控）
└── .archive/                # 已完成的設計計畫文件
```

## Click Heatmap 特殊設定

Dashboard 8 需要頁面截圖才能疊加熱點。

**更新截圖：**
```bash
uv run python tools/click_heatmap_discover.py --page /
uv run python tools/click_heatmap_discover.py --page /job/search
```

`click_heatmap_config.json` 記錄各頁面的 `featureId` → 元素位置對應關係，截圖存於 `output/click-heatmap/screenshots/`。

## 資料說明

- 資料來源：Elasticsearch index `operation-logs`，透過內部 Grafana proxy 存取
- 時區：所有時間統一轉為台灣時間（UTC+8）
- `dataset/` 目錄不進版控（`.gitignore` 排除），需在本機重新抓取
- T1 原始事件不部署至 GitHub Pages，瀏覽器端只讀取 T2 聚合 Parquet
