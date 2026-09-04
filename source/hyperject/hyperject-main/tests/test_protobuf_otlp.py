"""Tests for the OTLP protobuf codec, protobuf transport on the otlp module,
Live Metrics / QuickPulse, and the capture tool's zero-dependency path."""
import json

import pytest

from hyperject import proto, core, capture
from hyperject.transcript import Transcript, Exchange
from hyperject.registry import discover

BASE = "http://127.0.0.1:8080"
TECHNIQUES = {"large_payload_bytes": 128,
              "covert_field": {"enabled": True, "field": "app.version", "marker": "M"}}


def _cfg(name, mcfg, count=3):
    return {"run": {"count": count}, "modules": {name: mcfg}, "techniques": TECHNIQUES}


# --- protobuf codec ----------------------------------------------------------

def test_varint_roundtrip():
    for n in (0, 1, 127, 128, 300, 2 ** 32, 2 ** 63):
        buf = proto.encode_varint(n)
        got, i = proto._read_varint(buf, 0)
        assert got == n and i == len(buf)


def test_encode_traces_is_parseable_protobuf():
    payload = {"resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name",
                                     "value": {"stringValue": "svc"}}]},
        "scopeSpans": [{"scope": {"name": "s", "version": "1"},
                        "spans": [{"traceId": "0" * 32, "spanId": "1" * 16,
                                   "name": "op", "kind": 2,
                                   "startTimeUnixNano": "1", "endTimeUnixNano": "2",
                                   "attributes": [{"key": "k",
                                                   "value": {"stringValue": "v"}}]}]}]}]}
    wire = proto.encode_traces(payload)
    assert isinstance(wire, bytes) and wire
    # re-parse the top-level structure with the codec's own reader
    fields = list(proto.iter_fields(wire))
    assert fields and fields[0][0] == 1        # resource_spans = field 1
    assert fields[0][1] == proto.WIRE_LEN


def test_decode_export_response_partial_success():
    inner = proto._f_varint(1, 5) + proto._f_str(2, "bad batch")
    resp = proto._f_len(1, inner)
    out = proto.decode_export_response(resp)
    assert out == {"rejected": 5, "error_message": "bad batch"}
    assert proto.decode_export_response(b"") == {}


def test_encode_metrics_and_logs_nonempty():
    m = {"resourceMetrics": [{"resource": {}, "scopeMetrics": [{"scope": {},
         "metrics": [{"name": "c", "sum": {"aggregationTemporality": 2,
          "isMonotonic": True, "dataPoints": [{"asInt": "1", "timeUnixNano": "1",
          "startTimeUnixNano": "1", "attributes": []}]}}]}]}]}
    log = {"resourceLogs": [{"resource": {}, "scopeLogs": [{"scope": {},
           "logRecords": [{"timeUnixNano": "1", "severityNumber": 9,
            "severityText": "INFO", "body": {"stringValue": "hi"},
            "attributes": []}]}]}]}
    assert proto.encode_metrics(m)
    assert proto.encode_logs(log)


# --- otlp module protobuf transport -----------------------------------------

def test_otlp_protobuf_sends_bytes_with_right_content_type():
    mod = discover()["otlp"]
    mcfg = mod.default_config(BASE)
    mcfg["encoding"] = "protobuf"
    mcfg["signals"] = ["traces"]
    plans = mod.plan(mcfg, _cfg("otlp", mcfg), ("basic",))
    _, target, preps = plans[0]
    assert target.endswith("[traces/protobuf]")
    kw = preps[0].kwargs
    assert isinstance(kw["data"], bytes) and kw["data"]
    assert kw["headers"]["Content-Type"] == "application/x-protobuf"
    assert "json" not in kw


class _FakeResp:
    def __init__(self, status, content=b"", body="{}"):
        self.status_code = status
        self.content = content
        self._body = body

    def json(self):
        return json.loads(self._body)


def test_otlp_protobuf_check_predicate():
    mod = discover()["otlp"]
    assert mod._check_protobuf(_FakeResp(200, content=b"")) is True
    rejected = proto._f_len(1, proto._f_varint(1, 3))
    assert mod._check_protobuf(_FakeResp(200, content=rejected)) is False
    assert mod._check_protobuf(_FakeResp(401)) is False


# --- connection-string Live Metrics ------------------------------------------

def test_connection_string_live_target():
    ikey, base = core.connection_string_live_target(
        "InstrumentationKey=abc;LiveEndpoint=https://live.example.com/")
    assert ikey == "abc" and base == "https://live.example.com"
    _, derived = core.connection_string_live_target(
        "InstrumentationKey=abc;EndpointSuffix=ai.contoso.com")
    assert derived == "https://live.ai.contoso.com"


def test_live_metrics_plan_hits_quickpulse():
    mod = discover()["live_metrics"]
    mcfg = mod.default_config(BASE)
    plans = mod.plan(mcfg, _cfg("live_metrics", mcfg), ("basic",))
    urls = [preps[0].url for _, _, preps in plans]
    assert any(u.endswith("/QuickPulseService.svc/ping") for u in urls)
    assert any(u.endswith("/QuickPulseService.svc/post") for u in urls)
    ping = [p for _, _, preps in plans for p in preps
            if p.url.endswith("/ping")][0]
    assert "ikey" in ping.kwargs["params"]
    assert any(h.lower().startswith("x-ms-qps-") for h in ping.kwargs["headers"])


# --- capture tool (zero-dep hyperject source, in-process server) -------------

def test_capture_hyperject_protobuf_roundtrip(capsys):
    rc = capture.run(source="hyperject", signal="traces", encoding="protobuf",
                     target=None, proxy=None, insecure=False,
                     service_name="t", diff=False)
    out = capsys.readouterr().out
    assert rc == 0
    assert "REQUEST" in out and "RESPONSE" in out
    assert "protobuf" in out and "200" in out


def test_capture_hyperject_json_roundtrip(capsys):
    rc = capture.run(source="hyperject", signal="logs", encoding="json",
                     target=None, proxy=None, insecure=False,
                     service_name="t", diff=False)
    assert rc == 0
    assert "RESPONSE" in capsys.readouterr().out


def test_capture_diff_matches_real_sdk(capsys):
    pytest.importorskip("opentelemetry.sdk")
    pytest.importorskip("opentelemetry.exporter.otlp.proto.http")
    rc = capture.run(source="hyperject", signal="traces", encoding="protobuf",
                     target=None, proxy=None, insecure=False,
                     service_name="fidelity", diff=True)
    out = capsys.readouterr().out
    assert rc == 0
    # our hand-rolled protobuf must carry the same span the real SDK emits
    assert "MATCH" in out


# --- transcript renders binary (protobuf) request bodies ---------------------

def test_transcript_sanitizes_binary_body():
    tr = Transcript()
    tr.add(Exchange("otlp", "basic",
                    {"method": "POST", "url": "http://x/v1/traces",
                     "headers": {"Content-Type": "application/x-protobuf"},
                     "body": b"\x0a\x0b\x0c\xff"},
                    {"status": 200, "body": ""}))
    rendered = tr.render("har")            # must not raise on bytes
    assert "base64" in rendered
    dicts = tr.as_dicts()
    assert dicts[0]["request"]["body"]["_encoding"] == "binary"
    assert dicts[0]["request"]["body"]["bytes"] == 4
