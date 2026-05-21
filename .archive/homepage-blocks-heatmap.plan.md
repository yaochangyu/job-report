# homepage-blocks-heatmap 實作計畫

目標：在 `v1-3` 的 `homepage-blocks` 視角中，加入類似 `v1/click-heatmap` 的頁面疊圖效果，能以日期切換方式顯示每一天各按鈕附近的點擊次數，且支援相同模式延伸到其他已配置座標的頁面。

## 實作步驟

- [x] **步驟 1 — 盤點並整理可重用的熱點配置與頁面資產**
  - **Why**：目前 `homepage-blocks` 只有 feature 統計資料，真正決定數字要疊在哪裡的是 `click_heatmap_config.json` 與對應頁面截圖資產。先整理哪些頁面已有 `page_path`、`feature_id`、座標、viewport 與 screenshot，才能確認這次功能的最小可用範圍，不然前端做完也無法正確顯示。
  - **預期產出**：明確的頁面清單、每頁對應 screenshot 路徑規則、哪些 feature 有座標、哪些 feature 目前無法定位。
  - **盤點結果**：
    - `click_heatmap_config.json` 共 2 頁：首頁 (`/`, 1440x900 full-page) 有 13 個 feature_id 座標；搜尋結果頁 (`/search/job`) 有 0 個 feature_id 座標
    - `homepage-blocks` 共定義 51 個 feature_id
    - 兩者**交集（可定位）**：12 個（`T-job-category`, `T-job-location`, `search-general-submit`, `identify-*` 6 個, `identify-personal-tab-*` 3 個）
    - 只在 config 中：`search-ai`（未被 BLOCKS 定義）
    - **無座標（無法定位）**：39 個 homepage-blocks feature_id
    - **截圖資產：目前沒有**，需要在 build 流程中拍攝或複製首頁截圖
    - 最小可用範圍：首頁 `/`，12 個可定位 feature_id

- [x] **步驟 2 — 擴充 `homepage-blocks` 查詢輸出為「依日期、依頁面、依 feature」的熱點資料**
  - **Why**：現在 `homepageBlocksPlan()` 主要提供 KPI、趨勢與 feature 明細，但熱點圖需要的是可直接拿來疊圖的資料結構：至少要能知道某一天、某個頁面、某個 feature 的 click 次數。先把查詢結果整理成前端好消費的 shape，後面的 renderer 才不會混雜過多資料轉換邏輯。
  - **預期產出**：新增 heatmap 專用 query result，內容至少包含 `date / page_path / feature_id / feature_name / count`，並保留多日查詢可切換單日顯示。

- [x] **步驟 3 — 在前端加入可重用的熱點疊圖元件**
  - **Why**：這次不是只做首頁單一案例，而是要支援「同樣模式」擴到其他頁面，所以不應把 DOM 與樣式寫死在 `homepage-blocks`。應抽成可重用的 overlay renderer：輸入 screenshot、viewport、element 座標、每日 count，就能產生 badge、tooltip、未定位清單與空資料提示。
  - **預期產出**：可被 `homepage-blocks` 使用的共用熱點渲染流程，包含 badge 定位、數字格式、hover 資訊與缺漏資料提示。

- [x] **步驟 4 — 把熱點圖整合進 `homepage-blocks` 視角 UI**
  - **Why**：功能真正交付點在 `?view=homepage-blocks`，所以需要把熱點圖放進既有 dashboard flow，包含單日直接顯示、多日可切換日期、與現有圖表/表格共存時的版面安排。這一步會決定使用者實際操作是否順手，也會處理 screenshot 無對應頁面時的顯示策略。
  - **預期產出**：`homepage-blocks` 視角新增熱點圖區塊，能依日期顯示各頁面疊圖，並與既有查詢條件同步運作。

- [x] **步驟 5 — 補齊測試、build 與文件同步**
  - **Why**：這次牽涉 query 定義、renderer、靜態資產與可能的 config 依賴，若沒有最少必要的測試與文件，之後很容易在改版時壞掉卻沒發現。這一步要把資料格式、資產位置與使用限制補進文件，並確認既有 build 流程仍可正常產出。
  - **預期產出**：對應測試與文件更新，確保後續維護者知道 heatmap 資料與 screenshot/config 的依賴關係。

## 注意事項

- 每次只執行一個步驟，完成後回到這份計畫打勾，待你確認後再進下一步。
- 若某個頁面缺少 screenshot 或座標，會先列為限制，不會靜默忽略。
- 若實作途中遇到失敗方法，需記錄在下方，避免重複踩雷。

## 失敗紀錄

- 目前尚無。
