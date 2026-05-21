# period-subview-tabs 計畫書

## 目標

月報（`period_type=monthly`）內容區改為兩個子 tab：
- **月報** tab：月彙總 KPI + 趨勢圖 + breakdown（現有邏輯）
- **日報** tab：日期按鈕列 + 選定日的 KPI / breakdown（取代舊的 `.daily-day-selector`）

URL 反映完整狀態：`sub_view=monthly|daily` 與 `day=YYYY-MM-DD`

## 現況問題

- 日期按鈕與月報 breakdown 各自切換顯示，邏輯散落在多處
- `.daily-day-selector` / `#period-daily-drilldown` / `#period-breakdown-container` 顯隱耦合複雜
- URL 沒有記錄 sub_view / day

## 目標結構

```
[月份 tabs: 2026年05月 ｜ 2026年04月]
[子 tabs: 月報 ｜ 日報]               ← 僅 period_type=monthly 顯示

── 月報 active ──
  KPI cards + 趨勢圖 + breakdown

── 日報 active ──
  [1日][2日]…[N日]
  ────
  選定日的 KPI / breakdown
```

## URL 參數

| 參數 | 說明 | 預設 |
|------|------|------|
| `sub_view` | `monthly` \| `daily` | `monthly` |
| `day` | `YYYY-MM-DD`（`sub_view=daily` 時） | 月份第一天 |

## 實作步驟

- [ ] **步驟 1：state 與 URL 擴充**
  - 在 `monthlyReportRenderer` 新增 `currentSubView`（從 URL `sub_view` 初始化，預設 `"monthly"`）
  - 新增 `currentDay`（從 URL `day` 初始化，預設 `null`）
  - `updateUrl()` 加入 `sub_view`；若 `sub_view=daily` 且 `currentDay` 有值，加入 `day`

- [ ] **步驟 2：`buildPeriodSelector` — 加入子 tab 列**
  - `period_type=monthly` 才在月份 tabs 下方加 `<div class="sub-view-tabs">` 含「月報」「日報」兩顆按鈕
  - 切換月份時：`currentSubView = "monthly"`，`currentDay = null`，清空子 tab 選取狀態

- [ ] **步驟 3：新增 `buildSubViewTabs(container)` 函式**
  - 產生月報 / 日報兩顆按鈕，依 `currentSubView` 設 `is-active`
  - 點擊時：更新 `currentSubView` → `updateUrl()` → `renderForSubView(cachedData)`
  - `cachedData` 在 `loadAndRender` 拿到 data 後存到閉包變數 `lastData`

- [ ] **步驟 4：新增 `renderForSubView(data)` 函式**
  - `currentSubView === "monthly"` → `renderPeriodReport(d, cat, "monthly", period, data, runtime)`
  - `currentSubView === "daily"` → `renderDailyView(d, data, cat, runtime)`

- [ ] **步驟 5：新增 `renderDailyView(container, data, cat, runtime)` 函式**
  - 從 `data.summary` 取日期列表，升序排列，產生日期按鈕注入 container
  - 自動選取：`currentDay ?? 月份第一天`
  - 點擊日期按鈕：更新 `currentDay` → `updateUrl()` → lazy fetch breakdown → 渲染
  - 再點同一天 → 收合（`currentDay = null`，URL 移除 `day`）

- [ ] **步驟 6：`loadAndRender` 整合**
  - fetch data 後存到 `lastData`
  - 呼叫 `renderForSubView(lastData)` 取代原本直接呼叫 `renderPeriodReport`
  - 季報 / 年報：直接呼叫 `renderPeriodReport`，不走 sub-view 邏輯

- [ ] **步驟 7：清理舊邏輯**
  - 移除 `buildDaySelectorButtons`（由 `renderDailyView` 取代）
  - `renderPeriodReport` 移除 `#period-daily-drilldown` 佔位
  - 移除所有 `#period-breakdown-container` 顯隱的 `style.display` 操作
  - 移除 `.daily-day-selector` div 注入邏輯
  - `renderDailyDrilldown` 函式已是 dead code，可一併刪除

- [ ] **步驟 8：CSS — `.sub-view-tabs` 樣式**
  - 參考 `.monthly-nav-months` 風格，加分隔線與間距
  - `.sub-view-tab`（一般）/ `.sub-view-tab.is-active`（active 狀態）

- [ ] **步驟 9：本機測試**
  - 月報/日報 tab 切換，URL 正確更新
  - 重新整理後依 URL 恢復 sub_view 與 day
  - 切換月份後 sub_view 重置為月報、day 清空
  - 季報 / 年報不顯示子 tab
  - 切換類別後狀態正確重置

- [ ] **步驟 10：部署**
  - `bash deploy.sh --version v1-3 --skip-build`
