"""PostHog capture ingest target.

PostHog ingests events at ``POST /capture/`` with the project API key carried in
the JSON body. A project that accepts an unauthenticated event is EXPOSED;
success is ``200`` (``{"status":1}``).
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class PosthogModule(TargetModule):
    name = "posthog"
    description = "posthog capture ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("PostHog capture (real: /capture/). 'api_key' is sent in the "
                      "JSON body."),
            "endpoint": f"{base_url}/capture/",
            "api_key": f"phc_{sample_hex(32)}",
        }

    def _payload(self, mcfg, cfg, variant, index) -> dict:
        props = {"distinct_id": f"bas-{variant}-{index}", "variant": variant}
        if variant == "large":
            props["blob"] = large_blob(cfg)
        if variant == "covert":
            props[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"api_key": mcfg.get("api_key", ""), "event": "bas_event",
                "properties": props, "timestamp": now_iso(short=True)}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/json"}

        def check(r):
            return r.status_code == 200

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"json": self._payload(mcfg, cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
