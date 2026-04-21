# 計畫：小時粒度資料管線

## Context

需要近即時報表能力：每小時 cronjob 抽取 ES 增量資料、重建 T2 聚合、前端支援任意 datetime 區間（精確到小時）篩選。
自動化排程（GitHub Actions / crontab）先跳過，優先把三層管線改好。

---

## 先修正的風險與設計原則

1. **不能只留 `hourly_detail.parquet`。**  
   `hourly_detail` 只負責 KPI / 日趨勢 / 小時分佈；仍需保留各報表必要的明細型 parquet，否則 `device-platform`、`page-ranking`、`page-navigation`、`click-heatmap` 等功能會失效。

2. **T1 manifest 必須採 merge update，不可整份覆蓋。**  
   每小時增量只更新當日 `dates[date]` 與 `updated_at`，既有 `available_dates` 與其他日期 metadata 必須保留。

3. **`messageId` 去重規則要明確定義 null case。**  
   以 `message_id` 為主鍵；若缺值，改用 `occurred_at + session_id + event_type + action + feature_id + page_path` 組成 fallback key 去重，確保同一小時重跑可重入。

4. **必須支援 late-arrival / backfill。**  
   每小時模式不只抓單一小時，而是重抓「目標小時往前 N 小時」的滑動視窗後回寫當日 parquet；昨天以前仍可用 `--from/--to` 做補資料。

---

## 架構設計

### T1 — 以天為檔，每小時 merge（結構不變）

```
dataset/raw/
  date=2026-04-20/events.parquet  ← 歷史日檔（完整）
  date=2026-04-21/events.parquet  ← 今天：cronjob 每小時 merge，累積至當前小時
```

**每小時 cronjob 流程（T1）：**
```
extract hour=HH from ES（實作上重抓 HH 往前 N 小時 sliding window）
  → read date=today/events.parquet（若存在）
  → concat + dedup by canonical event key
  → write back date=today/events.parquet
  → merge-update t1 manifest（只更新當日 metadata）
```

---

### T2 — 以天為檔，核心聚合改為小時粒度

原本的 `range=from_to/*.parquet` 不再作為主要查詢入口，改為：

```
dataset/report/traffic-overview/
  date=2026-04-20/hourly_detail.parquet  ← 24 rows（完整）
  date=2026-04-21/hourly_detail.parquet  ← N rows（截至當前小時）
  date=2026-04-20/device_type.parquet
  date=2026-04-20/os.parquet
  date=2026-04-20/browser.parquet

dataset/report/search-behavior/
  date=2026-04-20/hourly_detail.parquet
  date=2026-04-20/feature_counts.parquet
  date=2026-04-20/search_page_dist.parquet
  ...
```

每個 `hourly_detail.parquet` = 該天的小時聚合，一列一小時：

| 報表 | 欄位 |
|------|------|
| traffic-overview | `date, hour, views, clicks, applies, sessions` |
| search-behavior | `date, hour, general, ai, quick, search_page` |
| apply-conversion | `date, hour, applies, job_views` |
| feature-engagement | `date, hour, explore_jobs, explore_corp, identity, news` |
| device-platform | `date, hour, mobile, desktop` |
| page-ranking | `date, hour, total_events` |
| page-navigation | `date, hour, nav_count` |
| click-heatmap | `date, hour, total_clicks` |

**仍需保留的明細型 parquet（day-keyed）：**

| 報表 | 仍需保留的檔案 |
|------|------|
| traffic-overview | `device_type.parquet`, `os.parquet`, `browser.parquet` |
| search-behavior | `feature_counts.parquet`, `search_page_dist.parquet` |
| apply-conversion | `funnel.parquet`, `device.parquet`, `os.parquet`, `source.parquet` |
| feature-engagement | `explore_jobs_features.parquet`, `explore_jobs_category_tabs.parquet`, `explore_corp_features.parquet`, `identity_main.parquet`, `identity_all.parquet`, `news_features.parquet` |
| device-platform | `os.parquet`, `browser.parquet`, `device_behavior.parquet`, `os_behavior.parquet` |
| page-ranking | `features.parquet` |
| page-navigation | `nav_pairs.parquet`, `entry_pages.parquet`, `page_sources.parquet`, `page_destinations.parquet` |
| click-heatmap | `click_counts.parquet` |

