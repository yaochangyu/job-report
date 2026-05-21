# Page Navigation 縮減實作計畫

## 目標
縮小 `page-navigation` 在前端 DuckDB 載入的 parquet 體積，優先處理 `page_sources.parquet`、`entry_pages.parquet`、`page_destinations.parquet` 三個大檔。

## 已確認現況（2026-05-01）
- `page-navigation` 總量：約 `1.8 MB`
- 最大檔案：
  - `page_sources.parquet`：約 `987 KB`
  - `entry_pages.parquet`：約 `472 KB`
  - `page_destinations.parquet`：約 `315 KB`
- `click` 資料不是空的：
  - `entry_pages.parquet`：`790` rows，約 `10 KB`
  - `page_sources.parquet`：`5,364` rows，約 `68 KB`
  - `page_destinations.parquet`：`2,084` rows，約 `39 KB`
- 把 `PAGE_RELATION_LIMIT` 從 `5` 改成 `3` 的縮減效果很小，因為大多數 page 本來就不到第 4、5 名

---

## 實作步驟

- [ ] **步驟 1：將 `page_sources` / `page_destinations` 的 top limit 從 5 改為 3**
  - 修改 `builders/build_page_navigation_t2.py` 的 `PAGE_RELATION_LIMIT`
  - 保持既有 schema 與前端查詢契約不變
  - **為什麼**：這是你指定的調整，且屬於低風險設定變更

- [ ] **步驟 2：`entry_pages` / `page_sources` / `page_destinations` 只保留 `view`**
  - builder 輸出這三份 parquet 時排除 `event_type = 'click'`
  - `nav_pairs.parquet` 保留 click/view，避免影響既有 KPI `nav_click`
  - **為什麼**：前端目前這三份檔案查詢都只用 `view`，保留 click 只會增加下載量，不會被畫面使用

- [ ] **步驟 3：更新前端與驗證邏輯以符合新契約**
  - 檢查 `frontend/query-definitions.js` 是否仍依賴這三份檔案的 `event_type`
  - 如有必要，移除多餘的 `WHERE event_type = 'view'`
  - 檢查 `tests/validation/validate_dashboard_data.py` 與單元測試
  - **為什麼**：資料格式縮減後，前端與驗證程式要同步，避免查詢條件與 schema 不一致

- [ ] **步驟 4：重建 `page-navigation` 並比較縮減結果**
  - 先針對 `2026-05-01` 重建
  - 比較調整前後的總量與三份 parquet 大小
  - **為什麼**：這次需求的核心就是縮小體積，必須直接量化成果

- [ ] **步驟 5：更新文件與目錄結構**
  - 更新 `README.md`（若有必要）
  - 更新 `tree.md`
  - 若計畫完成，將本計畫檔移至 `.archive/`
  - **為什麼**：專案規則要求新增、移動檔案時同步維護結構文件

---

## 判斷結論
- **`click` 有值，但占用量不大，主要約 `117 KB`**
- **真正大的還是 `view`**
- **單獨把 limit 5 改 3，效果有限**
- **最有感的縮減來自：三份 parquet 改成只保留 `view`**
