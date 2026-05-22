# gitlab-pages 實作計畫

目標：讓 `job-report` 專案可以在 GitLab 上透過 GitLab Pages 部署靜態網站，並保留目前 `run_all.py` 產出 `output/` 的流程；若實作過程遇到阻礙，需記錄在本計畫的失敗紀錄區，避免重複使用失敗方法。

## 實作步驟

- [x] **步驟 1 — 盤點現有部署流程與 GitLab Pages 需求差異**
  - **Why**：目前專案只有 `deploy.sh` 對 GitHub Pages 的流程，尚未有 `.gitlab-ci.yml`。先確認現有 build、輸出資料夾、版本子目錄、資產路徑與 GitLab Pages 的 `public/` 規則差異，才能避免後面直接照搬 GitHub Pages 流程導致部署後路徑錯誤。
  - **預期產出**：確認 GitLab Pages 需要的檔案與目錄規則、要不要保留版本子目錄（如 `v1-3/`）、以及目前前端資產與 dataset 路徑是否需調整。

- [x] **步驟 2 — 建立 GitLab CI / Pages 部署設定**
  - **Why**：GitLab Pages 主要靠 `.gitlab-ci.yml` 發佈，而不是像現在 `deploy.sh` 那樣直接 push `gh-pages`。需要建立可在 GitLab Runner 執行的 pipeline，完成依賴安裝、報表產生、輸出複製到 `public/`，並限制在指定 branch 或條件下發佈。
  - **預期產出**：新增 `.gitlab-ci.yml`，能在 GitLab 上執行 `uv sync`、`uv run python run_all.py ...`，並把網站內容發佈為 Pages artifact。

- [x] **步驟 3 — 調整 GitLab Pages 的靜態路徑與部署輸出**
  - **Why**：GitLab Pages 的站點 base path 與 GitHub Pages 不完全相同，如果不先調整，前端的 `app.js`、`dataset/manifest.json`、version 子目錄與靜態資產路徑可能會 404。這一步要釐清是部署到根路徑，還是部署到 `/job-report/` 或特定版本子路徑，並讓輸出與前端路徑一致。
  - **預期產出**：必要的路徑調整與部署輸出策略，確保首頁、各 report 頁、dataset 與前端資產都能正確載入。

- [x] **步驟 4 — 補充 GitLab 部署說明與操作方式**
  - **Why**：部署改成 GitLab Pages 後，維運方式會從 `bash deploy.sh` 轉為 GitLab pipeline。需要把如何觸發部署、用哪個 branch、部署後網址在哪裡、哪些 GitLab 設定要先打開，寫進文件，不然後續很難交接。
  - **預期產出**：README 或相關說明更新，清楚記錄 GitLab Pages 的部署流程、必要前置條件與使用方式。

- [x] **步驟 5 — build 驗證與部署驗證**
  - **Why**：這次變更會碰到 CI 設定與網站輸出，如果不實際 build，就很容易只是在理論上可行。需要先確認本地 build 可正常產出，再確認 GitLab pipeline 與 Pages 網址能正常提供網站內容。
  - **預期產出**：完成 build 驗證；若你同意，也可再進一步執行測試與 GitLab 上的部署驗證。

## 注意事項

- 每次只執行一個步驟，完成後回來把對應核取方塊打勾，待你確認後再進下一步。
- 若遇到 GitLab Pages 未啟用、Runner 不可用、Protected Branch 限制、Pages 網址規則不同等問題，需記錄於下方失敗紀錄。
- 若最後所有步驟完成，這份計畫檔再移入 `.archive/`。

## 失敗紀錄

- 嘗試直接沿用 `deploy.sh` 的 `gh-pages` branch 推送模式到 GitLab Pages：不可行。原因：GitLab Pages 必須由 `.gitlab-ci.yml` 產出 `public/` artifact，不能直接重用 GitHub Pages 的部署方式。
- 嘗試只依賴 repo checkout 內既有檔案部署 GitLab Pages：不可行。原因：`dataset/` 與 `output/` 被 `.gitignore` 排除，GitLab CI checkout 不會帶出現成產物，因此改採在 CI 內重新執行 `run_all.py` 產生部署內容。
