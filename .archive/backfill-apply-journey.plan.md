# backfill-apply-journey 計畫書

## 目標

`fix-apply-journey-page-path` 修正了 apply 事件的頁面路徑還原邏輯，
目前只重跑了 2026-05-01 做驗證，其餘 44 天的 T2 資料仍是舊版。
本計畫將全部 45 天補跑一次，讓歷史資料與修正後邏輯一致。

## 實作步驟

- [x] **步驟 1 — 重跑所有日期 T2**
  - 執行指令：`python builders/build_apply_journey_t2.py --from 2026-04-05 --to 2026-05-19`
  - 覆蓋現有 45 天的 `path_ranking`、`step_distribution`、`entry_page`、`daily_summary`
  - 預估耗時：~7 分鐘

- [x] **步驟 2 — 驗證**
  - 抽查 2–3 個日期，確認 `path_ranking` 無純 `"apply"` 路徑
  - 確認 top 路徑為 `job-page > apply`、`search-job-page > apply` 等合理路徑

- [x] **步驟 3 — 部署**
  - 執行 `bash deploy.sh --from 2026-04-05 --to 2026-05-19 --version v1-3`
