# Upload T2 Data to Google Sheets

## 目標
將 `dataset/report/` 下各 T2 report 的 parquet 資料，以累積追加的方式上傳到 Google Sheets。

## 規格
- **Auth**：OAuth2 互動登入，token 存於本地
- **Tab 命名**：`{report}_{parquet檔名}` 例如 `traffic-overview_daily_summary`
- **大型 parquet**：超過 1000 筆的 parquet 只取 Top 100（按數量欄排序）
- **排除**：`traffic-overview/session_ids.parquet`（session ID 列表，無分析價值）
- **date 欄位**：無 date 欄的 parquet，從資料夾名稱 `date=YYYY-MM-DD` 注入
- **累積追加**：比對 sheet 最後一筆日期，只上傳更新的日期

## 實作步驟

- [ ] **步驟 1：安裝依賴套件**
  - 在 `pyproject.toml` 加入 `gspread`、`google-auth-oauthlib`
  - 執行 `uv sync` 確認安裝成功

- [ ] **步驟 2：建立 OAuth2 認證模組**
  - 建立 `common/gsheets_auth.py`
  - 實作 OAuth2 flow：首次執行開啟瀏覽器授權，token 存於 `~/.claude/creds/gsheets_token.json`
  - credentials.json 路徑：`~/.claude/creds/gsheets_credentials.json`

- [ ] **步驟 3：建立 parquet 掃描與載入邏輯**
  - 建立 `common/parquet_loader.py`
  - 掃描 `dataset/report/` 下所有 `{report}/date={YYYY-MM-DD}/{name}.parquet`
  - 排除 `session_ids.parquet`
  - 無 date 欄的 parquet 注入 `date` 欄位（從資料夾名稱取得）
  - 大型 parquet（>1000 筆）截取 Top 100（按 count/total 欄位排序，若無則取前 100）

- [ ] **步驟 4：建立 Google Sheets 上傳邏輯**
  - 建立 `common/gsheets_uploader.py`
  - 實作 `get_or_create_tab(spreadsheet, tab_name)` — tab 不存在時自動建立
  - 實作 `get_last_date(tab)` — 讀取 sheet 最後一筆 date 欄的值
  - 實作 `append_rows(tab, df)` — 批次追加資料（包含 header 若為空 tab）

- [ ] **步驟 5：建立主腳本 `upload_to_sheets.py`**
  - CLI 參數：`--spreadsheet-id`（必填）、`--from-date`（可選，覆蓋自動偵測）、`--top-n`（大型 parquet 限制，預設 100）
  - 流程：auth → 掃描 parquet → 對每個 tab 取得最後日期 → 過濾新資料 → 追加上傳
  - 顯示進度（每個 tab 上傳前後印出狀態）

- [ ] **步驟 6：測試驗證**
  - 使用測試 spreadsheet 執行一次，確認 tab 建立、header、資料追加正確
  - 再執行一次確認冪等性（不重複上傳已有的日期）
