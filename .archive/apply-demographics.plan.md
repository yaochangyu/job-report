# 應徵者性別／年齡分析實作計畫

## 目標
從 `operation-logs` 的 apply 事件取出 `userId`，以 `userId = core6.talentNo_l` 關聯履歷資料，
建立可統計應徵者性別與年齡分布的 T2 資料與前端報表。

## 資料流架構
```
operation-logs ES
  └─ apply 事件 userId
       ↓ JOIN（userId = talentNo_l）
core6 Solr
  └─ sex_i
     birth_dt
       ↓ T2 parquet
frontend Dashboard / 報表查詢
```

## 已確認前提
- apply 事件已包含 `userId`
- `userId = core6.talentNo_l`
- `core6` 可查到 `sex_i` 與 `birth_dt`

---

## 實作步驟

- [x] **步驟 1：建立 core6 履歷查詢共用模組**
  - 新增 `common/resume_metadata.py`
  - 提供以 `talentNo_l` 批次查詢 `sex_i`、`birth_dt` 的函式
  - 統一處理 Solr endpoint、批次大小、欄位挑選與回傳格式
  - **為什麼**：apply builder 不應直接散落 Solr 呼叫邏輯，先抽成共用模組才能維持可測試性與重用性

- [x] **步驟 2：建立 apply demographics 的 T2 builder**
  - 新增 `builders/build_apply_demographics_t2.py`
  - 從 T1 讀取 apply 事件的 `date`、`system`、`action`、`user_id`
  - 用 `user_id` 批次 join core6，轉成性別與年齡
  - 依每日輸出 T2 parquet
  - **為什麼**：先把跨系統 join 結果固化成 day-keyed parquet，前端才能沿用既有 DuckDB-WASM 模式

- [x] **步驟 3：定義性別與年齡分組規則並輸出聚合檔**
  - 性別統計以 `sex_i` 做映射後聚合
  - 年齡由 `birth_dt` 依報表查詢當下日期或資料日期計算，並分成年齡層
  - 規劃輸出：
    - `daily_summary.parquet`
    - `gender.parquet`
    - `age_groups.parquet`
    - `gender_daily.parquet`
    - `age_groups_daily.parquet`
  - **為什麼**：先把聚合格式定清楚，前端與後續驗證才有穩定契約

- [x] **步驟 4：更新前端查詢定義**
  - 修改 `frontend/query-definitions.js`
  - 新增 apply demographics 對應的 registerFiles 與 DuckDB 查詢
  - 讓前端可跨天彙總性別與年齡層資料
  - **為什麼**：沒有 query plan，前端無法載入新 parquet，也無法維持現有報表架構一致性

- [x] **步驟 5：新增前端 renderer 與報表入口**
  - 修改 `frontend/dashboard-renderers.js`
  - 規劃至少包含性別分布、年齡層分布、每日趨勢
  - 修改 `run_all.py` 註冊新報表頁
  - **為什麼**：資料 builder 完成後仍需接到現有導覽與前端殼，使用者才看得到分析結果

- [x] **步驟 6：補單元測試與必要文件**
  - 新增對應 builder 的 unit test 與 fixture
  - 視需要更新 `README.md`
  - 更新 `tree.md`
  - **為什麼**：這次功能同時牽涉跨來源 join 與新報表，測試與文件能降低後續維護成本

---

## 技術重點

### 關聯鍵
- apply event `userId`
- core6 `talentNo_l`

### 目標欄位
- `sex_i`
- `birth_dt`

### 待實作時確認的細節
- `sex_i` 的顯示映射規則（例如 1/2 對應）
- 年齡計算基準日要用「事件日期」還是「查詢執行日」
- 年齡層區間要採用哪一組分箱

### 建議方向
- **以事件日期計算年齡**，避免回補歷史資料時年齡隨時間漂移
- **新增獨立報表**，避免把 demographic 分析硬塞進既有 apply-conversion，降低既有功能風險
