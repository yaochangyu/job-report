# Grafana Dashboard 數據分析計畫

> **資料來源**: Elasticsearch `operation-logs` index（透過 Grafana Datasource `af55vm1ovng1sb`）  
> **系統**: `jobbank-web`  
> **實作方式**: Python 腳本 + HTML（延續 `category_tab_report.py` 模式）  
> **建立日期**: 2026-04-10

---

## 資料結構摘要

### 完整欄位清單（ES Mapping）

| 欄位 | ES 類型 | 可 Aggregation | 說明 |
|---|---|---|---|
| `@timestamp` | date | YES | 事件時間 |
| `@timestamp_ms` | long | YES | 事件時間（毫秒） |
| `anonymousId` | keyword | YES | 匿名使用者 ID |
| `sessionId` | keyword | YES（七日 ~555K unique） | Session ID |
| `userId` | keyword | YES | 登入使用者 ID |
| `clientId` | keyword | YES | Client ID（固定 `jobbank-web`） |
| `system` | keyword | YES | 系統名稱（`jobbank-web`） |
| `source` | keyword | YES | 來源（固定 `web`） |
| `eventType` | keyword | YES | 事件類型（`view` / `click`） |
| `action` | keyword | YES | 動作（`view` / `click` / `apply`） |
| `featureId` | keyword | YES | 功能 ID |
| `featureName` | keyword | YES | 功能名稱 |
| `featureType` | keyword | YES | 功能類型（`page`） |
| `deviceType` | keyword | YES | 裝置（`mobile` / `desktop`） |
| `os` | keyword | YES | 作業系統 |
| `browser` | keyword | YES | 瀏覽器 |
| `browserVersion` | keyword | YES | 瀏覽器版本（jobbank-web 無資料） |
| `osVersion` | keyword | YES | OS 版本（jobbank-web 無資料） |
| `locale` | keyword | YES | 語系（100% `zh-TW`） |
| `networkType` | keyword | YES | 網路類型（jobbank-web 無資料） |
| `appVersion` | keyword | YES | App 版本（jobbank-web 無資料） |
| `buildNumber` | keyword | YES | Build 號（jobbank-web 無資料） |
| `pageUrl` | keyword | YES | 當前頁面 URL |
| `previousPageUrl` | keyword | YES | 前一頁 URL |
| `pageName` | keyword | YES | 頁面名稱 |
| `previousPageName` | keyword | YES | 前一頁名稱 |
| `screenName` | keyword | YES | 畫面名稱 |
| `previousScreenName` | keyword | YES | 前一畫面名稱 |
| `messageId` | keyword | YES | 訊息唯一 ID |
| `eventTime` | date | YES | 前端事件時間 |
| `metadata` | dynamic object | 需用 Painless Script | 動態欄位（見下方） |
| `experiments` | object | — | 實驗欄位（jobbank-web 無資料） |

### metadata 欄位分析（依 featureId）

| featureId | metadata 欄位 | 範例值 |
|---|---|---|
| `job-page` | `jobId` | `132496421` |
| `apply-job` | `jobId`, `companyId`, `companyName`, `source` | source: `job-detail`/`search`/`corp`/`job-pair`/`welcome` |
| `explore-jobs-organic` | `jobId`, `jobName`, `companyId`, `companyName`, `identityType`, `categoryTab` | identityType: `Default`/`Student`/`OfficeWorker`/`Reenter`/`Freshman`/`Senior`; categoryTab: `AI 推薦`/... |
| `explore-jobs-organic-corp` | （同上） | |
| `explore-company-*` | `companyId`, `companyName`, `industryTab` | industryTab: `一般傳統製造`/`批發╱零售`/`醫療照護╱環境衛生`/... |
| `corp-page` | `companyId` | |
| `company-select-job` | `companyId`, `companyName`, `source`, `link` | source: `corp-page` |
| `news-card-*` | `articleId`, `articleTitle`, `categoryTab`, `identityType`, `identityFeatureId` | categoryTab: `CareerProspects`/`JobHunting`/`TrendAnalysis`; identityType: `Default`/`Senior` |

### 七日資料量（2026-04-03 ~ 2026-04-10）

