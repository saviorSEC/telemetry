"""AWS CloudWatch Logs (PutLogEvents) ingest target.

CloudWatch Logs ingests events at ``POST /`` on ``logs.<region>.amazonaws.com``
using the AWS JSON 1.1 protocol (``X-Amz-Target: Logs_20140328.PutLogEvents``)
authenticated with **AWS Signature Version 4**. This module computes the REAL
SigV4 signature the AWS SDK computes (canonical request -> string-to-sign ->
derived signing key), so the request is wire-accurate against a live endpoint; a
target that accepts it is EXPOSED. Success is ``200 {"nextSequenceToken": ...}``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    sample_hex)

_TARGET = "Logs_20140328.PutLogEvents"
_CONTENT_TYPE = "application/x-amz-json-1.1"
_ALGORITHM = "AWS4-HMAC-SHA256"


class CloudwatchLogsModule(TargetModule):
    name = "cloudwatch_logs"
    description = "aws cloudwatch logs PutLogEvents (SigV4)"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("AWS CloudWatch Logs PutLogEvents (real: logs.<region>."
                      "amazonaws.com, AWS JSON 1.1 + SigV4). Fill access_key/"
                      "secret_key with credentials YOU own; the SigV4 signature is "
                      "computed for real, so a secured endpoint rejects a bad one."),
            "endpoint": base_url + "/",
            "region": "us-east-1",
            "access_key": "AKIA" + sample_hex(8).upper() + "LAB0000",
            "secret_key": sample_hex(20),
            "log_group": "/hyperject/bas",
            "log_stream": "hyperject-bas",
        }

    def _message(self, cfg, variant, index) -> str:
        msg = f"BAS event {variant} {index}"
        if variant == "large":
            msg += " " + large_blob(cfg)
        if variant == "covert":
            msg += " " + covert_marker(cfg)
        return msg

    def _body(self, mcfg, cfg, variant, index) -> bytes:
        event = {"timestamp": int(time.time() * 1000),
                 "message": self._message(cfg, variant, index)}
        payload = {"logGroupName": mcfg.get("log_group", "/hyperject/bas"),
                   "logStreamName": mcfg.get("log_stream", "hyperject-bas"),
                   "logEvents": [event]}
        return json.dumps(payload).encode("utf-8")

    # -- AWS Signature Version 4 --------------------------------------------- #
    @staticmethod
    def _sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _signing_key(self, secret: str, date_stamp: str, region: str,
                     service: str) -> bytes:
        k_date = self._sign(("AWS4" + secret).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, region)
        k_service = self._sign(k_region, service)
        return self._sign(k_service, "aws4_request")

    def _headers(self, mcfg, host: str, body: bytes) -> dict:
        region = mcfg.get("region", "us-east-1")
        service = "logs"
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        # 1) canonical request
        canonical_headers = (
            f"content-type:{_CONTENT_TYPE}\n"
            f"host:{host}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:{_TARGET}\n")
        signed_headers = "content-type;host;x-amz-date;x-amz-target"
        payload_hash = hashlib.sha256(body).hexdigest()
        canonical_request = (
            f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}")

        # 2) string to sign
        scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"{_ALGORITHM}\n{amz_date}\n{scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}")

        # 3) signature
        signing_key = self._signing_key(
            mcfg.get("secret_key", ""), date_stamp, region, service)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # 4) authorization header
        authorization = (
            f"{_ALGORITHM} Credential={mcfg.get('access_key', '')}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}")
        return {"Content-Type": _CONTENT_TYPE, "X-Amz-Target": _TARGET,
                "X-Amz-Date": amz_date, "Authorization": authorization}

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        host = urlparse(endpoint).netloc

        def check(r):
            return r.status_code == 200

        def make(v, i) -> Prepared:
            body = self._body(mcfg, cfg, v, i)
            headers = self._headers(mcfg, host, body)
            return Prepared("POST", endpoint,
                            {"data": body, "headers": headers}, check)

        out = []
        for v in variants:
            preps = [make(v, i) for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
