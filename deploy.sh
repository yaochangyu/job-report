#!/usr/bin/env bash
# deploy.sh — 產生報告並部署至 GitHub Pages
#
# 用法：
#   bash deploy.sh [--days N] [--from YYYY-MM-DD] [--to YYYY-MM-DD]
#                  [--version v1-3] [--skip-build]
#
# 範例：
#   bash deploy.sh --days 17 --version v1-3
#   bash deploy.sh --from 2026-05-01 --to 2026-05-17 --version v1-3
#   bash deploy.sh --version v1-3 --skip-build   # output/ 已產好，直接部署
set -e

DAYS=7
VERSION=""
FROM_DATE=""
TO_DATE=""
SKIP_BUILD=false

# ── 參數解析 ──────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)    DAYS="$2";     shift 2 ;;
    --from)    FROM_DATE="$2"; shift 2 ;;
    --to)      TO_DATE="$2";   shift 2 ;;
    --version) VERSION="$2";   shift 2 ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    *)
      # 相容舊用法：deploy.sh [DAYS] [VERSION]
      if [[ -z "$_COMPAT_DAYS_SET" ]]; then DAYS="$1"; _COMPAT_DAYS_SET=1
      elif [[ -z "$VERSION" ]];            then VERSION="$1"
      fi
      shift ;;
  esac
done

REPO_URL="https://github.com/yaochangyu/job-report.git"
OUTPUT_DIR="$(dirname "$0")/output"
TMP_DIR=$(mktemp -d)

# ── 日期區間 ──────────────────────────────────────────────────────
if [[ -z "$FROM_DATE" ]]; then
  TO_DATE=$(date +%F)
  FROM_DATE=$(date -d "$((DAYS - 1)) days ago" +%F)
elif [[ -z "$TO_DATE" ]]; then
  TO_DATE=$(date +%F)
fi

# ── 組裝報告 ──────────────────────────────────────────────────────
if [[ "$SKIP_BUILD" == false ]]; then
  echo "▶ 組裝網站報告（${FROM_DATE} ～ ${TO_DATE}）..."
  uv run python "$(dirname "$0")/run_all.py" --from "$FROM_DATE" --to "$TO_DATE"
else
  echo "▶ 跳過 build，直接使用現有 output/"
fi

# ── 部署到 GitHub Pages ───────────────────────────────────────────
echo "▶ 部署到 GitHub Pages..."
git init "$TMP_DIR"
git -C "$TMP_DIR" remote add origin "$REPO_URL"
git -C "$TMP_DIR" fetch origin gh-pages --depth=1 || echo "gh-pages branch not found, creating new..."
git -C "$TMP_DIR" checkout gh-pages || git -C "$TMP_DIR" checkout -b gh-pages

echo "▶ 清理 gh-pages 根目錄雜物..."
find "$TMP_DIR" -mindepth 1 -maxdepth 1 -not -name ".git" -not -name "v*" -not -name "index.html" -exec rm -rf {} +

if [ -n "$VERSION" ]; then
    TARGET_DIR="$TMP_DIR/$VERSION"
    echo "▶ 部署到版本目錄: $VERSION"
    mkdir -p "$TARGET_DIR"
    find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -r "$OUTPUT_DIR/." "$TARGET_DIR/"

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
