# 專案資料夾結構

```
job-report-1/
├── common/
│   ├── __init__.py
│   ├── es_client.py              # Grafana _msearch 共用封裝
│   ├── html_template.py          # HTML header/footer/style 共用模板
│   └── chart_helpers.py          # Chart.js 輔助函式
├── output/
│   └── traffic-overview/
│       └── index.html            # Dashboard 1 報告產出
├── category_tab_report.py        # 既有報告（保留）
├── traffic_overview_report.py    # Dashboard 1：整體流量概覽
├── grafana-dashboard.plan.md     # Dashboard 實作計畫
├── pyproject.toml                # uv 專案設定
├── .python-version               # Python 版本
└── tree.md                       # 本檔案
```
