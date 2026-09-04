"""
Mock telemetry collector — a safe, local stand-in for the ingest APIs that
hyperject exercises. Speaks the same response contracts and logs every request
to JSONL for the detector to consume. Standard library only.
"""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_LOG_PATH = "ingest.log.jsonl"


def _log_event(handler: "Handler", body: bytes) -> None:
    parsed = urlparse(handler.path)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": handler.command,
        "path": parsed.path,
        "query": parse_qs(parsed.query),
        "client": handler.client_address[0],
        "headers": {k: v for k, v in handler.headers.items()},
        "body_len": len(body),
        "body": body.decode("utf-8", "replace")[:100000],
    }
    with open(_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


class Handler(BaseHTTPRequestHandler):
    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def _respond(self, status: int, payload=None, extra_headers=None) -> None:
        self.send_response(status)
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        if payload is not None:
            data = json.dumps(payload).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.end_headers()

    def _respond_bytes(self, status: int, data: bytes, content_type: str,
                       extra_headers=None) -> None:
        self.send_response(status)
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def do_POST(self) -> None:
        body = self._read_body()
        _log_event(self, body)
        path = urlparse(self.path).path
        if path.endswith("/checkin"):
            self._respond(200, {"stats_ok": True})
        elif path.endswith("/v2.1/track"):
            self._respond(200, {"itemsReceived": 1, "itemsAccepted": 1, "errors": []})
        elif "/OneCollector/" in path:
            self._respond(204)
        elif path.startswith("/v1/") and path.split("/")[-1] in (
                "traces", "metrics", "logs"):
            # OTLP/HTTP success: 200 with an empty (full-success) body, echoing
            # the request's protobuf/JSON encoding.
            if "application/x-protobuf" in (self.headers.get("Content-Type") or ""):
                self._respond_bytes(200, b"", "application/x-protobuf")
            else:
                self._respond(200, {})
        elif "/QuickPulseService.svc/" in path:
            # Live Metrics / QuickPulse: signal subscription via a response header.
            self._respond(200, {}, extra_headers={"x-ms-qps-subscribed": "true"})
        elif path.endswith("/api/v1/write"):
            self._respond(204)                       # Prometheus remote write
        elif path.endswith("/loki/api/v1/push"):
            self._respond(204)                       # Grafana Loki push
        elif path.endswith("/api/v2/spans"):
            self._respond(202)                       # Zipkin collector
        elif path.endswith("/kv"):
            self._respond(200, {"ok": True})
        else:
            self._respond(200, {"ok": True})

    def do_PUT(self) -> None:
        body = self._read_body()
        _log_event(self, body)
        path = urlparse(self.path).path
        if "/webtests/" in path:
            # ARM WebTests Create-Or-Update success.
            self._respond(200, {"properties": {"provisioningState": "Succeeded"}})
        else:
            self._respond(200, {"ok": True})

    def do_GET(self) -> None:
        _log_event(self, b"")
        self._respond(200, {"ok": True})

    def log_message(self, *_a) -> None:  # silence default stderr noise
        pass


def serve(host: str = "127.0.0.1", port: int = 8080,
          log_path: str = "ingest.log.jsonl") -> None:
    global _LOG_PATH
    _LOG_PATH = log_path
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[*] mock collector listening on http://{host}:{port}")
    print(f"[*] logging ingested requests to {log_path}")
    print("[*] Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] stopped.")
