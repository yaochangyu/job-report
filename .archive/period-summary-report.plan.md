# period-summary-report 實作計畫

## 目標

對所有 10 個 T2 報表類別，預計算**月報、季報、年報**聚合 parquet，
並在前端新增「週期報表中心」，支援 類別 × 週期類型（月/季/年）× 具體週期 三維切換。

---

## 各類別聚合策略

| 類別 | period_summary 欄位 | 額外 breakdown |
|------|-------------------|----------------|
| traffic-overview | total / views / clicks / applies / sessions | — |
| search-behavior | general_click/view, ai_click/view, quick_click/view, search_page_click/view | feature_counts（sum） |
| apply-conversion | applies / job_views | source（sum）、funnel（sum） |
| apply-journey | applies / apply_sessions / total_steps | path_ranking（Top 30）、entry_page（sum） |
| feature-engagement | explore_jobs/corp/identity/news 各 click/view | — |
| device-platform | mobile / desktop | — |
| page-ranking | total_events / total_features | features Top 50（sum）、categories（sum） |
| page-navigation | nav_click/view / entry_click/view | nav_pairs **Top 30**（sum）、entry_pages（sum） |
| click-heatmap | total_clicks | click_counts Top 50（sum）**（不含截圖疊加）** |
| homepage-blocks | total_clicks / total_views | feature_counts（sum，含 event_type） |

### Period 粒度

| 週期類型 | `period` 欄位值 | 趨勢 X 軸 |
|---------|--------------|---------|
| 月報 `monthly=YYYY-MM` | `YYYY-MM-DD`（每日） | 日 |
| 季報 `quarterly=YYYY-QN` | `YYYY-MM`（每月） | 月 |
| 年報 `yearly=YYYY` | `YYYY-MM`（每月） | 月 |

---

## 目錄結構

```
dataset/report/{category}/
  date=YYYY-MM-DD/...                        ← 現有日報
  monthly=YYYY-MM/
    period_summary.parquet                   ← 趨勢用（period=YYYY-MM-DD）
    [breakdown].parquet                      ← 類別專屬明細（見上表）
  quarterly=YYYY-QN/
    period_summary.parquet                   ← 趨勢用（period=YYYY-MM）
    [breakdown].parquet
  yearly=YYYY/
    period_summary.parquet                   ← 趨勢用（period=YYYY-MM）
    [breakdown].parquet
```

---

## manifest.json 延伸

```json
{
  "available_dates":    [...],
  "available_months":   ["2026-05", "2026-04"],
  "available_quarters": ["2026-Q2"],
  "available_years":    ["2026"]
}
```

---

## 涉及檔案

| 檔案 | 說明 |
|------|------|
| `builders/build_period_summary.py` | 新增：10 類別 × 3 週期類型聚合 builder |
| `run_all.py` | 呼叫新 builder；manifest 掃描延伸 |
| `frontend/app.js` | 讀取 manifest 新欄位，存入 runtime |
| `frontend/dashboard-renderers.js` | 報表中心 UI + fetch + 各類別渲染 |
| `frontend/app.css` | 新增 tabs、趨勢圖、報表中心樣式 |
| `output/` 對應檔案 | 同步 |

---

## 實作步驟

- [x] **步驟 1 — 建立 `builders/build_period_summary.py`：period_summary.parquet**
  - 對所有 10 個類別，讀取全部 `date=*/daily_summary.parquet`。
  - 月報：保留每日一列，加 `period=date` 欄位，按月分組寫出 `monthly=YYYY-MM/period_summary.parquet`。
  - 季報：依月加總數值欄位（`SUM`），加 `period=YYYY-MM`，按季寫出 `quarterly=YYYY-QN/period_summary.parquet`。
  - 年報：同季報邏輯，按年寫出 `yearly=YYYY/period_summary.parquet`。
  - `top_feature_id` 等文字欄位在聚合層級不保留（drop）。
  - 支援 `--from` / `--to` / `--days` 參數，僅重建有變動的 period。

