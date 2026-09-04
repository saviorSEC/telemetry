"""Honeycomb events ingest target.

Honeycomb ingests events at ``POST /1/batch/{dataset}`` authenticated with an
``X-Honeycomb-Team`` header; the body is a JSON array of ``{"time","data"}``
events. A dataset that accepts an unauthenticated batch is EXPOSED; success is
``200`` with a per-event ``[{"status":202}]`` array.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class HoneycombModule(TargetModule):
    name = "honeycomb"
    description = "honeycomb events ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Honeycomb batch API (real: /1/batch/<dataset>). 'api_key' is "
                      "sent as the 'X-Honeycomb-Team' header."),
            "endpoint": f"{base_url}/1/batch/hyperject-bas",
            "api_key": sample_hex(32),
        }

    def _event(self, cfg, variant, index) -> dict:
        data = {"name": f"BAS event {variant} {index}", "variant": variant,
                "duration_ms": 1}
        if variant == "large":
            data["blob"] = large_blob(cfg)
        if variant == "covert":
            data[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"time": now_iso(short=True), "data": data}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}
        if mcfg.get("api_key"):
            headers["X-Honeycomb-Team"] = mcfg["api_key"]

        def check(r):
            return r.status_code == 200

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": [self._event(cfg, v, i)], "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
