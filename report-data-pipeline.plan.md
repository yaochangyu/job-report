# Report Data Pipeline 重構計畫

> **目標**：將目前「ES 直接查詢 + 報表直接產 HTML + 前端直接讀大份事件 parquet」的流程，重構為三層式資料管線：  
> `extract（ES → raw parquet）` → `transform（raw parquet → report parquet）` → `render（report parquet → html）`
>
> **重構目的**：
> 1. 讓 ES 只需要查一次，避免各報表重複打 ES。
> 2. 讓每份報表只讀自己需要的欄位與結果，降低資料量。
> 3. 讓 HTML 呈現層不直接碰大型原始事件資料，改善 GitHub Pages 載入速度。

---

## 規劃中的目錄分層

```text
dataset/
├── raw/       # 從 ES 匯出的標準化原始事件 parquet（依 date 分區）
├── report/    # 各報表分析完成後的報表專用 parquet
└── manifest/  # 各層資料集的 metadata / manifest

output/
└── ...        # HTML 與前端靜態資產
```

---

## 實作步驟

- [x] **Step 1 — 定義三層資料管線的資料契約與目錄結構**
  - 明確定義 `raw`、`report`、`output` 各層責任，包含檔案命名、目錄位置、manifest 格式與日期分區規則。
  - **為什麼需要這一步**：如果一開始不先定義資料契約，後面各腳本很容易再次耦合，最後又回到「分析邏輯、前端資料、部署內容混在一起」的狀態。

- [x] **Step 2 — 建立 ES → raw parquet 的抽取流程**
  - 新增或重構抽取腳本，支援：
    - 指定日期區間
    - 指定往前幾天
  - 將 ES 事件標準化後寫入本地 `dataset/raw/`，並依 `date=YYYY-MM-DD` 分區。
  - **為什麼需要這一步**：這是整條資料管線的唯一資料入口；ES 只查一次，後續報表就不必重複打 ES。

- [x] **Step 3 — 定義 raw parquet 的標準欄位**
  - 將目前報表共用的事件欄位整理成穩定 schema，例如：
    - 時間：`date`、`hour`、`occurred_at`
    - 行為：`event_type`、`action`
    - 脈絡：`session_id`
    - 頁面/功能：`feature_id`、`page_path`、`previous_page_path`
    - 裝置：`device_type`、`os`、`browser`
    - 業務欄位：`source`、`category_tab`、`identity_type`、`industry_tab`
  - **為什麼需要這一步**：raw 層若沒有穩定欄位契約，後面每份報表都要自己補 mapping，會讓維護成本失控。

- [ ] **Step 4 — 將各報表重構為讀取 raw parquet，而非直接查 ES**
  - 調整各報表產生器，改成從本地 `dataset/raw/` 讀資料。
  - 每份報表只保留自己的查詢邏輯與指標計算，不再關心 ES 查詢細節。
  - **為什麼需要這一步**：這一步會把「資料取得」與「資料分析」分離，讓報表邏輯變得可重跑、可測、可離線執行。
  - PoC：
    - [x] **Step 4.1 — traffic-overview 改讀 T1 raw parquet**
    - [x] **Step 4.2 — search-behavior 改讀 T1 raw parquet**
    - [x] **Step 4.3 — page-navigation 改讀 T1 raw parquet**
    - [x] **Step 4.4 — page-ranking 改讀 T1 raw parquet**
    - [x] **Step 4.5 — device-platform 改讀 T1 raw parquet**

- [ ] **Step 5 — 為每份報表輸出 report parquet**
  - 各報表分析完成後，將輸出寫入 `dataset/report/<report-name>/`。
  - 每份報表只存自己需要的結果欄位，不攜帶多餘明細。
  - **為什麼需要這一步**：前端與 HTML 產生器應該吃小而穩定的報表資料，而不是整包原始事件 parquet。
  - PoC：
    - [x] **Step 5.1 — traffic-overview 輸出 T2 report parquet**
    - [x] **Step 5.2 — search-behavior 輸出 T2 report parquet**
    - [x] **Step 5.3 — page-navigation 輸出 T2 report parquet**
    - [x] **Step 5.4 — page-ranking 輸出 T2 report parquet**
    - [x] **Step 5.5 — device-platform 輸出 T2 report parquet**

