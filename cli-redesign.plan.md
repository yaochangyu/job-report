# CLI Redesign Plan

## 目標

將 `run_all.py` 的步驟控制從 `--steps raw,report,html`（舊名稱）改為 `--step raw,report,html`（逗號分隔，名稱對齊目錄結構）。

## 步驟對應

| step 值  | 對應目錄            | 動作                        |
|----------|---------------------|-----------------------------|
| `raw`    | `dataset/raw/`      | 從 Elasticsearch 抽取 T1    |
| `report` | `dataset/report/`   | 建立 T2 day-keyed parquet   |
| `html`   | `output/`           | 產生 manifest + HTML shell  |

## 使用範例

```bash
# 全跑（預設，不加 --step）
uv run python run_all.py --from 2026-04-05 --to 2026-04-13

# T1 + T2，不產 HTML
uv run python run_all.py --from 2026-04-05 --to 2026-04-13 --step raw,report

# T2 + HTML（T1 已有）
uv run python run_all.py --from 2026-04-05 --to 2026-04-13 --step report,html

# 只產 HTML
uv run python run_all.py --step html
```

## 實作步驟

- [ ] **Step 1：修改 `_parse_args()`**
  - 將 `--steps`（複數）改為 `--step`（單數），接受逗號分隔字串
  - 預設值維持 `raw,report,html`（全跑）
  - 更新 help 文字，說明三個值與對應目錄

- [ ] **Step 2：更新 `main()` 的 steps 驗證與使用**
  - 解析 `--step` 字串為 set，驗證未知值
  - 將 `"raw" in steps`、`"report" in steps`、`"html" in steps` 取代舊的 `"raw" in steps` 等判斷
  - `--step html` 時，`--from`/`--to`/`--days` 可省略（`resolve_date_window` 已有預設值，不影響 HTML 產生）

- [ ] **Step 3：更新 README.md**
  - 使用範例改為新的 `--step` 語法
  - 移除舊的 `--steps`、`--skip-extract` 參考

- [ ] **Step 4：驗證**
  - `node --check query-definitions.js` 確認無語法錯誤（HTML 相關）
  - 實際執行 `--step html` 確認 output/ 正確產生
