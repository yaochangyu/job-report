# Project Cleanup 重構計畫

> **目標**：盤點目前專案中的 legacy 腳本、重複流程、暫存產物與可疑垃圾檔，先確認哪些能刪、哪些該保留，再分階段安全清理。

---

## 目前盤點結果

- 專案主流程已切到 `extract_raw_events.py` + `run_*_pipeline.py` + `run_all.py`。
- 仍存在一批 **legacy 腳本**：
  - `extract_all.py`
  - `build_frontend_bundle.py`
  - `traffic_overview_report.py`
  - `search_behavior_report.py`
  - `apply_conversion_report.py`
  - `feature_engagement_report.py`
  - `device_platform_report.py`
  - `page_ranking_report.py`
  - `page_navigation_report.py`
  - `click_heatmap_report.py`
- 但其中多數 `*_report.py` 目前仍提供：
  - `generate_html()`
  - 常數定義
  - 部分畫面邏輯
  所以**不能直接當垃圾刪掉**。
- 目前可直接辨識的本機產物：
  - `__pycache__/`
  - `common/__pycache__/`
  - `store.db`
- 計畫檔有兩種封存位置：
  - `.archive/`
  - `archive/`
  這表示**封存規則不一致**，需要整理。
- 已確認下列檔案目前沒有被主流程或其他 Python 入口引用：
  - `extract_all.py`
  - `build_frontend_bundle.py`
  - `frontend/`
- `click_heatmap_discover.py`、`category_tab_report.py` 與各 `*_report.py` 仍有保留價值，不納入本次刪除。

### 分類結果

#### 可直接刪除的暫存物

- `__pycache__/`
- `common/__pycache__/`
- 其他 `.pyc`

#### 應封存的已完成計畫

- `grafana-dashboard.plan.md`
- `archive/page-click-analysis.plan.md`

#### 已確認可移除的未使用腳本 / 資產

- `extract_all.py`
- `build_frontend_bundle.py`
- `frontend/`

---

## 實作步驟

- [x] **Step 1 — 建立垃圾檔 / legacy 檔案分類表**
  - 把目前檔案分成：
    - 可直接刪除的暫存物
    - 應封存的舊計畫檔
    - 仍被新流程引用的 legacy 檔
    - 真正可移除的未使用腳本
  - **為什麼需要這一步**：目前很多檔名看起來像舊版，但實際上還有被新流程引用；若不先分類，很容易誤刪。

- [x] **Step 2 — 清理可直接移除的本機產物**
  - 目標優先包含：
    - `__pycache__/`
    - `common/__pycache__/`
    - 其他 `.pyc`
  - **為什麼需要這一步**：這些檔案屬於執行暫存，不應干擾專案盤點與版控狀態。

- [x] **Step 3 — 整理計畫檔與封存目錄規則**
  - 檢查 `archive/` 與 `.archive/` 的用途是否重複。
  - 若確認可統一，將計畫檔封存位置收斂成單一路徑。
  - **為什麼需要這一步**：現在封存規則不一致，後續再做計畫管理會持續混亂。

- [x] **Step 4 — 盤點 legacy helper 是否仍有引用**
  - 針對下列檔案確認引用關係：
    - `build_frontend_bundle.py`
    - `extract_all.py`
    - 各 `*_report.py`
    - `click_heatmap_discover.py`
  - **為什麼需要這一步**：有些腳本雖然不再是主入口，但仍可能承擔 HTML 產生器或設定探索功能，不能直接刪。

- [x] **Step 5 — 把真正未使用的腳本標記為可刪除名單**
  - 只針對已確認「無引用、無部署用途、無人工操作需求」的檔案列入。
  - **為什麼需要這一步**：清理應以證據為基礎，不該靠檔名猜測。

- [x] **Step 6 — 實際移除垃圾檔與未使用檔案**
  - 依前面盤點結果，分批刪除並同步更新 `tree.md`。
  - **為什麼需要這一步**：把分析結果真正落地，讓專案結構變乾淨。

- [x] **Step 7 — build 驗證清理後仍可正常運作**
  - 重新跑主流程，確認 `run_all.py` / `deploy.sh` 不受影響。
  - **為什麼需要這一步**：清理類重構最容易刪到隱性依賴，必須做整體驗證。

### 驗證結果

- 已執行：`uv run python run_all.py --from 2026-04-13 --to 2026-04-13`
- 結果：8/8 報表成功產出，`output/index.html` 正常生成。

---

## 目前優先懷疑項目

1. `click_heatmap_discover.py` 是否仍要長期保留為人工維護工具
2. `category_tab_report.py` 是否要納入正式 pipeline，或維持獨立腳本

---

## 暫不建議直接刪除

1. 各 `*_report.py`：目前仍承擔 HTML 產生器與常數來源
2. `click_heatmap_discover.py`：仍是維護 `click_heatmap_config.json` 的輔助工具
3. `category_tab_report.py`：已改讀 T1 raw，但仍屬可獨立執行的額外報表
