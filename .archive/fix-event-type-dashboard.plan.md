# fix-event-type-dashboard 計畫書

## 背景
T2 parquet 已改為 click/view 各自統計，`query-definitions.js`（DuckDB SQL）與
`dashboard-renderers.js`（KPI 欄位參照）仍使用舊欄位名稱，需一併更新。

各視角的查詢策略：
- **搜尋行為 / 功能互動**：KPI 卡片拆為 click / view 各自顯示；趨勢圖以 click 為主線。
- **頁面導航**：頁面流向（nav/entry）以 view 為主；同步輸出 click 計數。
- **各分佈圖表**：query 加上 `WHERE event_type = 'click'`（互動分析）或 `'view'`（瀏覽分析）。

---

## 步驟

- [x] **步驟 1 — `query-definitions.js`：搜尋行為（searchPlan）**  
  - `kpi`：`SUM(general_click)`、`SUM(general_view)` 等取代舊欄位；新增 `general_click_total`、`general_view_total`、`ai_click_total`、`ai_view_total`、`quick_click_total`、`quick_view_total`、`search_page_click_total`、`search_page_view_total`。  
  - `daily_trend`：改為 `general_click, general_view, ai_click, ai_view`。  
  - `search_page_dist`：加 `WHERE event_type = 'click'`。  
  - `feature_detail`：加 `WHERE event_type = 'click'`。

- [x] **步驟 2 — `dashboard-renderers.js`：搜尋行為（searchRenderer）**  
  - KPI 卡片 1–4 改為顯示 click 總數，5–8 顯示 view 總數。  
  - 趨勢圖改用 `general_click`, `ai_click`。

- [x] **步驟 3 — `query-definitions.js`：功能互動（featurePlan）**  
  - `kpi`：改用 `explore_jobs_click`, `explore_jobs_view`, `explore_corp_click`, `explore_corp_view`, `identity_click`, `identity_view`, `news_click`, `news_view`。  
  - 各分佈 query（`explore_job_category`, `explore_corp_feature`, `identity_dist`, `news_dist`）：加 `WHERE event_type = 'click'`。

- [x] **步驟 4 — `dashboard-renderers.js`：功能互動（featureRenderer）**  
  - KPI 卡片改為 click / view 各自顯示。

- [x] **步驟 5 — `query-definitions.js`：頁面導航（navigationPlan）**  
  - `kpi`：`nav_click + nav_view` 加總為 `nav_total`；新增 `nav_click`, `nav_view`, `entry_click`, `entry_view`。  
  - `entry_dist`：加 `WHERE event_type = 'view'`（頁面進入以瀏覽為準）。  
  - `transition_ranking`, `page_sources`, `page_targets`：加 `WHERE event_type = 'view'`。

- [x] **步驟 6 — `dashboard-renderers.js`：頁面導航（navigationRenderer）**  
  - KPI 卡片加顯示 `nav_view` / `nav_click` 各自數值。

- [x] **步驟 7 — build T2 並部署**  
  執行 `deploy.sh --from 2026-05-01 --to 2026-05-17 --version v1-3`。
