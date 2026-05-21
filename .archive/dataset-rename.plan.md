# dataset 目錄重新命名計畫

## 目標

為資料目錄加上層次前綴，讓路徑一眼看出所屬層次：

| 現在 | 改後 |
|------|------|
| `dataset/raw/` | `dataset/t0-raw/` |
| `dataset/t1/` | `dataset/t1-enrich/` |
| `dataset/report/` | `dataset/t2-report/` |
| `dataset/manifest/` | 維持不動 |

---

## 實作步驟

- [x] **步驟 1：更新 `common/data_pipeline.py`**
  - `T0_RAW_DIR` 改為 `DATASET_DIR / "t0-raw"`
  - `T1_ENRICH_DIR` 改為 `DATASET_DIR / "t1-enrich"`
  - `T2_REPORT_DIR` 改為 `DATASET_DIR / "t2-report"`
  - **為什麼**：所有路徑依賴都從這裡引用，先改常數才能讓後續程式跟著正確

- [x] **步驟 2：修正 `run_all.py` 的硬編碼路徑**
  - `_collect_t2_available_dates` 與 `_collect_t2_available_periods` 裡的 `dataset_dir / "report"` 改為引用 `T2_REPORT_DIR`
  - `copy_frontend_bundle` 裡的 `DATASET_DIR / "report"` 同上
  - **為什麼**：`run_all.py` 有幾處直接拼接 `"report"` 字串，未透過 `data_pipeline.py` 的常數

- [x] **步驟 3：更新 `tests/unit/conftest.py`**
  - `patch_dirs` fixture 的暫存目錄名稱由 `"raw"` 改為 `"t0-raw"`，`"report"` 改為 `"t2-report"`，與正式路徑一致
  - **為什麼**：測試 monkeypatch 的路徑名稱應與正式命名對齊，避免混淆

- [x] **步驟 4：更新 `README.md` 與 `tree.md`**
  - 將所有 `dataset/raw/`、`dataset/t1/`、`dataset/report/` 的文字說明與路徑範例改為新名稱
  - **為什麼**：文件是架構的對外說明，要反映最新狀態

- [x] **步驟 5：遷移本機既有資料目錄（手動執行）**
  - 在本機執行：
    ```bash
    mv dataset/raw   dataset/t0-raw
    mv dataset/t1    dataset/t1-enrich
    mv dataset/report dataset/t2-report
    ```
  - **為什麼**：程式碼改完後，既有的本機 parquet 需要搬到新路徑才能繼續使用；若不搬則下次執行會重新抽取