- [ ] **Step 6 — 定義各報表的 report parquet schema**
  - 逐一列出各報表最終會輸出的表結構，例如：
    - KPI
    - 趨勢資料
    - 分布資料
    - 排行資料
    - 導航鏈路資料
  - **為什麼需要這一步**：HTML 產生器與前端畫面必須依賴穩定輸入；先定 schema 才能避免畫面層反過來綁死分析層。
  - PoC：
    - [x] **Step 6.1 — 定義 traffic-overview 的 T2 schema 與 manifest**
    - [x] **Step 6.2 — 定義 search-behavior 的 T2 schema 與 manifest**
    - [x] **Step 6.3 — 定義 page-navigation 的 T2 schema 與 manifest**
    - [x] **Step 6.4 — 定義 page-ranking 的 T2 schema 與 manifest**
    - [x] **Step 6.5 — 定義 device-platform 的 T2 schema 與 manifest**

- [ ] **Step 7 — 重構 HTML 產生器只讀 report parquet**
  - 讓 HTML 產生器從 `dataset/report/` 讀取資料，不直接碰 raw parquet。
  - 視需求決定是：
    - 直接在後端產生完成版 HTML，或
    - 將 report parquet 再轉成小型 JSON 給前端讀取
  - **為什麼需要這一步**：這一步是改善載入速度的核心，因為畫面層不該直接載入數十 MB 的原始資料。
  - PoC：
    - [x] **Step 7.1 — traffic-overview 從 T2 產出 HTML**
    - [x] **Step 7.2 — search-behavior 從 T2 產出 HTML**
    - [x] **Step 7.3 — page-navigation 從 T2 產出 HTML**
    - [x] **Step 7.4 — page-ranking 從 T2 產出 HTML**
    - [x] **Step 7.5 — device-platform 從 T2 產出 HTML**

- [ ] **Step 8 — 重整 `run_all.py` 與部署流程**
  - 將流程拆成清楚的三段：
    - `extract`
    - `transform`
    - `render`
  - 調整 `deploy.sh`，讓 GitHub Pages 只帶需要的 HTML / 前端資產 / 輕量資料，不部署 raw parquet。
  - **為什麼需要這一步**：若部署流程不一起調整，前面重構完資料層，最後仍可能把大資料整包帶上線。
  - PoC：
    - [x] **Step 8.1 — traffic-overview 串接 extract → transform → render**
    - [x] **Step 8.2 — search-behavior 串接 extract → transform → render**
    - [x] **Step 8.3 — page-navigation 串接 extract → transform → render**
    - [x] **Step 8.4 — page-ranking 串接 extract → transform → render**
    - [x] **Step 8.5 — device-platform 串接 extract → transform → render**

- [x] **Step 9 — 規劃 manifest 與版本資訊**
  - 為 `raw` 與 `report` 層建立 manifest，紀錄：
    - 可用日期
    - 列數
    - schema version
    - 更新時間
    - 檔案路徑
  - **為什麼需要這一步**：資料層一旦分層，manifest 會是流程串接、錯誤追查與版本相容性的關鍵基礎。

- [ ] **Step 10 — build 驗證與測試策略**
  - build 驗證整條流程可執行，包含抽取、分析、HTML 產出與部署內容。
  - 盤點是否有既有測試可跑；若要執行測試，再由你確認。
  - **為什麼需要這一步**：這次重構會動到資料入口、分析邏輯與輸出格式，若沒有整體驗證，很容易局部成功、整體失敗。

---

## 建議的執行順序

1. 先完成 `extract` 契約與 raw parquet schema。  
2. 再挑一份最具代表性的報表做 PoC（建議 `traffic-overview`）。  
3. 確認 `raw → report → html` 跑通後，再逐份報表遷移。  
4. 最後再調整部署內容與前端讀取方式。

---

## 目前已知的設計重點

- 原始事件資料量已達數百萬筆，不適合直接在 GitHub Pages 前端初始化時全部載入。
- 報表層與畫面層應解耦；畫面層不該直接依賴 raw dataset。
- `report parquet` 可以保留給分析與重用，但前端最終是否直接讀 parquet，仍應依載入效能再決定。
