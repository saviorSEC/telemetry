"""Marketing/conversion pixel target (cf. source-files/test_software_pixel.py).

Probes the endpoint the three ways the source does: a GET tracking pixel, a
POST form, and a POST JSON conversions-API body (event + user_data).
"""
from __future__ import annotations

import json
import random
import time

from ..base import TargetModule
from ..core import Prepared, variant_count

JSON = {"Content-Type": "application/json"}


class FacebookPixelModule(TargetModule):
    name = "facebook_pixel"
    description = "conversion pixel ingest (GET pixel / POST form / CAPI json)"
    supported_techniques = ("basic", "bulk")

    def default_config(self, base_url: str) -> dict:
        return {"enabled": True, "description": self.description,
                "endpoint": f"{base_url}/tr"}

    def _pixel_id(self) -> str:
        return str(random.randint(100000000000000, 999999999999999))

    def _get_params(self, pixel_id) -> dict:
        return {"id": pixel_id, "ev": "PageView", "dl": "https://example.com",
                "ts": str(int(time.time() * 1000)), "cd": json.dumps({"bas": "sim"}),
                "v": "2.9.0",
                "fbp": f"fb.1.{int(time.time())}.{random.randint(1000000000, 9999999999)}"}

    def _capi_body(self) -> dict:
        return {"data": [{"event_name": "PageView", "event_time": int(time.time()),
                          "user_data": {"em": "sim@example.com", "ph": "0000000000"}}]}

    def plan(self, mcfg, cfg, variants):
        url = mcfg["endpoint"]

        def check(r):
            return r.status_code in (200, 204)

        out = []
        for v in variants:
            n = variant_count(v, cfg)
            if v == "bulk":
                preps = [Prepared("GET", url, {"params": self._get_params(self._pixel_id())},
                                  check) for i in range(n)]
                out.append(("bulk", f"{url} [get-pixel]", preps))
            else:
                pid = self._pixel_id()
                out.append(("basic", f"{url} [get-pixel]",
                            [Prepared("GET", url, {"params": self._get_params(pid)}, check)]))
                out.append(("basic", f"{url} [post-form]",
                            [Prepared("POST", url,
                                      {"data": {"id": pid, "ev": "PageView",
                                                "dl": "https://example.com",
                                                "cd": json.dumps({"bas": "sim"})}}, check)]))
                out.append(("basic", f"{url} [capi-json]",
                            [Prepared("POST", url,
                                      {"json": self._capi_body(), "headers": JSON}, check)]))
        return out
