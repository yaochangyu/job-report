#!/usr/bin/env python3
"""
run_all.py
──────────
組裝 DuckDB 單頁網站輸出。

執行方式：
    uv run python run_all.py
    uv run python run_all.py --output /tmp/site
"""

import argparse
import json
import shutil
from pathlib import Path

from common.es_client import generated_now

ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATASET_DIR = ROOT_DIR / "dataset"
OUTPUT_DIR = ROOT_DIR / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="組裝 DuckDB 單頁網站輸出")
    parser.add_argument("--output", default=None, help="自訂輸出目錄")
    return parser.parse_args()


def copy_tree(source: Path, target: Path) -> None:
    if not source.exists():
        return
    for item in source.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def build_site(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copy_tree(FRONTEND_DIR, output_dir)
    copy_tree(DATASET_DIR, output_dir / "dataset")

    manifest_path = DATASET_DIR / "manifest.json"
    available_dates: list[str] = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        available_dates = manifest.get("available_dates", [])

    site_manifest = {
        "generated_at": generated_now(),
        "frontend": str(FRONTEND_DIR.relative_to(ROOT_DIR)),
        "dataset_present": DATASET_DIR.exists(),
        "available_dates": available_dates,
    }
    (output_dir / "site-manifest.json").write_text(
        json.dumps(site_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    build_site(output_dir)
    print(f"[OK] 單頁網站已輸出：{output_dir}")


if __name__ == "__main__":
    main()
