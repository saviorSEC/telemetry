"""Inject fixed headers into every request (e.g. auth tokens, correlation tags).

    {"name": "extra_headers", "options": {"headers": {"Authorization": "Bearer X"}}}
"""
from __future__ import annotations

from ..mwbase import Middleware


class ExtraHeadersMiddleware(Middleware):
    name = "extra_headers"
    description = "add fixed headers to every request (auth, tags, correlation ids)"

    def before_request(self, ctx) -> None:
        ctx.request.setdefault("headers", {})
        ctx.request["headers"].update(self.options.get("headers", {}))
