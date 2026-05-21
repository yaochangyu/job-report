# Page Navigation Lazy Load / Conditional Fetch 實作計畫

## 目標
優先縮短 `page-navigation` 首次載入時間，不再一開始就下載所有 relation parquet，而是依畫面情境只抓必要檔案。

## 已確認現況
- `page-navigation` 目前預設會同時載入：
  - `daily_summary.parquet`
  - `nav_pairs.parquet`
  - `entry_pages.parquet`
  - `page_sources.parquet`
  - `page_destinations.parquet`
- 體積主要集中在：
  - `page_sources.parquet`
  - `page_destinations.parquet`
- 首頁預設畫面其實不一定需要先抓完整 source / destination 關係資料

---

## 實作步驟

- [x] **步驟 1：調整 `page-navigation` 的 query plan，拆成 base 與 detail 兩段載入**
  - 修改 `frontend/query-definitions.js`
  - `registerFiles` 預設只載入：
    - `daily_summary.parquet`
    - `nav_pairs.parquet`
    - `entry_pages.parquet`
  - `page_sources.parquet`、`page_destinations.parquet` 改成僅在需要 detail 時才加入
  - **為什麼**：這兩份檔案最大，先從預設載入名單移除，才會對首次體感速度有明顯幫助

- [x] **步驟 2：定義 detail 觸發條件**
  - 當 `pagePath` 有值時，才載入 `page_sources.parquet` 與 `page_destinations.parquet`
  - 若 `pagePath` 為空，首頁預設不查 `page_sources` / `page_targets`
  - **為什麼**：`pagePath` 代表使用者已經指定要看單一頁面關係，這時下載 detail 檔案才有意義

- [x] **步驟 3：調整前端 renderer 的空資料顯示**
  - 修改 `frontend/dashboard-renderers.js`
  - 當 `page_sources` / `page_targets` 未載入時，表格要顯示清楚的提示文字，而不是空白或誤導成「查無資料」
  - 提示內容要反映「請指定頁面路徑後再載入詳細來源／目標」
  - **為什麼**：改成 conditional fetch 後，空表格不再代表資料不存在，而是尚未觸發 detail 載入

- [x] **步驟 4：確認 `frontend/app.js` 的查詢流程不需額外改動，必要時補狀態字樣**
  - 檢查 `collectFormFilters()`、`executeViewQueries()` 的既有流程是否足夠支援 `pagePath` 驅動載入
  - 若需要，在 query 狀態列補充目前是「摘要模式」或「頁面明細模式」
  - **為什麼**：盡量重用既有查詢提交流程，只在必要時才增加 UI 狀態，降低風險

- [x] **步驟 5：更新驗證與測試**
  - 調整 `tests/validation/validate_dashboard_data.py`
  - 針對 `page-navigation` 增加兩種情境：
    - 無 `pagePath`：不要求 `page_sources` / `page_targets`
    - 有 `pagePath`：仍可正確載入明細資料
  - 視需要補前端 query plan 的單元測試或既有驗證
  - **為什麼**：新的策略不是改資料內容，而是改載入時機，必須驗證兩種模式都正常

- [ ] **步驟 6：量化成效並更新文件**
  - 以 `2026-05-01` 為例，比較調整前後預設載入量
  - 預期預設模式可少抓約：
    - `page_sources.parquet`
    - `page_destinations.parquet`
  - 更新 `README.md`（若有必要）與 `tree.md`
  - 完成後將本計畫檔移入 `.archive/`
  - **為什麼**：這次調整的核心是下載量與首屏體感，要用實際數字驗證成果

---

## 預期結果
- `page-navigation` 首次進入時只下載摘要所需 parquet
- 使用者未指定 `pagePath` 時，不再預設下載大型 detail parquet
- 指定 `pagePath` 後，仍能看到完整來源 / 目標關係表

## 備註
- 這份計畫優先處理 **lazy load / conditional fetch**
- 若之後仍需進一步縮小體積，再回頭評估 builder 端的資料裁剪
