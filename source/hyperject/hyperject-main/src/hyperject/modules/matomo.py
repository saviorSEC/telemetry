"""Matomo (Piwik) tracking ingest target.

Matomo ingests hits at ``POST /matomo.php`` with the tracking parameters carried
as query params (``idsite``, ``rec=1``, ``action_name``, ``_id``, …). A tracker
that accepts an unauthenticated hit is EXPOSED; success is ``204`` (POST) or a
1x1 GIF (GET).
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, sample_hex


class MatomoModule(TargetModule):
    name = "matomo"
    description = "matomo/piwik tracking ingest"
    supported_techniques = ("basic", "bulk", "covert")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Matomo tracking (real: /matomo.php, params). 'site_id' is the "
                      "idsite; 'token_auth' (optional) authorizes some fields."),
            "endpoint": f"{base_url}/matomo.php",
            "site_id": "1",
        }

    def _params(self, mcfg, cfg, variant, index) -> dict:
        params = {"idsite": str(mcfg.get("site_id", "1")), "rec": "1", "apiv": "1",
                  "action_name": f"BAS/{variant}/{index}",
                  "_id": sample_hex(16), "rand": str(int(time.time() * 1000)),
                  "url": "http://lab.local/bas"}
        if mcfg.get("token_auth"):
            params["token_auth"] = mcfg["token_auth"]
        if variant == "covert":
            params[cfg["techniques"]["covert_field"]["field"].replace(".", "_")] = \
                covert_marker(cfg)
        return params

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]

        def check(r):
            return r.status_code in (200, 204)

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"params": self._params(mcfg, cfg, v, i)}, check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