**每小時 cronjob 流程（T2）：**
```
T1 merge 完成後
  → 讀 date=today/events.parquet
  → 重算當日所有小時的 hourly_detail
  → 同步重算該報表仍需保留的明細型 parquet
  → 覆寫 date=today/*.parquet
```

歷史日（昨天以前）：完整後不再異動。

---

### Frontend — datetime 區間查詢（精確到小時）

**UI 選擇器：**
```
從 [date picker] [hour 00-23 ▼]
到 [date picker] [hour 00-23 ▼]
```

範例 1：`2026-04-15 08:00 ~ 2026-04-15 17:00`（單天小時區間）
範例 2：`2026-04-15 08:00 ~ 2026-04-20 17:00`（跨天區間）

**fetch 策略：**
- KPI / 趨勢類 query：取 datetimeFrom.date ~ datetimeTo.date 之間所有日期的 `hourly_detail.parquet`
- 明細型 query：只針對當前 view 取該 view 需要的 day-keyed parquet
- `page-path` 欄位保留給 `navigation` / `heatmap`

**DuckDB 查詢條件（跨天 datetime 過濾）：**
```sql
WHERE (date > '{from_date}' OR (date = '{from_date}' AND hour >= {from_hour}))
  AND (date < '{to_date}'   OR (date = '{to_date}'   AND hour <= {to_hour}))
```

KPI、日趨勢、小時分佈從 `hourly_detail` 動態計算；排行榜 / 分布 / 導航 / heatmap 仍讀各 view 的 day-keyed 明細 parquet。

---

## 改動範圍

### Layer 1 — T1：新增 --hour 增量模式

**`extract_raw_events.py`**
- [ ] 加 `--hour HH` 參數（0–23），只查詢指定小時的 ES 資料（`@timestamp` 範圍縮為 1 小時）
- [ ] 加 `--lookback-hours N`（預設 2 或 3），每次重抓 `HH-N+1 ~ HH` 的 sliding window
- [ ] merge 邏輯：讀當日已有 parquet → concat + dedup by canonical event key → 寫回
- [ ] 若當日 parquet 不存在，直接寫入
- [ ] `message_id` 為空時使用 fallback key 去重
- [ ] T1 manifest `dates[date]` 加 `last_hour: HH`、`row_count`、`updated_at`
- [ ] manifest 改為 merge update，保留其他既有日期 metadata
- [ ] 保留 `--days` / `--from`/`--to` 模式不動

**驗證 Layer 1**
- [ ] 手動跑 `python extract_raw_events.py --hour 13`
- [ ] 確認 parquet 含 sliding window 內資料，且當日累積資料仍完整
- [ ] 確認 manifest 未遺失其他歷史日期
- [ ] 再跑一次 `--hour 13`，確認去重正確（row count 不增加）
- [ ] 模擬晚到資料後重跑，確認可被補進當日 parquet

---

### Layer 2 — T2：全部 8 個 builder 改為 day-keyed

**所有 `build_*_t2.py`：**
- [ ] 輸出路徑由 `range=from_to/` 改為 `date=YYYY-MM-DD/`
- [ ] 每個 builder 產生 `hourly_detail.parquet`（groupby date + hour）
- [ ] 原有 `kpi.parquet`、`daily.parquet` 等 range-keyed 預聚合檔停產
- [ ] 各 view 仍保留必要的 day-keyed 明細 parquet，不能只剩 hourly_detail
- [ ] `run_*_pipeline.py` / `run_all.py` 調整為逐日輸出

