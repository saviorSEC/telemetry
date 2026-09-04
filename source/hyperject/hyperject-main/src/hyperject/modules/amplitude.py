"""Amplitude HTTP V2 API ingest target.

Amplitude ingests events at ``POST /2/httpapi`` with the API key carried in the
JSON body (``{"api_key","events":[...]}``). A project that accepts an event with
no/invalid key is EXPOSED; success is ``200`` with a
``{"code":200,"events_ingested":N}`` body.
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)


class AmplitudeModule(TargetModule):
    name = "amplitude"
    description = "amplitude HTTP V2 ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Amplitude HTTP V2 API (real: /2/httpapi). 'api_key' is sent "
                      "in the JSON body."),
            "endpoint": f"{base_url}/2/httpapi",
            "api_key": sample_hex(32),
        }

    def _event(self, cfg, variant, index) -> dict:
        props = {"variant": variant}
        if variant == "large":
            props["blob"] = large_blob(cfg)
        if variant == "covert":
            props[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"user_id": f"bas-{variant}-{index}", "event_type": "bas_event",
                "time": int(time.time() * 1000), "event_properties": props}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}

        def check(r):
            try:
                return r.status_code == 200 and r.json().get("code") == 200
            except Exception:
                return r.status_code == 200

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": {"api_key": mcfg.get("api_key", ""),
                                        "events": [self._event(cfg, v, i)]},
                               "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
