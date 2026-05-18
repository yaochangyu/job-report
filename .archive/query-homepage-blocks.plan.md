# query-homepage-blocks 實作計畫

目標：建立 `query_homepage_blocks.py`，從 ES 查詢首頁四大類別區塊的每日點擊數，輸出 TSV 格式。

TSV 格式與 `identify-clicks-daily-*.tsv` 一致（區塊／分類／名稱／featureId／日期欄）。

---

## 實作步驟

- [x] **Step 1：定義 BLOCKS 常數**
  列出搜尋類別、身分類別、探索工作、探索企業所有 featureId 對應表。

- [x] **Step 2：建立 ES 查詢**
  `date_histogram` + `terms` sub-aggregation，一次查所有 featureId 每日點擊數。

- [x] **Step 3：整理結果並輸出 TSV**
  矩陣格式：rows = 各 featureId，columns = 日期，缺值補 0。

- [x] **Step 4：CLI 支援日期區間參數**
  支援 `--from / --to`、`--days N`，預設查今天。
  輸出檔名預設為 `homepage-clicks-daily-{from}-{to}.tsv`。
