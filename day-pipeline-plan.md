# 計畫：日粒度資料管線（Day Pipeline）

## Context

相較於 hourly-pipeline-plan.md，此計畫以**天**為最小查詢單位，目標是保留 day-keyed 分區的簡潔度，同時避免因過度簡化 T2 結構而讓既有 dashboard 功能縮水：
- T1 仍以 `date=YYYY-MM-DD` 為日檔，不引入小時級 merge/dedup 流程
- T2 改為 day-keyed 輸出，但**不是所有 view 都只剩一個 `daily_summary.parquet`**
- Frontend 只需 date range picker，無 hour selector，無跨天小時截斷邏輯

適合「每天更新一次、查詢精度到日」的場景。

---

## 先修正的風險與設計原則

1. **day-keyed 是分區策略，不是單檔策略。**  
   KPI / 趨勢類資料可收斂為 `daily_summary.parquet`，但各報表必要的分布、排行、導航、heatmap 明細 parquet 必須保留，否則現有前端查詢與圖表會失效。

2. **T1 manifest 不能只寫本次執行結果。**  
   即使 day pipeline 只每天重跑今天，`dataset/manifest/t1-raw-manifest.json` 仍需保留其他歷史日期 metadata；寫入時要 merge 而非覆寫。

3. **`run_*_pipeline.py` 和 `render_*_t3.py` 應先退出主管線，再視情況清理。**  
   現況：`run_all.py` → `run_*_pipeline.py` → `render_*_t3.py`（Python 產 HTML）。  
   新架構 UI 直接以 DuckDB-WASM 讀取 T2 parquet 自行渲染，T3 Python render 會被前端取代；但這批 PoC 腳本可先退出主管線、標記 deprecated，待 day pipeline 穩定後再另行刪除。

4. **Frontend 缺檔策略：partial success + 明確提示。**  
   正常情況下，frontend manifest 的 `available_dates` 應只列出 T2 真正可查日期，因此不應常態出現 404。若仍發生 404，視為部署不一致或產物不完整：查詢可用 partial success 繼續，但必須顯示 warning banner，說明「資料涵蓋 X 天（缺少 YYYY-MM-DD）」。

---

## 架構設計

### T1 — 以天為檔（結構大致不變）

```
dataset/raw/
  date=2026-04-20/events.parquet  ← 完整一天
  date=2026-04-21/events.parquet  ← 今天（cronjob 每天重建）
```

T1 cronjob（每天一次）仍可直接重跑今天，不需小時級 merge/dedup：
```
extract --from today --to today
  → 覆寫 date=today/events.parquet
  → merge-update t1 manifest（保留其他日期 metadata）
```

---

### T2 — 以天為檔，以日為最小查詢粒度

原本的 `range=from_to/` 主查詢入口改為 day-keyed：

```
dataset/report/traffic-overview/
  date=2026-04-20/daily_summary.parquet
  date=2026-04-20/device_type.parquet
  date=2026-04-20/os.parquet
  date=2026-04-20/browser.parquet

dataset/report/search-behavior/
  date=2026-04-20/daily_summary.parquet
  date=2026-04-20/feature_counts.parquet
  date=2026-04-20/search_page_dist.parquet
  ...
```

`daily_summary.parquet` 只負責該 view 的 KPI / 趨勢核心欄位，一天一列：

| 報表 | `daily_summary.parquet` 欄位 |
|------|------------------------------|
| traffic-overview | `date, views, clicks, applies, sessions` |
| search-behavior | `date, general, ai, quick, search_page` |
| apply-conversion | `date, applies, job_views` |
| feature-engagement | `date, explore_jobs, explore_corp, identity, news` |
| device-platform | `date, mobile, desktop` |
| page-ranking | `date, total_events, total_features, top_feature_id, top_feature_total` |
| page-navigation | `date, nav_total, entry_total, tracked_pages` |
| click-heatmap | `date, total_clicks, feature_count, top_feature_id, top_count` |

**仍需保留的 day-keyed 明細 parquet：**

| 報表 | 仍需保留的檔案 |
|------|----------------|
| traffic-overview | `device_type.parquet`, `os.parquet`, `browser.parquet` |
| search-behavior | `feature_counts.parquet`, `search_page_dist.parquet` |
| apply-conversion | `funnel.parquet`, `device.parquet`, `os.parquet`, `source.parquet` |
| feature-engagement | `explore_jobs_features.parquet`, `explore_jobs_category_tabs.parquet`, `explore_corp_features.parquet`, `identity_main.parquet`, `identity_all.parquet`, `news_features.parquet` |
| device-platform | `os.parquet`, `browser.parquet`, `device_behavior.parquet`, `os_behavior.parquet` |
| page-ranking | `features.parquet`, `categories.parquet` |
| page-navigation | `nav_pairs.parquet`, `entry_pages.parquet`, `page_sources.parquet`, `page_destinations.parquet` |
| click-heatmap | `click_counts.parquet` |

