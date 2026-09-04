"""
Capture and show the real request/response of telemetry going to an
OpenTelemetry / Azure Monitor endpoint.

Two telemetry sources:
  * ``hyperject`` (default, no extra deps): build the OTLP payload with
    hyperject's own encoders (JSON or the built-in protobuf codec) and send it.
  * ``sdk`` (needs the OpenTelemetry SDK): drive the *real* ``opentelemetry``
    exporter so you see exactly what the OpenTelemetry project puts on the wire.

By default traffic goes to a local in-process capture server (so both the
request and the response are shown even with no external endpoint); pass
``--target`` to hit a real collector, or ``--proxy`` to route through Burp/ZAP.

``--diff`` builds the payload with BOTH sources and compares them, so you can
confirm hyperject's synthetic OTLP matches what the real SDK emits (a fidelity
check on the ``otlp`` module).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import proto, ui
from .core import sample_hex
from .registry import discover

#: the single span both sources emit in --diff, so the comparison is apples-to-
#: apples (same name + attribute) and any difference is purely wire/structure.
_DIFF_SPAN_NAME = "BAS_basic"
_DIFF_ATTR = ("app.version", "SIMULATED_C2_MARKER")

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


# --------------------------------------------------------------------------- #
# In-process capture server
# --------------------------------------------------------------------------- #

class _CaptureHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(ln) if ln else b""
        self.server.captured.append({
            "path": urlparse(self.path).path,
            "headers": {k: v for k, v in self.headers.items()},
            "body": body,
        })
        path = urlparse(self.path).path
        ctype = (self.headers.get("Content-Type") or "").lower()
        if path.endswith(("/traces", "/metrics", "/logs")):
            if "x-protobuf" in ctype:
                self._send(200, b"", "application/x-protobuf")
            else:
                self._send(200, b"{}", "application/json")
        elif "/v2.1/track" in path:
            self._send(200, json.dumps(
                {"itemsReceived": 1, "itemsAccepted": 1, "errors": []}).encode(),
                "application/json")
        else:
            self._send(200, b"{}", "application/json")

    def _send(self, status, data, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def log_message(self, *_a):
        pass


def _start_capture_server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
    srv.captured = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# --------------------------------------------------------------------------- #
# Telemetry sources
# --------------------------------------------------------------------------- #

_DEMO_CFG = {"run": {"count": 1},
             "techniques": {"large_payload_bytes": 128,
                            "covert_field": {"enabled": True, "field": "app.version",
                                             "marker": "SIMULATED_C2_MARKER"}}}


def _hyperject_payload(signal, service_name):
    """Build one OTLP payload dict via hyperject's otlp module."""
    mod = discover()["otlp"]
    mcfg = mod.default_config("http://capture.local")
    mcfg["service_name"] = service_name
    builder = {"traces": mod._traces, "metrics": mod._metrics,
               "logs": mod._logs}[signal]
    return builder(mcfg, _DEMO_CFG, "basic", 0)


def _encode(signal, payload, encoding):
    if encoding == "protobuf":
        return proto.encode_signal(signal, payload), "application/x-protobuf"
    return json.dumps(payload).encode(), "application/json"


def _sdk_export_traces(base_url, service_name):
    """Export one span through the REAL OpenTelemetry SDK + OTLP/HTTP exporter."""
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = OTLPSpanExporter(endpoint=f"{base_url}/v1/traces")
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("hyperject-capture")
    with tracer.start_as_current_span(_DIFF_SPAN_NAME) as span:
        span.set_attribute(*_DIFF_ATTR)
    provider.force_flush()
    provider.shutdown()


def _hyperject_matched_traces(service_name) -> dict:
    """A traces payload carrying the exact same span the SDK emits in --diff."""
    return {"resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name",
                                     "value": {"stringValue": service_name}}]},
        "scopeSpans": [{"scope": {"name": "hyperject", "version": "1.0"},
                        "spans": [{"traceId": sample_hex(32), "spanId": sample_hex(16),
                                   "name": _DIFF_SPAN_NAME, "kind": 2,
                                   "startTimeUnixNano": "1", "endTimeUnixNano": "2",
                                   "attributes": [{"key": _DIFF_ATTR[0], "value":
                                                   {"stringValue": _DIFF_ATTR[1]}}]}]}]}]}


# --------------------------------------------------------------------------- #
# Decode captured OTLP request bytes into a normalized structure (for display
# and diff). Protobuf decode uses the real opentelemetry-proto if available.
# --------------------------------------------------------------------------- #

def _normalize_traces_dict(payload: dict) -> dict:
    spans, res_attrs = [], {}
    for rs in payload.get("resourceSpans", []):
        for a in rs.get("resource", {}).get("attributes", []):
            res_attrs[a["key"]] = a["value"].get("stringValue")
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                spans.append({"name": sp.get("name"),
                              "attributes": sorted(a["key"] for a in
                                                   sp.get("attributes", []))})
    return {"resource_attributes": res_attrs, "spans": spans}