| 指標 | 數值 |
|---|---|
| 總事件數 | ~3,075,785 |
| View 事件 | ~2,790,155（90.8%） |
| Click 事件 | ~283,069（9.2%） |
| Apply 事件（action=apply） | ~111,703 |
| 每日 Unique Sessions | ~33K ~ 143K |
| 七日 Unique Sessions | ~555,172 |
| 裝置比例 | mobile 65% / desktop 35% |

### featureId 完整分類

| 類別 | featureId | 七日總量 | 備註 |
|---|---|---|---|
| **頁面瀏覽** | `job-page`(1,811K), `search-job-page`(614K), `home-page`(316K), `job-pair-page`(25K), `job-preview-page`(2.7K), `corp-page`(263), `corp-preview-new-page`(544), `welcome-page`(451) | ~2,769K | eventType=view |
| **應徵** | `apply-job` | ~112K | action=apply |
| **一般搜尋** | `search-general-keyword`(44K), `search-general-submit`(33K), `search-general`(20K) | ~97K | eventType=click |
| **搜尋結果頁** | `search-job-page`(614K), `search-corp-page`(13K), `search-gig-page`(6.9K), `search-intern-page`(213) | ~634K | eventType=view |
| **AI 搜尋** | `search-ai-keyword`(12K), `search-ai-submit`(1K), `search-ai`(617), `search-ai-voice-input`(401), `search-ai-chat-mode`(269) | ~14.5K | eventType=click |
| **快速篩選** | `T-job-location`(26K), `T-job-category`(17K) | ~43K | eventType=click |
| **探索職缺** | `explore-jobs-organic`(5K), `explore-jobs-organic-corp`(1K) | ~6K | 有 categoryTab metadata |
| **探索企業** | `explore-company-corp`(505), `explore-company-job1`(483), `explore-company-job2`(353), `explore-company-job-more`(152), `explore-company-manufacturing`(92), `explore-company-service`(70), `explore-company-next`(1) | ~1.7K | 有 industryTab metadata |
| **身份辨識** | `identify-returning`(1.9K), `identify-student`(1K), `identify-worker`(1K), `identify-professional`(957), `identify-senior`(622), `identify-fresh`(613), `identify-personal`(408) + 各 tab | ~8.8K | |
| **產業分類** | 餐飲╱住宿服務(91), 電子科技╱資訊╱軟體╱半導體(79), ... | ~560 | featureId 為中文產業名 |
| **新聞** | `news-card-1~4`(108), `news-workplace`(3), `news-industry`(2) | ~113 | 有 articleId/articleTitle metadata |
| **企業選職缺** | `company-select-job` | ~364 | 有 companyId/source metadata |

---

## Dashboard 實作計畫

### Dashboard 1：整體流量概覽（Traffic Overview）— P0

> **目的**：一眼掌握 jobbank-web 的整體運營狀態  
> **輸出**：`traffic_overview_report.py` → `output/traffic-overview/index.html`

- [ ] **Step 1.1** — KPI 指標卡
  - 總事件數、View 數、Click 數、Apply 數
  - Unique Sessions 數
  - Click Rate（Click / 總量）、Apply Rate（Apply / Job Page View）
  - **為什麼**：提供即時的關鍵數字，快速判斷流量是否正常

- [ ] **Step 1.2** — 每日流量趨勢（Stacked Area Chart）
  - X 軸：日期，Y 軸：事件數
  - 三條線：view / click / apply（apply 用右側 Y 軸，因量級差異大）
  - 疊加 unique sessions 線
  - **為什麼**：觀察流量的日變化趨勢，識別異常波動

- [ ] **Step 1.3** — 每小時流量分佈（Bar Chart）
  - X 軸：小時（0-23，台灣時區），Y 軸：平均事件數
  - **為什麼**：找出流量高峰時段，支援行銷排程與系統運維決策

- [ ] **Step 1.4** — 裝置分佈（Doughnut + Table）
  - mobile vs desktop 佔比
  - OS 分佈（Android / iPhone / Windows / macOS / 其他）
  - 瀏覽器分佈 Top 10
  - **為什麼**：掌握使用者的裝置組成，指引 UI/UX 與測試策略

---

### Dashboard 2：搜尋行為分析（Search Behavior）— P1

> **目的**：了解使用者的搜尋模式與 AI 搜尋的採用率  
> **輸出**：`search_behavior_report.py` → `output/search-behavior/index.html`

