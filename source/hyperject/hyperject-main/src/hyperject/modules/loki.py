"""Grafana Loki push ingest target.

Loki ingests logs at ``POST /loki/api/v1/push`` in two encodings:
  * protobuf: a Snappy-compressed ``logproto.PushRequest`` (default,
    ``Content-Type: application/x-protobuf``)
  * JSON: ``{"streams": [{"stream": {labels}, "values": [[ts_ns, line]]}]}``

Multi-tenant Loki keys off the ``X-Scope-OrgID`` header rather than real auth, so
an endpoint that accepts an unauthenticated push is EXPOSED. The protobuf body is
built with hyperject's own codec + Snappy encoder (no external libraries).
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex)
from .. import proto, snappy


class LokiModule(TargetModule):
    name = "loki"
    description = "grafana loki push ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Loki push endpoint. 'encoding' is 'protobuf' "
                      "(Snappy-compressed logproto) or 'json'. Set 'org_id' to send "
                      "an X-Scope-OrgID tenant header."),
            "endpoint": f"{base_url}/loki/api/v1/push",
            "encoding": "protobuf",
            "org_id": "",
            "labels": {"job": "hyperject-bas", "level": "info"},
        }

    def _label_string(self, mcfg, cfg, variant) -> str:
        labels = dict(mcfg.get("labels") or {})
        labels["variant"] = variant
        if variant == "covert":
            labels[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        inner = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return "{" + inner + "}"

    def _line(self, cfg, variant, index) -> str:
        if variant == "large":
            return f"BAS {variant} {index} " + large_blob(cfg)
        if variant == "covert":
            return f"BAS {variant} {index} {covert_marker(cfg)}"
        return f"BAS log event {variant} {index}"

    def _protobuf_body(self, mcfg, cfg, variant, index) -> bytes:
        now = time.time_ns()
        payload = {"streams": [{
            "labels": self._label_string(mcfg, cfg, variant),
            "entries": [{"seconds": now // 1_000_000_000,
                         "nanos": now % 1_000_000_000,
                         "line": self._line(cfg, variant, index)}],
        }]}
        return snappy.compress(proto.encode_loki_push(payload))

    def _json_body(self, mcfg, cfg, variant, index) -> dict:
        return {"streams": [{
            "stream": self._labels_dict(mcfg, cfg, variant),
            "values": [[str(time.time_ns()), self._line(cfg, variant, index)]],
        }]}

    def _labels_dict(self, mcfg, cfg, variant) -> dict:
        labels = dict(mcfg.get("labels") or {})
        labels["variant"] = variant
        if variant == "covert":
            labels[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return labels

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        encoding = "json" if mcfg.get("encoding") == "json" else "protobuf"
        base_headers = {}
        if mcfg.get("org_id"):
            base_headers["X-Scope-OrgID"] = mcfg["org_id"]

        def check(r):
            return 200 <= r.status_code < 300

        out = []
        for v in variants:
            preps = []
            for i in range(variant_count(v, cfg)):
                if encoding == "protobuf":
                    kwargs = {"data": self._protobuf_body(mcfg, cfg, v, i),
                              "headers": {**base_headers,
                                          "Content-Type": "application/x-protobuf",
                                          "Content-Encoding": "snappy"}}
                else:
                    kwargs = {"json": self._json_body(mcfg, cfg, v, i),
                              "headers": {**base_headers,
                                          "Content-Type": "application/json"}}
                preps.append(Prepared("POST", endpoint, kwargs, check))
            out.append((v, f"{endpoint} [{encoding}]", preps))
        return out
