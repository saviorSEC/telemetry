"""Key-value / trace ingest target (cf. source-files/test_service_trace.py).

Probes the endpoint with the source's three encodings: a JSON body, a
form-urlencoded key-value body, and a form-urlencoded tracking-pixel (act/aid).
"""
from __future__ import annotations

import random
import time

from ..base import TargetModule
from ..core import Prepared, variant_count

FORM = {"Content-Type": "application/x-www-form-urlencoded"}
JSON = {"Content-Type": "application/json"}


class KvTraceModule(TargetModule):
    name = "kv_trace"
    description = "kv/trace ingest (json + form + pixel)"
    supported_techniques = ("basic", "bulk")

    def default_config(self, base_url: str) -> dict:
        return {"enabled": True, "description": self.description,
                "endpoint": f"{base_url}/kv"}

    def _json(self, index) -> dict:
        return {"key": f"bas_event_{index}", "value": f"sim_{index}",
                "timestamp": int(time.time()),
                "device_id": f"BAS_{random.randint(100000, 999999)}",
                "sim_marker": f"BAS-{index}"}

    def _form_kv(self) -> dict:
        return {"test_key": "bas_value", "timestamp": int(time.time()),
                "device_id": random.randint(100000, 999999)}

    def _form_pixel(self) -> dict:
        return {"act": "bas", "aid": random.randint(100000, 999999), "t": int(time.time())}

    def plan(self, mcfg, cfg, variants):
        url = mcfg["endpoint"]

        def check(r):
            return r.status_code in (200, 204)

        out = []
        for v in variants:
            n = variant_count(v, cfg)
            if v == "bulk":
                preps = [Prepared("POST", url, {"json": self._json(i), "headers": JSON}, check)
                         for i in range(n)]
                out.append(("bulk", f"{url} [json]", preps))
            else:
                out.append(("basic", f"{url} [json]",
                            [Prepared("POST", url, {"json": self._json(0), "headers": JSON}, check)]))
                out.append(("basic", f"{url} [form-kv]",
                            [Prepared("POST", url, {"data": self._form_kv(), "headers": FORM}, check)]))
                out.append(("basic", f"{url} [pixel]",
                            [Prepared("POST", url, {"data": self._form_pixel(), "headers": FORM}, check)]))
        return out
