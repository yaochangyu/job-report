# period-summary-report 實作計畫

## 目標

在現有日報表（每日 parquet）基礎上，預計算**月報、季報、年報**聚合 parquet，
並在前端 monthly-report 視角加入 period-type tabs（日報 / 月報 / 季報 / 年報）切換。

## 聚合 Parquet Schema（三種類型共用）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `period` | string | 月報=`YYYY-MM-DD`（日粒度）；季報/年報=`YYYY-MM`（月粒度） |
| `feature_id` | string | 功能 ID |
| `feature_name` | string | 功能名稱 |
| `event_type` | string | `click` 或 `view` |
| `count` | int64 | 加總計數 |

## 目錄結構

```
dataset/report/homepage-blocks/
  date=YYYY-MM-DD/feature_counts.parquet      ← 現有日報
  monthly=YYYY-MM/feature_counts.parquet      ← 新增：月報（period=日）
  quarterly=YYYY-Q{N}/feature_counts.parquet  ← 新增：季報（period=月）
  yearly=YYYY/feature_counts.parquet          ← 新增：年報（period=月）
```

## manifest.json 延伸

```json
{
  "available_dates": [...],
  "available_months": ["2026-05", "2026-04"],
  "available_quarters": ["2026-Q2"],
  "available_years": ["2026"]
}
```

## 涉及檔案

| 檔案 | 說明 |
|------|------|
| `builders/build_period_summary.py` | 新增：聚合 builder |
| `run_all.py` | 呼叫新 builder；manifest 掃描延伸 |
| `frontend/app.js` | 讀取 manifest 新欄位，存入 runtime |
| `frontend/dashboard-renderers.js` | period-type tabs、fetch、render |
| `frontend/app.css` | tabs 與趨勢圖樣式 |
| `output/` 對應檔案 | 同步 |

---

## 實作步驟

- [x] **步驟 1 — 建立 `builders/build_period_summary.py`**
  - 讀取所有現有 `date=*/feature_counts.parquet`（含 `period=date` 欄位）。
  - 按月聚合 → 產出 `monthly=YYYY-MM/feature_counts.parquet`（period 保留 YYYY-MM-DD，方便前端畫日趨勢）。
  - 按季聚合（Q1=1-3月、Q2=4-6月、Q3=7-9月、Q4=10-12月）→ 產出 `quarterly=YYYY-Q{N}/feature_counts.parquet`（period=YYYY-MM）。
  - 按年聚合 → 產出 `yearly=YYYY/feature_counts.parquet`（period=YYYY-MM）。
  - 所有現有 daily parquet 有資料才輸出對應 period（避免空檔）。

- [x] **步驟 2 — 更新 `run_all.py`**
  - 在 `build` 階段加入 `build_period_summary` 呼叫（在 homepage-blocks 之後）。
  - 在 `_collect_t2_available_dates` 旁新增 `_collect_t2_available_periods`，掃描 `monthly=`、`quarterly=`、`yearly=` 目錄。
  - 在 manifest.json 加入 `available_months`、`available_quarters`、`available_years`。

- [x] **步驟 3 — 更新 `app.js`：讀取 manifest 新欄位**
  - manifest 載入後，將 `available_months`、`available_quarters`、`available_years` 存入 `runtime`。
  - URL 新增 `period_type`（`daily`/`monthly`/`quarterly`/`yearly`，預設 `daily`）與 `period`（對應 period 值）兩個 params。

- [x] **步驟 4 — 更新 `dashboard-renderers.js`：period-type tabs + period 選擇器**
  - `monthlyReportRenderer` 最頂層加入 4 個 tabs：日報 / 月報 / 季報 / 年報。
  - tabs 下方的 period 選擇器隨 tab 切換：
    - 日報 → 月份 tabs + 日期按鈕（現有邏輯）。
    - 月報 → 月份下拉或 tabs（`available_months`）。
    - 季報 → 季度 tabs（`available_quarters`）。
    - 年報 → 年份 tabs（`available_years`）。

- [x] **步驟 5 — 新增 `fetchPeriodReport(type, period, runtime)`**
  - 根據 type 建構 parquet URL：
    - `monthly` → `report/homepage-blocks/monthly={period}/feature_counts.parquet`
    - `quarterly` → `report/homepage-blocks/quarterly={period}/feature_counts.parquet`
    - `yearly` → `report/homepage-blocks/yearly={period}/feature_counts.parquet`
  - 查詢後回傳 `{ rows, clickRows, viewMap, totalClicks, totalViews }`。

- [x] **步驟 6 — 新增 period 報表渲染**
  - 類別 sidebar（與 `monthly-report-day-nav` 計畫的 Plan B 共用相同 HTML/CSS 結構）。
  - 類別明細表（同現有日報表，`monthlyBuildCatTable`）。
  - 趨勢圖（Chart.js `line`，X 軸=period，Y 軸=clicks；月報每日、季報/年報每月）。
  - 圖表容器 id 統一命名：`period-trend-chart`。

- [x] **步驟 7 — URL sync**
  - 切換 period-type tab 或 period 選擇時，以 `history.replaceState` 寫入 `period_type` 與 `period` params。
  - 頁面載入時讀取這兩個 params 自動還原選取狀態（可分享連結）。

- [x] **步驟 8 — CSS：period-type tabs + 趨勢圖容器**
  - `.period-type-tabs`：與現有 `.monthly-nav-months` 風格一致的頂層 tab 列。
  - `.period-trend-wrap`：Chart.js canvas 容器，固定高度（如 `220px`）。
  - 視窗 ≤960px：趨勢圖縮減高度（`160px`）。

- [x] **步驟 9 — 同步 output/ 並驗證**
  - 複製 `frontend/app.css`、`frontend/app.js`、`frontend/dashboard-renderers.js` 至 `output/`。
  - 執行 `uv run python builders/build_period_summary.py --from 2026-05-01 --to 2026-05-17` 產出聚合 parquet。
  - 更新 `output/dataset/manifest.json`（或完整跑 `run_all.py --skip-build`）。
  - 瀏覽器驗證：
    - [x] 四個 period-type tabs 切換正常。
    - [x] 月報選月份後，顯示趨勢圖 + 類別 sidebar + 明細表。
    - [x] 季報/年報顯示月粒度趨勢圖。
    - [x] URL 同步且重整後能還原選取狀態。
    - [x] RWD 正常。
