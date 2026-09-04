"""
Minimal, dependency-free Protocol Buffers codec for OTLP.

Real OpenTelemetry collectors and the OTLP/gRPC endpoint speak binary protobuf,
not JSON. Rather than pull in the ~10 MB ``protobuf`` + ``opentelemetry-proto``
stack just to emit a few message shapes, this module hand-encodes the exact OTLP
messages hyperject builds (the same dicts the JSON path uses) straight to
protobuf wire bytes, and decodes the small Export*ServiceResponse / Status
messages that come back.

Wire format reference: https://protobuf.dev/programming-guides/encoding/
OTLP field numbers: opentelemetry/proto/{trace,metrics,logs,common,resource}/v1.

Only the field numbers hyperject actually populates are implemented; unknown
keys in the input dicts are ignored. This is intentionally a producer for our
own payloads, not a general-purpose protobuf library.
"""
from __future__ import annotations

import struct

# --------------------------------------------------------------------------- #
# Wire-level primitives
# --------------------------------------------------------------------------- #

WIRE_VARINT = 0
WIRE_I64 = 1
WIRE_LEN = 2
WIRE_I32 = 5

_U64 = (1 << 64) - 1


def encode_varint(n: int) -> bytes:
    """Base-128 varint of an unsigned integer (negatives are masked to 64 bits)."""
    n &= _U64
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return encode_varint((field << 3) | wire)


def _f_varint(field: int, n: int) -> bytes:
    return _tag(field, WIRE_VARINT) + encode_varint(n)


def _f_fixed64(field: int, n: int) -> bytes:
    return _tag(field, WIRE_I64) + struct.pack("<Q", n & _U64)


def _f_sfixed64(field: int, n: int) -> bytes:
    return _tag(field, WIRE_I64) + struct.pack("<q", n)


def _f_double(field: int, x: float) -> bytes:
    return _tag(field, WIRE_I64) + struct.pack("<d", x)


def _f_len(field: int, data: bytes) -> bytes:
    return _tag(field, WIRE_LEN) + encode_varint(len(data)) + data


def _f_str(field: int, s: str) -> bytes:
    return _f_len(field, s.encode("utf-8"))


# --------------------------------------------------------------------------- #
# OTLP common: AnyValue / KeyValue / Resource / InstrumentationScope
# --------------------------------------------------------------------------- #

def _any_value(v: dict) -> bytes:
    if "stringValue" in v:
        return _f_str(1, str(v["stringValue"]))
    if "boolValue" in v:
        return _f_varint(2, 1 if v["boolValue"] else 0)
    if "intValue" in v:
        return _f_varint(3, int(v["intValue"]))
    if "doubleValue" in v:
        return _f_double(4, float(v["doubleValue"]))
    if "bytesValue" in v:
        return _f_len(7, bytes(v["bytesValue"]))
    return b""


def _key_value(kv: dict) -> bytes:
    return _f_str(1, kv.get("key", "")) + _f_len(2, _any_value(kv.get("value", {})))


def _kvs(field: int, attrs) -> bytes:
    return b"".join(_f_len(field, _key_value(kv)) for kv in (attrs or []))


def _resource(res: dict) -> bytes:
    return _kvs(1, res.get("attributes", []))


def _scope(sc: dict) -> bytes:
    out = b""
    if sc.get("name"):
        out += _f_str(1, sc["name"])
    if sc.get("version"):
        out += _f_str(2, sc["version"])
    return out


# --------------------------------------------------------------------------- #
# Traces
# --------------------------------------------------------------------------- #

def _span(s: dict) -> bytes:
    out = b""
    out += _f_len(1, bytes.fromhex(s["traceId"]))          # trace_id
    out += _f_len(2, bytes.fromhex(s["spanId"]))           # span_id
    out += _f_str(5, s.get("name", ""))                    # name
    out += _f_varint(6, int(s.get("kind", 0)))             # kind
    out += _f_fixed64(7, int(s.get("startTimeUnixNano", 0)))
    out += _f_fixed64(8, int(s.get("endTimeUnixNano", 0)))
    out += _kvs(9, s.get("attributes", []))                # attributes
    return out


def _scope_spans(ss: dict) -> bytes:
    out = _f_len(1, _scope(ss.get("scope", {})))
    out += b"".join(_f_len(2, _span(s)) for s in ss.get("spans", []))
    return out


def _resource_spans(rs: dict) -> bytes:
    out = _f_len(1, _resource(rs.get("resource", {})))
    out += b"".join(_f_len(2, _scope_spans(ss)) for ss in rs.get("scopeSpans", []))
    return out


def encode_traces(payload: dict) -> bytes:
    """ExportTraceServiceRequest from a {"resourceSpans": [...]} dict."""
    return b"".join(_f_len(1, _resource_spans(rs))
                    for rs in payload.get("resourceSpans", []))


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def _number_dp(dp: dict) -> bytes:
    out = _kvs(7, dp.get("attributes", []))                # attributes
    out += _f_fixed64(2, int(dp.get("startTimeUnixNano", 0)))
    out += _f_fixed64(3, int(dp.get("timeUnixNano", 0)))
    if "asInt" in dp:
        out += _f_sfixed64(6, int(dp["asInt"]))
    elif "asDouble" in dp:
        out += _f_double(4, float(dp["asDouble"]))
    return out


