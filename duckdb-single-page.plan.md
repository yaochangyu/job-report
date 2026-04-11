# DuckDB 單頁報表實作計畫

## 目標
將目前「多份靜態 HTML 報表」調整為「單一頁面 + 前端依查詢條件讀取 Parquet + DuckDB-WASM 即時查詢」。

## 架構方向

```
Elasticsearch
    │
    ▼
ETL（Python）
    │
    ├─ 輸出 Parquet 檔
    │
    ▼
單一前端頁面（HTML + JS）
    │
    ├─ 載入 DuckDB-WASM
    ├─ 讀取 Parquet
    └─ 依查詢條件執行 SQL，更新圖表與表格
```

## 範圍說明
- 保留既有 Python ETL 能力，但輸出目標從 `store.db` 改為 Parquet。
- 前端改為單頁模式，不再維護 8 份獨立報表 HTML。
- 查詢條件由前端控制，頁面切換結果時不重新產生 HTML。
- 原本的 `snapshot-refactor.plan.md` 保留作為舊方案參考，不再延伸。

## 實作步驟

- [x] Step 1：盤點目前 8 份報表的查詢欄位與共用指標
  - 先整理哪些資料欄位真的需要進前端查詢，避免把目前每份報表的所有聚合結果原封不動搬過去。
  - 這一步需要先做，因為 Parquet schema 與前端 SQL 設計都要以實際查詢需求為準，否則後面容易重工。

- [x] Step 2：定義 Parquet 輸出格式與檔案切分策略
  - 要先決定是輸出單一大檔、按日期切檔，或按主題切檔，這會直接影響前端載入速度與 GitHub Pages 部署方式。
  - 同時要明確定義欄位型別、時間欄位格式、必要維度與指標欄位，讓 DuckDB-WASM 查詢可以穩定運作。

- [x] Step 3：新增 ETL 輸出 Parquet 的腳本或模式
  - 這一步是資料來源切換的核心，必須讓 Python 端能穩定把 ES 資料轉成前端可讀的 Parquet。
  - 建議盡量沿用現有查詢邏輯，只把輸出層抽換掉，這樣可以減少一次改太多地方造成風險。

- [x] Step 4：建立單一頁面的基本骨架
  - 需要先有唯一入口頁，包含查詢條件區、摘要 KPI 區、圖表區與表格區，才能承接後續查詢結果。
  - 這一步會同時決定前端元件配置，避免之後各區塊輸出格式不一致。

- [x] Step 5：接入 DuckDB-WASM 與 Parquet 載入流程
  - 前端必須先能初始化 DuckDB-WASM、載入 Parquet 檔、建立可重複執行的查詢入口，後續所有功能才有基礎。
  - 這一步是技術可行性的關鍵，若這裡不穩，後面圖表再完整也無法運作。

- [x] Step 6：把查詢條件綁到前端 SQL
  - 需讓日期區間、報表類型、頁面條件等查詢參數能轉成 DuckDB SQL，讓單一頁面真正做到條件切換即時更新。
  - 這一步要明確整理查詢參數與 SQL 模板的對應關係，避免之後條件越加越亂。

- [x] Step 7：重建主要 KPI、圖表與表格呈現
  - 既有報表的商業指標仍要保留，只是改由前端查詢結果驅動，因此需要重新接線，不是單純搬 HTML。
  - 這一步需要先挑核心區塊實作，確保單頁模式能覆蓋你真正要看的內容。

- [x] Step 8：移除或停用多頁靜態報表輸出流程
  - 當單頁查詢可運作後，再收斂 `run_all.py` 與 `output/*/index.html` 的舊路徑，避免未來維護兩套報表流程。
  - 這一步放後面做，能避免在新頁面尚未穩定前就失去舊輸出能力。

