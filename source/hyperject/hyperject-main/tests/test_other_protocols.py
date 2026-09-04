"""Tests for the additional protobuf telemetry protocols: the Snappy encoder,
Prometheus Remote Write, Grafana Loki, and Zipkin (protobuf + JSON), plus the
detector classifications for each."""
import json

import pytest

from hyperject import proto, snappy, detector
from hyperject.registry import discover

BASE = "http://127.0.0.1:8080"
TECHNIQUES = {"large_payload_bytes": 64,
              "covert_field": {"enabled": True, "field": "app_version", "marker": "M"}}


def _cfg(name, mcfg, count=3):
    return {"run": {"count": count}, "modules": {name: mcfg}, "techniques": TECHNIQUES}


def _read_varint(buf):
    n = shift = i = 0
    while True:
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n, i
        shift += 7


def _snappy_decompress(data):
    """Real decompress if a snappy lib is present, else None."""
    try:
        import snappy as _s
        return _s.decompress(data)
    except Exception:
        try:
            import cramjam
            return bytes(cramjam.snappy.decompress_raw(data))
        except Exception:
            return None


# --- snappy ------------------------------------------------------------------

def test_snappy_preamble_and_roundtrip():
    for payload in (b"", b"abc", b"q" * 200, bytes(range(256))):
        blob = snappy.compress(payload)
        declared, _ = _read_varint(blob)
        assert declared == len(payload)          # preamble = uncompressed length
        dec = _snappy_decompress(blob)
        if dec is not None:
            assert dec == payload


# --- prometheus remote write -------------------------------------------------

def test_encode_write_request_parseable():
    payload = {"timeseries": [{"labels": [{"name": "__name__", "value": "up"}],
                               "samples": [{"value": 1.0, "timestamp": 1700000000000}]}]}
    wire = proto.encode_write_request(payload)
    fields = list(proto.iter_fields(wire))
    assert fields and fields[0][0] == 1 and fields[0][1] == proto.WIRE_LEN


def test_prometheus_module_snappy_protobuf():
    mod = discover()["prometheus_remote_write"]
    mcfg = mod.default_config(BASE)
    plans = mod.plan(mcfg, _cfg("prometheus_remote_write", mcfg), ("basic",))
    _, endpoint, preps = plans[0]
    assert endpoint.endswith("/api/v1/write")
    kw = preps[0].kwargs
    assert kw["headers"]["Content-Encoding"] == "snappy"
    assert kw["headers"]["Content-Type"] == "application/x-protobuf"
    body = kw["data"]
    declared, _ = _read_varint(body)
    assert declared > 0                          # snappy preamble present
    dec = _snappy_decompress(body)
    if dec is not None:
        # decompressed payload must be a valid WriteRequest (timeseries = field 1)
        assert list(proto.iter_fields(dec))[0][0] == 1


def test_prometheus_covert_label_present():
    mod = discover()["prometheus_remote_write"]
    mcfg = mod.default_config(BASE)
    plans = mod.plan(mcfg, _cfg("prometheus_remote_write", mcfg), ("covert",))
    body = plans[0][2][0].kwargs["data"]
    dec = _snappy_decompress(body)
    if dec is not None:
        assert b"app_version" in dec             # covert label name on the wire


# --- loki --------------------------------------------------------------------

def test_loki_protobuf_and_json():
    mod = discover()["loki"]
    mcfg = mod.default_config(BASE)
    pb = mod.plan(mcfg, _cfg("loki", mcfg), ("basic",))[0][2][0].kwargs
    assert pb["headers"]["Content-Encoding"] == "snappy"
    assert isinstance(pb["data"], bytes)

    mcfg_json = mod.default_config(BASE)
    mcfg_json["encoding"] = "json"
    jp = mod.plan(mcfg_json, _cfg("loki", mcfg_json), ("basic",))[0][2][0].kwargs
    assert "json" in jp
    assert "streams" in jp["json"]
    ts, line = jp["json"]["streams"][0]["values"][0]
    assert isinstance(ts, str)                   # Loki requires string ns timestamps


# --- zipkin ------------------------------------------------------------------

def test_zipkin_protobuf_and_json():
    mod = discover()["zipkin"]
    mcfg = mod.default_config(BASE)          # default json
    jp = mod.plan(mcfg, _cfg("zipkin", mcfg), ("basic",))[0][2][0]
    assert jp.url.endswith("/api/v2/spans")
    assert jp.kwargs["json"][0]["kind"] == "SERVER"

    mcfg_pb = mod.default_config(BASE)
    mcfg_pb["encoding"] = "protobuf"
    pb = mod.plan(mcfg_pb, _cfg("zipkin", mcfg_pb), ("basic",))[0][2][0]
    assert pb.kwargs["headers"]["Content-Type"] == "application/x-protobuf"
    fields = list(proto.iter_fields(pb.kwargs["data"]))
    assert fields[0][0] == 1                      # ListOfSpans.spans = field 1


def test_zipkin_accepts_202():
    mod = discover()["zipkin"]
    mcfg = mod.default_config(BASE)
    check = mod.plan(mcfg, _cfg("zipkin", mcfg), ("basic",))[0][2][0].accept

    class R:
        status_code = 202
    assert check(R()) is True


# --- detector ----------------------------------------------------------------

def test_detector_flags_new_protocols(tmp_path, capsys):
    events = [
        {"ts": "t", "method": "POST", "path": "/api/v1/write", "query": {},
         "client": "1.1.1.1", "headers": {}, "body_len": 20, "body": ""},
        {"ts": "t", "method": "POST", "path": "/loki/api/v1/push", "query": {},
         "client": "1.1.1.1", "headers": {}, "body_len": 20, "body": ""},
        {"ts": "t", "method": "POST", "path": "/api/v2/spans", "query": {},
         "client": "1.1.1.1", "headers": {}, "body_len": 20, "body": ""},
    ]
    log = tmp_path / "ingest.log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in events))
    detector.detect(str(log))
    out = capsys.readouterr().out
    assert "REMOTE_WRITE_INGEST" in out
    assert "LOKI_INGEST" in out
    assert "ZIPKIN_INGEST" in out
