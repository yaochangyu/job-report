"""
es_client.py
────────────
Grafana _msearch proxy 共用封裝。
"""

import argparse
import base64
import json
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any

# ── Grafana / ES 設定 ────────────────────────────────────────────────────────

GRAFANA_URL = "https://grafana.web.internal"
GRAFANA_USER = "esodev"
GRAFANA_PASSWORD = "2KqHmF6x"
DATASOURCE_UID = "af55vm1ovng1sb"
ES_INDEX = "operation-logs"

TW = timezone(timedelta(hours=8))


# ── msearch ──────────────────────────────────────────────────────────────────

def _build_basic_auth_token() -> str:
    return base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()).decode()


def _open_json_request(url: str, data: bytes, content_type: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": content_type,
            "Authorization": f"Basic {_build_basic_auth_token()}",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())


def msearch(body: dict, index: str = ES_INDEX) -> dict:
    """透過 Grafana Datasource Proxy 發送 _msearch 請求，回傳第一個 response。"""
    url = f"{GRAFANA_URL}/api/datasources/proxy/uid/{DATASOURCE_UID}/_msearch"
    ndjson = (
        json.dumps({"index": index}) + "\n" +
        json.dumps(body) + "\n"
    ).encode("utf-8")

    data = _open_json_request(url, ndjson, "application/x-ndjson")
    r = data["responses"][0]
    if "error" in r:
        print(f"[ERROR] ES 回傳錯誤：{r['error']['reason']}", file=sys.stderr)
        sys.exit(1)
    return r


# ── CLI 參數 ─────────────────────────────────────────────────────────────────

def parse_args(description: str = "產生分析報告") -> argparse.Namespace:
    """統一的 CLI 參數解析。"""
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=None, help="查詢近 N 天（預設：當日）")
    group.add_argument("--from", dest="time_from", default=None, help="起始時間，例如 2026-04-01")
    parser.add_argument("--to", dest="time_to", default=None, help="結束時間，例如 2026-04-10")
    parser.add_argument("--output", default=None, help="自訂輸出目錄")
    return parser.parse_args()


def resolve_time_range(args: argparse.Namespace) -> tuple[str, str]:
    """根據 CLI 參數解析查詢時間區間。"""
    if args.time_from:
        time_from = args.time_from if "T" in args.time_from else args.time_from + "T00:00:00Z"
        time_to = (args.time_to + "T23:59:59Z") if args.time_to else "now"
    elif args.days:
        time_from = f"now-{args.days}d"
        time_to = "now"
    else:
        today = datetime.now(TW).strftime("%Y-%m-%d")
        time_from = today + "T00:00:00+08:00"
        time_to = "now"
    return time_from, time_to


def generated_now() -> str:
    """回傳目前時間字串（台灣時區）。"""
    return datetime.now(TW).strftime("%Y-%m-%d %H:%M:%S +08:00")
