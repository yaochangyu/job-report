# Dashboard 8：頁面點擊熱點分析（Page Click Heatmap）

> **目的**：在實際頁面截圖上疊加點擊次數 badge，呈現 Clarity 風格的點擊熱點圖  
> **資料來源**：Elasticsearch `operation-logs`，篩選 `eventType=click`  
> **技術方案**：Playwright 截圖 + CSS 定位 badge 疊加  
> **輸出**：`click_heatmap_report.py` → `output/click-heatmap/index.html`  
> **建立日期**：2026-04-11

---

## 技術挑戰與解決方案

### 核心問題

前端是 Nuxt 3（Vue 3），追蹤透過 Vue 元件內的程式碼發送 `featureId` 到後端。  
DOM 上**沒有** `data-feature-id` 屬性 → 無法自動對應 featureId 到 DOM 元素。

### 解決方案：Config 驅動 + 自動探索輔助

1. **自動探索**：用 Playwright 掃描頁面上所有可點擊元素，匯出位置 + 文字 → 產生對應表範本
2. **手動對應**：使用者在 JSON config 中填入 featureId → 元素位置的對應
3. **報表產生**：截圖 + 讀取 config + 查詢 ES → 產生帶有 badge 疊加的 HTML

---

## 實作計畫

### Step 0 — 資料探索與驗證

- [x] **Step 0.1** — 查詢 ES 確認 `pageUrl` × `featureId` 在 click 事件中的資料分佈
  - ~~pageName~~ click 事件中無 `pageName`，改用 `pageUrl`（text 欄位，需用 runtime_mappings 提取路徑）
  - 結果：首頁 `/` 有 195K clicks、50 種 featureId；搜尋頁 `/search/job` 有 31K clicks
  - **為什麼**：確認有足夠資料產生有意義的熱點圖，並決定要涵蓋哪些頁面

---

### Step 1 — 頁面對應配置（`click_heatmap_config.json`）

- [x] **Step 1.1** — 建立 pageName → URL 對應表
  - 定義每個 pageName 對應的實際 URL，用於 Playwright 截圖
  - 格式範例：
    ```json
    {
      "pages": [
        {
          "page_name": "home-page",
          "url": "https://www.1111.com.tw",
          "viewport": { "width": 1440, "height": 900 }
        }
      ]
    }
    ```
  - **為什麼**：Playwright 需要知道要截圖哪個 URL

- [x] **Step 1.2** — 用 Playwright 自動探索可點擊元素，產生對應表範本
  - 掃描頁面上所有 `<a>`、`<button>`、`[role="button"]` 等元素
  - 匯出每個元素的：bounding box (x, y, width, height)、文字內容、href
  - 輸出成 JSON 範本，供使用者填入 featureId
  - **為什麼**：減少手動量測座標的工作，使用者只需對照 featureId 填入即可

- [x] **Step 1.3** — 手動補完 featureId → 元素對應
  - 使用者根據 Step 1.2 產生的範本，將 ES 中的 featureId 對應到正確的元素位置
  - 格式範例：
    ```json
    {
      "feature_id": "search-general-submit",
      "x": 850, "y": 210, "width": 80, "height": 36,
      "label": "搜尋按鈕"
    }
    ```
  - **為什麼**：這是 featureId → 位置對應的唯一可靠來源

---

### Step 2 — 報表產生腳本（`click_heatmap_report.py`）

- [x] **Step 2.1** — 截圖功能
  - 用 Playwright（Python）載入每個頁面 URL
  - 截取全頁截圖（full page screenshot），存為 PNG
  - 處理彈窗關閉、Cookie consent 等干擾元素
  - **為什麼**：截圖是疊加 badge 的底圖基礎

- [x] **Step 2.2** — ES 查詢：各頁面的 featureId 點擊數
  - 篩選 `eventType=click` + `system=jobbank-web`
  - 以 `pageName` → `featureId` 雙層 aggregation 取得點擊數
  - **為什麼**：取得要顯示在 badge 上的數字

