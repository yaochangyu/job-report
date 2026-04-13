# GitHub Pages 結構清理計畫 (Cleanup gh-pages)

目標是將 `gh-pages` 分支整理成乾淨的「版本化」結構，並移除根目錄的冗餘檔案。

## 理想結構
```text
gh-pages/
├── index.html (自動導向到最新版的 Redirector)
├── v1/
│   ├── index.html, app.js, app.css...
│   └── dataset/ (v1 專用資料)
└── v2/
    ├── index.html, app.js, app.css...
    └── dataset/ (v2 專用資料)
```

## 實作步驟

- [ ] **1. 檢查並備份 gh-pages**
    - 確認目前 `gh-pages` 遠端的分支內容。
- [ ] **2. 徹底清理 gh-pages 根目錄**
    - 刪除根目錄下所有「非版本目錄」的檔案（如舊的 `app.js`, `dataset/` 等）。
    - 僅保留 `v1/`, `v2/` 以及我們剛建立的 `index.html` (Redirector)。
- [ ] **3. 優化 `deploy.sh` 的清理邏輯**
    - 修改腳本，使其在部署新版本時，能自動清理掉根目錄那些「不屬於任何版本」的雜物。
- [ ] **4. 推送更新**
    - 將清理後的乾淨結構推送到遠端。

## 預期效益
- 分支結構清晰，一眼就能看出有哪些版本。
- 減少 GitHub Pages 的儲存空間占用（移除舊的重複資料）。