- [ ] **Step 2.1** — 搜尋功能總覽（Horizontal Bar Chart）
  - 比較各搜尋類型的使用量
  - 分類：搜尋結果頁（view）/ 一般搜尋互動（click）/ AI 搜尋互動（click）/ 快速篩選（click）
  - **為什麼**：衡量搜尋功能的整體使用狀況

- [ ] **Step 2.2** — AI 搜尋 vs 一般搜尋每日趨勢（Time Series）
  - 每日 `search-general-*` vs `search-ai-*` 的 click 數
  - 計算 AI 搜尋佔比趨勢（AI / (AI + General)）
  - **為什麼**：追蹤 AI 搜尋功能是否持續成長

- [ ] **Step 2.3** — 搜尋結果頁分佈（Doughnut）
  - `search-job-page`(正職) / `search-corp-page`(企業) / `search-gig-page`(兼差) / `search-intern-page`(實習) 的佔比
  - **為什麼**：了解使用者主要搜尋的職缺類型

- [ ] **Step 2.4** — AI 搜尋互動方式（Doughnut + Trend）
  - keyword(12K) / submit(1K) / voice-input(401) / chat-mode(269) / general(617) 的佔比
  - 每日趨勢
  - **為什麼**：了解使用者偏好哪種 AI 互動方式

- [ ] **Step 2.5** — 快速篩選使用（Bar）
  - `T-job-location`(26K) vs `T-job-category`(17K) 的使用量與每日趨勢
  - **為什麼**：了解地區 vs 職類篩選的使用偏好

---

### Dashboard 3：應徵轉換分析（Apply Conversion）— P0

> **目的**：追蹤應徵行為與轉換漏斗  
> **輸出**：`apply_conversion_report.py` → `output/apply-conversion/index.html`

- [ ] **Step 3.1** — 應徵 KPI
  - 總應徵數、每日平均應徵數
  - 應徵轉換率（apply / job-page view）
  - 應徵來源分佈（metadata.source: job-detail 59% / search 28% / corp 13%）
  - **為什麼**：核心業務指標

- [ ] **Step 3.2** — 應徵每日趨勢（Dual Y-Axis Time Series）
  - 左 Y 軸：`job-page` view 數
  - 右 Y 軸：`apply-job` 數
  - 折線：每日轉換率
  - **為什麼**：追蹤應徵量與轉換率的健康度

- [ ] **Step 3.3** — 轉換漏斗（Funnel Chart）
  - `home-page`(316K) → `search-job-page`(614K) → `job-page`(1,811K) → `apply-job`(112K)
  - 各階段數量與階段間的轉換率
  - **為什麼**：找出使用者在哪個環節流失最多（注意：非 session-based，為整體事件數）

- [ ] **Step 3.4** — 應徵來源分佈（Doughnut + Table）
  - metadata.source: `job-detail`(65K) / `search`(32K) / `corp`(14K) / `job-pair`(533) / `welcome`(29)
  - **為什麼**：了解使用者從哪個入口應徵最多

- [ ] **Step 3.5** — 應徵裝置/OS 分佈（Grouped Bar）
  - mobile(72K) vs desktop(39K) 應徵量
  - 各裝置的「應徵/職缺瀏覽」轉換率
  - OS 分佈：Android(48K) / Windows(34K) / iPhone(25K) / macOS(1.5K) / ...
  - **為什麼**：確認行動端的應徵體驗是否順暢

- [ ] **Step 3.6** — 應徵時段分佈（Bar Chart）
  - 每小時 `apply-job` 數量
  - **為什麼**：了解應徵高峰時段

---

### Dashboard 4：功能互動分析（Feature Engagement）— P2

> **目的**：深入各功能模組的使用狀況  
> **輸出**：`feature_engagement_report.py` → `output/feature-engagement/index.html`

- [ ] **Step 4.1** — 探索職缺分析
  - organic vs corp 的 categoryTab 分佈（沿用既有邏輯）
  - identityType 分佈：Default(5.8K) / Student(100) / OfficeWorker(75) / Reenter(60) / ...
  - 每日趨勢
  - **為什麼**：追蹤「探索職缺」的 Tab 偏好與 AI 推薦佔比

