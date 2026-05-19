# Apply Journey 分析計畫

使用者從進入網站到送出應徵的完整頁面路徑分析。

---

## 實作步驟

- [ ] **步驟 1：建立 T2 builder `build_apply_journey_t2.py`**

  從 T1 raw 重建每個 session 的應徵路徑，輸出以下 parquet：

  - `daily_summary.parquet`：每日應徵 session 數、總應徵次數、平均步數
  - `path_ranking.parquet`：去重後的路徑字串排行（path, count, step_count）
  - `step_distribution.parquet`：應徵前步數分佈（steps, count）
  - `entry_page.parquet`：應徵 session 的第一個頁面排行

  **路徑重建邏輯：**
  1. 載入欄位：`date`, `session_id`, `occurred_at`, `page_path`, `action`
  2. 篩選含 `action=apply` 的 session
  3. 每個 session 按 `occurred_at` 排序 page_path
  4. 去除連續重複頁面（`A→A→B` 變為 `A→B`）
  5. 對每一次 apply，截取 apply 之前的完整路徑（含 apply 本身）
  6. 路徑轉字串：`"home-page > search-job-page > job-page > apply"`
  7. 跨日期聚合計數

- [ ] **步驟 2：將新 builder 加入 `run_all.py`**

  在 REPORTS 清單加入 apply-journey，指定 `view_mode = "apply-journey"`。

- [ ] **步驟 3：在 `query-definitions.js` 新增 `applyJourneyPlan`**

  - 載入 `daily_summary`, `path_ranking`, `step_distribution`, `entry_page`
  - 查詢：
    - `kpi`：總應徵次數、涉及 session 數、平均步數、最常見路徑
    - `path_ranking`：路徑排行（Top 30）
    - `step_distribution`：步數分佈
    - `entry_page`：進入頁排行
    - `daily_trend`：每日趨勢

- [ ] **步驟 4：在 `dashboard-renderers.js` 新增 `applyJourneyRenderer`**

  - KPI：總應徵數、涉及 Session 數、平均步數、Top 1 路徑
  - 圖表 1（bar-H）：Top 20 路徑排行
  - 圖表 2（doughnut）：步數分佈（1步、2步、3步、4步以上）
  - 圖表 3（doughnut）：進入頁分佈
  - 表格 1：完整路徑排行（#、路徑、步數、次數、佔比）

- [ ] **步驟 5：更新 `dashboard-renderers.js` 的 `VIEW_PANEL_TEXT` 與 `showPanels`**

  加入 `apply-journey` 的 panel 標題文字與 table 顯示數量設定。

- [ ] **步驟 6：更新 `app.js`**

  - `VIEW_FILTER_FIELDS` 加入 `"apply-journey": { pagePath: false }`
  - `VIEW_META` 加入標題、副標、描述（顯示於導覽選單）

- [ ] **步驟 7：功能驗證**

  - 執行 builder，確認 4 個 parquet 正確產出
  - 確認路徑去重邏輯正確（手動抽查幾個 session）
  - 確認前端圖表與表格正常顯示

- [ ] **步驟 8：提交、推上去、部署**

---

## 輸出範例

### path_ranking.parquet
| path | count | step_count |
|---|---|---|
| job-page > apply | 12,345 | 2 |
| search-job-page > job-page > apply | 8,210 | 3 |
| home-page > search-job-page > job-page > apply | 3,100 | 4 |
| home-page > job-page > apply | 1,850 | 3 |

### step_distribution.parquet
| steps | count |
|---|---|
| 1 | 500 |
| 2 | 12,345 |
| 3 | 8,210 |
| 4 | 3,100 |
| 5+ | 1,200 |
