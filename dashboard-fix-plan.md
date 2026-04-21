# Dashboard 修正計劃書

## 問題

目前 8 個 dashboard view 中，`feature`、`device`、`ranking`、`heatmap`、`navigation` 與 T2 day-keyed 資料存在語意或聚合不一致；其中 `navigation` 另有明顯效能問題。

## 修正原則

- [x] 先修 correctness，再處理 performance，避免先優化錯的指標。
- [x] 優先修正前端 query / renderer 的聚合語意，避免把跨日 distinct 誤算成每日加總。
- [x] `navigation` 額外調整 builder 端輸出，縮小查詢與渲染資料量。

## 實作步驟

### A. feature

- [x] **調整身份辨識 KPI 文案**：原文案寫成「7 種身份類型」，但目前數值來自所有 `identify-*` 互動總數，不只 7 類；因此只改 `dashboard-renderers.js` 文案，讓畫面語意與既有 T2 定義一致。

### B. device

- [x] **補回 OS / Browser distinct KPI**：在 `query-definitions.js` 的 `devicePlan().kpi` 補 `os_count` 與 `browser_count`，直接從完整 parquet 做 `COUNT(DISTINCT name)`，避免受 top-N limit 影響。

### C. ranking

- [x] **修正跨日聚合 KPI 口徑**：將 `total`、`feature_count`、`top_feature`、`top_count` 改由 `features.parquet` 跨區間重新聚合，不再使用每日摘要相加。
- [x] **修正類別圖資料來源**：renderer 改直接使用 `categories` query，避免用 Top 30 排名反推整體類別分布。
- [x] **修正排行表格語意**：移除 ranking query 的 `LIMIT 30`，讓表格資料與「完整排行」語意一致。

### D. heatmap

- [x] **修正 heatmap KPI 口徑**：改由 `click_counts.parquet` 跨日聚合計算 `total_clicks`、`feature_count`、`top_feature`、`top_count`，避免每日 distinct 相加造成高估。

### E. navigation

- [x] **修正 navigation KPI 語意**：`page_count` 改由明細 parquet 做跨區間 distinct page 計算，不再使用每日 `tracked_pages` 相加。
- [x] **修正文案**：KPI「導航轉換事件」改為「導航事件總數」，副標改成「全部 from→to 轉換事件」，避免誤導成 Top 30 合計。
- [x] **限制 query 預設輸出量**：未指定 `pagePath` 時限制 `page_sources` / `page_targets` 查詢列數，降低 DuckDB-WASM 與前端傳輸負擔。
- [x] **限制 renderer 預設渲染量**：前端表格預設只插入前 100 筆，避免一次渲染過大 DOM。
- [x] **保留 builder 端縮表策略**：`build_page_navigation_t2.py` 使用每頁 top-N 關聯輸出，持續控制 parquet 體積。

## 測試與驗證步驟

### 1. Build / 語法檢查

- [x] **檢查前端 JS 語法**：執行 `node --check query-definitions.js` 與 `node --check dashboard-renderers.js`，確認修改後沒有語法錯誤。
- [x] **重建輸出**：執行 `uv run python run_all.py --from 2026-04-05 --to 2026-04-13 --skip-extract`，確認 T2 parquet 與 frontend shell 可完整重建。

### 2. 資料正確性驗證

- [x] **驗證 device KPI**：直接讀取 `output/dataset/report/device-platform/...`，確認 distinct OS / browser 數量正確。
- [x] **驗證 ranking KPI**：直接讀取 `output/dataset/report/page-ranking/...`，確認跨日 distinct `featureId`、Top 1 feature 與總量正確。
- [x] **驗證 heatmap KPI**：直接讀取 `output/dataset/report/click-heatmap/...`，確認跨日 distinct `feature_id`、Top 1 feature 與總量正確。
- [x] **驗證 navigation KPI**：直接讀取 `output/dataset/report/page-navigation/...`，確認 `page_count` 來自跨日 distinct page，而不是每日相加。
- [x] **整理成可重複執行腳本**：新增 `validate_dashboard_data.py`，自動比對瀏覽器內 `executeViewQueries()` 的實際輸出與 parquet 重算結果。

### 3. UI 手動驗證

- [ ] **檢查 feature 頁**：確認身份辨識 KPI 副標文案與資料定義一致。
- [ ] **檢查 device 頁**：確認 OS / 瀏覽器種類 KPI 有正確數值。
- [ ] **檢查 ranking 頁**：確認功能數量、Top 1、類別圖與資料口徑一致。
- [ ] **檢查 heatmap 頁**：確認不重複功能數、Top 1 與資料口徑一致。
- [ ] **檢查 navigation 頁**：確認 KPI 文案正確，且頁面載入速度與表格渲染量已改善。

## 修改檔案

- [x] `dashboard-renderers.js`
- [x] `query-definitions.js`
- [x] `build_page_navigation_t2.py`
- [x] `validate_dashboard_data.py`
- [x] `tree.md`

## 驗收清單

- [x] `feature`：身份辨識 KPI 文案與 T2 定義一致。
- [x] `device`：OS / browser KPI 顯示實際 distinct 數。
- [x] `ranking`：功能數量、Top 1、類別分布以跨日聚合結果為準。
- [x] `heatmap`：不重複功能數與 Top 1 以 `click_counts` 跨日聚合為準。
- [x] `navigation`：page_count 正確、KPI 文案正確，且預設載入時間與渲染量已收斂。
