# remove-session-ids 計畫書

## 目標

`session_ids.parquet` 每天約 1.1 MB，存的是原始 session_id 清單，僅用於跨天 `COUNT(DISTINCT session_id)` 去重。
`daily_summary.parquet` 已有每日 `sessions`（per-day nunique），前端也有 fallback 可直接 `SUM(sessions)`。
移除此檔案可讓 overview 19 天查詢從 ~21 MB 降到 ~0.2 MB（差約 100 倍）。

## 注意事項

- 跨午夜的 session（同一 session_id 出現在兩天）不再去重，改為各天加總
- 對報表精度影響極小，可接受

## 實作步驟

- [x] **步驟 1 — 修改 builder**
  - 檔案：`builders/build_traffic_overview_t2.py`
  - 刪除 `SESSION_IDS_FILE` 常數及產生 `session_ids.parquet` 的程式碼（約第 80–83 行）
  - 移除 `daily_summary` metadata 裡的 `session_ids` 欄位（第 95 行附近）

- [x] **步驟 2 — 修改前端 query**
  - 檔案：`frontend/query-definitions.js`
  - 移除 `overviewPlan` 的 `roles` 裡的 `session_ids` 項目，避免發出 404 請求

- [x] **步驟 3 — 驗證**
  - 重跑一天 T2：`python builders/build_traffic_overview_t2.py --days 1`
  - 確認輸出目錄不再有 `session_ids.parquet`
  - 確認 `daily_summary.parquet` 的 `sessions` 欄位數值正確
  - 在瀏覽器開啟 overview 頁，確認 sessions KPI 正常顯示
