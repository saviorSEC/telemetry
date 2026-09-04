"""Graylog GELF (HTTP) ingest target.

Graylog ingests GELF messages at ``POST /gelf`` (GELF HTTP input, commonly on
:12201) as a JSON GELF object. A GELF input that accepts an unauthenticated
message is EXPOSED; success is ``202`` (empty).
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, large_blob


class GraylogGelfModule(TargetModule):
    name = "graylog_gelf"
    description = "graylog GELF HTTP ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": "Graylog GELF HTTP input (real: POST /gelf, commonly :12201).",
            "endpoint": f"{base_url}/gelf",
            "host": "hyperject-bas",
        }

    def _gelf(self, mcfg, cfg, variant, index) -> dict:
        msg = {"version": "1.1", "host": mcfg.get("host", "hyperject-bas"),
               "short_message": f"BAS event {variant} {index}",
               "timestamp": time.time(), "level": 6, "_variant": variant}
        if variant == "large":
            msg["_blob"] = large_blob(cfg)
        if variant == "covert":
            field = "_" + cfg["techniques"]["covert_field"]["field"].replace(".", "_")
            msg[field] = covert_marker(cfg)
        return msg

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": self._gelf(mcfg, cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
