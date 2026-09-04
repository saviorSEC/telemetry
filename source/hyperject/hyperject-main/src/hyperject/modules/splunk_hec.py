"""Splunk HTTP Event Collector (HEC) ingest target.

Splunk receives events at ``POST /services/collector/event`` (default port 8088)
authenticated with an ``Authorization: Splunk <token>`` header. A HEC input that
accepts an event with no/invalid token is EXPOSED; the success body is
``{"text":"Success","code":0}``.
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)


class SplunkHecModule(TargetModule):
    name = "splunk_hec"
    description = "splunk HTTP Event Collector ingest"

    def default_config(self, base_url: str) -> dict:
        token = (f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
                 f"{sample_hex(4)}-{sample_hex(12)}")
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Splunk HEC event endpoint (real: /services/collector/event "
                      "on :8088). 'token' is sent as 'Authorization: Splunk <token>'."),
            "endpoint": f"{base_url}/services/collector/event",
            "token": token,
            "sourcetype": "hyperject:bas",
            "index": "main",
        }

    def _event(self, mcfg, cfg, variant, index) -> dict:
        event = {"event": f"BAS event {variant} {index}",
                 "action": "simulation", "variant": variant}
        if variant == "large":
            event["blob"] = large_blob(cfg)
        if variant == "covert":
            event[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"time": time.time(), "sourcetype": mcfg.get("sourcetype", "hyperject:bas"),
                "index": mcfg.get("index", "main"), "event": event}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}
        if mcfg.get("token"):
            headers["Authorization"] = f"Splunk {mcfg['token']}"

        def check(r):
            try:
                return r.status_code == 200 and r.json().get("code") == 0
            except Exception:
                return False

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": self._event(mcfg, cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
