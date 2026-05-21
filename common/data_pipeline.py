"""
data_pipeline.py
────────────────
T1 / T2 / T3 三層資料管線的共用契約與路徑定義。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DataTier(StrEnum):
    """資料管線三層命名。"""

    T1_RAW = "t1-raw"
    T2_REPORT = "t2-report"
    T3_RENDER = "t3-render"


@dataclass(frozen=True)
class TierContract:
    """描述單一資料層的責任與目錄契約。"""

    tier: DataTier
    root_dir: Path
    manifest_path: Path
    description: str
    partition_rule: str


ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "dataset"
MANIFEST_DIR = DATASET_DIR / "manifest"

# T0：純 ES 原始事件（不含外部 metadata）
T0_RAW_DIR = DATASET_DIR / "t0-raw"
T0_RAW_MANIFEST_PATH = MANIFEST_DIR / "t0-raw-manifest.json"

# T1：T0 + 外部 metadata 補強（Solr sex_i/birth_dt、Matching ES 職類/產業）
T1_ENRICH_DIR = DATASET_DIR / "t1-enrich"
T1_ENRICH_MANIFEST_PATH = MANIFEST_DIR / "t1-enrich-manifest.json"

# 向下相容 alias（T2 builder 透過 t1_reader 讀 T1_RAW_DIR，自動指向 T1_ENRICH_DIR）
T1_RAW_DIR = T1_ENRICH_DIR
T1_RAW_MANIFEST_PATH = T1_ENRICH_MANIFEST_PATH

T2_REPORT_DIR = DATASET_DIR / "t2-report"
T3_RENDER_DIR = ROOT_DIR / "output"

T2_REPORT_MANIFEST_PATH = MANIFEST_DIR / "t2-report-manifest.json"
T3_RENDER_MANIFEST_PATH = MANIFEST_DIR / "t3-render-manifest.json"

RAW_PARTITION_RULE = "date=YYYY-MM-DD"
REPORT_PARTITION_RULE = "report-name/range=YYYY-MM-DD_YYYY-MM-DD"
RENDER_PARTITION_RULE = "render-output/<version-or-latest>"

TIER_CONTRACTS: dict[DataTier, TierContract] = {
    DataTier.T1_RAW: TierContract(
        tier=DataTier.T1_RAW,
        root_dir=T1_ENRICH_DIR,
        manifest_path=T1_ENRICH_MANIFEST_PATH,
        description="T0 + 外部 metadata 補強後的事件 parquet，供所有 T2 builder 使用。",
        partition_rule=RAW_PARTITION_RULE,
    ),
    DataTier.T2_REPORT: TierContract(
        tier=DataTier.T2_REPORT,
        root_dir=T2_REPORT_DIR,
        manifest_path=T2_REPORT_MANIFEST_PATH,
        description="各報表從 T1 取數、分析後輸出的報表專用 parquet。",
        partition_rule=REPORT_PARTITION_RULE,
    ),
    DataTier.T3_RENDER: TierContract(
        tier=DataTier.T3_RENDER,
        root_dir=T3_RENDER_DIR,
        manifest_path=T3_RENDER_MANIFEST_PATH,
        description="最終 HTML、前端靜態資產與部署用輸出內容。",
        partition_rule=RENDER_PARTITION_RULE,
    ),
}


def ensure_pipeline_directories() -> None:
    """建立三層資料管線需要的基礎目錄。"""

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    T0_RAW_DIR.mkdir(parents=True, exist_ok=True)
    T1_ENRICH_DIR.mkdir(parents=True, exist_ok=True)
    T2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    T3_RENDER_DIR.mkdir(parents=True, exist_ok=True)


def get_tier_contract(tier: DataTier) -> TierContract:
    """取得指定資料層的契約資訊。"""

    return TIER_CONTRACTS[tier]


def t0_raw_date_dir(target_date: str) -> Path:
    """回傳 T0 指定日期分區目錄。"""

    return T0_RAW_DIR / f"date={target_date}"


def t1_enrich_date_dir(target_date: str) -> Path:
    """回傳 T1 enriched 指定日期分區目錄。"""

    return T1_ENRICH_DIR / f"date={target_date}"


def t1_raw_date_dir(target_date: str) -> Path:
    """回傳 T1 指定日期分區目錄（向下相容 alias）。"""

    return T1_ENRICH_DIR / f"date={target_date}"


def t2_report_date_dir(report_name: str, target_date: str) -> Path:
    """回傳 T2 指定報表與日期分區目錄。"""

    return T2_REPORT_DIR / report_name / f"date={target_date}"


def t2_report_root_dir(report_name: str) -> Path:
    """回傳 T2 單一報表根目錄。"""

    return T2_REPORT_DIR / report_name


def t2_report_range_dir(report_name: str, date_from: str, date_to: str) -> Path:
    """回傳 T2 單一報表指定日期區間目錄。"""

    return t2_report_root_dir(report_name) / f"range={date_from}_{date_to}"


def update_t2_manifest_dates(report_name: str, dates_written: dict[str, dict]) -> None:
    """將 per-date T2 報表記錄 merge 進 T2 manifest，保留既有日期資料。"""

    from common.es_client import generated_now  # lazy import to avoid circular

    manifest: dict = {}
    if T2_REPORT_MANIFEST_PATH.exists():
        try:
            manifest = json.loads(T2_REPORT_MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    reports = manifest.setdefault("reports", {})
    report_entry = reports.setdefault(report_name, {})
    existing_dates: dict = report_entry.setdefault("dates", {})

    now = generated_now()
    for target_date, info in dates_written.items():
        existing_dates[target_date] = {**info, "updated_at": now}

    report_entry["available_dates"] = sorted(existing_dates.keys())

    manifest["tier"] = "t2-report"
    manifest["schema_version"] = 1
    manifest["updated_at"] = now
    T2_REPORT_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
