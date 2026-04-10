# 專案資料夾結構

```
job-report-1/
├── common/
│   ├── __init__.py
│   ├── es_client.py                    # Grafana _msearch 共用封裝
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
│   └── page-navigation/index.html      # Dashboard 7 報告產出
├── category_tab_report.py             # 既有報告（保留）
├── traffic_overview_report.py         # Dashboard 1：整體流量概覽
├── search_behavior_report.py          # Dashboard 2：搜尋行為分析
├── apply_conversion_report.py         # Dashboard 3：應徵轉換分析
├── feature_engagement_report.py       # Dashboard 4：功能互動分析
├── device_platform_report.py          # Dashboard 5：裝置與平台分析
├── page_ranking_report.py             # Dashboard 6：頁面流量排行
├── page_navigation_report.py          # Dashboard 7：頁面導航鏈路分析
├── run_all.py                         # 一鍵執行所有報告 + 產生導覽頁
├── grafana-dashboard.plan.md          # Dashboard 實作計畫
├── pyproject.toml                     # uv 專案設定
├── .python-version                    # Python 版本
└── tree.md                            # 本檔案
```
