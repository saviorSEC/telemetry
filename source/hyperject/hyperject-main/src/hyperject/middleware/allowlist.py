"""Safety middleware: block any request whose host is not on the allowlist,
answering with a synthetic BLOCKED response instead of hitting the network.

    {"name": "allowlist", "options": {"hosts": ["127.0.0.1", "collector.lab"]}}

Runs at low priority (early) so it can veto before other middleware act.
"""
from __future__ import annotations

from urllib.parse import urlparse

from ..mwbase import Middleware, SyntheticResponse


class AllowlistMiddleware(Middleware):
    name = "allowlist"
    description = "block requests to hosts not on the allowlist (safety guard)"
    priority = 10   # run before other middleware

    def before_request(self, ctx) -> None:
        allow = self.options.get("hosts") or []
        if not allow:
            return
        host = urlparse(ctx.request["url"]).hostname or ""
        if host not in allow:
            ctx.short_circuit(SyntheticResponse(
                status_code=0, reason="blocked-by-allowlist",
                body={"blocked": True, "host": host, "allow": allow}))