- [ ] **Step 4.2** — 探索企業分析
  - featureId 分佈：corp / job1 / job2 / job-more / manufacturing / service
  - industryTab 分佈：一般傳統製造(218) / 批發╱零售(172) / 醫療照護(154) / 餐飲(150) / ...
  - **為什麼**：衡量企業探索功能的使用深度與熱門產業

- [ ] **Step 4.3** — 身份辨識分析（Pie + Bar）
  - 主要身份分佈：returning(1.9K) / student(1K) / worker(1K) / professional(957) / senior(622) / fresh(613) / personal(408)
  - 各身份的 tab 互動深度（tab-1/2/3 的點擊比例）
  - **為什麼**：了解使用者群體組成與互動深度

- [ ] **Step 4.4** — 產業點擊分佈（Horizontal Bar）
  - 各產業分類的點擊次數
  - **為什麼**：了解熱門產業需求

- [ ] **Step 4.5** — 新聞互動分析（Table）
  - news-card 位置效果：card-1(30) / card-2(30) / card-3(24) / card-4(25)
  - 新聞分類：CareerProspects(44) / JobHunting(36) / TrendAnalysis(26)
  - 閱讀者身份：Default(88) / Senior(18)
  - **為什麼**：衡量新聞內容的點擊效果

- [ ] **Step 4.6** — 企業選職缺（company-select-job）分析
  - 使用量趨勢
  - 來源分佈（metadata.source）
  - **為什麼**：了解企業端的互動行為

---

### Dashboard 5：裝置與平台分析（Device & Platform）— P1

> **目的**：深入分析不同裝置/平台的使用行為差異  
> **輸出**：`device_platform_report.py` → `output/device-platform/index.html`

- [ ] **Step 5.1** — 裝置類型每日趨勢（Stacked Area）
  - mobile vs desktop 的每日事件數
  - mobile 佔比趨勢線
  - **為什麼**：追蹤行動端的成長趨勢

- [ ] **Step 5.2** — OS 分佈（Doughnut + Table）
  - Android(1,141K) / iPhone(851K) / Windows(804K) / macOS(45K) / iPad(15K) / Linux(24K) / 其他
  - **為什麼**：指引跨平台測試的優先級

- [ ] **Step 5.3** — 瀏覽器分佈（Horizontal Bar）
  - Chromium(1,813K) / Netscape(1,059K) / Google Chrome(169K) / Samsung Internet(7.7K) / Edge(7.1K) / ...
  - **為什麼**：確認瀏覽器相容性的測試覆蓋範圍

- [ ] **Step 5.4** — 裝置 × 行為交叉分析（Grouped Bar + Table）
  - 各裝置（mobile/desktop）的 view / click / apply 數量與佔比
  - 各裝置的 apply 轉換率比較
  - **為什麼**：找出不同裝置的行為差異

- [ ] **Step 5.5** — OS × 行為交叉分析（Table）
  - 各 OS 的 view / click / apply 數量
  - **為什麼**：識別特定 OS 上的體驗問題

---

### Dashboard 6：頁面流量排行（Page Ranking）— P2

> **目的**：掌握各頁面的流量與互動排名  
> **輸出**：`page_ranking_report.py` → `output/page-ranking/index.html`

- [ ] **Step 6.1** — Top 功能排行（Table + Bar）
  - 按 `featureId` 排序的 view / click 數量
  - 包含 click-through rate（CTR）
  - **為什麼**：快速識別高流量功能與低互動功能

- [ ] **Step 6.2** — 功能類別佔比（Treemap）
  - 將 featureId 歸類為：頁面瀏覽、搜尋、應徵、探索、身份辨識、其他
  - 以 Treemap 或分層 Bar 呈現
  - **為什麼**：以視覺化方式呈現功能使用的全局分佈

---

### Dashboard 7：頁面導航鏈路分析（Page Navigation Flow）— P1

> **目的**：追蹤頁面間的導航關係，了解使用者從哪個頁面進入、往哪個頁面離開  
> **輸出**：`page_navigation_report.py` → `output/page-navigation/index.html`  
> **關鍵欄位**：`pageName`、`previousPageName`、`pageUrl`、`previousPageUrl`（皆可 aggregation）