各 builder：
- [ ] `build_traffic_overview_t2.py`
- [ ] `build_search_behavior_t2.py`
- [ ] `build_apply_conversion_t2.py`
- [ ] `build_feature_engagement_t2.py`
- [ ] `build_device_platform_t2.py`
- [ ] `build_page_ranking_t2.py`
- [ ] `build_page_navigation_t2.py`
- [ ] `build_click_heatmap_t2.py`

**驗證 Layer 2**
- [ ] 跑 `build_traffic_overview_t2.py --days 3`，產出 3 個 `date=*/hourly_detail.parquet`
- [ ] 確認 date × hour 欄位正確，無空值
- [ ] 確認各 view 必要明細 parquet 仍存在且改為 `date=YYYY-MM-DD/` 路徑
- [ ] 確認 `page-navigation` / `click-heatmap` / `page-ranking` 功能所需欄位未流失

---

### Layer 3 — Frontend：datetime 區間查詢

**`common/frontend_shell.py`（HTML 模板）**
- [ ] 將現有兩個 `<input type="date">` 各加配對的 `<select>` hour（00–23）
- [ ] 保留 `page-path` 欄位，僅在 `navigation` / `heatmap` 顯示

**`app.js`**
- [ ] `dateFrom`/`dateTo` 改為 `datetimeFrom`/`datetimeTo`（含 hour）
- [ ] `collectFormFilters()` 讀取 date + hour 組成 `{date}T{hour:02d}`
- [ ] `syncUrlParams()` / `readInitialFilters()` 更新參數名
- [ ] fetch 策略：列出 datetimeFrom.date ~ datetimeTo.date 所有日期，依 view parallel fetch 對應的 day-keyed parquet
- [ ] `manifest.available_dates` 僅做日期範圍提示，不假設只有今天會更新

**`query-definitions.js`（大幅重寫）**
- [ ] 所有 plan 改為按日 fetch `date=YYYY-MM-DD/*.parquet`
- [ ] 需要時間截斷的查詢一律加跨天 datetime 過濾條件
- [ ] KPI = SUM 在過濾後的 hourly_detail
- [ ] 日趨勢 = GROUP BY date
- [ ] 小時分佈 = GROUP BY hour
- [ ] 移除舊的 range-keyed registerFiles 邏輯
- [ ] 導航 / heatmap / ranking 等明細查詢改讀 day-keyed 明細 parquet，不降級成功能縮水版

**驗證 Layer 3**
- [ ] 單天小時區間（08:00–17:00）：圖表只顯示該時段資料
- [ ] 跨天區間（Apr 15 08:00 ~ Apr 20 17:00）：首末天截斷正確，中間天完整
- [ ] `page-navigation` 的 page filter、transition ranking、source/target 查詢仍可用
- [ ] `click-heatmap` 的 page filter 與 feature ranking 仍可用

---

### 額外修正

- [ ] **`README.md`**：更新 T1 路徑（`dataset/raw/`）、T2 架構（day-keyed）

---

## 關鍵檔案

| 檔案 | 改動 |
|------|------|
 | `extract_raw_events.py` | 加 `--hour` / `--lookback-hours` 模式 + merge/dedup + manifest merge-update |
 | `build_*_t2.py`（全部 8 個） | 輸出改為 day-keyed；新增 `hourly_detail.parquet` 並保留必要明細 parquet |
 | `run_*_pipeline.py` / `run_all.py` | 調整逐日輸出邏輯 |
 | `common/frontend_shell.py` | date picker 加配對 hour selector，保留 navigation/heatmap 的 page-path |
 | `app.js` | datetimeFrom/datetimeTo + 依 view 多日 fetch |
 | `query-definitions.js` | 全部重寫，day-keyed + 跨天 datetime 過濾 + 明細查詢改讀 day-keyed 明細 parquet |
 | `README.md` | 架構說明全面更新 |
