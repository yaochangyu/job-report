# fix-event-type-split 計畫書

## 背景
前次修正將 3 支腳本過濾為單一 event_type，但正確做法應是 click / view **各自統計**，
讓 parquet 資料同時保留兩種計數，dashboard query 再依需求取用。

---

## 步驟

- [x] **步驟 1 — `build_feature_engagement_t2.py`**  
  移除 `event_type == "click"` 過濾。修改 `_count_by_value` 輔助函式，接受額外的 `group_by` 欄位（加入 `event_type`），讓各 parquet 輸出欄位變為 `event_type | name | count`。  
  影響檔案：`explore_jobs_features`, `explore_corp_features`, `identity_all`, `identity_main`, `news_features`。  
  `daily_summary` 拆為 `*_click` / `*_view` 各自加總欄位。

- [x] **步驟 2 — `build_search_behavior_t2.py`**  
  移除 `event_type == "click"` 過濾。`feature_counts` parquet 加入 `event_type` 欄位（groupby `["event_type", "feature_id"]`）。  
  `daily_summary` 拆為 `general_click`, `general_view`, `ai_click`, `ai_view`, `quick_click`, `quick_view`, `search_page_click`, `search_page_view`。

- [x] **步驟 3 — `build_page_navigation_t2.py`**  
  移除 `event_type == "view"` 過濾。`pair_counts` groupby 加入 `event_type`，讓 `nav_pairs`, `entry_pages`, `page_sources`, `page_destinations` 均帶有 `event_type` 欄位，view / click 各自成列。

- [ ] **步驟 4 — 重新 build T2 並部署**  
  執行 `deploy.sh --from 2026-05-01 --to 2026-05-17 --version v1-3`，確認各報表正常。
