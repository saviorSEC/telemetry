"""Elastic APM Server ingest target.

The APM Server ingests events at ``POST /intake/v2/events`` (default port 8200)
as NDJSON: a ``metadata`` line then ``transaction``/``span``/``error`` lines. An
optional ``Authorization: Bearer <secret-token>`` gates it; an endpoint that
accepts an unauthenticated intake is EXPOSED; success is ``202`` (empty).
"""
from __future__ import annotations

import json

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, large_blob, sample_hex


class ElasticApmModule(TargetModule):
    name = "elastic_apm"
    description = "elastic APM Server intake"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Elastic APM Server intake (real: /intake/v2/events on :8200, "
                      "NDJSON). 'secret_token' (optional) is sent as 'Bearer'."),
            "endpoint": f"{base_url}/intake/v2/events",
            "secret_token": "",
        }

    def _ndjson(self, cfg, variant, index) -> bytes:
        meta = {"metadata": {"service": {
            "name": "hyperject-bas", "agent": {"name": "hyperject", "version": "1.0"}}}}
        ctx = {"tags": {"variant": variant}}
        if variant == "covert":
            ctx["tags"][cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        if variant == "large":
            ctx["tags"]["blob"] = large_blob(cfg)
        txn = {"transaction": {
            "id": sample_hex(16), "trace_id": sample_hex(32), "type": "request",
            "name": f"BAS {variant} {index}", "duration": 1.0,
            "span_count": {"started": 0}, "context": ctx}}
        return (json.dumps(meta) + "\n" + json.dumps(txn) + "\n").encode("utf-8")

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/x-ndjson"}
        if mcfg.get("secret_token"):
            headers["Authorization"] = f"Bearer {mcfg['secret_token']}"

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._ndjson(cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
