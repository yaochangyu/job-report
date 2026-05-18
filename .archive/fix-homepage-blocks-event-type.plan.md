# fix-homepage-blocks-event-type 計畫書

## 背景
`build_homepage_blocks_t2.py` 目前硬寫 `event_type == "click"` 過濾，
T2 parquet (`click_counts.parquet`) 只有點擊數。
T1 原始資料確認 view 事件數量約為 click 的 3 倍，必須補上。
月報表 (`monthlyFetchDay`) 也直接讀 `click_counts.parquet`，需一併調整。

## 目標
- `build_homepage_blocks_t2.py` 輸出 `feature_counts.parquet`，欄位：`feature_id | event_type | count`
- `daily_summary.parquet` 同步增加 `total_views` 欄位
- `query-definitions.js` (`homepageBlocksPlan`) 改讀新 parquet，KPI/趨勢圖分 click/view 顯示
- `dashboard-renderers.js` (`homepageBlocksRenderer`) KPI 卡片、趨勢圖、明細表均顯示 click/view
- `dashboard-renderers.js` (`monthlyFetchDay`) 改讀 `feature_counts.parquet`，表格顯示 click/view 各自數量
- 月報表表頭「點擊」→「點擊 / 瀏覽」

---

## 步驟

- [ ] **步驟 1 — `build_homepage_blocks_t2.py`：移除 click 過濾，產出含 event_type 的 feature_counts.parquet**
  - 移除 `df["event_type"].eq("click")` 過濾
  - groupby 改為 `["feature_id", "event_type"]`
  - 輸出檔名由 `click_counts.parquet` → `feature_counts.parquet`，schema：`feature_id | event_type | count | date`
  - `daily_summary.parquet` 新增 `total_views`、`total_clicks` 欄位（拆開原 `total_clicks`）

- [ ] **步驟 2 — `query-definitions.js`：homepageBlocksPlan 改用 feature_counts**
  - 角色名稱 `click_counts` → `feature_counts`，對應 `feature_counts.parquet`
  - `kpi`：加 `total_views`，區分 click/view 各分類加總
  - `daily_trend`：每個分類拆為 `*_click` / `*_view` 兩欄
  - `click_detail` → `feature_detail`：加 `event_type` 欄位輸出

- [ ] **步驟 3 — `dashboard-renderers.js`：homepageBlocksRenderer 顯示 click/view**
  - KPI 卡片：加「總瀏覽數」及各分類 view 卡片
  - 趨勢圖：click 實線、view 虛線，各分類共 8 條線
  - 明細表：`event_type` 欄位欄顯示 click/view

- [ ] **步驟 4 — `dashboard-renderers.js`：monthlyFetchDay 改讀 feature_counts**
  - 讀 `feature_counts.parquet`（含 event_type 欄）
  - 表格分兩欄：「點擊」與「瀏覽」，各自統計
  - 表頭總計改為「總點擊 / 總瀏覽」
  - `cat-table` 表頭「點擊」→ 顯示兩欄

- [ ] **步驟 5 — 重新 build T2 並部署**
  - 執行 `deploy.sh --from 2026-04-05 --to 2026-05-18 --version v1-3`
  - 確認 homepage-blocks 報表與月報表均顯示 click/view 分開數字
