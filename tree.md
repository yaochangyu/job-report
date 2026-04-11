# 專案資料夾結構

```
job-report-1/
├── common/
│   ├── __init__.py
│   ├── es_client.py                    # Grafana _msearch 共用封裝（含 --from-store flag）
│   ├── store.py                        # SQLite 雙層儲存（interval + daily）
│   ├── parquet_schema.py               # DuckDB 單頁方案的 Parquet schema / 輸出設定
│   ├── parquet_dataset.py              # Parquet 寫入、欄位正規化與 manifest 維護
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
├── frontend/
│   ├── index.html                      # DuckDB 單頁報表入口
│   ├── app.css                         # DuckDB 單頁報表樣式
│   ├── app.js                          # DuckDB 單頁報表前端邏輯
│   ├── dashboard-renderers.js          # KPI、圖表、表格的前端渲染邏輯
│   └── query-definitions.js            # DuckDB 單頁查詢條件 → SQL 定義
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
├── extract_all.py                     # ETL 腳本：從 ES 擷取聚合結果存入 store.db
│                                      #   --mode interval（即時層，每 10~60 分鐘）
│                                      #   --mode daily（日報層，每日整天精確值）
├── extract_events.py                  # ETL 腳本：從 ES 擷取原始事件輸出為 Parquet
├── store.db                           # SQLite 資料庫（git ignore）
│                                      #   snapshots_interval：time_from+time_to+report+query_name
│                                      #   snapshots_daily：date+report+query_name
│                                      #   meta：key-value（last_interval_run 等）
├── deploy.sh                          # 一鍵產生報告並部署到 GitHub Pages
├── run_all.py                         # 一鍵執行所有報告 + 產生導覽頁
│                                      #   --from-store 讓所有子腳本從 store.db 讀取
├── snapshot-refactor.plan.md          # ETL 雙層儲存架構實作計畫（含備忘方案 A~E）
├── duckdb-single-page.plan.md         # 單一頁面 + DuckDB-WASM + Parquet 實作計畫
├── grafana-dashboard.plan.md          # Dashboard 實作計畫（Grafana JSON 匯出待完成）
├── archive/
│   └── page-click-analysis.plan.md   # ✅ 已完成：Dashboard 8 實作計畫
├── pyproject.toml                     # uv 專案設定
├── .python-version                    # Python 版本
└── tree.md                            # 本檔案
```
