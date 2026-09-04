"""
Request/response transcript: a reviewable record of every exchange the tool has
with an endpoint, plus exporters (json, jsonl, HAR 1.2, and colorized pretty).
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field, asdict

from . import ui

FORMATS = ("json", "jsonl", "har", "pretty")


def _sanitize(obj):
    """Make a value JSON-renderable. Binary bodies (e.g. protobuf OTLP payloads)
    become a self-describing marker with the base64 of the wire bytes, so they
    survive json/jsonl/har/pretty export instead of crashing or printing b'...'."""
    if isinstance(obj, (bytes, bytearray)):
        return {"_encoding": "binary", "bytes": len(obj),
                "base64": base64.b64encode(bytes(obj)).decode("ascii")}
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


@dataclass
class Exchange:
    module: str
    technique: str
    request: dict            # {method, url, params, headers, body}
    response: dict = field(default_factory=dict)   # {status, headers, body, elapsed_ms}
    error: str = ""


def _redact(obj, keys):
    """Recursively mask values whose key matches (case-insensitive)."""
    if not keys:
        return obj
    low = {k.lower() for k in keys}
    if isinstance(obj, dict):
        return {k: ("***REDACTED***" if k.lower() in low else _redact(v, keys))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, keys) for v in obj]
    return obj


class Transcript:
    def __init__(self, redact=None):
        self.exchanges: list[Exchange] = []
        self.redact = redact or []

    def add(self, ex: Exchange) -> None:
        self.exchanges.append(ex)

    def __len__(self):
        return len(self.exchanges)

    # -- views --------------------------------------------------------------
    def as_dicts(self) -> list:
        out = []
        for ex in self.exchanges:
            d = asdict(ex)
            d["request"] = _redact(_sanitize(d["request"]), self.redact)
            d["response"] = _redact(_sanitize(d["response"]), self.redact)
            out.append(d)
        return out

    def responses_only(self) -> list:
        return [{"method": ex.request.get("method"), "url": ex.request.get("url"),
                 "status": ex.response.get("status"),
                 "response": ex.response.get("body", "")}
                for ex in self.exchanges]

    # -- exporters ----------------------------------------------------------
    def render(self, fmt: str) -> str:
        if fmt == "json":
            return json.dumps(self.as_dicts(), indent=2, default=str)
        if fmt == "jsonl":
            return "".join(json.dumps(d, default=str) + "\n" for d in self.as_dicts())
        if fmt == "har":
            return json.dumps(self._to_har(), indent=2, default=str)
        if fmt == "pretty":
            return self._to_pretty()
        raise ValueError(f"unknown format: {fmt} (choose from {', '.join(FORMATS)})")

    def save(self, path: str, fmt: str = "json") -> None:
        with open(path, "w") as f:
            f.write(self.render(fmt))

    def _to_har(self) -> dict:
        entries = []
        for ex in self.as_dicts():
            req, resp = ex["request"], ex["response"]
            headers = [{"name": k, "value": str(v)}
                       for k, v in (req.get("headers") or {}).items()]
            query = [{"name": k, "value": str(v)}
                     for k, v in (req.get("params") or {}).items()]
            body = req.get("body")
            post = None
            if body is not None:
                text = body if isinstance(body, str) else json.dumps(body, default=str)
                post = {"mimeType": "application/json", "text": text}
            entries.append({
                "request": {
                    "method": req.get("method", ""), "url": req.get("url", ""),
                    "httpVersion": "HTTP/1.1", "headers": headers,
                    "queryString": query, "postData": post,
                    "headersSize": -1, "bodySize": -1,
                },
                "response": {
                    "status": resp.get("status", 0), "statusText": "",
                    "httpVersion": "HTTP/1.1", "headers": [],
                    "content": {"mimeType": "application/json",
                                "text": resp.get("body", "")},
                    "redirectURL": "", "headersSize": -1, "bodySize": -1,
                },
                "cache": {}, "timings": {"send": 0, "wait": resp.get("elapsed_ms", 0),
                                         "receive": 0},
                "comment": f"{ex['module']}/{ex['technique']}",
            })
        return {"log": {"version": "1.2",
                        "creator": {"name": "hyperject", "version": "0.8.0"},
                        "entries": entries}}

    def _to_pretty(self) -> str:
        lines = []
        for ex in self.as_dicts():
            req, resp = ex["request"], ex["response"]
            status = resp.get("status")
            ok = isinstance(status, int) and status < 400
            arrow = ui.paint("-->", "grey")
            head = (ui.paint(f"{ex['module']}/{ex['technique']}", "bold") + "  " +
                    ui.paint(req.get("method", ""), "yellow") + " " +
                    ui.cyan(req.get("url", "")))
            lines.append(head)
            if req.get("params"):
                lines.append(f"  {arrow} params  " + ui.pretty_json(req["params"]))
            if req.get("headers"):
                lines.append(f"  {arrow} headers " + ui.pretty_json(req["headers"]))
            if req.get("body") is not None:
                lines.append(f"  {arrow} body    " + ui.pretty_json(req["body"]))
            code_txt = str(status)
            code = ui.green(code_txt) if ok else ui.red(code_txt)
            elapsed = resp.get("elapsed_ms")
            suffix = ui.grey(f"  ({elapsed} ms)") if elapsed is not None else ""
            if ex.get("error"):
                lines.append("  " + ui.red(f"<-- error: {ex['error']}"))
            else:
                lines.append("  " + ui.paint("<--", "grey") + f" {code}{suffix}")
                if resp.get("body"):
                    lines.append("      " + ui.pretty_json(resp["body"]))
            lines.append("")
        return "\n".join(lines)