- [x] **步驟 2 — 建立各類別 breakdown parquets**
  - 對有 breakdown 的 7 個類別，讀取對應明細 parquet，依 period 分組加總：
    - **search-behavior**：`feature_counts.parquet`（feature_id × sum(count)）
    - **apply-conversion**：`source.parquet`、`funnel.parquet`
    - **apply-journey**：`path_ranking.parquet`（Top 30 by session_count）、`entry_page.parquet`
    - **page-ranking**：`features.parquet`（Top 50）、`categories.parquet`
    - **page-navigation**：`nav_pairs.parquet`（Top 30）、`entry_pages.parquet`
    - **click-heatmap**：`click_counts.parquet`（Top 50，無截圖欄位）
    - **homepage-blocks**：`feature_counts.parquet`（含 event_type）
  - 輸出至對應 `monthly=/quarterly=/yearly=` 目錄，檔名與日報層級相同。

- [x] **步驟 3 — 更新 `run_all.py`**
  - `report` 階段末尾加入 `build_period_summary` 呼叫。
  - `_collect_t2_available_dates` 旁新增 `_collect_t2_available_periods`，掃描所有類別下的 `monthly=`、`quarterly=`、`yearly=` 目錄，取聯集。
  - manifest.json 加入 `available_months`、`available_quarters`、`available_years`。

- [x] **步驟 4 — 更新 `app.js`：讀取 manifest 新欄位**
  - manifest 載入後，將 `available_months`、`available_quarters`、`available_years` 存入 `runtime`。
  - URL 支援新 params：`period_type`（`monthly`/`quarterly`/`yearly`）、`period`（如 `2026-05`）、`report_category`（如 `traffic-overview`）。

- [x] **步驟 5 — Frontend：報表中心 UI（category tabs + period-type tabs + period 選擇器）**
  - 將 `#monthly-section` 改為「週期報表中心」，頂層結構：
    ```
    [週期類型 tabs]  月報 / 季報 / 年報
    [類別 tabs]      10 個類別（橫向捲動）
    [period 選擇器]  依 period_type 顯示對應的月份/季度/年份按鈕
    [detail 區塊]    趨勢圖 + KPI 摘要 + breakdown 表格
    ```
  - 類別 tabs 從常數陣列產生，新增類別只需改陣列。

- [x] **步驟 6 — Frontend：通用 `fetchPeriodReport(category, periodType, period, runtime)`**
  - 根據 category + periodType + period 組合 parquet URL。
  - 載入 `period_summary.parquet`（趨勢）+ 類別專屬 breakdown parquets。
  - 回傳結構化資料供 renderer 使用。

- [x] **步驟 7 — Frontend：各類別趨勢圖 + KPI 摘要 + breakdown 渲染**
  - 趨勢圖（Chart.js line）：X 軸=period、Y 軸依類別選主要指標（如 clicks、applies、sessions）。
  - KPI 摘要列：period 內各指標加總，顯示在趨勢圖上方。
  - Breakdown 表格：依類別顯示對應明細（feature 排行、路徑排行、來源分佈等）。
  - **特殊處理**：
    - click-heatmap：只顯示 Top 50 功能排行表，無截圖疊加。
    - page-navigation：nav_pairs 限 Top 30，說明文字標注「僅顯示前 30 筆」。

- [x] **步驟 8 — CSS：報表中心樣式**
  - `.period-type-tabs`：頂層週期類型 tab 列。
  - `.report-category-tabs`：類別 tab 列（`overflow-x: auto` 支援橫向捲動）。
  - `.period-selector`：period 按鈕列（月份/季度/年份）。
  - `.period-kpi-row`：KPI 摘要橫列。
  - `.period-trend-wrap`：趨勢圖 canvas 容器（高度 220px，RWD 縮至 160px）。

- [x] **步驟 9 — URL sync**
  - 切換 period-type、category、period 時，以 `history.replaceState` 同步 3 個 params。
  - 頁面載入時讀取 params 自動還原選取狀態（可分享連結）。

- [x] **步驟 10 — 同步 output/ 並驗證**
  - 複製 `frontend/` 三個檔至 `output/`。
  - 執行 `uv run python builders/build_period_summary.py --from 2026-05-01 --to 2026-05-17`。
  - 更新 manifest（或跑 `run_all.py --steps html`）。
  - 瀏覽器驗證：
    - [ ] 所有 10 個類別的月報趨勢圖正常顯示。
    - [ ] 季報/年報切換正常。
    - [ ] click-heatmap 不顯示截圖，顯示排行表。
    - [ ] page-navigation nav_pairs 顯示 Top 30 說明。
    - [ ] URL sync + 重整還原正常。
    - [ ] RWD 正常。
