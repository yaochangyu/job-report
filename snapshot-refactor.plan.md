# ETL：分離資料擷取與報告產生

## 問題
目前所有報告腳本直接透過 Grafana Proxy 查詢 ES（`common/es_client.msearch()`），
一旦 ES 資料被刪除，就無法重新產生歷史報告。

## 解決方案：雙層 ETL + SQLite

cron job 定期從 ES 抽取聚合結果，存入 SQLite（`store.db`）。
報告腳本改為從 SQLite 讀取，完全不依賴 ES。

### 架構圖

```
cron job（每 10~60 分鐘）
  ├─ 即時層：查「這段時間（約 10 分鐘區間）」→ snapshots_interval
  └─ 日報層：每天 00:05 重查「昨天整天」→ snapshots_daily（精確值）

報告產生（任意時間）
  ├─ 即時報告（最近 N 分鐘）→ 讀 snapshots_interval
  ├─ 日報 / 週報           → 讀 snapshots_daily
  └─ 完全不碰 ES
```

### SQLite Schema（`store.db`）

```sql
-- 即時層：每次 cron 執行一筆（10 分鐘粒度）
CREATE TABLE snapshots_interval (
    time_from  TEXT NOT NULL,   -- "2026-04-11T06:10:00+08:00"
    time_to    TEXT NOT NULL,   -- "2026-04-11T06:20:00+08:00"
    report     TEXT NOT NULL,   -- "traffic-overview"
    query_name TEXT NOT NULL,   -- "query_kpi"
    data       TEXT NOT NULL,   -- JSON（ES 聚合結果）
    created_at TEXT NOT NULL,
    PRIMARY KEY (time_from, time_to, report, query_name)
);

-- 日報層：每天一筆，對整天重查，獨立訪客數精確
CREATE TABLE snapshots_daily (
    date       TEXT NOT NULL,   -- "2026-04-11"
    report     TEXT NOT NULL,
    query_name TEXT NOT NULL,
    data       TEXT NOT NULL,   -- JSON
    updated_at TEXT NOT NULL,
    PRIMARY KEY (date, report, query_name)
);
```

### 獨立訪客數說明

| 情境 | 準確性 |
|------|--------|
| 即時：單一區間（過去 10 分鐘） | ✅ 精確 |
| 即時：跨區間加總（過去 1 小時） | ⚠️ 近似（同一 user 可能重複） |
| 日報：單日（整天一次查詢） | ✅ 精確 |
| 日報：跨天 KPI 加總（過去 7 天） | ⚠️ 近似（跨天同一 user 可能重複） |

跨區間加總的獨立訪客數在報告中標註 `＊`：
> ＊ 獨立訪客數為每日去重加總，跨天可能重複計算

## 使用情境

```bash
# cron job：每 10~60 分鐘抽取即時資料
uv run python extract_all.py --mode interval

# cron job：每天 00:05 抽取昨日精確日報
uv run python extract_all.py --mode daily --date yesterday

# 從 SQLite 產生報告（不碰 ES）
uv run python run_all.py --from 2026-04-01 --to 2026-04-10

# 即時報告（最近 60 分鐘）
uv run python run_all.py --realtime --minutes 60
```

## 實作步驟

- [ ] Step 1：建立 `common/store.py`
  - 初始化 `store.db`，建立 `snapshots_interval` 與 `snapshots_daily` 表
  - `save_interval(time_from, time_to, report, query_name, data)`
  - `save_daily(date, report, query_name, data)`
  - `load_interval(time_from, time_to, report, query_name) -> dict | None`
  - `load_daily(date, report, query_name) -> dict | None`
  - `load_daily_range(date_from, date_to, report, query_name) -> list[dict]`

- [ ] Step 2：建立 `extract_all.py`
  - `--mode interval`：查詢最近一段時間（auto-detect 距上次執行的時間差）
  - `--mode daily --date YYYY-MM-DD`：查詢指定整天
  - 匯入所有報告的 `query_*` 函式
  - 呼叫後以 `save_interval` / `save_daily` 存入 SQLite

