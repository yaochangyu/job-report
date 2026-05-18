# fix-event-type-filter 計畫書

## 背景
`event_type` 只有 `view` 與 `click` 兩種值。  
以下 3 支 T2 build 腳本未明確過濾 `event_type`，導致 view + click 混合計算，數字失真。

| 腳本 | 應過濾為 | 原因 |
|------|---------|------|
| `build_feature_engagement_t2.py` | `click` | 功能互動（探索職缺／企業／身分）以點擊行為為主 |
| `build_search_behavior_t2.py` | `click` | 搜尋行為是用戶主動操作，應計點擊次數 |
| `build_page_navigation_t2.py` | `view` | 頁面導航反映瀏覽路徑，應計頁面瀏覽次數 |

---

## 步驟

- [x] **步驟 1 — `build_feature_engagement_t2.py`**  
  在 `columns` 加入 `"event_type"`，並在 DataFrame 過濾條件加上 `df["event_type"].eq("click")`，排除 view 事件。

- [x] **步驟 2 — `build_search_behavior_t2.py`**  
  在 `columns` 加入 `"event_type"`，並在 DataFrame 過濾條件加上 `df["event_type"].eq("click")`，排除 view 事件。

- [x] **步驟 3 — `build_page_navigation_t2.py`**  
  在 `columns` 加入 `"event_type"`，並在 DataFrame 過濾條件加上 `df["event_type"].eq("view")`，排除 click 事件。

- [x] **步驟 4 — 重新 build T2 並部署**  
  執行 `deploy.sh` 重新產出 T2 parquet 並佈署，確認各報表數字正確。
