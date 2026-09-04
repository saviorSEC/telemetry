"""OTLP/HTTP ingest target (OpenTelemetry Protocol over HTTP).

Exercises an OpenTelemetry collector / OTLP ingest endpoint the way the
OpenTelemetry SDKs do: POST JSON-encoded protobuf to the signal paths
``/v1/traces``, ``/v1/metrics`` and ``/v1/logs`` (default OTLP/HTTP port 4318).

The OTLP spec leaves authentication to the deployment (arbitrary headers, e.g.
``OTEL_EXPORTER_OTLP_HEADERS``); a collector that accepts unauthenticated OTLP
is EXPOSED. Success is HTTP 200 with ``partial_success`` unset; 401/403 means
the endpoint required auth (secure); 400 means the payload was rejected.

JSON-protobuf encoding notes (per the OTLP spec): ``traceId``/``spanId`` are
hex strings, enum fields are integers, 64-bit ints are strings.
"""
from __future__ import annotations

import time

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)
from .. import proto

#: default OTLP/HTTP signal paths (the spec allows non-default paths too)
SIGNAL_PATHS = {
    "traces": "/v1/traces",
    "metrics": "/v1/metrics",
    "logs": "/v1/logs",
}


def _now_ns() -> str:
    # OTLP JSON encodes 64-bit timestamps as strings.
    return str(time.time_ns())


def _attr(key: str, value) -> dict:
    """One OTLP KeyValue with a stringValue (the common attribute shape)."""
    return {"key": key, "value": {"stringValue": str(value)}}


class OtlpModule(TargetModule):
    name = "otlp"
    description = "opentelemetry OTLP/HTTP ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("OTLP/HTTP root (real collectors listen on :4318). Signal "
                      "paths /v1/traces|metrics|logs are appended. 'headers' lets "
                      "you probe with/without auth, e.g. "
                      "{\"Authorization\": \"Bearer TEST\"}."),
            "base_url": base_url,
            "signals": ["traces", "metrics", "logs"],
            "encoding": "json",
            "service_name": "hyperject-bas",
            "headers": {},
        }

    # ---- signal builders ---------------------------------------------------
    def _resource(self, mcfg) -> dict:
        return {"attributes": [_attr("service.name",
                                     mcfg.get("service_name", "hyperject-bas"))]}

    def _attributes(self, cfg, variant, index) -> list:
        attrs = [_attr("bas.variant", variant), _attr("bas.index", index)]
        if variant == "large":
            attrs.append(_attr("bas.blob", large_blob(cfg)))
        if variant == "covert":
            field = cfg["techniques"]["covert_field"]["field"]
            attrs.append(_attr(field, covert_marker(cfg)))
        return attrs

    def _traces(self, mcfg, cfg, variant, index) -> dict:
        start = _now_ns()
        return {"resourceSpans": [{
            "resource": self._resource(mcfg),
            "scopeSpans": [{
                "scope": {"name": "hyperject", "version": "1.0"},
                "spans": [{
                    "traceId": sample_hex(32),
                    "spanId": sample_hex(16),
                    "name": f"BAS_{variant}_{index}",
                    "kind": 2,                       # SPAN_KIND_SERVER
                    "startTimeUnixNano": start,
                    "endTimeUnixNano": _now_ns(),
                    "attributes": self._attributes(cfg, variant, index),
                }],
            }],
        }]}

    def _metrics(self, mcfg, cfg, variant, index) -> dict:
        return {"resourceMetrics": [{
            "resource": self._resource(mcfg),
            "scopeMetrics": [{
                "scope": {"name": "hyperject", "version": "1.0"},
                "metrics": [{
                    "name": f"bas.count.{variant}",
                    "unit": "1",
                    "sum": {
                        "aggregationTemporality": 2,  # CUMULATIVE
                        "isMonotonic": True,
                        "dataPoints": [{
                            "asInt": "1",
                            "startTimeUnixNano": _now_ns(),
                            "timeUnixNano": _now_ns(),
                            "attributes": self._attributes(cfg, variant, index),
                        }],
                    },
                }],
            }],
        }]}

    def _logs(self, mcfg, cfg, variant, index) -> dict:
        return {"resourceLogs": [{
            "resource": self._resource(mcfg),
            "scopeLogs": [{
                "scope": {"name": "hyperject", "version": "1.0"},
                "logRecords": [{
                    "timeUnixNano": _now_ns(),
                    "severityNumber": 9,             # INFO
                    "severityText": "INFO",
                    "body": {"stringValue": f"BAS_{variant}_{index}"},
                    "attributes": self._attributes(cfg, variant, index),
                }],
            }],
        }]}

    @staticmethod
    def _check_json(r):
        # OTLP success == 200; a populated partial_success means some items were
        # rejected, so require a clean/empty body when present.
        if r.status_code != 200:
            return False
        try:
            return not (r.json() or {}).get("partialSuccess", {}).get("rejectedSpans")
        except Exception:
            return True

    @staticmethod
    def _check_protobuf(r):
        if r.status_code != 200:
            return False
        try:
            return not proto.decode_export_response(r.content or b"").get("rejected")
        except Exception:
            return True

    def _kwargs(self, encoding, signal, body, headers):
        """Build the request kwargs for the chosen OTLP encoding."""
        if encoding == "protobuf":
            hdrs = {**headers, "Content-Type": "application/x-protobuf"}
            return {"data": proto.encode_signal(signal, body), "headers": hdrs}
        return {"json": body, "headers": {**headers, "Content-Type": "application/json"}}

    def plan(self, mcfg, cfg, variants):
        base = mcfg.get("base_url", "").rstrip("/")
        signals = mcfg.get("signals") or list(SIGNAL_PATHS)
        encoding = "protobuf" if mcfg.get("encoding") == "protobuf" else "json"
        headers = dict(mcfg.get("headers") or {})
        builders = {"traces": self._traces, "metrics": self._metrics,
                    "logs": self._logs}
        check = self._check_protobuf if encoding == "protobuf" else self._check_json

        out = []
        for signal in signals:
            path = SIGNAL_PATHS.get(signal)
            build = builders.get(signal)
            if not path or not build:
                continue
            url = base + path
            for v in variants:
                preps = [Prepared("POST", url,
                                  self._kwargs(encoding, signal,
                                               build(mcfg, cfg, v, i), headers),
                                  check)
                         for i in range(variant_count(v, cfg))]
                out.append((v, f"{url} [{signal}/{encoding}]", preps))
        return out
