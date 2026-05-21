# period-selector-day-nav 計畫書

## 目標

月報（`period_type=monthly`）的期間選擇區塊，改成兩層導覽：
- 第一層：月份 tabs（現有）
- 第二層：點選月份後，在月份 tabs 下方展開日期按鈕列
- 點日期 → 在月報內容下方顯示當日明細
- 切換月份 → 日期按鈕更新，清除已選日期

## 現況

```
[period-selector]         ← 只有月份 tabs
  [monthly-day-detail]    ← 月報內容 + 趨勢圖 + breakdown
    [period-daily-drilldown]  ← 各日明細（日期按鈕在內容區底部）
```

## 目標結構

```
[period-selector]
  [月份 tabs row]        ← 現有
  [daily-day-selector]   ← 新增，月份選定後展開日期按鈕

[monthly-day-detail]     ← 月報 KPI + 圖表 + breakdown
  [period-daily-drilldown]  ← 點日後的當日明細（保留）
```

## 實作步驟

- [ ] **步驟 1：`buildPeriodSelector` — 加入 `.daily-day-selector` 佔位**
  - 月報的 `selectorEl` HTML 改為：`<nav class="monthly-nav-months">…</nav><div class="daily-day-selector"></div>`
  - 切換月份 / 切換 period type 時，清空 `.daily-day-selector`

- [ ] **步驟 2：`loadAndRender` — 月報載入後呼叫 `buildDaySelectorButtons`**
  - `fetchPeriodReport` 回傳 `data.summary`（含每日 period 列）
  - 月報才呼叫：`buildDaySelectorButtons(summary, catCfg, category, runtime, daySelectorEl)`
  - 季報 / 年報 不呼叫（清空 `.daily-day-selector`）

- [ ] **步驟 3：新增 `buildDaySelectorButtons(summary, catCfg, category, runtime, container)`**
  - 從 `summary` 取出所有日期（`r.period`），升序排列
  - 產生 `[1日]…[N日]` 按鈕，注入 `container`（`.daily-day-selector`）
  - 點擊按鈕：
    - 切換 `is-active`（再點同一天 → 收合）
    - `loaded=false` 時 fetch `fetchDailyBreakdown` 並渲染到 `#period-daily-drilldown`
    - `loaded=true` 時直接顯示/隱藏（已快取）

- [ ] **步驟 4：`renderPeriodReport` — 移除舊的 `renderDailyDrilldown` 呼叫**
  - 移除 `<div id="period-daily-drilldown">` 插入邏輯中的 `renderDailyDrilldown` 呼叫
  - 保留 `<div id="period-daily-drilldown"></div>` HTML 佔位（日明細仍渲染於此）
  - 整理：`renderDailyDrilldown` 函式可刪除

- [ ] **步驟 5：`app.css` — `.daily-day-selector` 樣式**
  - 在月份 tabs 下加分隔線或間距
  - 日期按鈕 wrap 排列（`.daily-date-btn` 已有，只補容器）

- [x] **步驟 6：本機測試**
  - homepage-blocks 月報：點月份 → 日期列展開；點日 → 明細顯示
  - search-behavior 月報：同上，確認 breakdown lazy fetch 正常
  - 季報 / 年報：`.daily-day-selector` 維持空白
  - 切換類別：日期列和明細正確重置

- [x] **步驟 7：部署**
  - `bash deploy.sh --version v1-3 --skip-build`
