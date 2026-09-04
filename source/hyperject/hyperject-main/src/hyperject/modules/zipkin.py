"""Zipkin v2 span ingest target.

Zipkin's HTTP collector accepts spans at ``POST /api/v2/spans`` in two encodings:
  * JSON: a list of span objects (``Content-Type: application/json``)
  * protobuf: a ``zipkin.proto3`` ``ListOfSpans`` (``application/x-protobuf``)

A successful submit returns ``202 Accepted``. Zipkin has no built-in auth, so an
internet-reachable collector that accepts spans is EXPOSED. The protobuf body is
built with hyperject's own codec (no external libraries).
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)
from .. import proto

#: zipkin Kind enum: 0 unspecified, 1 CLIENT, 2 SERVER, 3 PRODUCER, 4 CONSUMER
KIND_SERVER = 2


class ZipkinModule(TargetModule):
    name = "zipkin"
    description = "zipkin v2 span ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Zipkin collector endpoint (real: /api/v2/spans). 'encoding' "
                      "is 'json' or 'protobuf' (zipkin.proto3 ListOfSpans). "
                      "Successful submit returns 202."),
            "endpoint": f"{base_url}/api/v2/spans",
            "encoding": "json",
            "service_name": "hyperject-bas",
            "headers": {},
        }

    def _span(self, mcfg, cfg, variant, index) -> dict:
        tags = {"bas.variant": variant, "bas.index": str(index)}
        if variant == "large":
            tags["blob"] = large_blob(cfg)
        if variant == "covert":
            tags[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return {
            "traceId": sample_hex(32),
            "id": sample_hex(16),
            "kind": KIND_SERVER,
            "name": f"bas_{variant}_{index}",
            "timestamp": int(time.time() * 1_000_000),
            "duration": 1234,
            "localEndpoint": {"serviceName": mcfg.get("service_name", "hyperject-bas")},
            "tags": tags,
        }

    def _json_span(self, span) -> dict:
        # zipkin JSON uses hex string ids and a nested localEndpoint; the same
        # dict shape works, only 'kind' must be the string form.
        kinds = {1: "CLIENT", 2: "SERVER", 3: "PRODUCER", 4: "CONSUMER"}
        out = dict(span)
        out["kind"] = kinds.get(span.get("kind"), "SERVER")
        return out

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        encoding = "protobuf" if mcfg.get("encoding") == "protobuf" else "json"
        base_headers = dict(mcfg.get("headers") or {})

        def check(r):
            return r.status_code in (200, 202)

        out = []
        for v in variants:
            preps = []
            for i in range(variant_count(v, cfg)):
                span = self._span(mcfg, cfg, v, i)
                if encoding == "protobuf":
                    kwargs = {"data": proto.encode_zipkin([span]),
                              "headers": {**base_headers,
                                          "Content-Type": "application/x-protobuf"}}
                else:
                    kwargs = {"json": [self._json_span(span)],
                              "headers": {**base_headers,
                                          "Content-Type": "application/json"}}
                preps.append(Prepared("POST", endpoint, kwargs, check))
            out.append((v, f"{endpoint} [{encoding}]", preps))
        return out