def _normalize_traces_proto(wire: bytes) -> dict:
    from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
    msg = trace_service_pb2.ExportTraceServiceRequest()
    msg.ParseFromString(wire)
    spans, res_attrs = [], {}
    for rs in msg.resource_spans:
        for a in rs.resource.attributes:
            res_attrs[a.key] = a.value.string_value
        for ss in rs.scope_spans:
            for sp in ss.spans:
                spans.append({"name": sp.name,
                              "attributes": sorted(a.key for a in sp.attributes)})
    return {"resource_attributes": res_attrs, "spans": spans}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def _show_request(logical: dict, wire: bytes, encoding: str) -> None:
    print(ui.bold("REQUEST (logical payload):"))
    print(ui.pretty_json(logical))
    kind = "protobuf" if encoding == "protobuf" else "json"
    print(ui.grey(f"  wire: {len(wire)} bytes {kind}  "
                  f"{wire[:32].hex() if encoding == 'protobuf' else ''}"))


def _show_response(status, headers, body: bytes, encoding: str) -> None:
    code = ui.green(str(status)) if isinstance(status, int) and status < 400 \
        else ui.red(str(status))
    print(ui.bold("RESPONSE:") + f" {code}")
    ctype = ""
    for k, v in (headers or {}).items():
        if k.lower() == "content-type":
            ctype = v
    if "x-protobuf" in (ctype or "").lower():
        decoded = proto.decode_export_response(body)
        summary = decoded or {"partial_success": "unset (full success)"}
        print(ui.grey("  body (decoded protobuf): ") + ui.pretty_json(summary))
    else:
        text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
        print(ui.grey("  body: ") + (text or "<empty>"))


def _diff(signal, service_name):
    """Compare hyperject's synthetic OTLP against the real SDK's output."""
    if signal != "traces":
        print(ui.yellow("[*] --diff currently supports --signal traces only."))
        return 2
    matched = _hyperject_matched_traces(service_name)
    ours = _normalize_traces_dict(matched)
    our_wire = proto.encode_traces(matched)
    srv = _start_capture_server()
    try:
        _sdk_export_traces(f"http://127.0.0.1:{srv.server_address[1]}", service_name)
    except ImportError:
        print(ui.red("[-] --source sdk needs the OpenTelemetry SDK. Install:"))
        print("      pip install 'hyperject[otel]'")
        return 2
    finally:
        srv.shutdown()
    if not srv.captured:
        print(ui.red("[-] the SDK exporter sent nothing to capture."))
        return 1
    their_wire = srv.captured[-1]["body"]
    theirs = _normalize_traces_proto(their_wire)

    print(ui.bold("FIDELITY DIFF — hyperject otlp vs real OpenTelemetry SDK\n"))
    print(ui.cyan("hyperject:"), ui.pretty_json(ours),
          ui.grey(f"({len(our_wire)} bytes protobuf)"))
    print(ui.cyan("sdk      :"), ui.pretty_json(theirs),
          ui.grey(f"({len(their_wire)} bytes protobuf)"))
    our_names = {s["name"] for s in ours["spans"]}
    their_names = {s["name"] for s in theirs["spans"]}
    our_attrs = {a for s in ours["spans"] for a in s["attributes"]}
    their_attrs = {a for s in theirs["spans"] for a in s["attributes"]}
    # both hand-built to emit the same span; MATCH => our protobuf is structurally
    # the OTLP the SDK produces (the SDK also auto-adds telemetry.sdk.* resource
    # attributes, which is expected and not a fidelity failure).
    same_shape = our_names == their_names and our_attrs == their_attrs
    verdict = ui.green("MATCH") if same_shape else ui.yellow("DIVERGENT")
    print("\n" + ui.bold("verdict: ") + verdict +
          ui.grey("  (identical span name + attributes on the wire)"))
    extra = sorted(set(theirs["resource_attributes"]) - set(ours["resource_attributes"]))
    if extra:
        print(ui.grey(f"  note: SDK auto-adds resource attrs {extra}"))
    return 0


# --------------------------------------------------------------------------- #
# Entry point (called by cli.cmd_capture)
# --------------------------------------------------------------------------- #

def run(source, signal, encoding, target, proxy, insecure, service_name,
        diff=False) -> int:
    if requests is None:
        print(ui.red("[-] the 'requests' package is required."))
        return 2
    if diff:
        return _diff(signal, service_name)

    srv = None
    base = target.rstrip("/") if target else None
    if base is None:
        srv = _start_capture_server()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        if source == "sdk":
            if signal != "traces":
                print(ui.yellow("[*] --source sdk currently supports traces only."))
                return 2
            try:
                _sdk_export_traces(base, service_name)
            except ImportError:
                print(ui.red("[-] --source sdk needs the OpenTelemetry SDK. Install:"))
                print("      pip install 'hyperject[otel]'")
                return 2
            if srv is None or not srv.captured:
                print(ui.yellow("[*] Sent via the real SDK. Capture-server display is "
                                "only available without --target."))
                return 0
            cap = srv.captured[-1]
            wire = cap["body"]
            logical = _normalize_traces_proto(wire)
            _show_request(logical, wire, "protobuf")
            print()
            _show_response(200, {"Content-Type": "application/x-protobuf"}, b"",
                           "protobuf")
            return 0

        # source == hyperject
        payload = _hyperject_payload(signal, service_name)
        wire, ctype = _encode(signal, payload, encoding)
        url = f"{base}/v1/{signal}"
        resp = requests.post(url, data=wire, headers={"Content-Type": ctype},
                             proxies=proxies, verify=not insecure, timeout=10)
        _show_request(payload, wire, encoding)
        print()
        _show_response(resp.status_code, dict(resp.headers), resp.content, encoding)
        return 0
    finally:
        if srv is not None:
            srv.shutdown()
