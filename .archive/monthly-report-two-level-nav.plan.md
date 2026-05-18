# monthly-report-two-level-nav 計畫書

## 背景
月報表日期選單目前為橫排所有月份的日期按鈕，月份一多版面高度難以控制。
改為兩層導航：第一層月份 tab（固定一行）、第二層只顯示選中月份的日期按鈕（固定一行）。

## 目標結構
```
[ 2026/05 ][ 2026/04 ][ 2026/03 ] ...   ← 月份 tab 列（overflow-x: auto）
[ 01 ][ 02 ][ 03 ] ... [ 17 ]           ← 選中月份的日期列（overflow-x: auto）
─────────────────────────────────────────
  2026/05/01 日報表 ...                  ← 內容
```

---

## 步驟

- [ ] **步驟 1 — `app.css`：新增兩層導航樣式**
  - 移除舊 `.month-group`、`.day-list` 相關樣式
  - 新增 `.monthly-nav-months`：flex row、`overflow-x: auto`、`border-bottom`
  - 新增 `.month-tab`：tab 按鈕樣式，`.active` 狀態有底線或背景高亮
  - 新增 `.monthly-nav-days`：flex row、`overflow-x: auto`、`flex-wrap: nowrap`、`padding`
  - `.day-btn` 保留現有樣式，不需大改

- [ ] **步驟 2 — `dashboard-renderers.js`：重構 HTML 結構與互動邏輯**
  - 將資料整理為 `{ "2026/05": ["2026/05/17", ...], "2026/04": [...] }` 的 Map
  - 月份 tab 列：按月份降序排列，預設選中最新月份（或 URL `date_from` 對應月份）
  - 日期列：只顯示選中月份的日期，日期按降序排列
  - 點月份 tab → 切換日期列、清除日報表內容區、更新 tab active 狀態
  - 點日期按鈕 → 行為與現在相同（查詢並渲染日報表）
  - URL `date_from` 自動選日：先切至對應月份 tab，再點擊對應日期按鈕

- [ ] **步驟 3 — 確認功能與部署**
  - 驗證：月份切換、日期選取、URL 自動選日、日報表渲染均正常
  - 提交、推、部署
