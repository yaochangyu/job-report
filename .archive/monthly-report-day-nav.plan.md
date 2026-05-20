# monthly-report-day-nav 實作計畫

## 目標

1. **日報表獨立 URL**：點擊日期按鈕時同步更新 `date_from` 到 URL，讓每一天的日報表可被直接分享或書籤。
2. **類別側邊導覽（方案 B）**：日報表詳細頁改為左側 sticky 類別清單 + 右側內容兩欄版型，支援未來類別持續擴充。

## 涉及檔案

| 檔案 | 說明 |
|------|------|
| `frontend/dashboard-renderers.js` | 月報表渲染邏輯主體 |
| `frontend/app.css` | 樣式 |
| `output/dashboard-renderers.js` | 同步 |
| `output/app.css` | 同步 |

---

## 實作步驟

- [x] **步驟 1 — URL sync：點擊日期按鈕時同步 `date_from`**
  - 在 `monthlyReportRenderer` 的 day-btn click handler 裡加入 `history.replaceState`，
    將選取的日期寫入 URL 的 `date_from` query param。
  - 這樣分享 `?view=monthly-report&date_from=2026-05-01` 就能直接開啟對應日報表（現有讀取邏輯已支援）。
  - 僅修改 `frontend/dashboard-renderers.js`。

- [x] **步驟 2 — 為 `MONTHLY_CATEGORIES` 加上 `navId` 欄位**
  - 每個類別加上 `navId` 字串（如 `"cat-search"`），作為 HTML `id` 屬性與錨點連結依據。
  - 後續新增類別只需在此陣列加一筆，UI 自動更新，無需改其他地方。
  - 僅修改 `frontend/dashboard-renderers.js`。

- [x] **步驟 3 — 改版 `monthlyFetchDay` HTML 輸出結構**
  - 將原本 `day-detail-header + cat-grid（兩欄 grid）` 改為：
    ```
    day-detail-header
    day-detail-body
      ├── cat-sidebar（左，sticky）
      │     └── cat-sidebar-item × N（由 MONTHLY_CATEGORIES 產生）
      └── cat-content（右，單欄垂直排列）
            └── cat-section × N（加上 id="cat-{navId}"）
    ```
  - `cat-sidebar` 的連結點擊後平滑捲動到對應 `cat-section`。
  - 僅修改 `frontend/dashboard-renderers.js`。

- [x] **步驟 4 — 加入 IntersectionObserver 自動高亮側邊類別**
  - 在 `monthlyFetchDay` 完成渲染後，建立 `IntersectionObserver` 監聽各 `.cat-section`。
  - 當某個 section 進入視窗時，對應的 `cat-sidebar-item` 加上 `is-active` class。
  - 僅修改 `frontend/dashboard-renderers.js`。

- [x] **步驟 5 — CSS：新版兩欄佈局樣式**
  - 新增 `.day-detail-body`、`.cat-sidebar`、`.cat-sidebar-item`、`.cat-content` 規則。
  - `.cat-sidebar` 寬度固定（如 148px），`position: sticky; top: 0; align-self: flex-start`。
  - `.cat-content` 改為單欄 flex 排列（移除原 `cat-grid` 的兩欄 grid）。
  - RWD（≤960px）：`cat-sidebar` 轉為頂部橫向捲動列，`cat-content` 回到全寬單欄。
  - 僅修改 `frontend/app.css`。

- [x] **步驟 6 — 同步 output/ 並驗證**
  - 將 `frontend/app.css` 與 `frontend/dashboard-renderers.js` 複製到 `output/`。
  - 用瀏覽器開啟 `output/index.html?view=monthly-report`，確認：
    - 點擊日期後 URL 正確更新。
    - 重新整理後能自動展開對應日報表。
    - 側邊類別導覽 sticky 且捲動時高亮正確切換。
    - RWD 在窄視窗下正常顯示。
