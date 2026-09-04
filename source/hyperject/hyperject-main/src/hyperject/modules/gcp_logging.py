"""GCP Cloud Logging ingest target.

Cloud Logging ingests entries at ``POST /v2/entries:write`` authenticated with an
``Authorization: Bearer <oauth-token>`` header; the body is
``{"logName","resource","entries":[...]}``. An endpoint that accepts an
unauthenticated write is EXPOSED; success is ``200 {}``.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso)


class GcpLoggingModule(TargetModule):
    name = "gcp_logging"
    description = "gcp cloud logging entries.write"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("GCP Cloud Logging (real: /v2/entries:write). 'bearer_token' is "
                      "sent as 'Authorization: Bearer'; 'project_id' names the log."),
            "endpoint": f"{base_url}/v2/entries:write",
            "project_id": "hyperject-lab",
            "bearer_token": "",
        }

    def _entry(self, cfg, variant, index) -> dict:
        payload = {"message": f"BAS entry {variant} {index}", "variant": variant}
        if variant == "large":
            payload["blob"] = large_blob(cfg)
        if variant == "covert":
            payload[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"jsonPayload": payload, "severity": "INFO",
                "timestamp": now_iso(short=True)}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        project = mcfg.get("project_id", "hyperject-lab")
        headers = {"Content-Type": "application/json"}
        if mcfg.get("bearer_token"):
            headers["Authorization"] = f"Bearer {mcfg['bearer_token']}"

        def check(r):
            return r.status_code == 200

        def body(v, i):
            return {"logName": f"projects/{project}/logs/hyperject-bas",
                    "resource": {"type": "global"},
                    "entries": [self._entry(cfg, v, i)]}

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": body(v, i), "headers": headers}, check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
