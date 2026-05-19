# Reorganize Frontend Files

## 目標
將根目錄的前端靜態資源移到 `frontend/` 資料夾，保持根目錄整潔。

## 目標資料夾結構
```
job-report/
├── frontend/
│   ├── app.js
│   ├── app.css
│   ├── dashboard-renderers.js
│   ├── query-definitions.js
│   └── site-manifest.json
└── ...
```

## 相依關係（需要同步修改）
- `run_all.py` 的 `copy_frontend_bundle()` 從 `ROOT_DIR / asset_name` 複製 → 改為 `ROOT_DIR / "frontend" / asset_name`

## 實作步驟

- [x] **步驟 1：建立 `frontend/` 資料夾並移動檔案**
  - 建立 `frontend/`
  - 移動 `app.js`、`app.css`、`dashboard-renderers.js`、`query-definitions.js`、`site-manifest.json`

- [x] **步驟 2：修正 `run_all.py` 的複製路徑**
  - 將 `copy_frontend_bundle()` 中的 `ROOT_DIR / asset_name` 改為 `ROOT_DIR / "frontend" / asset_name`

- [x] **步驟 3：驗證**
  - 執行 `uv run python run_all.py --steps html` 確認前端檔案正確複製到 `output/`

- [x] **步驟 4：更新 `tree.md` 與 `README.md`**
