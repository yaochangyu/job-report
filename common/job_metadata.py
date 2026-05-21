"""
job_metadata.py
───────────────
從 Matching Search ES（search-jobs-v1-*）批次查詢職缺的職類與產業資訊。
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from typing import Any

from common.es_client import GRAFANA_URL, _build_basic_auth_token

MATCHING_ES_UID = "bf3z8ygb41hq8a"
JOB_INDEX = "search-jobs-v1-*"
BATCH_SIZE = 500


def _msearch_matching(body: str) -> dict[str, Any]:
    url = f"{GRAFANA_URL}/api/datasources/proxy/uid/{MATCHING_ES_UID}/_msearch"
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/x-ndjson",
            "Authorization": f"Basic {_build_basic_auth_token()}",
        },
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_job_metadata(job_ids: list[int | str]) -> dict[str, dict[str, Any]]:
    """批次查詢職缺 metadata，回傳 {job_id_str: {"job_positions": [...], "company_industries": [...]}}。

    找不到的 job_id（已下架）不會出現在回傳字典中。
    """
    if not job_ids:
        return {}

    int_ids = [int(j) for j in job_ids if j is not None]
    results: dict[str, dict[str, Any]] = {}

    for i in range(0, len(int_ids), BATCH_SIZE):
        batch = int_ids[i : i + BATCH_SIZE]
        body = (
            json.dumps({"index": JOB_INDEX}) + "\n"
            + json.dumps({
                "size": len(batch),
                "_source": ["id", "jobPositionNames", "companyIndustryNames"],
                "query": {"terms": {"id": batch}},
            }) + "\n"
        )
        data = _msearch_matching(body)
        hits = data.get("responses", [{}])[0].get("hits", {}).get("hits", [])
        for hit in hits:
            s = hit["_source"]
            jid = str(s["id"])
            results[jid] = {
                "job_positions": s.get("jobPositionNames") or [],
                "company_industries": s.get("companyIndustryNames") or [],
            }

    return results
