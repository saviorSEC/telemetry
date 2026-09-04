"""Azure Monitor Log Analytics (classic HTTP Data Collector API) ingest target.

Logs are posted to ``POST /api/logs?api-version=2016-04-01`` authenticated with an
``Authorization: SharedKey <workspaceId>:<signature>`` header, where the signature
is an HMAC-SHA256 over a canonical string (this module computes the REAL signature
the Azure SDK computes, so the request is wire-accurate against a live workspace).
A workspace that accepts the write is EXPOSED; success is ``200`` (empty).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class AzureLogAnalyticsModule(TargetModule):
    name = "azure_log_analytics"
    description = "azure log analytics data collector API"

    def default_config(self, base_url: str) -> dict:
        workspace = (f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
                     f"{sample_hex(4)}-{sample_hex(12)}")
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Azure Log Analytics HTTP Data Collector API (real: /api/logs). "
                      "'shared_key' must be base64; the SharedKey HMAC is computed for "
                      "real. Secure workspaces reject a bad signature."),
            "endpoint": f"{base_url}/api/logs",
            "workspace_id": workspace,
            "shared_key": base64.b64encode(os.urandom(32)).decode(),
            "log_type": "HyperjectBAS",
        }

    def _record(self, cfg, variant, index) -> dict:
        rec = {"Message": f"BAS record {variant} {index}", "Variant": variant,
               "TimeGenerated": now_iso(short=True)}
        if variant == "large":
            rec["Blob"] = large_blob(cfg)
        if variant == "covert":
            rec[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return rec

    @staticmethod
    def _sign(workspace_id: str, shared_key: str, content_len: int):
        rfc1123 = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        to_hash = (f"POST\n{content_len}\napplication/json\n"
                   f"x-ms-date:{rfc1123}\n/api/logs")
        try:
            decoded = base64.b64decode(shared_key)
            digest = hmac.new(decoded, to_hash.encode("utf-8"), hashlib.sha256).digest()
            sig = base64.b64encode(digest).decode()
        except Exception:
            sig = ""
        return rfc1123, f"SharedKey {workspace_id}:{sig}"

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        params = {"api-version": "2016-04-01"}
        workspace_id = mcfg.get("workspace_id", "")
        shared_key = mcfg.get("shared_key", "")
        log_type = mcfg.get("log_type", "HyperjectBAS")

        def check(r):
            return r.status_code == 200

        def make(v, i) -> Prepared:
            body = json.dumps([self._record(cfg, v, i)]).encode("utf-8")
            rfc1123, auth = self._sign(workspace_id, shared_key, len(body))
            headers = {"Content-Type": "application/json", "Log-Type": log_type,
                       "x-ms-date": rfc1123, "Authorization": auth,
                       "time-generated-field": "TimeGenerated"}
            return Prepared("POST", endpoint,
                            {"data": body, "params": params, "headers": headers},
                            check)

        out = []
        for v in variants:
            preps = [make(v, i) for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
