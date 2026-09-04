"""New Relic Log API ingest target.

New Relic ingests logs at ``POST /log/v1`` authenticated with an ``Api-Key``
header; the body is a JSON array of log objects. An endpoint that accepts an
event with no/invalid key is EXPOSED; success is ``202`` with a
``{"requestId": ...}`` body.
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)


class NewRelicModule(TargetModule):
    name = "new_relic"
    description = "new relic Log API ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("New Relic Log API (real: /log/v1). 'api_key' is sent as the "
                      "'Api-Key' header (an ingest/license key)."),
            "endpoint": f"{base_url}/log/v1",
            "api_key": sample_hex(40),
            "service": "hyperject-bas",
        }

    def _log(self, mcfg, cfg, variant, index) -> dict:
        attrs = {"variant": variant, "service.name": mcfg.get("service", "hyperject-bas")}
        entry = {"message": f"BAS log {variant} {index}",
                 "timestamp": int(time.time() * 1000), "attributes": attrs}
        if variant == "large":
            entry["message"] = f"BAS log {variant} {index} " + large_blob(cfg)
        if variant == "covert":
            attrs[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return entry

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}
        if mcfg.get("api_key"):
            headers["Api-Key"] = mcfg["api_key"]

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
