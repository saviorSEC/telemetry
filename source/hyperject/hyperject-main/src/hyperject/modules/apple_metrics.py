"""Metrics ingest target (cf. source-files/test_platform_metrics.py).

Probes the endpoint with the source's four encodings: a basic JSON body, the
native metrics-array format, a plain-text body, and a form-urlencoded body.
"""
from __future__ import annotations

import random
import time

from ..base import TargetModule
from ..core import Prepared, variant_count

FORM = {"Content-Type": "application/x-www-form-urlencoded"}
TEXT = {"Content-Type": "text/plain"}


class AppleMetricsModule(TargetModule):
    name = "apple_metrics"
    description = "metrics ingest (json / native / plaintext / form)"
    supported_techniques = ("basic", "bulk")

    def default_config(self, base_url: str) -> dict:
        return {"enabled": True, "description": self.description,
                "endpoint": f"{base_url}/metrics"}

    def _native(self, index) -> dict:
        return {"metrics": [{"name": f"bas_metric_{index}",
                             "value": random.randint(1, 100),
                             "timestamp": int(time.time() * 1000),
                             "device_id": f"BAS-{random.randint(100000, 999999)}"}]}

    def plan(self, mcfg, cfg, variants):
        url = mcfg["endpoint"]

        def check(r):
            return r.status_code in (200, 204)

        out = []
        for v in variants:
            n = variant_count(v, cfg)
            if v == "bulk":
                preps = [Prepared("POST", url, {"json": self._native(i)}, check)
                         for i in range(n)]
                out.append(("bulk", f"{url} [native]", preps))
            else:
                out.append(("basic", f"{url} [json]",
                            [Prepared("POST", url,
                                      {"json": {"test": "bas_injection",
                                                "timestamp": int(time.time())}}, check)]))
                out.append(("basic", f"{url} [native]",
                            [Prepared("POST", url, {"json": self._native(0)}, check)]))
                out.append(("basic", f"{url} [text]",
                            [Prepared("POST", url, {"data": "bas_data", "headers": TEXT}, check)]))
                out.append(("basic", f"{url} [form]",
                            [Prepared("POST", url,
                                      {"data": {"metric": "bas", "value": "1"},
                                       "headers": FORM}, check)]))
        return out