- [ ] **Step 7.1** — 頁面導航 Sankey 圖
  - `previousPageName` → `pageName` 的流量轉移
  - 過濾掉 `previousPageName` 為空的初始進入事件
  - **為什麼**：一眼看出使用者在各頁面間的主要流動路徑

- [ ] **Step 7.2** — 各頁面的 Top 來源（從哪來）
  - 以 `pageName` 分組，列出 Top 5 `previousPageName`
  - 包含次數與佔比
  - **為什麼**：找出每個頁面最主要的流量入口

- [ ] **Step 7.3** — 各頁面的 Top 目標（往哪去）
  - 以 `previousPageName` 分組，列出 Top 5 `pageName`（下一頁）
  - 包含次數與佔比
  - **為什麼**：了解使用者離開特定頁面後最常去哪裡

- [ ] **Step 7.4** — 完整鏈路排行（Table）
  - `previousPageName` → `pageName` 組合的轉換次數排行 Top 20
  - 包含裝置分佈（mobile / desktop）
  - **為什麼**：精確掌握最頻繁的頁面轉換路徑

- [ ] **Step 7.5** — 初始進入頁面分佈（Bar Chart）
  - `previousPageName` 為空的事件，統計 `pageName` 分佈
  - **為什麼**：了解使用者最常從哪個頁面開始瀏覽

---

### Grafana Dashboard JSON — 全部 Dashboard

> **目的**：產出可直接匯入 Grafana 的 Dashboard JSON，作為 HTML 報告的補充  
> **Datasource UID**：`af55vm1ovng1sb`（Elasticsearch `operation-logs`）  
> **輸出目錄**：`grafana-dashboards/`

每個 Dashboard JSON 對應一個 HTML 報告，包含相同的面板邏輯，但以 Grafana 原生面板呈現。

- [ ] **Step G.1** — Dashboard 1：整體流量概覽（`1-traffic-overview.json`）
  - Panel: KPI Stat（總事件數 / View / Click / Apply / Unique Sessions / Click Rate / Apply Rate）
  - Panel: 每日流量趨勢（Time Series, dual Y-axis）
  - Panel: 每小時流量分佈（Bar Chart）
  - Panel: 裝置分佈（Pie Chart）+ OS 分佈（Table）+ 瀏覽器 Top 10（Table）
  - 變數：`$timeRange`（Grafana 內建時間選擇器）

- [ ] **Step G.2** — Dashboard 2：搜尋行為分析（`2-search-behavior.json`）
  - Panel: 搜尋功能總覽（Bar Chart - horizontal）
  - Panel: AI vs 一般搜尋每日趨勢（Time Series）+ AI 佔比趨勢線
  - Panel: 搜尋結果頁分佈（Pie Chart）
  - Panel: AI 搜尋互動方式（Pie Chart + Time Series）
  - Panel: 快速篩選使用（Bar Chart + Time Series）

- [ ] **Step G.3** — Dashboard 3：應徵轉換分析（`3-apply-conversion.json`）
  - Panel: 應徵 KPI Stat（總應徵數 / 每日平均 / 轉換率）
  - Panel: 應徵每日趨勢（Time Series, dual Y-axis）+ 轉換率折線
  - Panel: 轉換漏斗（Bar Gauge）
  - Panel: 應徵來源分佈（Pie Chart + Table）
  - Panel: 應徵裝置/OS 分佈（Bar Chart - grouped）
  - Panel: 應徵時段分佈（Bar Chart）

- [ ] **Step G.4** — Dashboard 4：功能互動分析（`4-feature-engagement.json`）
  - Panel: 探索職缺 categoryTab 分佈（Bar Chart）+ identityType 分佈（Pie Chart）
  - Panel: 探索企業 featureId 分佈（Bar Chart）+ industryTab 分佈（Bar Chart）
  - Panel: 身份辨識分佈（Pie Chart）+ tab 互動深度（Bar Chart）
  - Panel: 產業點擊排行（Bar Chart - horizontal）
  - Panel: 新聞互動（Table）
  - Panel: 企業選職缺趨勢（Time Series）+ 來源分佈（Pie Chart）

