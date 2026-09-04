"""Azure Monitor Live Metrics (QuickPulse) ingest target.

The `LiveEndpoint` in an Application Insights connection string is the real-time
"Live Metrics" stream (QuickPulse). Clients call
``POST {LiveEndpoint}/QuickPulseService.svc/ping?ikey=<ikey>`` to subscribe, then
``.../QuickPulseService.svc/post?ikey=<ikey>`` to stream MonitoringDataPoints.
Auth is ikey-in-query plus ``x-ms-qps-*`` headers; the server signals whether it
is streaming via the ``x-ms-qps-subscribed`` response header.

This module exercises that surface the same way the ingest modules do: an
endpoint that accepts unauthenticated QuickPulse traffic is EXPOSED.
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex, connection_string_live_target)

QPS_INVARIANT_VERSION = "5"


class LiveMetricsModule(TargetModule):
    name = "live_metrics"
    description = "azure-monitor Live Metrics (QuickPulse) ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Live Metrics base (real: the connection string's "
                      "LiveEndpoint, e.g. https://<region>.livediagnostics.monitor."
                      "azure.com). /QuickPulseService.svc/ping|post is appended. "
                      "Use endpoints+ikeys or paste 'connection_strings'."),
            "endpoints": [base_url],
            "ikeys": [f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
                      f"{sample_hex(4)}-{sample_hex(12)}"],
            "connection_strings": [],
            "actions": ["ping", "post"],
            "role_name": "hyperject-bas",
            "accept_status": 200,
        }

    def _headers(self, mcfg) -> dict:
        return {
            "Content-Type": "application/json",
            "x-ms-qps-transmission-time": str(int(time.time() * 1e7)),
            "x-ms-qps-stream-id": sample_hex(32),
            "x-ms-qps-machine-name": "hyperject",
            "x-ms-qps-instance-name": mcfg.get("role_name", "hyperject-bas"),
            "x-ms-qps-role-name": mcfg.get("role_name", "hyperject-bas"),
            "x-ms-qps-invariant-version": QPS_INVARIANT_VERSION,
        }

    def _body(self, ikey, mcfg, cfg, variant, index) -> dict:
        doc = {"__type": "RequestTelemetryDocument", "DocumentType": "Request",
               "Name": f"BAS_{variant}_{index}", "Url": "http://bas.local/",
               "ResponseCode": "200"}
        body = {
            "Instance": "hyperject", "RoleName": mcfg.get("role_name", "hyperject-bas"),
            "InstrumentationKey": ikey, "InvariantVersion": int(QPS_INVARIANT_VERSION),
            "Timestamp": f"/Date({int(time.time() * 1000)})/", "Version": "hyperject",
            "StreamId": sample_hex(32), "Timestamp_iso": now_iso(),
            "Metrics": [{"Name": "\\ApplicationInsights\\Requests/Sec",
                         "Value": 1, "Weight": 1}],
            "Documents": [doc],
        }
        if variant == "large":
            doc["Blob"] = large_blob(cfg)
        if variant == "covert":
            body["Properties"] = {cfg["techniques"]["covert_field"]["field"]:
                                  covert_marker(cfg)}
        return body

    def _targets(self, mcfg):
        for endpoint in mcfg.get("endpoints", []):
            for ikey in mcfg.get("ikeys", []):
                yield endpoint.rstrip("/"), ikey, ""
        for cs in mcfg.get("connection_strings", []) or []:
            raw = cs.get("value", "") if isinstance(cs, dict) else cs
            label = cs.get("label", "conn-str") if isinstance(cs, dict) else "conn-str"
            ikey, base = connection_string_live_target(raw)
            yield base.rstrip("/"), ikey, label

    def plan(self, mcfg, cfg, variants):
        accept_status = mcfg.get("accept_status", 200)
        actions = mcfg.get("actions") or ["ping", "post"]

        def check(r):
            return r.status_code == accept_status

        out = []
        for base, ikey, label in self._targets(mcfg):
            for action in actions:
                url = f"{base}/QuickPulseService.svc/{action}"
                tag = f"{label}/{action}" if label else action
                for v in variants:
                    preps = [Prepared("POST", url,
                                      {"params": {"ikey": ikey},
                                       "json": self._body(ikey, mcfg, cfg, v, i),
                                       "headers": self._headers(mcfg)}, check)
                             for i in range(variant_count(v, cfg))]
                    out.append((v, f"{url} [{tag}]", preps))
        return out