---

### Frontend — 日期區間查詢

**UI 選擇器（不變）：**
```
從 [date picker]  到 [date picker]
```

**fetch 策略：**
- T1 manifest（`dataset/manifest/t1-raw-manifest.json`）的 `available_dates` 代表原始事件資料已存在的日期
- Frontend manifest（`output/dataset/manifest.json`，由 `run_all.py` 的 `copy_frontend_bundle()` 產生）另有 `available_dates`，需改為代表 **T2 真正可查日期**（即 day-keyed builder 實際產出的日期），兩者不互用
- 將 dateFrom ~ dateTo 與 frontend manifest 的 `available_dates` 取交集，得出 `fetchDates`
- 依 view parallel fetch 所有 `fetchDates` 的 parquet（`daily_summary` + 必要明細）
- 若某天 parquet 404，記入 `missingDates`；此屬異常情況，UI 需 warning 提示，但其餘日期仍可照常查詢

**DuckDB 查詢（跨天聚合）：**
```sql
-- KPI：SUM 所有天的 daily_summary
SELECT SUM(views) AS views, SUM(clicks) AS clicks
FROM read_parquet([...daily_summary_files])

-- 日趨勢：GROUP BY date
SELECT date, SUM(views) AS views
FROM read_parquet([...daily_summary_files])
GROUP BY date ORDER BY date

-- 排行 / 分布（page-ranking features 為例）：跨天合算
SELECT featureId, SUM(total) AS total, SUM(views) AS views, SUM(clicks) AS clicks
FROM read_parquet([...features_files])
GROUP BY featureId ORDER BY total DESC

-- click-heatmap：跨天合算各 feature 點擊數
SELECT page_path, feature_id, feature_name, SUM(count) AS count
FROM read_parquet([...click_counts_files])
GROUP BY page_path, feature_id, feature_name ORDER BY count DESC

-- page-navigation nav_pairs：跨天累計轉換次數
SELECT "from", "to", SUM(count) AS count
FROM read_parquet([...nav_pairs_files])
GROUP BY "from", "to" ORDER BY count DESC
```

**缺檔提示（UI）：**
```
查詢完成後，若 missingDates 非空：
→ 圖表上方顯示 warning banner：
  「資料涵蓋 N 天（缺少：YYYY-MM-DD, ...）」
→ 仍顯示可用天的聚合結果，不整體失敗
```

---

## 改動範圍

### Layer 1 — T1：小改動，修正 manifest 更新方式

**`extract_raw_events.py`**
- [x] 確認 `--from today --to today` 模式可單獨執行
- [x] 保留現有覆寫日檔行為（同日重跑仍直接覆寫 parquet）
- [x] `write_manifest()` 改為 merge update，保留其他既有日期 metadata
- [x] `available_dates` 需從「既有 T1 manifest + 本次更新日期」共同計算

**驗證 Layer 1**
- [ ] 先有多天 T1 資料時，再跑單日 `extract`
- [ ] 確認 `date=today/events.parquet` 被正確覆寫
- [ ] 確認 manifest 未遺失其他歷史日期

---

### Layer 2 — T2：8 個 builder 改為 day-keyed

**所有 `build_*_t2.py`：**
- [x] 輸出路徑改為 `date=YYYY-MM-DD/`（使用既有 `t2_report_date_dir()`）
- [x] 改為逐日迭代：`for date in iter_dates(date_from, date_to):`
- [x] KPI / 趨勢核心資料輸出為 `daily_summary.parquet`
- [x] 保留各 view 必要的 day-keyed 明細 parquet，不降級成單檔版本
- [x] 停產舊的 range-keyed `kpi.parquet`、`daily.parquet`、`hourly.parquet` 等檔案
- [x] T2 manifest 結構由 snapshot key 改為 per-date 記錄（`common/data_pipeline.py` 新增 `update_t2_manifest_dates()`）
- [x] 提供 frontend manifest 所需的 T2 可查日期來源，避免沿用 T1 `available_dates`

各 builder：
- [x] `build_traffic_overview_t2.py`
- [x] `build_search_behavior_t2.py`
- [x] `build_apply_conversion_t2.py`
- [x] `build_feature_engagement_t2.py`
- [x] `build_device_platform_t2.py`
- [x] `build_page_ranking_t2.py`
- [x] `build_page_navigation_t2.py`
- [x] `build_click_heatmap_t2.py`

