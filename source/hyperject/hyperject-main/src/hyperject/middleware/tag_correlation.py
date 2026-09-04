"""Tag every request with a correlation id header so you can find this run's
traffic in the endpoint/proxy logs you are reviewing.

    {"name": "tag_correlation", "options": {"header": "X-BAS-Run", "value": "run-42"}}
"""
from __future__ import annotations

from ..mwbase import Middleware


class TagCorrelationMiddleware(Middleware):
    name = "tag_correlation"
    description = "stamp a correlation-id header on every request for log review"

    def before_request(self, ctx) -> None:
        header = self.options.get("header", "X-BAS-Correlation")
        value = self.options.get("value", "hyperject")
        ctx.request.setdefault("headers", {})
        ctx.request["headers"][header] = value