- [ ] Step 9：更新文件與專案結構說明
  - 需要同步更新 README、tree.md 與部署說明，否則之後很難看出專案已從 SQLite 靜態報表切到 DuckDB 單頁模式。
  - 文件更新也是交接的一部分，尤其資料來源與部署方式都已改變。

## 注意事項
- DuckDB-WASM 方案適合公開資料；若資料不可公開，這條路不適合。
- Parquet 檔案大小要控制，否則前端首次載入會太慢。
- ES 的 `cardinality` 跨區間仍不可精確合併，前端查詢也不會自動解決這個限制。
- 若要長期保留舊方案，應把新舊流程明確分開，避免 ETL 輸出互相污染。

## Step 1 盤點結果

### 報表與查詢對應

| 報表 | 主要查詢 |
|------|----------|
| `traffic_overview_report.py` | `query_kpi`、`query_daily_trend`、`query_hourly_distribution`、`query_device_distribution` |
| `search_behavior_report.py` | `query_search_overview`、`query_daily_search_trend`、`query_search_page_dist`、`query_ai_interaction`、`query_quick_filter` |
| `apply_conversion_report.py` | `query_apply_kpi`、`query_apply_source`、`query_apply_daily_trend`、`query_funnel`、`query_apply_device`、`query_apply_hourly` |
| `feature_engagement_report.py` | `query_explore_jobs`、`query_explore_corp`、`query_identity`、`query_news` |
| `device_platform_report.py` | `query_device_daily`、`query_os_browser`、`query_device_behavior`、`query_os_behavior` |
| `page_ranking_report.py` | `query_feature_ranking`、`query_category_summary` |
| `page_navigation_report.py` | `query_nav_pairs`、`query_entry_pages`、`query_page_sources`、`query_page_destinations` |
| `click_heatmap_report.py` | `query_page_clicks` |

### 跨報表共用核心維度

- 時間：`date`、`hour`
- 事件：`eventType`、`action`、`sessionId`
- 平台：`deviceType`、`os`、`browser`
- 頁面 / 功能：`featureId`、`pagePath`、`previousPagePath`
- metadata：`source`、`categoryTab`、`identityType`、`industryTab`

### 跨報表共用核心指標

- `total`
- `views`
- `clicks`
- `applies`
- `sessions`
- `count`

### 單頁前端需要覆蓋的主要呈現

- KPI 卡片：總事件、view、click、apply、sessions、轉換率、裝置占比
- 趨勢圖：每日趨勢、每小時趨勢、AI vs 一般搜尋趨勢、每日應徵趨勢
- 分佈圖：裝置、OS、browser、來源、功能分類、搜尋結果頁分佈
- 表格：排行表、來源/目標頁、Top feature、Top click element

### 需單獨處理的特殊欄位

- 頁面導航：`from`、`to`、`label`
- 點擊熱點：頁面路徑對應的 `featureId` 點擊數，且後續仍需搭配設定檔中的元素座標
- 漏斗：固定階段名稱與排序，不能只靠一般 count 聚合
- 功能分類：`featureId` 對 `category` 的對照需保留映射規則

### 對 Step 2 的結論

- Parquet 不應直接沿用目前每份報表的聚合 JSON 結果，應改為可重用的查詢底表。
- 建議以「事件寬表」為主，至少涵蓋時間、裝置、頁面、功能與 metadata 維度。
- 建議優先以 `date` 做切分，讓前端可以依日期區間載入需要的 Parquet 檔。
- 若資料量偏大，再補每日預聚合表給 KPI 與熱門排行使用。

## Step 2 決策

### Dataset 目錄

```text
dataset/
└── events/
    └── date=YYYY-MM-DD/
        └── events.parquet
```

- 主資料集固定為 `dataset/events`
- 以 `date` 作為唯一 partition key
- 同一天只保留單一 `events.parquet`，避免靜態部署下產生過多小檔

### Schema 決策

- 主表名稱：`events`
- schema 版本：`v1`
- 排序欄位：`date`、`occurred_at`、`feature_id`、`event_type`
- 壓縮：`zstd`
- row group：100,000 rows

