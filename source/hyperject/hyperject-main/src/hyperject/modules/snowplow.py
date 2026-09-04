"""Snowplow collector ingest target.

The Snowplow collector ingests events at ``POST
/com.snowplowanalytics.snowplow/tp2`` as a self-describing JSON payload_data
envelope. A collector that accepts an unauthenticated event is EXPOSED; success
is ``200``.
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, sample_hex

_TP2 = "/com.snowplowanalytics.snowplow/tp2"
_SCHEMA = ("iglu:com.snowplowanalytics.snowplow/payload_data/jsonschema/1-0-4")


class SnowplowModule(TargetModule):
    name = "snowplow"
    description = "snowplow collector ingest"
    supported_techniques = ("basic", "bulk", "covert")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": f"Snowplow collector (real: POST {_TP2}, self-describing JSON).",
            "endpoint": f"{base_url}{_TP2}",
        }

    def _event(self, cfg, variant, index) -> dict:
        ev = {"e": "ue", "eid": sample_hex(32), "dtm": str(int(time.time() * 1000)),
              "p": "srv", "aid": "hyperject-bas", "tv": "hyperject-1.0",
              "variant": variant}
        if variant == "covert":
            ev[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return ev

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": {"schema": _SCHEMA,
                                        "data": [self._event(cfg, v, i)]},
                               "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
