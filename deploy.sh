#!/usr/bin/env bash
set -e

DAYS=${1:-7}
REPO_URL="https://github.com/yaochangyu/job-report.git"
OUTPUT_DIR="$(dirname "$0")/output"
TMP_DIR=$(mktemp -d)

echo "▶ 產生報告（近 ${DAYS} 天）..."
uv run python "$(dirname "$0")/run_all.py" --days "$DAYS"

echo "▶ 部署到 GitHub Pages..."
git init "$TMP_DIR"
git -C "$TMP_DIR" remote add origin "$REPO_URL"
git -C "$TMP_DIR" fetch origin gh-pages --depth=1
git -C "$TMP_DIR" checkout gh-pages
cp -r "$OUTPUT_DIR/." "$TMP_DIR/"
git -C "$TMP_DIR" add -A
git -C "$TMP_DIR" commit -m "🚀 deploy: 更新分析報告"
git -C "$TMP_DIR" push origin gh-pages

rm -rf "$TMP_DIR"
echo "✅ 部署完成：https://yaochangyu.github.io/job-report/"
