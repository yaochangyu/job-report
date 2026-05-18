# fix-monthly-report-ux 計畫書

## 問題
1. URL 帶 `date_from` 進入月報表時，不會自動選取對應日期
2. 月份／日期選單佔據左側 240px，壓縮內容欄位寬度

## 步驟

- [ ] **步驟 1 — `app.css`：選單移至頂部**  
  - `.monthly-layout` 改為 `flex-direction: column`  
  - `.monthly-nav` 移除 `border-right`，改 `border-bottom`；flex 橫排，`overflow-x: auto`  
  - `.day-list` 改 `flex-direction: row; flex-wrap: wrap`  
  - `.day-btn` 調整 padding 適合橫排顯示，移除 `border-left`，改 `border-bottom`  
  - `.month-group` 改為橫排並列  

- [ ] **步驟 2 — `dashboard-renderers.js`：URL date_from 自動選日 + 提示文字**  
  - `monthlyReportRenderer` 建完按鈕後，讀 `new URLSearchParams(location.search).get("date_from")`  
  - 若對應 `.day-btn` 存在，程式觸發點擊（`.click()`）並 scroll into view  
  - 提示文字「點選左側日期」→「點選上方日期」  

- [ ] **步驟 3 — 提交、推、部署**