- [x] **Step 2.3** — HTML 疊加產生
  - 截圖作為 `<img>` 底圖
  - 外層用 `position: relative` 容器包裹
  - 每個 featureId 用 `position: absolute` 的 badge 定位
  - badge 樣式：圓角小方塊，背景半透明紅/橙色，白色數字，帶陰影
  - Hover tooltip 顯示 featureId 名稱與詳細點擊數
  - **為什麼**：這是 Clarity 風格熱點圖的核心呈現方式

- [x] **Step 2.4** — 頁面切換機制
  - 如果有多個頁面，用 Tab 或下拉選單切換不同頁面的熱點圖
  - 每個頁面獨立的截圖 + badge 疊加
  - **為什麼**：單一 HTML 檔案涵蓋所有頁面，方便瀏覽

- [x] **Step 2.5** — 未對應 featureId 的備援表格
  - 若某些 featureId 在 config 中沒有位置對應，以表格形式列在底部
  - 顯示 featureId、點擊數、佔比
  - **為什麼**：確保所有點擊數據都有呈現，不會因為缺少對應而遺漏

---

### Step 3 — 整合與測試

- [ ] **Step 3.1** — 更新 `run_all.py`
  - 加入 Dashboard 8 的執行
  - 更新導覽頁 `output/index.html`
  - **為什麼**：確保一鍵執行能涵蓋新報表

- [ ] **Step 3.2** — 更新 `tree.md` 與 `grafana-dashboard.plan.md`
  - 加入新檔案與計畫項目
  - **為什麼**：維護專案文件的完整性

---

## 預期產出畫面

```
┌─────────────────────────────────────────────────────────────┐
│  頁面點擊熱點分析 — Page Click Heatmap                       │
│  資料來源：operation-logs · 查詢區間：...                     │
├─────────────────────────────────────────────────────────────┤
│  [Tab: home-page] [Tab: search-job-page] [Tab: job-page]    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │   1111人力銀行                               │   │    │
│  │  │                                              │   │    │
│  │  │  ┌─────────────┐  ┌──────┐                   │   │    │
│  │  │  │  搜尋關鍵字  │  │ 搜尋 │ [44,123]          │   │    │
│  │  │  └─────────────┘  └──────┘                   │   │    │
│  │  │                                              │   │    │
│  │  │  [學生 1,023] [上班族 1,045] [新鮮人 613]      │   │    │
│  │  │                                              │   │    │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐            │   │    │
│  │  │  │職缺卡片│ │職缺卡片│ │職缺卡片│            │   │    │
│  │  │  │ [5,234]│ │ [3,102]│ │ [2,891]│            │   │    │
│  │  │  └────────┘ └────────┘ └────────┘            │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  │           ↑ 實際頁面截圖 + badge 疊加                │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  [Table] 未對應的 featureId 點擊數據                         │
│  featureId          │ 點擊數  │ 佔比                        │
│  some-unmatched-id  │ 1,234   │ 2.3%                       │
└─────────────────────────────────────────────────────────────┘
```

## 檔案結構

```
job-report-1/
├── click_heatmap_report.py           # 主程式
├── click_heatmap_config.json         # pageName → URL + featureId → 位置 對應表
├── click_heatmap_discover.py         # 輔助：自動探索可點擊元素產生對應範本
├── output/
│   └── click-heatmap/
│       ├── index.html                # 報表 HTML
│       └── screenshots/              # 頁面截圖 PNG
└── ...
```

## 依賴

- `playwright`（Python）— 頁面截圖與元素探索
- 需執行 `playwright install chromium` 安裝瀏覽器

---

## 工作流程（日常使用）

```
首次設定：
  1. uv run python click_heatmap_discover.py          → 產生 config 範本
  2. 手動編輯 click_heatmap_config.json               → 填入 featureId 對應
  
日常產報表：
  3. uv run python click_heatmap_report.py --days 7   → 截圖 + 查 ES + 產生 HTML
```
