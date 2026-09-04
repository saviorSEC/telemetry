"""Mixpanel /track ingest target.

Mixpanel ingests events at ``POST /track`` with the event JSON base64-encoded in
a form ``data=`` field (project token carried in the event properties). A project
that accepts an unauthenticated event is EXPOSED; success is ``200`` (``{"status":1}``
verbose, or ``1``).
"""
from __future__ import annotations

import base64
import json

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)


class MixpanelModule(TargetModule):
    name = "mixpanel"
    description = "mixpanel /track ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Mixpanel /track (real: base64 JSON in a form 'data=' field). "
                      "'token' is the project token carried in event properties."),
            "endpoint": f"{base_url}/track",
            "token": sample_hex(32),
        }

    def _data(self, mcfg, cfg, variant, index) -> dict:
        props = {"token": mcfg.get("token", ""), "distinct_id": f"bas-{variant}-{index}",
                 "variant": variant}
        if variant == "large":
            props["blob"] = large_blob(cfg)
        if variant == "covert":
            props[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        payload = json.dumps({"event": "BAS Event", "properties": props})
        encoded = base64.b64encode(payload.encode()).decode()
        return {"data": encoded, "verbose": "1"}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        def check(r):
            return r.status_code == 200

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._data(mcfg, cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
