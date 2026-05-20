# nav-pairs-limit 計畫書

## 目標

`nav_pairs.parquet` 目前無截斷，每天約 1.8–3.3 MB，是 page-navigation view 最重的檔案。
加上 limit=30 per event_type，可顯著縮小檔案，降低瀏覽器下載與 DuckDB-WASM 處理壓力。

## 注意事項

方案 A（全局 top 30 per event_type），選擇此方案表示：
- 前端使用 `pagePath` 篩選時，`transition_ranking` 可能為空（非 top-30 的頁面不在檔案裡）
- `page_sources` / `page_destinations` 已各自含 per-page top-5，仍可顯示頁面來源/目標

## 實作步驟

- [x] **步驟 1 — 修改 builder**
  - 檔案：`builders/build_page_navigation_t2.py`
  - 加常數 `NAV_PAIRS_LIMIT = 30`
  - `nav_pairs` 寫入 parquet 前，加上 rank（per event_type cumcount）並過濾 `rank <= NAV_PAIRS_LIMIT`
  - `pair_counts` 已按 `[event_type, count DESC, from, to]` 排序，cumcount 即為正確排名

- [x] **步驟 2 — 重跑所有日期 T2**
  - 執行指令：`python builders/build_page_navigation_t2.py --from 2026-04-05 --to 2026-05-19`
  - 共 45 天，覆蓋現有 `nav_pairs.parquet`

- [x] **步驟 3 — 驗證**
  - 抽查 2–3 個日期，確認每個 event_type 不超過 30 筆
  - 比較修改前後檔案大小（預期從 ~1.9 MB → 幾 KB）
