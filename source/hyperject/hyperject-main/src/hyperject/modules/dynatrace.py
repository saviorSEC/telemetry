"""Dynatrace metric ingest target.

Dynatrace ingests metrics at ``POST /api/v2/metrics/ingest`` authenticated with
an ``Authorization: Api-Token <token>`` header; the body is Dynatrace metric line
protocol (``metric.key,dim=val count,1``). An endpoint that accepts an
unauthenticated ingest is EXPOSED; success is ``202`` with
``{"linesOk": N, "linesInvalid": 0, ...}``.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, sample_hex


class DynatraceModule(TargetModule):
    name = "dynatrace"
    description = "dynatrace metric ingest"
    # line protocol has no natural place for a large blob; keep the sane subset.
    supported_techniques = ("basic", "bulk", "covert")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Dynatrace metric ingest (real: /api/v2/metrics/ingest). "
                      "'api_token' is sent as 'Authorization: Api-Token <token>'."),
            "endpoint": f"{base_url}/api/v2/metrics/ingest",
            "api_token": f"dt0c01.{sample_hex(24).upper()}",
        }

    def _line(self, cfg, variant, index) -> str:
        dims = f"variant={variant},env=lab"
        if variant == "covert":
            field = cfg["techniques"]["covert_field"]["field"].replace(".", "_")
            dims += f",{field}={covert_marker(cfg)}"
        return f"hyperject.bas.event,{dims} count,{index + 1}"

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "text/plain"}
        if mcfg.get("api_token"):
            headers["Authorization"] = f"Api-Token {mcfg['api_token']}"

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._line(cfg, v, i).encode("utf-8"),
                               "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
