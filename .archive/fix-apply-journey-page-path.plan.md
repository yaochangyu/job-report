# fix-apply-journey-page-path 計畫書

## 目標

`_build_journeys` 處理 apply 事件時，目前只加入 `"apply"` 字串，丟棄了當前頁面（`page_path`）。
導致沒有上一頁的 session 路徑為純 `"apply"`（5/1 共 376 筆），實際上這些 session 的 apply 事件都有 `page_path`。

修正後，apply 事件先加入當前頁面，再加入 `"apply"`，讓路徑還原更完整。

## 修改邏輯

修改前：
```python
names.append("apply" if row["action"] == "apply" else _normalize_page(row.get("page_path")))
```

修改後：
```python
if row["action"] == "apply":
    names.append(_normalize_page(row.get("page_path")))  # 當前頁
    names.append("apply")
else:
    names.append(_normalize_page(row.get("page_path")))
```

dedup 邏輯不變，連續相同頁面自動合併，不影響已有前置頁面的 session。

## 實作步驟

- [x] **步驟 1 — 修改 builder**
  - 檔案：`builders/build_apply_journey_t2.py`
  - 修改 `_build_journeys` 函式內的 names.append 邏輯

- [x] **步驟 2 — 重跑所有日期 T2**
  - 執行指令：`python builders/build_apply_journey_t2.py --from 2026-04-05 --to 2026-05-19`
  - 覆蓋現有 45 天的 `path_ranking`、`step_distribution`、`entry_page`、`daily_summary`

- [x] **步驟 3 — 驗證**
  - 確認 `path_ranking` 裡 `path = "apply"` 的純 apply 路徑消失或大幅減少
  - 確認 top 路徑出現 `search-job-page > apply`、`job-page > apply` 等合理路徑
  - 確認 `daily_summary.applies` 總數不變（路徑重組不影響應徵筆數）
