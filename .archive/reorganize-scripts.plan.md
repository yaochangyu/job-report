# Reorganize Scripts into Folders

## 目標
將根目錄的腳本依職責分類到子資料夾，避免根目錄腳本持續累積。

## 目標資料夾結構
```
job-report/
├── builders/          # build_*_t2.py × 9（從 T1 產出 T2 parquet）
├── exporters/         # 資料匯出腳本（如 upload_to_sheets.py）
├── tools/             # 工具 / 一次性查詢腳本
├── common/            # 共用模組（不動）
├── run_all.py         # 保留根目錄
└── ...
```

## 相依關係（需要同步修改）
- `run_all.py` 用 `subprocess` 呼叫 builder：script 路徑字串 `"build_*.py"` → `"builders/build_*.py"`
- `run_all.py` import `extract_raw_events` → `from tools.extract_raw_events import ...`
- `build_homepage_blocks_t2.py` import `query_homepage_blocks` → `from tools.query_homepage_blocks import ...`

## 實作步驟

- [x] **步驟 1：建立資料夾與 `__init__.py`**
  - 建立 `builders/`、`exporters/`、`tools/`
  - `tools/` 需加 `tools/__init__.py`（因為有腳本被其他模組 import）
  - `builders/` 不需 `__init__.py`（只透過 subprocess 呼叫）
  - `exporters/` 不需 `__init__.py`（同上）

- [x] **步驟 2：移動 builder 腳本**
  - 將 `build_*_t2.py` × 9 移到 `builders/`
  - 確認這些腳本只 import `common.*`，不需修改 import

- [x] **步驟 3：移動工具腳本**
  - 將 `extract_raw_events.py`、`query_homepage_blocks.py`、`click_heatmap_discover.py` 移到 `tools/`

- [x] **步驟 4：修正 `run_all.py` 的相依**
  - 將 `"script": "build_*.py"` 改為 `"script": "builders/build_*.py"`（共 9 處）
  - 將 `from extract_raw_events import extract_raw_events` 改為 `from tools.extract_raw_events import extract_raw_events`

- [x] **步驟 5：修正 `build_homepage_blocks_t2.py` 的相依**
  - 將 `from query_homepage_blocks import ALL_FEATURE_IDS` 改為 `from tools.query_homepage_blocks import ALL_FEATURE_IDS`

- [x] **步驟 6：驗證**
  - 執行 `uv run python run_all.py --help` 確認無 import 錯誤
  - 執行其中一支 builder 確認可正常運作，例如：`uv run python builders/build_traffic_overview_t2.py --help`

- [x] **步驟 7：更新 `tree.md`**
  - 反映新的資料夾結構