def _sum(sm: dict) -> bytes:
    out = b"".join(_f_len(1, _number_dp(dp)) for dp in sm.get("dataPoints", []))
    out += _f_varint(2, int(sm.get("aggregationTemporality", 0)))
    out += _f_varint(3, 1 if sm.get("isMonotonic") else 0)
    return out


def _gauge(g: dict) -> bytes:
    return b"".join(_f_len(1, _number_dp(dp)) for dp in g.get("dataPoints", []))


def _metric(m: dict) -> bytes:
    out = _f_str(1, m.get("name", ""))
    if m.get("description"):
        out += _f_str(2, m["description"])
    if m.get("unit"):
        out += _f_str(3, m["unit"])
    if "gauge" in m:
        out += _f_len(5, _gauge(m["gauge"]))
    if "sum" in m:
        out += _f_len(7, _sum(m["sum"]))
    return out


def _scope_metrics(sm: dict) -> bytes:
    out = _f_len(1, _scope(sm.get("scope", {})))
    out += b"".join(_f_len(2, _metric(m)) for m in sm.get("metrics", []))
    return out


def _resource_metrics(rm: dict) -> bytes:
    out = _f_len(1, _resource(rm.get("resource", {})))
    out += b"".join(_f_len(2, _scope_metrics(sm)) for sm in rm.get("scopeMetrics", []))
    return out


def encode_metrics(payload: dict) -> bytes:
    """ExportMetricsServiceRequest from a {"resourceMetrics": [...]} dict."""
    return b"".join(_f_len(1, _resource_metrics(rm))
                    for rm in payload.get("resourceMetrics", []))


# --------------------------------------------------------------------------- #
# Logs
# --------------------------------------------------------------------------- #

def _log_record(lr: dict) -> bytes:
    out = _f_fixed64(1, int(lr.get("timeUnixNano", 0)))
    if lr.get("severityNumber"):
        out += _f_varint(2, int(lr["severityNumber"]))
    if lr.get("severityText"):
        out += _f_str(3, lr["severityText"])
    if "body" in lr:
        out += _f_len(5, _any_value(lr["body"]))
    out += _kvs(6, lr.get("attributes", []))
    return out


def _scope_logs(sl: dict) -> bytes:
    out = _f_len(1, _scope(sl.get("scope", {})))
    out += b"".join(_f_len(2, _log_record(lr)) for lr in sl.get("logRecords", []))
    return out


def _resource_logs(rl: dict) -> bytes:
    out = _f_len(1, _resource(rl.get("resource", {})))
    out += b"".join(_f_len(2, _scope_logs(sl)) for sl in rl.get("scopeLogs", []))
    return out


def encode_logs(payload: dict) -> bytes:
    """ExportLogsServiceRequest from a {"resourceLogs": [...]} dict."""
    return b"".join(_f_len(1, _resource_logs(rl))
                    for rl in payload.get("resourceLogs", []))


#: signal name -> (encoder, OTLP/gRPC full method path)
ENCODERS = {
    "traces": (encode_traces,
               "/opentelemetry.proto.collector.trace.v1.TraceService/Export"),
    "metrics": (encode_metrics,
                "/opentelemetry.proto.collector.metrics.v1.MetricsService/Export"),
    "logs": (encode_logs,
             "/opentelemetry.proto.collector.logs.v1.LogsService/Export"),
}


def encode_signal(signal: str, payload: dict) -> bytes:
    enc, _ = ENCODERS[signal]
    return enc(payload)


# --------------------------------------------------------------------------- #
# Prometheus Remote Write (prometheus.WriteRequest)
#   WriteRequest { repeated TimeSeries timeseries = 1 }
#   TimeSeries   { repeated Label labels = 1; repeated Sample samples = 2 }
#   Label        { string name = 1; string value = 2 }
#   Sample       { double value = 1; int64 timestamp = 2 }
# --------------------------------------------------------------------------- #

def _pw_label(lab: dict) -> bytes:
    return _f_str(1, lab.get("name", "")) + _f_str(2, lab.get("value", ""))


def _pw_sample(s: dict) -> bytes:
    return _f_double(1, float(s.get("value", 0))) + _f_varint(2, int(s.get("timestamp", 0)))


def _pw_timeseries(ts: dict) -> bytes:
    out = b"".join(_f_len(1, _pw_label(l)) for l in ts.get("labels", []))
    out += b"".join(_f_len(2, _pw_sample(s)) for s in ts.get("samples", []))
    return out


def encode_write_request(payload: dict) -> bytes:
    """Prometheus remote-write WriteRequest from {"timeseries": [...]}."""
    return b"".join(_f_len(1, _pw_timeseries(ts))
                    for ts in payload.get("timeseries", []))


