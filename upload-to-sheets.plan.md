# Upload T2 Data to Google Sheets

## 目標
將 `dataset/report/` 下各 T2 report 的 parquet 資料，以累積追加的方式上傳到 Google Sheets。

## 規格
- **Auth**：透過 `gws` CLI（googleworkspace cli），不需額外套件
- **輸出位置**：`https://docs.google.com/spreadsheets/d/14YtyGO05UjJcGAQRx4WQURLbFwhebcR2tS2HYJGhWt4`（hardcode 於腳本中）
- **Tab 命名**：`{report}_{parquet檔名}` 例如 `traffic-overview_daily_summary`
- **大型 parquet**：超過 1000 筆的 parquet 只取 Top 100（按數量欄排序）
- **排除**：`traffic-overview/session_ids.parquet`（session ID 列表，無分析價值）
- **date 欄位**：無 date 欄的 parquet，從資料夾名稱 `date=YYYY-MM-DD` 注入
- **累積追加**：比對 sheet 最後一筆日期，只上傳更新的日期

## gws 對應指令
| 操作 | 指令 |
|---|---|
| 確認登入 | `gws sheets spreadsheets get --params '{"spreadsheetId":"..."}'` |
| 取得現有 tabs | `gws sheets spreadsheets get --params '{"spreadsheetId":"..."}'` |
| 建立 tab | `gws sheets spreadsheets batchUpdate` + `addSheet` request |
| 讀取最後日期 | `gws sheets +read --spreadsheet ID --range "TabName!A:A"` |
| 追加資料 | `gws sheets spreadsheets values append` |

## 實作步驟

- [x] **步驟 1：確認 `gws` 已登入**
  - 執行 `gws sheets spreadsheets get` 對目標 spreadsheet 測試連線
  - 確認回傳正常，無需安裝任何 Python 套件

- [ ] **步驟 2：建立 `common/gsheets_client.py`**
  - 封裝所有 `gws` subprocess 呼叫
  - `get_existing_tabs(spreadsheet_id)` — 取得現有所有 tab 名稱
  - `create_tab(spreadsheet_id, tab_name)` — 建立新 tab
  - `get_last_date(spreadsheet_id, tab_name)` — 讀取該 tab A 欄最後一個日期值
  - `append_rows(spreadsheet_id, tab_name, rows)` — 批次追加資料

- [ ] **步驟 3：建立 `common/parquet_loader.py`**
  - 掃描 `dataset/report/` 下所有 `{report}/date={YYYY-MM-DD}/{name}.parquet`
  - 排除 `session_ids.parquet`
  - 無 date 欄的 parquet 注入 `date` 欄位（從資料夾名稱取得）
  - 大型 parquet（>1000 筆）截取 Top 100（按 count/total 欄位排序，若無則取前 100）

- [ ] **步驟 4：建立主腳本 `exporters/upload_to_sheets.py`**
  - `SPREADSHEET_ID = "14YtyGO05UjJcGAQRx4WQURLbFwhebcR2tS2HYJGhWt4"` hardcode 於腳本頂端
  - CLI 參數：`--from-date`（可選，覆蓋自動偵測）、`--top-n`（大型 parquet 限制，預設 100）
  - 流程：掃描 parquet → 對每個 tab 取得最後日期 → 過濾新資料 → 追加上傳
  - 顯示進度（每個 tab 上傳前後印出狀態）
  - 加入 `sys.path.insert(0, str(Path(__file__).parent.parent))` 以正確引用 `common/`

- [ ] **步驟 5：測試驗證**
  - 執行一次，確認 tab 建立、header、資料追加正確
  - 再執行一次確認冪等性（不重複上傳已有的日期）
