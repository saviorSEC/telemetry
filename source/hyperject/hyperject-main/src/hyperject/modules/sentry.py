"""Sentry envelope ingest target.

Sentry SDKs POST error/transaction envelopes to ``/api/{project_id}/envelope/``
authenticated with an ``X-Sentry-Auth`` header carrying the DSN public key. The
body is a newline-delimited envelope: an envelope header, then item header /
item payload pairs. A project that accepts an unauthenticated envelope is
EXPOSED; success is ``200`` with an ``{"id": "<event-id>"}`` body.
"""
from __future__ import annotations

import json

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)


class SentryModule(TargetModule):
    name = "sentry"
    description = "sentry envelope ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Sentry envelope endpoint (real: /api/<project>/envelope/). "
                      "'public_key' is sent in the X-Sentry-Auth header; "
                      "'project_id' selects the path."),
            "endpoint": f"{base_url}/api/1/envelope/",
            "public_key": sample_hex(32),
            "project_id": "1",
        }

    def _event(self, cfg, variant, index) -> dict:
        event = {
            "event_id": sample_hex(32),
            "timestamp": now_iso(short=True),
            "platform": "python",
            "level": "error",
            "logger": "hyperject.bas",
            "message": f"BAS event {variant} {index}",
            "tags": {"variant": variant, "action": "simulation"},
        }
        if variant == "large":
            event["extra"] = {"blob": large_blob(cfg)}
        if variant == "covert":
            event["tags"][cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return event

    def _envelope(self, cfg, variant, index) -> bytes:
        event = self._event(cfg, variant, index)
        header = json.dumps({"event_id": event["event_id"]})
        item_header = json.dumps({"type": "event"})
        item = json.dumps(event)
        return (header + "\n" + item_header + "\n" + item + "\n").encode("utf-8")

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/x-sentry-envelope"}
        if mcfg.get("public_key"):
            headers["X-Sentry-Auth"] = (
                f"Sentry sentry_version=7, sentry_client=hyperject/1.0, "
                f"sentry_key={mcfg['public_key']}")

        def check(r):
            return r.status_code == 200

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._envelope(cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