# --------------------------------------------------------------------------- #
# Loki push (logproto.PushRequest)
#   PushRequest   { repeated StreamAdapter streams = 1 }
#   StreamAdapter { string labels = 1; repeated EntryAdapter entries = 2 }
#   EntryAdapter  { Timestamp timestamp = 1; string line = 2 }
#   Timestamp     { int64 seconds = 1; int32 nanos = 2 }
# --------------------------------------------------------------------------- #

def _loki_timestamp(seconds: int, nanos: int) -> bytes:
    return _f_varint(1, int(seconds)) + _f_varint(2, int(nanos))


def _loki_entry(e: dict) -> bytes:
    out = _f_len(1, _loki_timestamp(e.get("seconds", 0), e.get("nanos", 0)))
    out += _f_str(2, e.get("line", ""))
    return out


def _loki_stream(s: dict) -> bytes:
    out = _f_str(1, s.get("labels", ""))
    out += b"".join(_f_len(2, _loki_entry(e)) for e in s.get("entries", []))
    return out


def encode_loki_push(payload: dict) -> bytes:
    """Loki logproto PushRequest from {"streams": [...]}."""
    return b"".join(_f_len(1, _loki_stream(s)) for s in payload.get("streams", []))


# --------------------------------------------------------------------------- #
# Zipkin v2 (zipkin.proto3)
#   ListOfSpans { repeated Span spans = 1 }
#   Span { bytes trace_id=1; bytes id=3; Kind kind=4; string name=5;
#          fixed64 timestamp=6; uint64 duration=7; Endpoint local_endpoint=8;
#          map<string,string> tags=11 }
#   Endpoint { string service_name = 1 }
# --------------------------------------------------------------------------- #

def _zipkin_endpoint(e: dict) -> bytes:
    return _f_str(1, e.get("serviceName", "")) if e.get("serviceName") else b""


def _zipkin_tag(key: str, value: str) -> bytes:
    return _f_str(1, key) + _f_str(2, value)


def _zipkin_span(s: dict) -> bytes:
    out = _f_len(1, bytes.fromhex(s["traceId"]))
    out += _f_len(3, bytes.fromhex(s["id"]))
    if s.get("kind"):
        out += _f_varint(4, int(s["kind"]))
    out += _f_str(5, s.get("name", ""))
    if s.get("timestamp"):
        out += _f_fixed64(6, int(s["timestamp"]))
    if s.get("duration"):
        out += _f_varint(7, int(s["duration"]))
    if s.get("localEndpoint"):
        out += _f_len(8, _zipkin_endpoint(s["localEndpoint"]))
    for k, v in (s.get("tags") or {}).items():
        out += _f_len(11, _zipkin_tag(k, v))
    return out


def encode_zipkin(spans: list) -> bytes:
    """Zipkin proto3 ListOfSpans from a list of span dicts."""
    return b"".join(_f_len(1, _zipkin_span(s)) for s in spans)


# --------------------------------------------------------------------------- #
# Decoding (responses only)
# --------------------------------------------------------------------------- #

def _read_varint(buf: bytes, i: int):
    shift = 0
    result = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7


def iter_fields(buf: bytes):
    """Yield (field_number, wire_type, raw_value) for a protobuf message. Value is
    an int for varint, or raw bytes for the length/fixed wire types."""
    i, n = 0, len(buf)
    while i < n:
        key, i = _read_varint(buf, i)
        field, wire = key >> 3, key & 7
        if wire == WIRE_VARINT:
            val, i = _read_varint(buf, i)
        elif wire == WIRE_I64:
            val, i = buf[i:i + 8], i + 8
        elif wire == WIRE_LEN:
            ln, i = _read_varint(buf, i)
            val, i = buf[i:i + ln], i + ln
        elif wire == WIRE_I32:
            val, i = buf[i:i + 4], i + 4
        else:
            return
        yield field, wire, val


def decode_export_response(data: bytes) -> dict:
    """Decode an OTLP Export*ServiceResponse. Returns {} on full success, or
    {"rejected": N, "error_message": str} when partial_success is populated."""
    out: dict = {}
    if not data:
        return out
    for field, wire, val in iter_fields(data):
        if field == 1 and wire == WIRE_LEN:            # partial_success
            for f2, w2, v2 in iter_fields(val):
                if f2 == 1 and w2 == WIRE_VARINT:
                    out["rejected"] = v2
                elif f2 == 2 and w2 == WIRE_LEN:
                    out["error_message"] = v2.decode("utf-8", "replace")
    return out


def decode_status(data: bytes) -> dict:
    """Decode a google.rpc.Status (OTLP 4xx/5xx error body)."""
    out: dict = {}
    for field, wire, val in iter_fields(data or b""):
        if field == 1 and wire == WIRE_VARINT:
            out["code"] = val
        elif field == 2 and wire == WIRE_LEN:
            out["message"] = val.decode("utf-8", "replace")
    return out
