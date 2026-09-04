"""Segment (Twilio) HTTP Tracking API ingest target.

Segment ingests events at ``POST /v1/batch`` authenticated with HTTP Basic auth
(the write key as the username, empty password). A source that accepts an
unauthenticated batch is EXPOSED; success is ``200 {"success": true}``.
"""
from __future__ import annotations

import base64

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class SegmentModule(TargetModule):
    name = "segment"
    description = "segment tracking API ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Segment HTTP Tracking API (real: /v1/batch). 'write_key' is "
                      "sent via HTTP Basic auth (write key as username)."),
            "endpoint": f"{base_url}/v1/batch",
            "write_key": sample_hex(32),
        }

    def _event(self, cfg, variant, index) -> dict:
        props = {"variant": variant, "index": index}
        if variant == "large":
            props["blob"] = large_blob(cfg)
        if variant == "covert":
            props[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"type": "track", "event": "BAS Event",
                "userId": f"bas-{variant}-{index}", "properties": props,
                "timestamp": now_iso(short=True)}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}
        if mcfg.get("write_key"):
            token = base64.b64encode(f"{mcfg['write_key']}:".encode()).decode()
            headers["Authorization"] = f"Basic {token}"

        def check(r):
            try:
                return r.status_code == 200 and r.json().get("success") is True
            except Exception:
                return r.status_code == 200

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": {"batch": [self._event(cfg, v, i)]},
                               "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
