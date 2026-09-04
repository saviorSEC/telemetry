"""Prometheus Pushgateway ingest target.

Batch jobs push metrics to the Pushgateway at ``POST /metrics/job/<job>``
(default port 9091) as Prometheus exposition text. A Pushgateway that accepts an
unauthenticated push is EXPOSED; success is ``200`` (``202`` on Pushgateway >=1.0).
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker


class PushgatewayModule(TargetModule):
    name = "pushgateway"
    description = "prometheus pushgateway ingest"
    # exposition text carries metrics; labels carry the covert marker.
    supported_techniques = ("basic", "bulk", "covert")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Prometheus Pushgateway (real: /metrics/job/<job> on :9091, "
                      "exposition text)."),
            "endpoint": f"{base_url}/metrics/job/hyperject-bas",
        }

    def _exposition(self, cfg, variant, index) -> str:
        labels = f'variant="{variant}"'
        if variant == "covert":
            field = cfg["techniques"]["covert_field"]["field"].replace(".", "_")
            labels += f',{field}="{covert_marker(cfg)}"'
        return (f"# TYPE hyperject_bas_events counter\n"
                f"hyperject_bas_events{{{labels}}} {index + 1}\n")

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "text/plain; version=0.0.4"}

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._exposition(cfg, v, i).encode("utf-8"),
                               "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
