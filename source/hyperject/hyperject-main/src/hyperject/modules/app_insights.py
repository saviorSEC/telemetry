"""App Insights /v2.1/track ingest target (cf. source-files/hyperject-msrc.py)."""
from __future__ import annotations

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class AppInsightsModule(TargetModule):
    name = "app_insights"
    description = "app-insights ingest"

    def default_config(self, base_url: str) -> dict:
        ikey = (f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
                f"{sample_hex(4)}-{sample_hex(12)}")
        return {
            "enabled": True,
            "description": self.description,
            "endpoints": [f"{base_url}/v2.1/track"],
            "ikeys": [ikey],
            "accept_field": "itemsAccepted",
        }

    def _build(self, ikey, cfg, variant, index) -> dict:
        base = {
            "name": "Microsoft.ApplicationInsights.Event",
            "time": now_iso(short=True),
            "iKey": ikey,
            "tags": {"ai.device.id": f"bas-{variant}-{index}"},
            "data": {"baseType": "EventData",
                     "baseData": {"ver": 2, "name": f"BAS_{variant}"}},
        }
        if variant == "large":
            base["data"]["baseData"]["properties"] = {"blob": large_blob(cfg)}
        if variant == "covert":
            base["tags"][cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return base

    @staticmethod
    def _ikey_entries(mcfg):
        """Yield (ikey, label) for each configured key. An entry may be a bare
        GUID string or an annotated object {"ikey"/"value": ..., "label": ...}."""
        for item in mcfg.get("ikeys", []):
            if isinstance(item, dict):
                yield (item.get("ikey") or item.get("value") or ""), item.get("label", "")
            else:
                yield item, ""

    def plan(self, mcfg, cfg, variants):
        accept_field = mcfg.get("accept_field", "itemsAccepted")

        def check(r):
            try:
                return r.status_code == 200 and r.json().get(accept_field, 0) >= 1
            except Exception:
                return False

        out = []
        for endpoint in mcfg.get("endpoints", []):
            for ikey, label in self._ikey_entries(mcfg):
                target = f"{endpoint} [{label}]" if label else endpoint
                for v in variants:
                    preps = [Prepared("POST", endpoint,
                                      {"json": self._build(ikey, cfg, v, i)}, check)
                             for i in range(variant_count(v, cfg))]
                    out.append((v, target, preps))
        return out
