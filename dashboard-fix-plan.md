# Dashboard 修正計劃書

## 問題

目前 8 個 dashboard view 中，`feature`、`device`、`ranking`、`heatmap`、`navigation` 與 T2 day-keyed 資料存在語意或聚合不一致；其中 `navigation` 另有明顯效能問題。

## 修正原則

1. 先修 correctness，再處理 performance。
2. 優先修正前端 query / renderer 的聚合語意，避免把跨日 distinct 誤算成每日加總。
3. 只有 `navigation` 需要進一步調整 builder 端輸出，縮小查詢與渲染資料量。

## 修正範圍

### A. feature

**問題**
- KPI「身份辨識」副標寫成「7 種身份類型」。
- 但目前數值來自所有 `identify-*` 互動總數，不只 7 類。

**目標**
- 讓畫面文案與目前 T2 定義一致。

**修改檔案**
- `dashboard-renderers.js`

**實作**
- 將 KPI 文案改為：
  - `identify-* 互動總數`，或
  - `含主身份與延伸身份互動`
- 若後續業務要真的只看 7 類主身份，再另開第二階段改用 `identity_main.parquet` 聚合。

**驗收**
- 畫面不再宣稱只有 7 類。
- KPI 數值與現有 T2 聚合結果一致。

### B. device

**問題**
- 畫面顯示 `OS 種類`、`瀏覽器種類`。
- 但 query 沒有回傳 `os_count` / `browser_count`，目前 KPI 是空值或錯值。

**目標**
- KPI 卡 3 / 4 顯示實際 distinct OS / browser 數量。

**修改檔案**
- `query-definitions.js`

**實作**
- 在 `devicePlan().kpi` 補：
  - `COUNT(DISTINCT name)` from `os.parquet` → `os_count`
  - `COUNT(DISTINCT name)` from `browser.parquet` → `browser_count`
- 不使用 top-N query 結果回推，避免受 `LIMIT` 影響。

**驗收**
- KPI 卡 3 顯示完整 OS distinct 數。
- KPI 卡 4 顯示完整 browser distinct 數。

### C. ranking

**問題**
- `功能數量` 目前是每日 `total_features` 相加，不是跨區間 distinct。
- `Top 1 功能` 的次數目前取單日最大值，不是整段聚合總和。
- 類別 doughnut 實際用 `ranking LIMIT 30` 重算，不是完整 categories。
- 表格若只顯示 30 筆，卻標成完整排行，語意不一致。

**目標**
- KPI、圖表、表格都以跨日期區間聚合後結果為準。

**修改檔案**
- `query-definitions.js`
- `dashboard-renderers.js`

**實作**
- 改寫 KPI query，改從 `features.parquet` 聚合後計算：
  - `SUM(total)` → `total`
  - `COUNT(DISTINCT featureId)` → `feature_count`
  - 依 `SUM(total)` 找 `top_feature`，顯示 `featureId`（`features.parquet` 無 `featureName` 欄位）
  - 取對應 `top_count`
- renderer 的類別圖改直接使用 `categories` query。
- 表格若保留 `LIMIT 30`，標題改成 `Top 30 功能排行`；否則移除 `LIMIT 30`。

**驗收**
- `功能數量` 等於整段區間 distinct `featureId`。
- `Top 1 功能` 與其數量來自整段聚合。
- 類別圖與完整 T2 categories 聚合一致。

### D. heatmap

**問題**
- `不重複功能數` 現在是每日 `feature_count` 相加，跨日高估。
- `Top 1 功能` 次數目前取單日最大值，不是整段聚合總和。

**目標**
- KPI 直接由 `click_counts.parquet` 聚合。

**修改檔案**
- `query-definitions.js`

**實作**
- 改寫 `heatmapPlan().kpi`，直接從 `click_counts.parquet` 計算：
  - `SUM(count)` → `total_clicks`
  - `COUNT(DISTINCT feature_id)` → `feature_count`
  - 聚合後排序取得 `top_feature`，顯示 `feature_id`
  - 同步取得 `top_count`
- ⚠️ **已知限制**：T1 資料目前沒有 `feature_name` 欄位，`click_counts.parquet` 的 `feature_name` 全為空字串。`Top 1 功能` 只能顯示 `feature_id`，待 T1 資料補齊 `feature_name` 後再改。

**驗收**
- `不重複功能數` 為整段 distinct `feature_id`。
- `Top 1 功能` 與次數為整段聚合結果。

### E. navigation

#### E-1. Correctness

**問題**
- `追蹤頁面數` 目前把每日 `tracked_pages` 相加，不是區間 distinct page。
- KPI 文案寫 `Top 30 路徑合計`，但實際 query 是全部 `nav_total`。

**目標**
- KPI 與實際查詢口徑一致。

**修改檔案**
- `query-definitions.js`
- `dashboard-renderers.js`

**實作**
- `page_count` 改由明細 parquet 做 distinct page 計算。
- `nav_total` 文案改成：
  - `導航事件總數`
  - 副標：`全部 from→to 轉換事件`
- 若之後真要顯示 top30 合計，應另做獨立 KPI。

**驗收**
- `追蹤頁面數` 為區間 distinct page 數。
- KPI 文案不再誤導。

#### E-2. Performance

**問題**
- `page_sources` / `page_targets` 目前資料量過大。
- 前端會抓取、聚合、渲染大量資料，造成頁面過慢。

**目標**
- 預設載入只呈現可閱讀範圍，顯著降低查詢與 DOM 壓力。

**修改檔案**
- `build_page_navigation_t2.py`
- `query-definitions.js`
- `dashboard-renderers.js`

**實作**
- builder 端：
  - `page_sources.parquet` 每個 page 只保留 top N source
  - `page_destinations.parquet` 每個 page 只保留 top N target
  - 建議 `N = 10`
- query 端：
  - 未指定 `pagePath` 時，限制輸出列數
  - 指定 `pagePath` 時，再放寬該頁查詢範圍
- renderer 端：
  - 預設只在 DOM 插入前 100 筆（純 UI 截斷，不改 DuckDB query，避免影響聚合結果）
  - 其餘改分頁或「顯示更多」

**驗收**
- 修改 builder 後執行 `uv run python run_all.py --from <date_from> --to <date_to> --skip-extract` 重新產生 T2 parquet。
- 預設頁面載入時間明顯下降。
- 不再一次渲染數十萬列。
- 指定 `pagePath` 時仍能看主要來源 / 去向。

## 建議實作順序

1. `device`
2. `ranking`
3. `heatmap`
4. `feature`
5. `navigation` correctness
6. `navigation` performance

## 預計修改檔案

- `dashboard-renderers.js`
- `query-definitions.js`
- `build_page_navigation_t2.py`

## 驗收清單

- `feature`：身份辨識 KPI 文案與 T2 定義一致。
- `device`：OS / browser KPI 顯示實際 distinct 數。
- `ranking`：功能數量、Top 1、類別分布以跨日聚合結果為準。
- `heatmap`：不重複功能數與 Top 1 以 `click_counts` 跨日聚合為準。
- `navigation`：page_count 正確、KPI 文案正確，且預設載入時間與渲染量明顯下降。
