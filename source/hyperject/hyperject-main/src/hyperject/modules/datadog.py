"""Datadog logs intake target.

Datadog ingests logs at ``POST /api/v2/logs`` authenticated with a ``DD-API-KEY``
header; the body is a JSON array of log objects. A log intake that accepts an
event with no/invalid key is EXPOSED; success is ``202 Accepted``.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class DatadogModule(TargetModule):
    name = "datadog"
    description = "datadog logs intake"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Datadog logs intake (real: /api/v2/logs). 'api_key' is sent "
                      "as the 'DD-API-KEY' header."),
            "endpoint": f"{base_url}/api/v2/logs",
            "api_key": sample_hex(32),
            "service": "hyperject-bas",
            "ddsource": "hyperject",
        }

    def _log(self, mcfg, cfg, variant, index) -> dict:
        entry = {
            "message": f"BAS log {variant} {index}",
            "ddsource": mcfg.get("ddsource", "hyperject"),
            "service": mcfg.get("service", "hyperject-bas"),
            "ddtags": f"variant:{variant},env:lab",
            "timestamp": now_iso(short=True),
        }
        if variant == "large":
            entry["message"] = f"BAS log {variant} {index} " + large_blob(cfg)
        if variant == "covert":
            entry[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return entry

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}
        if mcfg.get("api_key"):
            headers["DD-API-KEY"] = mcfg["api_key"]

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": [self._log(mcfg, cfg, v, i)], "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
