#!/usr/bin/env bash
set -e

DAYS=${1:-7}
VERSION=${2}
REPO_URL="https://github.com/yaochangyu/job-report.git"
OUTPUT_DIR="$(dirname "$0")/output"
TMP_DIR=$(mktemp -d)
TO_DATE=$(date +%F)
FROM_DATE=$(date -d "$((DAYS - 1)) days ago" +%F)

echo "▶ 匯出 Parquet dataset（${FROM_DATE} ~ ${TO_DATE}）..."
# v1 版本使用的是 extract_all.py
uv run python "$(dirname "$0")/extract_all.py" --mode daily --from "$FROM_DATE" --to "$TO_DATE"

echo "▶ 組裝單頁網站..."
uv run python "$(dirname "$0")/run_all.py"

echo "▶ 部署到 GitHub Pages..."
git init "$TMP_DIR"
git -C "$TMP_DIR" remote add origin "$REPO_URL"
git -C "$TMP_DIR" fetch origin gh-pages --depth=1 || echo "gh-pages branch not found, creating new..."
git -C "$TMP_DIR" checkout gh-pages || git -C "$TMP_DIR" checkout -b gh-pages

# 🧹 清理根目錄下不屬於任何版本的舊檔案 (非版本資料夾且非 index.html)
echo "▶ 清理 gh-pages 根目錄雜物..."
find "$TMP_DIR" -maxdepth 1 -not -name "." -not -name ".git" -not -name "v*" -not -name "index.html" -exec rm -rf {} +

if [ -n "$VERSION" ]; then
    TARGET_DIR="$TMP_DIR/$VERSION"
    echo "▶ 部署到版本目錄: $VERSION"
    mkdir -p "$TARGET_DIR"
    cp -r "$OUTPUT_DIR/." "$TARGET_DIR/"
    
    # 產生根目錄導向 index.html
    cat <<EEOF > "$TMP_DIR/index.html"
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <link rel="canonical" href="./$VERSION/">
    <script>location.href="./$VERSION/"</script>
    <meta http-equiv="refresh" content="0; url=./$VERSION/">
</head>
<body>
    <p>Redirecting to latest version: <a href="./$VERSION/">$VERSION</a></p>
</body>
</html>
EEOF
else
    TARGET_DIR="$TMP_DIR"
    echo "▶ 部署到根目錄"
    cp -r "$OUTPUT_DIR/." "$TARGET_DIR/"
fi

git -C "$TMP_DIR" add -A
git -C "$TMP_DIR" commit -m "🚀 deploy: 更新分析報告 ${VERSION:-latest}"
git -C "$TMP_DIR" push origin gh-pages

rm -rf "$TMP_DIR"
if [ -n "$VERSION" ]; then
    echo "✅ 部署完成：https://yaochangyu.github.io/job-report/$VERSION/"
else
    echo "✅ 部署完成：https://yaochangyu.github.io/job-report/"
fi
