# 應徵者性別／年齡 × 職類／產業交叉分析實作計畫

## 目標
將 apply 事件同時 JOIN core6 Solr（sex_i、birth_dt）與 Matching ES（職類、產業），
產出性別／年齡層 × 職類／產業的交叉聚合 T2 資料與前端報表。

## 資料流架構
```
T1 apply 事件
  ├─ user_id → core6 Solr → sex_i, birth_dt → gender, age_group
  └─ job_id  → Matching ES → job_positions, company_industries
       ↓ 交叉聚合
apply-demographics-category T2 parquet
       ↓
前端 Dashboard
```

## 輸出 parquet 規劃
```
apply-demographics-category/date=YYYY-MM-DD/
  daily_summary.parquet              # date, total_applies, coverage_demo, coverage_job
  gender_job_position.parquet        # gender × job_position → count (TOP 30)
  gender_company_industry.parquet    # gender × company_industry → count (TOP 30)
  age_group_job_position.parquet     # age_group × job_position → count (TOP 30)
  age_group_company_industry.parquet # age_group × company_industry → count (TOP 30)
```

---

## 實作步驟

- [x] **步驟 1：建立 T2 builder**
  - 新增 `builders/build_apply_demographics_category_t2.py`
  - 同時呼叫 `fetch_resume_metadata`（Solr）與 `fetch_job_metadata`（Matching ES）
  - 交叉聚合輸出 5 個 parquet
  - **為什麼**：兩個資料來源都需要，且交叉計算在 Python 端做比在前端 DuckDB 做更簡單

- [x] **步驟 2：更新前端查詢定義**
  - 修改 `frontend/query-definitions.js`
  - 新增 `applyDemographicsCategoryPlan`，定義 5 個 parquet 的 DuckDB 查詢
  - **為什麼**：前端需要對應的 registerFiles 與 SQL 才能載入新 parquet

- [x] **步驟 3：新增前端 renderer 與報表入口**
  - 修改 `frontend/dashboard-renderers.js`：新增 renderer，規劃圖表
    - chart1：性別 × TOP 職類（grouped bar）
    - chart2：年齡層 × TOP 職類（grouped bar）
    - chart3：性別 × TOP 產業（grouped bar）
    - table1：性別 × 職類交叉表
    - table2：年齡層 × 職類交叉表
  - 修改 `frontend/app.js`：新增 VIEW_FILTER_FIELDS 與 VIEW_META
  - 修改 `common/frontend_shell.py`：sidebar 新增導覽項目
  - 修改 `run_all.py`：REPORTS 新增報表入口
  - **為什麼**：資料完成後需接到現有導覽殼

- [x] **步驟 4：單元測試與文件更新**
  - 新增 `tests/unit/test_build_apply_demographics_category.py`
  - 更新 `tree.md`、`README.md`
  - **為什麼**：跨來源 JOIN 邏輯是重點，需要測試保護
