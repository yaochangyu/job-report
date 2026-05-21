# monthly-daily-drilldown 計畫書

## 目標

在月報視圖（`period_type=monthly`）的趨勢圖下方，新增「各日明細」區塊，
列出當月每一天的 KPI，點擊任一日期可展開當日的 breakdown 明細。

## 背景

- 月報的 `period_summary.parquet` 每一列就是一天（`period='2026-05-01'`）
- 因此無需重新 fetch daily KPI，直接從 `summary` rows 取得即可
- 只有展開時才需要額外 fetch `report/{category}/date=YYYY-MM-DD/{breakdown}` 檔案
- 僅對 `period_type=monthly` 啟用（季/年報列數太多，不適合逐日展開）

## 資料流

```
period_summary.parquet (已載入)
  └─ period='2026-05-01', explore_jobs_click=1436, ...
  └─ period='2026-05-02', ...
  ...

展開某日時，lazy fetch:
  report/{category}/date=2026-05-01/feature_counts.parquet
  report/{category}/date=2026-05-01/source.parquet  （視 catCfg.breakdowns）
```

## 實作步驟

- [x] **步驟 1：`dashboard-renderers.js` — 新增 `renderDailyDrilldown()`**
  - 在 `renderPeriodReport()` 結尾（當 `periodType === 'monthly'` 時）呼叫
  - 接收 `summary` rows、`category`、`runtime`
  - 產生各日列表 HTML：日期 | mainMetric 值 | 展開箭頭
  - 綁定點擊事件：展開/收合，初次展開時 lazy fetch breakdown 並渲染

- [x] **步驟 2：`dashboard-renderers.js` — 新增 `fetchDailyBreakdown()`**
  - 從 `report/{category}/date=YYYY-MM-DD/` fetch `catCfg.breakdowns` 各檔
  - 與 `fetchPeriodReport` 類似，但路徑改用 `date=` 前綴、alias 前綴 `dd_`
  - 回傳 `{ breakdowns }`

- [x] **步驟 3：`app.css` — 新增各日展開的 CSS**
  - `.daily-drilldown-list`：列表容器
  - `.daily-drilldown-row`：每日列，含日期、KPI、箭頭
  - `.daily-drilldown-row.is-open`：展開狀態
  - `.daily-drilldown-detail`：展開後的 breakdown 區塊（預設 hidden）

- [x] **步驟 4：本機測試**
  - 啟動 local server，開啟月報功能互動 2026-05，確認每日列表顯示
  - 點擊一日確認 breakdown 正確載入（無 console error）
  - 點擊無 breakdown 的類別（如裝置平台），確認只顯示 KPI 不報錯

- [x] **步驟 5：部署**
  - `bash deploy.sh --version v1-3 --skip-build`
