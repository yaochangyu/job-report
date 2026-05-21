# Upload T2 Data to Google Sheets

## 目標
將 `dataset/report/` 下各 T2 report 的 parquet 資料匯出到 Google Sheets，支援日 / 月 / 季 / 年分區，且**不在匯出層額外做人為 Top N 限制**；若來源資料含 `event_type`，要以各自統計結果分開輸出。

## 規格
- **Auth**：透過 `gws` CLI（googleworkspace cli），不需額外安裝 Google Sheets Python 套件
- **輸出位置**：`https://docs.google.com/spreadsheets/d/14YtyGO05UjJcGAQRx4WQURLbFwhebcR2tS2HYJGhWt4`（hardcode 於腳本中）
- **來源分區**：掃描 `dataset/report/{report}/date=*/*.parquet`、`monthly=*/*.parquet`、`quarterly=*/*.parquet`、`yearly=*/*.parquet`
- **Tab 命名**：
  - 無 `event_type`：`{report}_{scope}_{parquet檔名}`
  - 有 `event_type`：`{report}_{scope}_{parquet檔名}_{event_type}`
  - `scope` 固定為 `daily` / `monthly` / `quarterly` / `yearly`
- **event_type 規則**：若 parquet 含 `event_type` 欄位，匯出前先依 `event_type` 拆成不同 tab，避免 click / view 混在同一個 tab
- **分區欄位補齊**：
  - `date=*` 且缺少 `date` 欄位時，從資料夾名稱注入 `date`
  - 所有輸出資料都額外補 `partition_type` 與 `partition_value` 欄位，方便追蹤來源
- **排除**：若未來再次出現 `session_ids.parquet`，仍略過不匯出
- **增量策略**：不再只看 sheet 最後一筆日期，改為使用 `_export_state` tab 記錄各 tab 最後成功匯出的 `partition_value`
- **冪等性**：同一個 tab 與同一個 `partition_value` 重跑時，不應重複追加
- **限制說明**：匯出腳本不做人為筆數裁切，但 Google Sheets 本身仍有儲存格與 API 配額限制

## gws 對應指令
| 操作 | 指令 |
|---|---|
| 確認登入 / 讀取 spreadsheet | `gws sheets spreadsheets get --params '{"spreadsheetId":"..."}'` |
| 取得現有 tabs | `gws sheets spreadsheets get --params '{"spreadsheetId":"..."}'` |
| 建立 tab | `gws sheets spreadsheets batchUpdate` + `addSheet` request |
| 讀取 tab 內容 | `gws sheets +read --spreadsheet ID --range "TabName!A:Z"` |
| 追加資料 | `gws sheets spreadsheets values append` |
| 更新 `_export_state` | `gws sheets spreadsheets values update` |

## 實作步驟

- [x] **步驟 1：確認 `gws` 已登入**
  - 先確認目標 spreadsheet 可讀，避免後面做到一半才發現帳號或權限有問題
  - 這一步已完成，可作為後續實作 `gsheets_client` 的基準

- [ ] **步驟 2：建立 `common/gsheets_client.py`**
  - 需要先把所有 `gws` subprocess 呼叫集中封裝，後續主流程才不會散落一堆 shell 字串，方便處理錯誤與重用
  - 提供 `get_existing_tabs(spreadsheet_id)`、`ensure_tab(spreadsheet_id, tab_name)`、`read_range(spreadsheet_id, range_name)`、`append_rows(spreadsheet_id, tab_name, rows)`
  - 提供 `_export_state` 專用的 `read_export_state(spreadsheet_id)` 與 `write_export_state(spreadsheet_id, rows)`，讓增量判斷不要綁死在 A 欄日期
  - 在這一步一併處理 tab 名稱正規化，避免名稱過長或字元不合法造成 Sheets API 失敗

- [ ] **步驟 3：建立 `common/parquet_loader.py`**
  - 需要有一個共用 loader 掃描所有 T2 分區，否則主腳本會混雜太多路徑判斷與資料整理邏輯
  - 掃描 `dataset/report/` 下所有 daily / monthly / quarterly / yearly parquet，回傳統一的 export unit 結構
  - 若來源缺少 `date` 欄位或分區資訊，要在這裡補 `date`、`partition_type`、`partition_value`
  - 若來源含 `event_type`，要在這一步先拆成不同 export unit，確保後續每個 tab 只處理單一 event type
  - 不加入 Top N、row limit 之類的人為裁切，保持與來源 parquet 一致

- [ ] **步驟 4：建立主腳本 `exporters/upload_to_sheets.py`**
  - 需要一個正式入口把掃描 parquet、建立 tab、增量判斷、上傳資料串起來，這才是真正可執行的匯出流程
  - `SPREADSHEET_ID = "14YtyGO05UjJcGAQRx4WQURLbFwhebcR2tS2HYJGhWt4"` hardcode 於腳本頂端
  - CLI 參數改為 `--partition-type`（可選：daily / monthly / quarterly / yearly）與 `--from-value`（可選，覆蓋 `_export_state` 起點）
  - 流程：掃描 parquet → 依 tab 組裝資料 → 讀取 `_export_state` → 過濾未匯出的 `partition_value` → 建立 / 補 header / 追加資料 → 回寫 `_export_state`
  - 顯示每個 tab 的處理狀態，方便看出是新建 tab、略過、還是有實際上傳
  - 加入 `sys.path.insert(0, str(Path(__file__).parent.parent))` 以正確引用 `common/`

- [ ] **步驟 5：測試驗證**
  - 需要實跑一次確認 daily / monthly / quarterly / yearly 都能正確建立 tab，避免只測到單一路徑
  - 需要驗證含 `event_type` 的 parquet 是否真的被拆到不同 tab，確保 click / view 沒有混在一起
  - 再執行一次確認 `_export_state` 生效，避免同一個 `partition_value` 被重複上傳
