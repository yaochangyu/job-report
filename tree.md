# 專案資料夾結構

```
job-report-1/
├── .archive/
│   └── v1-2-ui-sync.plan.md           # ✅ 已完成：v1-2 UI 對齊 v1-1 的實作計畫
├── common/
│   ├── __init__.py
│   ├── data_pipeline.py               # T1/T2/T3 資料管線契約與路徑定義
│   ├── es_client.py                    # Grafana _msearch 共用封裝
│   ├── raw_events.py                  # T1 raw 事件欄位契約與正規化工具
│   ├── t1_reader.py                   # 讀取 T1 raw parquet 的共用工具
│   ├── html_template.py                # HTML header/footer/style 共用模板
│   └── chart_helpers.py               # Chart.js 輔助函式
├── output/
│   ├── index.html                      # 導覽頁面（由 run_all.py 產生）
│   ├── traffic-overview/index.html     # Dashboard 1 報告產出
│   ├── search-behavior/index.html      # Dashboard 2 報告產出
│   ├── apply-conversion/index.html     # Dashboard 3 報告產出
│   ├── feature-engagement/index.html   # Dashboard 4 報告產出
│   ├── device-platform/index.html      # Dashboard 5 報告產出
│   ├── page-ranking/index.html         # Dashboard 6 報告產出
│   ├── page-navigation/index.html      # Dashboard 7 報告產出
│   └── click-heatmap/index.html        # Dashboard 8 報告產出
├── category_tab_report.py             # 既有報告（保留）
├── traffic_overview_report.py         # Dashboard 1：整體流量概覽
├── search_behavior_report.py          # Dashboard 2：搜尋行為分析
├── apply_conversion_report.py         # Dashboard 3：應徵轉換分析
├── feature_engagement_report.py       # Dashboard 4：功能互動分析
├── device_platform_report.py          # Dashboard 5：裝置與平台分析
├── page_ranking_report.py             # Dashboard 6：頁面流量排行
├── page_navigation_report.py          # Dashboard 7：頁面導航鏈路分析
├── click_heatmap_report.py            # Dashboard 8：頁面點擊熱點分析
├── click_heatmap_discover.py          # 輔助：自動探索頁面可點擊元素
├── click_heatmap_config.json          # 頁面 URL + featureId → 元素位置 對應表
├── build_apply_conversion_t2.py       # 從 T1 產出 apply-conversion 的 T2 parquet
├── build_device_platform_t2.py        # 從 T1 產出 device-platform 的 T2 parquet
├── build_frontend_bundle.py           # 將 v1-1 前端資產與 dataset 複製到 output/
├── build_page_navigation_t2.py        # 從 T1 產出 page-navigation 的 T2 parquet
├── build_page_ranking_t2.py           # 從 T1 產出 page-ranking 的 T2 parquet
├── build_search_behavior_t2.py        # 從 T1 產出 search-behavior 的 T2 parquet
├── build_traffic_overview_t2.py       # 從 T1 產出 traffic-overview 的 T2 parquet
├── deploy.sh                          # 一鍵產生報告並部署到 GitHub Pages
├── extract_raw_events.py              # 從 ES 抽取 T1 raw 事件 parquet
├── frontend/
│   ├── app.css                        # v1-1 共用前端樣式
│   ├── app.js                         # v1-1 SPA 入口互動邏輯
│   ├── dashboard-renderers.js         # v1-1 圖表與表格渲染邏輯
│   ├── index.html                     # v1-1 主入口頁
│   └── query-definitions.js           # v1-1 DuckDB 查詢定義
├── render_apply_conversion_t3.py      # 從 T2 產出 apply-conversion HTML
├── render_device_platform_t3.py       # 從 T2 產出 device-platform HTML
├── render_page_navigation_t3.py       # 從 T2 產出 page-navigation HTML
├── render_page_ranking_t3.py          # 從 T2 產出 page-ranking HTML
├── render_search_behavior_t3.py       # 從 T2 產出 search-behavior HTML
├── render_traffic_overview_t3.py      # 從 T2 產出 traffic-overview HTML
├── run_device_platform_pipeline.py    # device-platform 的 extract→transform→render PoC
├── run_page_navigation_pipeline.py    # page-navigation 的 extract→transform→render PoC
├── run_page_ranking_pipeline.py       # page-ranking 的 extract→transform→render PoC
├── run_search_behavior_pipeline.py    # search-behavior 的 extract→transform→render PoC
├── run_traffic_overview_pipeline.py   # traffic-overview 的 extract→transform→render PoC
├── run_all.py                         # 一鍵執行所有報告 + 產生導覽頁
├── run_apply_conversion_pipeline.py   # apply-conversion 的 extract→transform→render PoC
├── grafana-dashboard.plan.md          # Dashboard 實作計畫（Grafana JSON 匯出待完成）
├── report-data-pipeline.plan.md       # ES→raw→report→html 三層資料管線重構計畫
├── archive/
│   └── page-click-analysis.plan.md   # ✅ 已完成：Dashboard 8 實作計畫
├── pyproject.toml                     # uv 專案設定
├── .python-version                    # Python 版本
└── tree.md                            # 本檔案
```
