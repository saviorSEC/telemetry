"""Device check-in telemetry ingest target (cf. source-files/hyperject-goog.py)."""
from __future__ import annotations

import random
import time

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, large_blob, rand_hex_id


class CheckinModule(TargetModule):
    name = "checkin"
    description = "device check-in ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "base_url": f"{base_url}/checkin",
            "accept_field": "stats_ok",
            "device_profiles": [
                # a plain device, and a fleet-vehicle profile (cf. the source's
                # Waymo path): kind=vehicle triggers dynamic vehicle_id + prefixed ids.
                {"device": "sim-device", "manufacturer": "sim-vendor",
                 "model": "Sim Model", "sdk": "29"},
                {"device": "sim-vehicle", "manufacturer": "sim-fleet",
                 "model": "Compute Unit", "sdk": "30", "fleet": "sim-autonomous",
                 "kind": "vehicle", "id_prefix": "FLEET"},
            ],
        }

    def _build(self, mcfg, cfg, variant, index) -> dict:
        profile = random.choice(mcfg.get("device_profiles") or [{}])
        # device_info excludes control keys used only to drive generation
        device_info = [f"{k}:{v}" for k, v in profile.items()
                       if k not in ("kind", "id_prefix")]
        checkin = {
            "device_info": device_info,
            "android_id": rand_hex_id(),
            "security_token": str(random.getrandbits(63)),
            "last_checkin_msec": int(time.time() * 1000),
            "user_serial_number": str(random.randint(1000, 9999)),
            "checkin_timestamp": int(time.time()),
            "locale": "en-US",
            "sim_marker": f"BAS-{variant}-{index}",
        }
        if profile.get("kind") == "vehicle":
            prefix = profile.get("id_prefix", "FLEET")
            vehicle_id = f"WV{random.randint(100000, 999999)}"
            checkin["android_id"] = f"{prefix}-{rand_hex_id()}"
            checkin["security_token"] = f"{prefix}_TOKEN_{random.randint(100000, 999999)}"
            checkin["vehicle_id"] = vehicle_id
            device_info.append(f"vehicle_id:{vehicle_id}")
        if variant == "large":
            checkin["blob"] = large_blob(cfg)
        if variant == "covert":
            checkin[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {"checkin": checkin}

    def plan(self, mcfg, cfg, variants):
        url = mcfg["base_url"]
        accept_field = mcfg.get("accept_field", "stats_ok")

        def check(r):
            try:
                return r.status_code == 200 and r.json().get(accept_field) is True
            except Exception:
                return False

        out = []
        for v in variants:
            preps = [Prepared("POST", url,
                              {"json": self._build(mcfg, cfg, v, i),
                               "headers": {"Content-Type": "application/json"}}, check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, url, preps))
        return out
