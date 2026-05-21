# 專案資料夾結構

```
job-report/
├── .archive/
│   ├── apply-journey.plan.md          # ✅ 已完成：應徵路徑分析實作計畫
│   ├── grafana-dashboard.plan.md      # ✅ 已完成：原始 Dashboard 規劃總計畫
│   ├── dashboard-fix-plan.md          # ✅ 已完成：dashboard 資料吻合性修正計畫
│   ├── page-click-analysis.plan.md    # ✅ 已完成：Dashboard 8 實作計畫
│   ├── project-cleanup.plan.md        # ✅ 已完成：專案垃圾檔 / legacy 清理計畫
│   ├── report-data-pipeline.plan.md   # ✅ 已完成：三層資料管線重構計畫
│   ├── v1-2-report-shell-sync.plan.md  # ✅ 已完成：v1-2 報表頁接回 v1-1 導覽殼與查詢條件的實作計畫
│   ├── v1-2-ui-sync.plan.md           # ✅ 已完成：v1-2 UI 對齊 v1-1 的實作計畫
│   ├── cli-redesign.plan.md           # ✅ 已完成：run_all.py CLI 重新設計計畫
│   ├── query-homepage-blocks.plan.md  # ✅ 已完成：首頁區塊點擊查詢腳本計畫
│   ├── nav-pairs-limit.plan.md        # ✅ 已完成：nav_pairs top-30 截斷計畫
│   ├── remove-session-ids.plan.md     # ✅ 已完成：移除 session_ids.parquet 計畫
│   ├── fix-apply-journey-page-path.plan.md  # ✅ 已完成：apply 事件補入當前頁面修正計畫
│   ├── backfill-apply-journey.plan.md       # ✅ 已完成：apply-journey 45 天歷史資料補跑計畫
│   ├── monthly-report-day-nav.plan.md       # ✅ 已完成：月報表日期導覽與側邊類別欄實作計畫
│   ├── period-summary-report.plan.md        # ✅ 已完成：月報/季報/年報聚合 + period-type tabs 實作計畫
│   ├── period-report-rename.plan.md         # ✅ 已完成：月報表改名為週期報表與 URL 調整計畫
│   ├── sidebar-dynamic-height.plan.md       # ✅ 已完成：分析角度導覽動態高度修正計畫
│   ├── sidebar-touchpad-scroll.plan.md      # ✅ 已完成：分析角度導覽觸控板捲動修正計畫
│   ├── sidebar-scroll-container.plan.md     # ✅ 已完成：分析角度導覽固定框捲動修正計畫
│   ├── builder-unit-tests.plan.md           # ✅ 已完成：10 個 T2 builder 單元測試實作計畫
│   ├── apply-demographics.plan.md           # ✅ 已完成：應徵者性別／年齡分析實作計畫
│   └── page-navigation-lazy-load.plan.md   # ✅ 已完成：page-navigation lazy load / conditional fetch 實作計畫
├── builders/                          # 從 T1 產出 T2 parquet 的建置腳本
│   ├── build_apply_conversion_t2.py
│   ├── build_apply_job_category_t2.py # 應徵職類／產業 TOP N 分析
│   ├── build_apply_demographics_t2.py # 應徵者性別／年齡層分析
│   ├── build_apply_demographics_category_t2.py # 性別／年齡層 × 職類／產業交叉分析
│   ├── build_apply_journey_t2.py      # 應徵路徑分析
│   ├── build_click_heatmap_t2.py
│   ├── build_device_platform_t2.py
│   ├── build_feature_engagement_t2.py
│   ├── build_homepage_blocks_t2.py
│   ├── build_period_summary.py             # 月報/季報/年報聚合 parquet builder
│   ├── build_page_navigation_t2.py
│   ├── build_page_ranking_t2.py
│   ├── build_search_behavior_t2.py
│   └── build_traffic_overview_t2.py
├── common/
│   ├── __init__.py
│   ├── data_pipeline.py               # T0/T1/T2/T3 資料管線契約與路徑定義
│   ├── es_client.py                   # Grafana _msearch 共用封裝
│   ├── frontend_shell.py             # GitHub Pages v1-2 共用前端殼 HTML 模板
│   ├── job_metadata.py                # 從 search-jobs-v1-* 批次查詢職類/產業 metadata（供 T1 補強用）
│   ├── resume_metadata.py             # 從 core6 Solr 批次查詢應徵者 sex_i/birth_dt（供 T1 補強用）
│   ├── raw_events.py                  # T0/T1 事件欄位契約（RAW_EVENT_SCHEMA + T1_ENRICH_EVENT_SCHEMA）
│   ├── t1_reader.py                   # 讀取 T1 enriched parquet 的共用工具
│   ├── html_template.py               # HTML header/footer/style 共用模板
│   └── chart_helpers.py              # Chart.js 輔助函式
├── exporters/                         # 資料匯出腳本
├── frontend/                          # 前端靜態資源（部署時複製到 output/）
│   ├── app.js                         # 前端殼啟動邏輯
│   ├── app.css                        # 前端殼樣式
│   ├── dashboard-renderers.js         # 各 dashboard 前端 renderer
│   ├── query-definitions.js           # DuckDB 前端查詢定義
│   └── site-manifest.json             # 前端站點資產與資料集 manifest
├── output/
│   ├── index.html                     # 導覽頁面（由 run_all.py 產生）
│   └── report/
│       ├── traffic-overview/index.html    # Dashboard 1 報告產出
│       ├── search-behavior/index.html     # Dashboard 2 報告產出
│       ├── apply-conversion/index.html    # Dashboard 3 報告產出
│       ├── apply-journey/index.html       # Dashboard 4 報告產出
│       ├── feature-engagement/index.html  # Dashboard 5 報告產出
│       ├── device-platform/index.html     # Dashboard 6 報告產出
│       ├── page-ranking/index.html        # Dashboard 7 報告產出
│       ├── page-navigation/index.html     # Dashboard 8 報告產出
│       ├── click-heatmap/index.html       # Dashboard 9 報告產出
│       ├── homepage-blocks/index.html     # Dashboard 10 報告產出
│       ├── apply-job-category/index.html  # Dashboard 11 應徵職類／產業報告產出
│       ├── apply-demographics/index.html  # Dashboard 12 應徵者性別／年齡報告產出
│       ├── apply-demographics-category/index.html  # Dashboard 13 性別／年齡 × 職類／產業交叉分析
│       ├── period-report/index.html       # Dashboard 13 週期報表頁面
│       └── monthly-report/index.html      # 舊網址相容轉址頁
├── tests/
│   ├── unit/                           # T2 builder 單元測試
│   │   ├── conftest.py                 # 共用 fixtures（路徑 monkeypatch、T1 寫入工具）
│   │   ├── fixture_data.py             # 各 builder 合成 T1 rows 與預期輸出值
│   │   ├── test_build_apply_conversion.py
│   │   ├── test_build_apply_demographics.py
│   │   ├── test_build_apply_demographics_category.py
│   │   ├── test_build_apply_job_category.py
│   │   ├── test_build_apply_journey.py
│   │   ├── test_build_click_heatmap.py
│   │   ├── test_build_device_platform.py
│   │   ├── test_build_feature_engagement.py
│   │   ├── test_build_homepage_blocks.py
│   │   ├── test_build_page_navigation.py
│   │   ├── test_build_page_ranking.py
│   │   ├── test_build_search_behavior.py
│   │   └── test_build_traffic_overview.py
│   └── validation/
│       └── validate_dashboard_data.py  # 比對 JS 實際查詢結果與 T2 parquet 聚合結果
├── tools/                             # 工具 / 一次性查詢腳本
│   ├── __init__.py
│   ├── click_heatmap_discover.py      # 自動探索頁面可點擊元素
│   ├── enrich_t1_events.py            # 讀 T0，批次補強 Solr/Matching ES，寫 T1（dataset/t1-enrich/）
│   ├── extract_raw_events.py          # 從 ES 抽取純原始事件，寫 T0（dataset/t0-raw/）
│   └── query_homepage_blocks.py       # 從 ES 查詢首頁四大區塊每日點擊數
├── page-navigation-shrink.plan.md     # page-navigation parquet 縮減實作計畫
├── app.css                            # v1-2 / GitHub Pages 共用前端殼樣式
├── app.js                             # v1-2 / GitHub Pages 共用前端殼啟動邏輯
├── click_heatmap_config.json          # 頁面 URL + featureId → 元素位置 對應表
├── dashboard-renderers.js             # 各 dashboard 視角的前端 renderer
├── deploy.sh                          # 一鍵產生報告並部署到 GitHub Pages
├── query-definitions.js               # DuckDB 前端查詢定義
├── run_all.py                         # 一鍵執行所有報告 + 產生導覽頁
├── site-manifest.json                 # 前端站點資產與資料集 manifest
├── pyproject.toml                     # uv 專案設定
├── .python-version                    # Python 版本
└── tree.md                            # 本檔案
```
