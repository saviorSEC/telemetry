"""Google Analytics 4 Measurement Protocol ingest target.

GA4 ingests events at ``POST /mp/collect?measurement_id=&api_secret=`` as JSON
(``{"client_id","events":[...]}``). The production endpoint returns ``204`` for
any structurally-valid request regardless of the secret — so reachability itself
is the exposure signal.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, sample_hex


class Ga4Module(TargetModule):
    name = "ga4"
    description = "google analytics 4 measurement protocol"
    supported_techniques = ("basic", "bulk", "covert")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("GA4 Measurement Protocol (real: /mp/collect). 'api_secret' "
                      "and 'measurement_id' are sent as query params."),
            "endpoint": f"{base_url}/mp/collect",
            "measurement_id": "G-HYPERJECT0",
            "api_secret": sample_hex(22),
        }

    def _payload(self, cfg, variant, index) -> dict:
        params = {"variant": variant, "engagement_time_msec": "1"}
        if variant == "covert":
            params[cfg["techniques"]["covert_field"]["field"].replace(".", "_")] = \
                covert_marker(cfg)
        return {"client_id": f"{sample_hex(8)}.{sample_hex(8)}",
                "events": [{"name": "bas_event", "params": params}]}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        params = {"measurement_id": mcfg.get("measurement_id", ""),
                  "api_secret": mcfg.get("api_secret", "")}
        headers = {"Content-Type": "application/json"}

        def check(r):
            return r.status_code in (200, 204)

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": self._payload(cfg, v, i), "params": params,
                               "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
