# GitHub Pages 版本化部署計畫 (Versioning Support)

為了讓 `https://yaochangyu.github.io/job-report/` 能夠依據版號區分（如 `/v1.0.0/`），我們需要調整部署流程。

## 實作步驟

- [x] **1. 修改 `deploy.sh` 支援版本號參數**
    - 讓腳本接受第二個參數作為版本號（例如 `./deploy.sh 7 v1.0.0`）。
    - 調整檔案複製邏輯，將 `output/` 內的檔案放入 `gh-pages` 分支下的 `v{version}/` 資料夾。
    - 確保 `gh-pages` 分支原有的其他版本資料夾不會被刪除（不使用 `git checkout --orphan`，而是保留歷史或手動管理目錄）。


- [x] **2. 建立根目錄索引 (Redirector)**
    - 在 `gh-pages` 的根目錄放置一個 `index.html`。
    - 讓預設存取 `https://.../job-report/` 時能自動跳轉到最新版本，或是顯示版本清單。

- [x] **3. 驗證部署流程**
    - 執行帶有版本號的部署測試。
    - 確認 GitHub Pages 上的目錄結構正確。

## 預期結果
- `https://yaochangyu.github.io/job-report/v1.0.0/index.html` 可正常存取。
- 不同版本的報告可以並存。
