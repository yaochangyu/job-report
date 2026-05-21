# T0 / T1 資料管線重構計畫

## 目標
將現有 T1（原始事件 + 部分補強）拆成兩層：
- **T0**：純 operation-logs 原始事件，immutable，不含任何外部資料
- **T1**：T0 + 外部 metadata 補強（page_path 正規化、Solr sex_i/birth_dt、Matching ES 職類/產業）

## 目前問題
- 現有 `dataset/raw/` 已包含 `page_path` 正規化，叫「raw」名不符實
- `build_apply_demographics_t2.py` 與 `build_apply_job_category_t2.py` 各自在 T2 打外部服務，重複且難複用
- 新的交叉分析 builder 若繼續在 T2 JOIN，同一批 user_id / job_id 會被打三次

## 目標架構
```
ES operation-logs
    ↓ extract (T0)
dataset/t0/date=YYYY-MM-DD/events.parquet       ← 純原始事件，不可變
    ↓ enrich (T1)
dataset/t1/date=YYYY-MM-DD/events.parquet       ← T0 + 外部補強欄位
    ↓ builders (T2)
dataset/report/<報表>/date=YYYY-MM-DD/*.parquet
    ↓ shell (T3)
output/
```

## 新增欄位（T0 → T1）
| 欄位 | 來源 | 說明 |
|------|------|------|
| `page_path` / `previous_page_path` | T0 page_url 正規化 | 現在已在 T1，維持不變 |
| `sex_i` | core6 Solr（apply 事件） | 1=男, 2=女, null=查無資料 |
| `birth_dt` | core6 Solr（apply 事件） | ISO 8601 UTC |
| `job_positions` | Matching ES（apply 事件） | list[str]，職類名稱 |
| `company_industries` | Matching ES（apply 事件） | list[str]，產業名稱 |

---

## 實作步驟

- [x] **步驟 1：更新 data_pipeline.py**
  - 新增 `T0_RAW_DIR`、`T1_ENRICH_DIR` 路徑定義
  - 保留 `T1_RAW_DIR` alias 指向 `T1_ENRICH_DIR`（向下相容）
  - 更新 `TierContract` 說明
  - **為什麼**：所有路徑依賴都從這裡引用，先建立命名才能逐步遷移

- [x] **步驟 2：拆分 extract_raw_events.py**
  - T0 抽取：純從 ES 拉事件，寫入 `dataset/t0/`
  - T1 enrichment：讀 T0，批次查 Solr（apply 事件）與 Matching ES（apply 事件），寫入 `dataset/t1/`
  - **為什麼**：T0 與 T1 職責分離，T0 可獨立重跑，T1 enrichment 可單獨補跑

- [x] **步驟 3：更新 t1_reader.py**
  - `T1_RAW_DIR` 改讀 `dataset/t1/`
  - **為什麼**：所有 T2 builder 透過 t1_reader 讀資料，只改這一處即可

- [x] **步驟 4：簡化 build_apply_demographics_t2.py**
  - 移除 `fetch_resume_metadata` 呼叫
  - 直接讀 T1 的 `sex_i`、`birth_dt` 欄位
  - **為什麼**：資料已在 T1，T2 只做聚合

- [x] **步驟 5：簡化 build_apply_job_category_t2.py**
  - 移除 `fetch_job_metadata` 呼叫
  - 直接讀 T1 的 `job_positions`、`company_industries` 欄位
  - **為什麼**：同上

- [x] **步驟 6：更新 run_all.py**
  - `raw` 階段拆成 `t0`（抽取）與 `t1`（補強）兩個子步驟
  - **為什麼**：讓使用者可以分開重跑 T0 / T1

- [x] **步驟 7：更新單元測試與文件**
  - conftest.py 新增 T1 enriched 欄位
  - 更新 README.md 架構說明
  - 更新 tree.md
  - **為什麼**：架構圖與測試要反映新的層次定義
