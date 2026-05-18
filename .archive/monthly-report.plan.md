# monthly-report — 月/日報表瀏覽器

## 需求摘要

新增一個「月報表」瀏覽頁面，入口以月份為主，向下鑽取到日報表。
日報表直接呈現 homepage-blocks T2 資料集，依 4 個分類分組顯示：
- 搜尋類別（search-*）
- 身分類別（identify-*）
- 探索工作（explore-jobs-*）
- 探索企業（explore-company-*）

## 頁面階層

```
月報表列表
  └── 2026/04 → 點擊展開 → 日報表列表（2026/04/05 ~ 2026/04/13）
  └── 2026/05 → 點擊展開 → 日報表列表（2026/05/01 ~ 2026/05/07）
                              └── 2026/05/01 → 點擊展開 → 當日 T2 詳細資料
                                    搜尋類別：feature_id × count 表格
                                    身分類別：feature_id × count 表格
                                    探索工作：feature_id × count 表格
                                    探索企業：feature_id × count 表格
```

## 資料來源

T2：`dataset/report/homepage-blocks/date=YYYY-MM-DD/click_counts.parquet`
欄位：`feature_id, count, date`

---

## 實作步驟

- [x] **Step 1：新增 `monthly-report` 至 `app.js`**
  - 在 `VIEW_META` 新增 `"monthly-report"` 條目（title/subtitle/desc）
  - 在 `VIEW_FILTER_FIELDS` 新增 `"monthly-report": { pagePath: false }`
  - 新增輔助函式 `groupDatesByMonth(dates)`：將 `available_dates` 依年月分組，回傳 `{ "2026-04": [...], "2026-05": [...] }`
  - **Why**：讓 `isValidViewMode("monthly-report")` 正確回傳 true，且初始化月份分組資料供 renderer 使用

- [x] **Step 2：在 `query-definitions.js` 新增 `monthlyReportPlan`**
  - 不走現有日期範圍 plan，而是接受單一 `targetDate` 參數
  - `registerFiles`：fetch `homepage-blocks/date={targetDate}/click_counts.parquet`
  - `buildQueries`：回傳原始 click_counts 資料（`SELECT feature_id, count FROM ...`）
  - 新增至 `planBuilders["monthly-report"]`
  - **Why**：日報表只看單日 T2，不需要跨天聚合；與現有 plan 的 fetchDates 機制分離

- [x] **Step 3：在 `dashboard-renderers.js` 新增 `monthlyReportRenderer`**
  - 接管 `.content` 區域的 HTML，不使用 kpi-grid / chart-grid / table-panel 等現有容器
  - 月份列表層（`#monthly-month-list`）：從 `availableDates` 分組，每個月一個可摺疊 `<details>` 元素
  - 日期列表層（`<details>` 內）：每個可用日期一個按鈕
  - 日期詳細層（`#monthly-day-detail`）：按下日期後 fetch 該日 `click_counts.parquet`，依 4 個類別分 4 個表格呈現
  - 4 類別 ID 常數直接在 renderer 中定義（複製自 query-definitions.js 的 HB_*_IDS）
  - **Why**：月/日鑽取是純導覽狀態，不需要走現有 runQuery 流程；renderer 自己管理 fetch 與狀態

- [x] **Step 4：更新 `common/frontend_shell.py`**
  - 在 sidebar nav 新增 `data-view-mode="monthly-report"` 按鈕（圖示 📅，名稱「月報表」）
  - **Why**：sidebar 是硬編碼 HTML，必須手動新增入口

- [x] **Step 5：更新 `run_all.py`**
  - 在 `REPORTS` 清單新增 monthly-report 條目（`script` 指向現有 `build_homepage_blocks_t2.py`，`view_mode="monthly-report"`）
  - **Why**：`build_shell_pages()` 依 REPORTS 產生每個 view 的 HTML shell；monthly-report 的 T2 資料就是 homepage-blocks，不需另建 T2 腳本

- [x] **Step 6：重新產生 HTML 並驗證**
  - 執行 `run_all.py --steps html`
  - 在瀏覽器開啟本地頁面，驗證月份列表、日期鑽取、4 分類表格正確顯示
  - **Why**：確認 renderer 邏輯與 T2 資料路徑正確，再部署

- [x] **Step 7：提交並部署**
  - git commit
  - `bash deploy.sh --version v1-3 --skip-build` 推上 gh-pages
  - **Why**：完成後讓已部署網站可以使用月報表瀏覽器
