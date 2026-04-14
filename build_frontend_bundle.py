#!/usr/bin/env python3
"""
build_frontend_bundle.py
────────────────────────
Legacy helper：僅複製前端靜態資產到 output/，不再部署 dataset 或覆蓋首頁。
"""

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATASET_DIR = ROOT_DIR / "dataset"
OUTPUT_DIR = ROOT_DIR / "output"
FRONTEND_FILES = (
    "app.css",
    "app.js",
    "dashboard-renderers.js",
    "query-definitions.js",
)
TW = timezone(timedelta(hours=8))


def _load_dataset_manifest() -> dict:
    manifest_path = DATASET_DIR / "manifest" / "t2-report-manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _copy_frontend_assets() -> None:
    for file_name in FRONTEND_FILES:
        shutil.copy2(FRONTEND_DIR / file_name, OUTPUT_DIR / file_name)


def _write_site_manifest(dataset_manifest: dict) -> None:
    report_names = sorted((dataset_manifest.get("reports") or {}).keys())
    site_manifest = {
        "generated_at": datetime.now(TW).strftime("%Y-%m-%d %H:%M:%S +08:00"),
        "frontend": "static-assets-only",
        "dataset_present": False,
        "report_names": report_names,
    }
    (OUTPUT_DIR / "site-manifest.json").write_text(
        json.dumps(site_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_frontend_bundle() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_manifest = _load_dataset_manifest()
    _copy_frontend_assets()
    _write_site_manifest(dataset_manifest)


if __name__ == "__main__":
    build_frontend_bundle()
