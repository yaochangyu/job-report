# 應徵職類/產業分析 Dashboard 實作計畫

## 目標
分析應徵者都在應徵哪些產業（`companyIndustryNames`）與職類（`jobPositionNames`），
新增一個 Dashboard 呈現 TOP N 排行與日趨勢。

## 資料流架構
```
operation-logs ES
  └─ apply 事件 metadata.jobId
       ↓ JOIN
search-jobs-v1-* ES（Matching search）
  └─ jobPositionNames（職類）
     companyIndustryNames（產業）
       ↓ T2 parquet
frontend Dashboard（新增）
```

## 根本原因
目前 T1 parquet 的 `normalize_raw_event()` 未抽取 `metadata.jobId`，
導致所有下游報表都無法關聯職缺資訊。

---

## 實作步驟

- [x] **步驟 1：擴充 T1 raw schema，加入 `job_id` 欄位**
  - 修改 `common/raw_events.py`：`RawEventRecord` 新增 `job_id: str | None`、`company_id: str | None`
  - 修改 `RAW_EVENT_SCHEMA`（PyArrow schema）加入兩欄
  - 修改 `normalize_raw_event()` 從 `metadata.get("jobId")` 抽取並轉為 string
  - **為什麼**：job_id 是 join 職缺 metadata 的唯一 key，沒有這個欄位後續步驟無法進行

- [x] **步驟 2：重新抽取現有 47 天的 T1 parquet（backfill）**
  - 執行 `tools/extract_raw_events.py --from 2026-04-05 --to 2026-05-21`（覆寫現有）
  - **為什麼**：schema 新增欄位後，舊 parquet 缺少 `job_id`，需要重跑才能讓 T2 builder 使用

- [x] **步驟 3：建立職缺 metadata 查詢工具 `common/job_metadata.py`**
  - 提供 `fetch_job_metadata(job_ids: list[int]) -> dict[int, dict]`
  - 批次查詢 `search-jobs-v1-*`（Matching ES, uid `bf3z8ygb41hq8a`）
  - 回傳 `{job_id: {"job_positions": [...], "company_industries": [...]}}`
  - **為什麼**：抽成共用模組，T2 builder 和未來其他報表都可重用，避免重複寫 ES 查詢邏輯

- [x] **步驟 4：建立 T2 builder `builders/build_apply_job_category_t2.py`**
  - 從 T1 讀取 apply 事件（`action == 'apply'`），過濾有 `job_id` 的資料
  - 批次呼叫 `common/job_metadata.py` 取得職類/產業
  - 聚合輸出以下 parquet：
    - `daily_summary.parquet`：每日 apply 總數（含有/無 job_id 覆蓋率）
    - `job_position_top.parquet`：職類 TOP 30（name, count）
    - `company_industry_top.parquet`：產業 TOP 30（name, count）
    - `job_position_daily.parquet`：TOP 10 職類的每日趨勢
    - `company_industry_daily.parquet`：TOP 10 產業的每日趨勢
  - **為什麼**：前端需要多個維度的資料，分開存儲讓查詢更快

- [x] **步驟 5：更新 `frontend/query-definitions.js`，新增 `applyJobCategoryPlan()`**
  - 定義 DuckDB 查詢（讀取步驟 4 產出的 parquet）
  - 回傳職類 TOP N、產業 TOP N、每日趨勢
  - **為什麼**：前端透過 DuckDB-wasm 讀取 parquet，需要在 query-definitions.js 登記

- [x] **步驟 6：更新 `frontend/dashboard-renderers.js`，新增 `renderApplyJobCategory()`**
  - 水平長條圖：職類 TOP 20
  - 水平長條圖：產業 TOP 20
  - 折線圖：TOP 5 職類每日趨勢
  - 折線圖：TOP 5 產業每日趨勢
  - **為什麼**：長條圖最適合 TOP N 排名比較，折線圖展示時間趨勢

- [x] **步驟 7：在 `run_all.py` 登記新 Dashboard**
  - 在 DASHBOARDS list 加入 `apply-job-category`
  - **為什麼**：`run_all.py` 統一管理所有報表，需要登記才會被產生與部署

- [x] **步驟 8：更新 `tree.md`**
  - 新增 `common/job_metadata.py` 與 `builders/build_apply_job_category_t2.py`
  - **為什麼**：CLAUDE.md 要求每次新增檔案都要更新 tree.md

---

## 技術細節

### 步驟 1 schema 變更
```python
# raw_events.py 新增欄位
job_id: str | None      # from metadata.jobId
company_id: str | None  # from metadata.companyId

# PyArrow schema 新增
("job_id", pa.string()),
("company_id", pa.string()),

# normalize 新增
"job_id": str(metadata.get("jobId")) if metadata.get("jobId") else None,
"company_id": str(metadata.get("companyId")) if metadata.get("companyId") else None,
```

### 步驟 3 ES 查詢（Matching search）
- Datasource UID: `bf3z8ygb41hq8a`
- Index: `search-jobs-v1-*`
- 批次大小：500 個 job_id / 請求（terms query）
- 取欄位：`id`, `jobPositionNames`, `companyIndustryNames`

### apply 事件 job_id 覆蓋率（預估）
- 有 job_id 的 apply 事件：約 70-80%（來自 job-detail / corp 頁面）
- 無 job_id（來自 search 列表頁快速應徵）：約 20-30%
- 報表需顯示覆蓋率供參考

### 注意：search-jobs-v1-* 只有現存職缺
- 已下架職缺不在索引中，join 後會有部分 NULL
- T2 統計只計算有成功 join 的資料，並標注覆蓋率
