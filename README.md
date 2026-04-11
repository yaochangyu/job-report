# jobbank-web 數據分析報告

從 Elasticsearch（透過 Grafana proxy）擷取 jobbank-web 的使用者行為資料，產生 HTML 靜態報告，並部署到 GitHub Pages。

---

## 目錄

- [架構概覽](#架構概覽)
- [快速開始](#快速開始)
- [報告一覽](#報告一覽)
- [ETL 資料擷取](#etl-資料擷取)
- [排程設定（cron）](#排程設定cron)
- [產生報告](#產生報告)
- [部署到 GitHub Pages](#部署到-github-pages)
- [store.db 資料庫結構](#storedb-資料庫結構)
- [專案結構](#專案結構)
- [環境需求](#環境需求)

---

## 架構概覽

```
Elasticsearch
     │  每 10~60 分鐘（cron）
     ▼
extract_all.py  ──→  store.db（SQLite 雙層儲存）
                          │  interval 表（即時層）
                          │  daily 表（日報層）
                          │
                    report_*.py --from-store
                          │
                          ▼
                     output/index.html
                     output/*/index.html
                          │
                          ▼
                    GitHub Pages（靜態部署）
```

**設計動機**：ES 資料有保留期限，ES 消失後仍能從 `store.db` 重新產生任意日期區間的報告，完全不依賴 ES。

---

## 快速開始

```bash
# 安裝相依套件（含 Playwright）
uv sync
uv run playwright install chromium

# 從 ES 直接產生今日報告（傳統模式）
uv run python run_all.py --days 1

# 先擷取資料到 store.db，再從 store 產生報告
uv run python extract_all.py --mode daily --date today
uv run python run_all.py --from-store --days 1
```

---

## 報告一覽

| 圖示 | 腳本 | 報告名稱 | 說明 |
|------|------|----------|------|
| 📊 | `traffic_overview_report.py` | 整體流量概覽 | KPI、每日趨勢、每小時分佈、裝置分佈 |
| 🔍 | `search_behavior_report.py` | 搜尋行為分析 | AI vs 一般搜尋、搜尋結果頁、快速篩選 |
| 🎯 | `apply_conversion_report.py` | 應徵轉換分析 | 應徵漏斗、每日趨勢、來源、裝置與時段 |
| ⚡ | `feature_engagement_report.py` | 功能互動分析 | 探索職缺/企業、身份辨識、產業 Tab、新聞 |
| 📱 | `device_platform_report.py` | 裝置與平台分析 | Mobile/Desktop 趨勢、OS/瀏覽器、行為交叉 |
| 🏆 | `page_ranking_report.py` | 頁面流量排行 | featureId Top 20、功能類別佔比 |
| 🔀 | `page_navigation_report.py` | 頁面導航鏈路 | 轉換路徑排行、頁面來源/目標、進入分佈 |
| 🔥 | `click_heatmap_report.py` | 頁面點擊熱點 | 截圖疊加 click count 的 Clarity 風格熱點 |

---

## ETL 資料擷取

### `extract_all.py` 用法

```bash
# ── 即時層（interval）──────────────────────────────────────────────
# 自動讀取上次執行時間（meta 表），查詢距今的差距
uv run python extract_all.py --mode interval

# 手動指定區間
uv run python extract_all.py --mode interval \
  --from 2026-04-11T06:00:00+08:00 \
  --to   2026-04-11T06:10:00+08:00

# ── 日報層（daily）─────────────────────────────────────────────────
# 昨天（預設）
uv run python extract_all.py --mode daily

# 今天
uv run python extract_all.py --mode daily --date today

# 指定日期
uv run python extract_all.py --mode daily --date 2026-04-10

# 補跑一段日期區間
uv run python extract_all.py --mode daily \
  --from 2026-04-01 --to 2026-04-10
```

---

## 排程設定（cron）

```bash
# 編輯 crontab
crontab -e
```

加入以下兩行（請將路徑替換為實際路徑）：

```cron
# 每 10 分鐘擷取即時層
*/10 * * * * cd /path/to/job-report-1 && /home/user/.local/bin/uv run python extract_all.py --mode interval >> /var/log/job-report-interval.log 2>&1

# 每天凌晨 2 點擷取日報層（整天精確值）
0 2 * * * cd /path/to/job-report-1 && /home/user/.local/bin/uv run python extract_all.py --mode daily >> /var/log/job-report-daily.log 2>&1
```

> **注意**：cron 沒有 `$PATH`，`uv` 必須使用完整路徑。  
> 用 `which uv` 查詢實際路徑。

---

## 產生報告

### 單份報告

```bash
# 直接查 ES（需要 ES 可連線）
uv run python traffic_overview_report.py --days 7

# 從 store.db 讀取（ES 離線也能跑）
uv run python traffic_overview_report.py --from-store --days 7

# 指定日期區間
uv run python traffic_overview_report.py --from 2026-04-01 --to 2026-04-10
```

### 全部報告一次執行

```bash
# 查 ES
uv run python run_all.py --days 7

# 從 store.db（ES 消失後仍可用）
uv run python run_all.py --from-store --days 7

# 指定日期區間
uv run python run_all.py --from-store --from 2026-04-01 --to 2026-04-10
```

產生的檔案位於 `output/`：
```
output/
├── index.html                  # 導覽頁
├── traffic-overview/index.html
├── search-behavior/index.html
└── ...（其餘報告）
```

### CLI 參數說明

| 參數 | 說明 | 範例 |
|------|------|------|
| `--days N` | 近 N 天（預設 7） | `--days 30` |
| `--from DATE` | 起始日期或 ISO 時間 | `--from 2026-04-01` |
| `--to DATE` | 結束日期（預設 now） | `--to 2026-04-10` |
| `--from-store` | 從 store.db 讀取，不查 ES | `--from-store` |

---

## 部署到 GitHub Pages

```bash
# 產生近 7 天報告並推送到 gh-pages 分支
bash deploy.sh

# 指定天數
bash deploy.sh 30
```

部署後可於以下網址查看：  
👉 https://yaochangyu.github.io/job-report/

---

## store.db 資料庫結構

`store.db` 是 SQLite 資料庫，包含三張資料表：

### `snapshots_interval`（即時層）
每 10 分鐘 cron 寫入，保存固定時間窗口的聚合結果。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `time_from` | TEXT | 區間起始（ISO 8601） |
| `time_to` | TEXT | 區間結束（ISO 8601） |
| `report` | TEXT | 報告名稱（如 `traffic-overview`） |
| `query_name` | TEXT | 查詢函式名稱（如 `query_kpi`） |
| `data` | TEXT | JSON 結果 |
| `created_at` | TEXT | 寫入時間 |

主鍵：`(time_from, time_to, report, query_name)`

### `snapshots_daily`（日報層）
每天整天精確值，適合跨天查詢。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | TEXT | 日期（`YYYY-MM-DD`） |
| `report` | TEXT | 報告名稱 |
| `query_name` | TEXT | 查詢函式名稱 |
| `data` | TEXT | JSON 結果 |
| `created_at` | TEXT | 寫入時間 |

主鍵：`(date, report, query_name)`

### `meta`（元資料）
| 欄位 | 說明 |
|------|------|
| `last_interval_run` | 上次 interval 模式執行的結束時間，供下次自動計算起點 |

### ⚠️ Unique Sessions 跨天近似值說明

ES `cardinality`（HyperLogLog）統計的 unique session 數**無法跨天合併加總**，多天區間的數值為各天加總的近似值，報告中以 `＊` 標記。

---

## 專案結構

```
job-report-1/
├── common/
│   ├── es_client.py          # Grafana _msearch 共用封裝、CLI 參數解析
│   ├── store.py              # SQLite 雙層儲存 CRUD
│   ├── html_template.py      # HTML header/footer/style 共用模板
│   └── chart_helpers.py      # Chart.js 輔助函式
├── extract_all.py            # ETL 腳本（cron 執行）
├── run_all.py                # 一鍵執行所有報告 + 產生導覽頁
├── traffic_overview_report.py
├── search_behavior_report.py
├── apply_conversion_report.py
├── feature_engagement_report.py
├── device_platform_report.py
├── page_ranking_report.py
├── page_navigation_report.py
├── click_heatmap_report.py
├── click_heatmap_config.json # 點擊熱點頁面設定
├── click_heatmap_discover.py # 自動探索頁面可點擊元素
├── deploy.sh                 # 部署到 GitHub Pages
├── store.db                  # SQLite 資料庫（不納入版控）
├── output/                   # 產出的 HTML 報告
├── pyproject.toml
└── tree.md                   # 詳細資料夾結構說明
```

---

## 環境需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 套件管理
- Playwright（click_heatmap 截圖用）
- 可連線的 Grafana / Elasticsearch（直接查詢模式需要）

```bash
# 安裝 uv（若尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝專案相依套件
uv sync

# 安裝 Playwright 瀏覽器
uv run playwright install chromium
```