**`run_all.py`**
- [x] `REPORTS` 清單的 `"script"` 欄位由 `run_*_pipeline.py` 改為直接呼叫 `build_*_t2.py`
- [x] 維持現有 `--days` / `--from` / `--to` 參數不動
- [x] `copy_frontend_bundle()` 可正確複製新的 day-keyed `dataset/report/` 結構
- [x] frontend `manifest.json` 的 `available_dates` 改由 T2 day-keyed 實際產出日期產生（非沿用 T1 raw available_dates）

**`run_*_pipeline.py` / `render_*_t3.py`（退出主管線，後續清理）**
- [x] `run_all.py` 不再呼叫 `run_*_pipeline.py`
- [x] 將 `run_*_pipeline.py` / `render_*_t3.py` 標記 deprecated
- [ ] 待新 day pipeline 穩定後，再另立清理計畫刪除這批腳本

**驗證 Layer 2**
- [x] 跑 `python run_all.py --days 3`
- [x] 每報表都產出 3 個 `date=*/` 分區
- [x] 確認每個 view 的 `daily_summary.parquet` 與必要明細 parquet 都存在
- [x] 確認欄位正確，無功能所需欄位流失

---

### Layer 3 — Frontend：多日 fetch + DuckDB 聚合

**`query-definitions.js`**
- [x] 所有 plan 改為按日 fetch `date=YYYY-MM-DD/*.parquet`
- [x] 各 view 明確列出「daily_summary + 必要明細檔」的 register 規則
- [x] KPI = SUM 所有已載入的 `daily_summary`
- [x] 日趨勢 = GROUP BY date（直接讀所有 registered daily summary）
- [x] 分布 / 排行 / 導航 / heatmap = 讀多天明細 parquet 後再聚合
- [x] 移除舊的 range-keyed `range=${f.dateFrom}_${f.dateTo}/` 邏輯
- [x] 不再以 `.catch(() => {})` 靜默吞掉 register failure

**`app.js`**
- [x] `runQuery()` 以 `enumerateDates(dateFrom, dateTo)` 產生日期陣列，與 frontend manifest 的 T2 `available_dates` 取交集得出 `fetchDates`
- [x] fetch 策略：依 view parallel fetch `fetchDates` 所有必要 parquet（`Promise.all`）
- [x] 追蹤 `missingDates`（404 的日期）並傳入查詢結果
- [x] 查詢完成後若 `missingDates` 非空，於圖表上方注入 warning banner

**驗證 Layer 3**
- [ ] 選單天（2026-04-20）：圖表顯示當日資料
- [ ] 選跨天區間（Apr 15 ~ Apr 20）：KPI 為 6 天加總，趨勢圖顯示 6 個資料點
- [ ] 模擬少一天 parquet：UI 明確顯示缺少日期或查詢範圍縮水
- [ ] `page-navigation` 的 page filter、transition ranking、source/target 查詢仍可用
- [ ] `click-heatmap` 的 page filter 與 feature ranking 仍可用

---

### 額外修正

- [x] **`README.md`**：更新 T2 架構說明，從 range-keyed 改成 day-keyed，並註明各 view 仍保留必要明細 parquet

---

## 與 hourly-pipeline-plan.md 比較

| 面向 | day pipeline | hourly pipeline |
|------|-------------|----------------|
| T1 改動 | 小幅調整 manifest merge-update；無 `--hour` 模式 | 加 `--hour` merge/dedup 邏輯 |
| T2 分區 | `date=YYYY-MM-DD/` | `date=YYYY-MM-DD/` |
| T2 核心聚合 | `daily_summary.parquet`（一天一列） | `hourly_detail.parquet`（一天最多 24 列） |
| 明細 parquet | 仍保留 | 仍保留 |
| Frontend 選擇器 | 只有 date picker | date + hour picker |
| DuckDB WHERE | 無需小時截斷條件 | 需做跨天 datetime 截斷 |
| 查詢精度 | 天 | 小時 |
| 實作複雜度 | 中 | 高 |

---

## 關鍵檔案

| 檔案 | 改動 |
|------|------|
| `extract_raw_events.py` | 保留日檔覆寫模式，但 manifest 改為 merge-update |
| `build_*_t2.py`（全部 8 個） | 改為 day-keyed 逐日輸出；產生 `daily_summary.parquet` 並保留必要明細 parquet |
| `common/data_pipeline.py` | 啟用既有 `t2_report_date_dir()`；必要時補 day-keyed manifest helper |
| `run_*_pipeline.py` / `render_*_t3.py` | 先退出主管線並標記 deprecated；待新流程穩定後再清理 |
| `run_all.py` | 確認整條 pipeline 與 bundle copy 流程相容 day-keyed 結構 |
| `query-definitions.js` | 改為依 view 多日 fetch + DuckDB 聚合，且補缺檔錯誤處理 |
| `app.js` | `enumerateDates()` 產生日期陣列，並把缺檔資訊反映到 UI |
| `README.md` | 架構說明更新 |
