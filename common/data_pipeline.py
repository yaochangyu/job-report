"""
data_pipeline.py
────────────────
T1 / T2 / T3 三層資料管線的共用契約與路徑定義。
"""

from __future__ import annotations

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
T1_RAW_DIR = DATASET_DIR / "raw"
T2_REPORT_DIR = DATASET_DIR / "report"
T3_RENDER_DIR = ROOT_DIR / "output"

T1_RAW_MANIFEST_PATH = MANIFEST_DIR / "t1-raw-manifest.json"
T2_REPORT_MANIFEST_PATH = MANIFEST_DIR / "t2-report-manifest.json"
T3_RENDER_MANIFEST_PATH = MANIFEST_DIR / "t3-render-manifest.json"

RAW_PARTITION_RULE = "date=YYYY-MM-DD"
REPORT_PARTITION_RULE = "report-name/range=YYYY-MM-DD_YYYY-MM-DD"
RENDER_PARTITION_RULE = "render-output/<version-or-latest>"

TIER_CONTRACTS: dict[DataTier, TierContract] = {
    DataTier.T1_RAW: TierContract(
        tier=DataTier.T1_RAW,
        root_dir=T1_RAW_DIR,
        manifest_path=T1_RAW_MANIFEST_PATH,
        description="從 ES 匯出的標準化原始事件 parquet，供所有報表分析重用。",
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
    T1_RAW_DIR.mkdir(parents=True, exist_ok=True)
    T2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    T3_RENDER_DIR.mkdir(parents=True, exist_ok=True)


def get_tier_contract(tier: DataTier) -> TierContract:
    """取得指定資料層的契約資訊。"""

    return TIER_CONTRACTS[tier]


def t1_raw_date_dir(target_date: str) -> Path:
    """回傳 T1 指定日期分區目錄。"""

    return T1_RAW_DIR / f"date={target_date}"


def t2_report_date_dir(report_name: str, target_date: str) -> Path:
    """回傳 T2 指定報表與日期分區目錄。"""

    return T2_REPORT_DIR / report_name / f"date={target_date}"


def t2_report_root_dir(report_name: str) -> Path:
    """回傳 T2 單一報表根目錄。"""

    return T2_REPORT_DIR / report_name


def t2_report_range_dir(report_name: str, date_from: str, date_to: str) -> Path:
    """回傳 T2 單一報表指定日期區間目錄。"""

    return t2_report_root_dir(report_name) / f"range={date_from}_{date_to}"