### 事件寬表欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | date | 台灣時區日期 |
| `hour` | tinyint | 台灣時區小時 |
| `occurred_at` | timestamp | 原始事件時間 |
| `system` | string | 系統名稱 |
| `event_type` | string | view / click |
| `action` | string | apply 等動作 |
| `session_id` | string | session 去重 |
| `feature_id` | string | featureId |
| `page_path` | string | pageUrl 正規化後路徑 |
| `previous_page_path` | string | previousPageUrl 正規化後路徑 |
| `device_type` | string | mobile / desktop |
| `os` | string | 作業系統 |
| `browser` | string | 瀏覽器 |
| `source` | string | metadata.source |
| `category_tab` | string | metadata.categoryTab |
| `identity_type` | string | metadata.identityType |
| `industry_tab` | string | metadata.industryTab |

### 延伸表策略

- 先只實作 `events` 主表，確保單頁查詢可跑通
- 預聚合表維持為可選擴充：
  - `daily_kpi`
  - `daily_feature`
  - `daily_page_navigation`

### 程式落點

- 共用 schema 與輸出規則統一定義在 `common/parquet_schema.py`
- Step 3 的 ETL 與後續前端 manifest 都必須沿用這份定義

## Step 3 產出

- 新增 `extract_events.py`
  - 依日期或日期區間抓取 ES 原始事件
  - 以 `search_after` 分頁抓取資料
  - 每日輸出到 `dataset/events/date=YYYY-MM-DD/events.parquet`
- 新增 `common/parquet_dataset.py`
  - 處理欄位正規化、Parquet 寫入、manifest 更新
- `common/es_client.py`
  - 補上 `es_search()` 供原始事件 ETL 使用
- `pyproject.toml`
  - 加入 `pyarrow`

## Step 4 產出

- 建立 `frontend/` 靜態單頁骨架
  - `frontend/index.html`
  - `frontend/app.css`
  - `frontend/app.js`
- 畫面已先放入：
  - 查詢條件區
  - 資料集 / DuckDB 狀態區
  - KPI 區
  - 圖表區
  - 表格區
- `app.js` 先處理預設日期與基本狀態顯示，Step 5 再接上 DuckDB 與 manifest

## Step 5 產出

- `frontend/app.js`
  - 接入 DuckDB-WASM CDN bundle
  - 啟動 `AsyncDuckDB`
  - 載入 `dataset/manifest.json`
  - 依 manifest 註冊 Parquet 檔案 URL
  - 建立 `events` view 作為後續 SQL 查詢入口
- `frontend/index.html`
  - 新增已載入日期與資料列數狀態欄位

## Step 6 產出

- 新增 `frontend/query-definitions.js`
  - 依 `view_mode` 產生對應 SQL
  - 支援 overview、search、apply、feature、device、ranking、navigation、heatmap
- `frontend/app.js`
  - 表單送出時會真正執行 DuckDB 查詢
  - 查詢結果會先顯示在查詢記錄與主表格

## Step 7 產出

- 新增 `frontend/dashboard-renderers.js`
  - 依不同 view mode 更新 KPI
  - 依不同查詢結果更新 3 個圖表
  - 回傳表格資料，供主表格渲染
- `frontend/app.js`
  - 查詢完成後不再只顯示 raw JSON，會同步刷新 KPI、圖表與表格

## Step 8 產出

- `run_all.py`
  - 不再呼叫 8 份報表腳本
  - 改為把 `frontend/` 與 `dataset/` 組裝成可部署站台
- `deploy.sh`
  - 部署前先執行 `extract_events.py`
  - 以 Parquet dataset + 單頁網站作為新的 GitHub Pages 輸出

## 執行方式
- 目前僅建立新計畫書，不實作程式。
- 待你確認後，再依步驟逐步實作；若你下「自動執行」，就可連續往下做。
