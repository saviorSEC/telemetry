"""InfluxDB v2 write ingest target.

InfluxDB ingests points at ``POST /api/v2/write?org=&bucket=`` (default port 8086)
authenticated with an ``Authorization: Token <token>`` header; the body is line
protocol (``measurement,tag=v field=1 timestamp``). A write endpoint that accepts
an unauthenticated point is EXPOSED; success is ``204`` (empty).
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, sample_hex


class InfluxdbModule(TargetModule):
    name = "influxdb"
    description = "influxdb v2 line-protocol write"
    supported_techniques = ("basic", "bulk", "covert")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("InfluxDB v2 write (real: /api/v2/write on :8086, line "
                      "protocol). 'token' is sent as 'Authorization: Token <token>'."),
            "endpoint": f"{base_url}/api/v2/write",
            "token": sample_hex(43),
            "org": "hyperject",
            "bucket": "bas",
        }

    def _line(self, cfg, variant, index) -> str:
        tags = f"variant={variant},host=lab"
        if variant == "covert":
            field = cfg["techniques"]["covert_field"]["field"].replace(".", "_")
            tags += f",{field}={covert_marker(cfg)}"
        return f"hyperject_bas,{tags} value={index + 1}i {time.time_ns()}"

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        params = {"org": mcfg.get("org", "hyperject"),
                  "bucket": mcfg.get("bucket", "bas"), "precision": "ns"}
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        if mcfg.get("token"):
            headers["Authorization"] = f"Token {mcfg['token']}"

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._line(cfg, v, i).encode("utf-8"),
                               "params": params, "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
