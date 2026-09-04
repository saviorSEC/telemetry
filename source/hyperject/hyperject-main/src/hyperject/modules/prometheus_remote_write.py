"""Prometheus Remote Write ingest target.

Remote Write is how Prometheus, Grafana Mimir, Cortex, Thanos and
VictoriaMetrics receive metrics: ``POST /api/v1/write`` with a
Snappy-compressed, protobuf-encoded ``prometheus.WriteRequest`` and headers
``Content-Type: application/x-protobuf`` + ``Content-Encoding: snappy``.

Like OTLP, the spec makes authentication "a transport-layer problem" -- so an
endpoint that accepts an unauthenticated remote-write is EXPOSED. Body is built
with hyperject's own protobuf codec and wrapped with the dependency-free Snappy
block encoder (no protobuf/snappy libraries required).
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)
from .. import proto, snappy

REMOTE_WRITE_VERSION = "0.1.0"


class PrometheusRemoteWriteModule(TargetModule):
    name = "prometheus_remote_write"
    description = "prometheus remote-write ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Remote-write receiver path (real: /api/v1/write on "
                      "Prometheus, Mimir, Cortex, Thanos, VictoriaMetrics). Body "
                      "is Snappy-compressed protobuf; add 'headers' to probe an "
                      "authenticated receiver."),
            "endpoint": f"{base_url}/api/v1/write",
            "job": "hyperject-bas",
            "headers": {},
        }

    def _labels(self, cfg, variant, index) -> list:
        labels = [
            {"name": "__name__", "value": f"hyperject_bas_{variant}"},
            {"name": "job", "value": "hyperject-bas"},
            {"name": "instance", "value": f"bas-{index}"},
        ]
        if variant == "large":
            labels.append({"name": "blob", "value": large_blob(cfg)})
        if variant == "covert":
            labels.append({"name": cfg["techniques"]["covert_field"]["field"],
                           "value": covert_marker(cfg)})
        return labels

    def _write_request(self, cfg, variant, index) -> dict:
        return {"timeseries": [{
            "labels": self._labels(cfg, variant, index),
            "samples": [{"value": 1.0, "timestamp": int(time.time() * 1000)}],
        }]}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
            "X-Prometheus-Remote-Write-Version": REMOTE_WRITE_VERSION,
            "User-Agent": "hyperject",
            **(mcfg.get("headers") or {}),
        }

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = []
            for i in range(variant_count(v, cfg)):
                body = snappy.compress(proto.encode_write_request(
                    self._write_request(cfg, v, i)))
                preps.append(Prepared("POST", endpoint,
                                      {"data": body, "headers": headers}, check))
            out.append((v, endpoint, preps))
        return out