- [ ] **Step G.5** — Dashboard 5：裝置與平台分析（`5-device-platform.json`）
  - Panel: 裝置類型每日趨勢（Time Series - stacked）+ mobile 佔比折線
  - Panel: OS 分佈（Pie Chart + Table）
  - Panel: 瀏覽器分佈（Bar Chart - horizontal）
  - Panel: 裝置 × 行為交叉分析（Bar Chart - grouped + Table）
  - Panel: OS × 行為交叉分析（Table）

- [ ] **Step G.6** — Dashboard 6：頁面流量排行（`6-page-ranking.json`）
  - Panel: Top 功能排行（Table + Bar Chart）含 CTR
  - Panel: 功能類別佔比（Bar Chart - stacked 或 Treemap plugin）

- [ ] **Step G.7** — Dashboard 7：頁面導航鏈路分析（`7-page-navigation.json`）
  - Panel: 頁面導航 Top 轉換路徑（Table：previousPageName → pageName + 次數）
  - Panel: 各頁面 Top 來源（Bar Chart - horizontal）
  - Panel: 各頁面 Top 目標（Bar Chart - horizontal）
  - Panel: 初始進入頁面分佈（Pie Chart）
  - Panel: 導航路徑每日趨勢（Time Series）
  - 注意：Sankey 圖需 Grafana plugin（`netsage-sankey-panel`），若未安裝則以 Table + Bar 替代

---

## 共用架構

### 程式架構

```
job-report/
├── common/
│   ├── __init__.py
│   ├── es_client.py          # Grafana _msearch 共用封裝
│   ├── html_template.py      # HTML header/footer/style 共用模板
│   └── chart_helpers.py      # Chart.js 輔助函式
├── traffic_overview_report.py
├── search_behavior_report.py
├── apply_conversion_report.py
├── feature_engagement_report.py
├── device_platform_report.py
├── page_ranking_report.py
├── page_navigation_report.py
├── run_all.py                 # 一鍵執行所有報告
├── output/
│   ├── traffic-overview/index.html
│   ├── search-behavior/index.html
│   ├── apply-conversion/index.html
│   ├── feature-engagement/index.html
│   ├── device-platform/index.html
│   ├── page-ranking/index.html
│   └── page-navigation/index.html
├── grafana-dashboards/
│   ├── 1-traffic-overview.json
│   ├── 2-search-behavior.json
│   ├── 3-apply-conversion.json
│   ├── 4-feature-engagement.json
│   ├── 5-device-platform.json
│   ├── 6-page-ranking.json
│   └── 7-page-navigation.json
├── category_tab_report.py     # 既有報告（保留）
├── index.html                 # 既有報告產出（保留）
└── tree.md
```

### CLI 介面（每支腳本統一）

```bash
python3 <report>.py                           # 預設：當日
python3 <report>.py --days 7                   # 近 7 天
python3 <report>.py --from 2026-04-01 --to 2026-04-10  # 指定區間
python3 <report>.py --output /tmp/report       # 自訂輸出目錄
```

---

## 已知限制

| 限制 | 影響 | 替代方案 |
|---|---|---|
| `metadata` 為 dynamic object，未建立索引 | 需透過 Grafana `_msearch` proxy + Painless Script 查詢 | 已有既有作法可沿用 |
| 轉換漏斗非 session-based | 漏斗數字為整體事件數，非真實使用者路徑 | 已於報告中標註此限制 |

---

## 實作順序

| 順序 | 項目 | 說明 |
|---|---|---|
| 0 | 建立共用模組 `common/` | 抽取 ES client、HTML 模板、Chart 輔助函式 |
| 1 | Dashboard 1 — 整體流量概覽（HTML + Grafana JSON） | P0 |
| 2 | Dashboard 3 — 應徵轉換分析（HTML + Grafana JSON） | P0 |
| 3 | Dashboard 2 — 搜尋行為分析（HTML + Grafana JSON） | P1 |
| 4 | Dashboard 5 — 裝置與平台分析（HTML + Grafana JSON） | P1 |
| 5 | Dashboard 7 — 頁面導航鏈路分析（HTML + Grafana JSON） | P1 |
| 6 | Dashboard 4 — 功能互動分析（HTML + Grafana JSON） | P2 |
| 7 | Dashboard 6 — 頁面流量排行（HTML + Grafana JSON） | P2 |
| 8 | `run_all.py` 整合腳本 | 一鍵產生所有報告 |
