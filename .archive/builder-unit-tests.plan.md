# builder-unit-tests 實作計畫

## 目標

為所有 10 個 T2 builder 建立單元測試，使用**已知的合成 fixture 資料**取代真實 T1 Parquet，
驗證每個 builder 輸出的 schema、數值正確性，確保資料變動或重構時能立即發現錯誤。

## 測試策略

- **fixture 資料**：合成小量 T1 rows（含已知計數），寫入 `tmp_path` 臨時目錄
- **路徑注入**：用 `monkeypatch` 將 `T1_RAW_DIR`、`T2_REPORT_DIR` 指向臨時目錄，不碰真實 dataset
- **驗證項目**：輸出檔案存在、欄位名稱與型別、key 欄位無 null、數值與 fixture 計算結果一致
- **工具**：`pytest`（需加入 pyproject.toml）

## 每個測試的驗證模式

```
fixture T1 → monkeypatch 路徑 → 呼叫 build_xxx_t2() → 讀取輸出 parquet → 比對 schema + 數值
```

## 涉及檔案

| 檔案 | 說明 |
|------|------|
| `pyproject.toml` | 加入 pytest 依賴 |
| `tests/unit/conftest.py` | 共用 pytest fixtures（路徑 monkeypatch、fixture parquet 產生器） |
| `tests/unit/fixture_data.py` | 各 builder 所需的合成 T1 rows 常數與預期輸出值 |
| `tests/unit/test_build_traffic_overview.py` | traffic-overview builder 測試 |
| `tests/unit/test_build_search_behavior.py` | search-behavior builder 測試 |
| `tests/unit/test_build_apply_conversion.py` | apply-conversion builder 測試 |
| `tests/unit/test_build_apply_journey.py` | apply-journey builder 測試 |
| `tests/unit/test_build_feature_engagement.py` | feature-engagement builder 測試 |
| `tests/unit/test_build_device_platform.py` | device-platform builder 測試 |
| `tests/unit/test_build_page_ranking.py` | page-ranking builder 測試 |
| `tests/unit/test_build_page_navigation.py` | page-navigation builder 測試 |
| `tests/unit/test_build_click_heatmap.py` | click-heatmap builder 測試 |
| `tests/unit/test_build_homepage_blocks.py` | homepage-blocks builder 測試 |

---

## 實作步驟

- [x] **步驟 1 — 加入 pytest 依賴並確認可執行**
  - `pyproject.toml` 的 `[project.optional-dependencies]` 加入 `test = ["pytest>=8"]`。
  - 執行 `uv run pytest --collect-only` 確認 pytest 可運作（尚無測試也 OK）。

- [x] **步驟 2 — 建立 `tests/unit/conftest.py`：共用 fixtures**
  - `t1_dir(tmp_path)` fixture：在 `tmp_path/raw/date=YYYY-MM-DD/` 寫入 fixture T1 events.parquet，回傳 tmp_path。
  - `t2_dir(tmp_path)` fixture：建立 `tmp_path/report/` 目錄，回傳 tmp_path。
  - `patch_pipeline_dirs(monkeypatch, t1_dir, t2_dir)` fixture：monkeypatch `common.data_pipeline.T1_RAW_DIR` 與 `T2_REPORT_DIR` 指向臨時目錄。
  - 提供 `make_t1_events(rows: list[dict]) -> pd.DataFrame` helper，補齊所有 T1 欄位的預設值（null-safe）。

- [x] **步驟 3 — 建立 `tests/unit/fixture_data.py`：合成資料常數**
  - 定義各 builder 所需的最小 T1 rows，例如：
    - `HOMEPAGE_BLOCKS_ROWS`：包含 `explore-jobs-organic`、`identify-student` 等 feature_id，已知 click/view 各幾筆
    - `TRAFFIC_ROWS`：包含已知數量的 view/click/apply event
    - `SEARCH_ROWS`：包含 AI 搜尋與一般搜尋 feature_id
    - …（每個 builder 一份）
  - 同一份檔案定義對應的 `EXPECTED_*` 數值（從 rows 直接算出，不依賴 builder 邏輯）。

- [x] **步驟 4 — 實作 `test_build_traffic_overview.py`**
  - 驗證 `daily_summary.parquet` 欄位：`['date','total','views','clicks','applies','sessions']`
  - 驗證 `views`、`clicks`、`applies` 數值與 fixture 計算一致
  - 驗證 `device_type.parquet`、`os.parquet`、`browser.parquet` 均存在且 row count > 0

- [x] **步驟 5 — 實作 `test_build_search_behavior.py`**
  - 驗證 `daily_summary.parquet` 欄位與數值（general_click/view、ai_click/view 等）
  - 驗證 `feature_counts.parquet` 欄位與 count 加總

- [x] **步驟 6 — 實作 `test_build_apply_conversion.py`**
  - 驗證 `daily_summary.parquet`（applies、job_views）
  - 驗證 `source.parquet`、`funnel.parquet` 存在且 schema 正確

- [x] **步驟 7 — 實作 `test_build_apply_journey.py`**
  - 驗證 `daily_summary.parquet`（applies、apply_sessions、total_steps）
  - 驗證 `path_ranking.parquet`、`entry_page.parquet`、`step_distribution.parquet` 存在且 schema 正確

- [x] **步驟 8 — 實作 `test_build_feature_engagement.py`**
  - 驗證 `daily_summary.parquet` 欄位：explore_jobs_click/view、explore_corp_click/view、identity_click/view、news_click/view
  - 驗證各欄位數值與 fixture 一致

- [x] **步驟 9 — 實作 `test_build_device_platform.py`**
  - 驗證 `daily_summary.parquet`（mobile、desktop）
  - 驗證 `os.parquet`、`browser.parquet`、`device_behavior.parquet`、`os_behavior.parquet` 存在

- [x] **步驟 10 — 實作 `test_build_page_ranking.py`**
  - 驗證 `daily_summary.parquet`（total_events、total_features）
  - 驗證 `features.parquet` 的 featureId 與 total 數值
  - 驗證 `categories.parquet` 存在

- [x] **步驟 11 — 實作 `test_build_page_navigation.py`**
  - 驗證 `daily_summary.parquet`（nav_click、nav_view、entry_click、entry_view、tracked_pages）
  - 驗證 `nav_pairs.parquet`（from_page、to_page、count）
  - 驗證 `entry_pages.parquet`、`page_sources.parquet`、`page_destinations.parquet` 存在且 schema 正確

- [x] **步驟 12 — 實作 `test_build_click_heatmap.py`**
  - 驗證 `daily_summary.parquet`（total_clicks、feature_count、top_feature_id、top_count）
  - 驗證 `click_counts.parquet`（feature_id、count）數值與 fixture 一致

- [x] **步驟 13 — 實作 `test_build_homepage_blocks.py`**
  - 驗證 `daily_summary.parquet`（total_clicks、total_views、feature_count）
  - 驗證 `feature_counts.parquet`（event_type × feature_id × count）與 fixture 一致
  - 驗證不在 `ALL_FEATURE_IDS` 的 feature 不出現在輸出中

- [x] **步驟 14 — 全部跑過並確認 green**
  - 執行 `uv run pytest tests/unit/ -v`，所有測試通過。
  - 確認 coverage 涵蓋所有 builder 的核心邏輯路徑。