- [ ] Step 3：修改 `common/es_client.py`
  - `parse_args()` 加入 `--from-store` flag（從 SQLite 讀取，不查 ES）

- [ ] Step 4：修改 `traffic_overview_report.py`（作為模板）
  - `main()` 支援 `--from-store`：從 SQLite 讀取各 query 結果
  - 跨天 KPI 加總時附加 `*` 標註

- [ ] Step 5：修改其餘 7 個報告腳本
  - `search_behavior_report.py`
  - `apply_conversion_report.py`
  - `feature_engagement_report.py`
  - `device_platform_report.py`
  - `page_ranking_report.py`
  - `page_navigation_report.py`
  - `click_heatmap_report.py`

- [ ] Step 6：更新 `run_all.py`
  - 傳遞 `--from-store` 給所有子腳本

- [ ] Step 7：更新 `tree.md`
  - 新增 `common/store.py`、`extract_all.py`、`store.db` 說明

## 注意事項
- `store.db` 加入 `.gitignore`，不進版控
- `click_heatmap_report.py` 的 `query_page_clicks` 需以 `query_name = f"query_page_clicks_{page_path}"` 區分不同頁面
- `extract_all.py` 需記錄上次執行時間（存於 `store.db` 的 `meta` 表），供 `--mode interval` 自動偵測時間差

---

## 備忘：曾討論過的其他方案

> 若日後需求改變，可參考以下方案重新評估。

### 前端讀取資料的選項

#### 方案 A：維持靜態 HTML（現況）
```
ETL → store.db → run_all.py → 靜態 HTML → GitHub Pages
```
- ✅ 不需要伺服器，現有流程幾乎不變
- ❌ 不能互動查詢，每次須重跑腳本

#### 方案 B：Parquet + DuckDB-WASM（純前端，無伺服器）
```
ETL → Parquet 檔 → commit 進 repo → GitHub Pages
前端 → DuckDB-WASM 載入 Parquet → 瀏覽器直接跑 SQL
```
- ✅ 不需要後端 API 或 DB Server，完全免費
- ✅ 任意時間範圍互動查詢
- ⚠️ Parquet 檔進 git repo，需控制檔案大小（只保留近 N 天，或用 Git LFS）
- ⚠️ 資料必須是 public（GitHub Pages 上）

#### 方案 C：FastAPI + PostgreSQL（最完整）
```
ETL → PostgreSQL → FastAPI → 前端
```
- ✅ 任意互動查詢，DB 自由選
- ✅ 資料完全自控，支援並發
- ❌ 需要一台常駐伺服器

#### 方案 D：Supabase（PostgreSQL + 自動 JS SDK，免自架）
```
ETL → Supabase (PostgreSQL) → 前端用 supabase-js 直接查
```
- ✅ 有免費方案，不用自架 Server
- ✅ JS SDK 直接查詢，無需自寫 API
- ⚠️ 資料儲存在雲端（Supabase 服務）

#### 方案 E：Datasette（SQLite → 自動 Web UI，最省力）
```
store.db → datasette serve → 自動產生查詢介面 + JSON API
```
- ✅ 幾乎零開發
- ❌ UI 是通用介面，非客製化報告
- ❌ 需要一台伺服器

### 儲存格式比較

| 儲存 | 特點 | 適合情境 |
|------|------|---------|
| **SQLite** | 檔案型，零部署 | 單機、低並發（本計畫採用） |
| **PostgreSQL** | 完整關聯式，支援並發 | 多人使用、生產環境 |
| **DuckDB** | 純分析型，查詢極快 | 大量聚合查詢、搭配 Parquet |
| **Parquet 檔案** | 欄位式壓縮，省空間 | 歸檔、DuckDB-WASM 前端讀取 |
| **InfluxDB / TimescaleDB** | 時序資料庫 | 高頻監控指標 |

### 獨立訪客數跨區間的根本限制
ES 的 `cardinality` 聚合（HyperLogLog）**不可合併**。
要取得任意區間的精確獨立訪客數，唯一方法是對該區間直接查一次 ES。
本計畫的因應方式：日報層每天整天重查（精確），跨天 KPI 加總標註 `＊` 說明為近似值。
