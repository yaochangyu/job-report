"""
resume_metadata.py
──────────────────
從 core6 Solr 批次查詢應徵者履歷基本資料（sex_i、birth_dt）。
"""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from typing import Any

SOLR_BASE_URL = "http://solr.web.internal:8985/solr"
SOLR_CORE = "core6"
BATCH_SIZE = 200


def fetch_resume_metadata(user_ids: list[int | str]) -> dict[str, dict[str, Any]]:
    """批次查詢應徵者 sex_i / birth_dt，回傳 {user_id_str: {"sex_i": int|None, "birth_dt": str|None}}。

    找不到的 user_id（尚未建立履歷）不會出現在回傳字典中。
    """
    if not user_ids:
        return {}

    str_ids = [str(u) for u in user_ids if u is not None]
    results: dict[str, dict[str, Any]] = {}

    for i in range(0, len(str_ids), BATCH_SIZE):
        batch = str_ids[i : i + BATCH_SIZE]
        q = "talentNo_l:(" + " OR ".join(batch) + ")"
        url = (
            f"{SOLR_BASE_URL}/{SOLR_CORE}/select?"
            + urllib.parse.urlencode({
                "q": q,
                "fl": "talentNo_l,sex_i,birth_dt",
                "rows": len(batch),
                "wt": "json",
            })
        )
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(urllib.request.Request(url), context=ctx, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"[WARN] Solr 查詢失敗（batch {i}）：{e}")
            continue

        for doc in data.get("response", {}).get("docs", []):
            uid = str(doc.get("talentNo_l", ""))
            if uid:
                results[uid] = {
                    "sex_i": doc.get("sex_i"),
                    "birth_dt": doc.get("birth_dt"),
                }

    return results
