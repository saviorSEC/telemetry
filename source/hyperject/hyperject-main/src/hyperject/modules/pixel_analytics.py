"""GET tracking-pixel analytics ingest target (cf. source-files/test_program_analytics.py)."""
from __future__ import annotations

import random
import time

from ..base import TargetModule
from ..core import Prepared, variant_count


class PixelAnalyticsModule(TargetModule):
    name = "pixel_analytics"
    description = "GET pixel ingest"
    # covert/large don't map cleanly onto a GET pixel; expose the ones that do.
    supported_techniques = ("basic", "bulk")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "endpoint": f"{base_url}/hm.gif",
        }

    def _full(self, variant, index) -> dict:
        return {
            "si": str(random.randint(10000000, 99999999)), "et": "1",
            "ep": f"bas_{variant}", "el": "simulation", "ev": str(index),
            "st": str(int(time.time())), "su": "https://example.com",
            "sr": "1920x1080", "sd": "24-bit", "en": "en-us",
            "sim_marker": f"BAS-{variant}-{index}",
        }

    def _minimal(self) -> dict:
        return {"si": str(random.randint(10000000, 99999999)), "et": "0",
                "st": str(int(time.time()))}

    def plan(self, mcfg, cfg, variants):
        url = mcfg["endpoint"]

        def check(r):
            return r.status_code == 200

        out = []
        for v in variants:
            n = variant_count(v, cfg)
            if v == "bulk":
                preps = [Prepared("GET", url, {"params": self._full("bulk", i),
                                               "allow_redirects": False}, check)
                         for i in range(n)]
                out.append(("bulk", f"{url} [full]", preps))
            else:
                out.append(("basic", f"{url} [full]",
                            [Prepared("GET", url, {"params": self._full("basic", 0),
                                                   "allow_redirects": False}, check)]))
                out.append(("basic", f"{url} [minimal]",
                            [Prepared("GET", url, {"params": self._minimal(),
                                                   "allow_redirects": False}, check)]))
        return out
