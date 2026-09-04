"""Retry an exchange when the endpoint returns a transient status (e.g. rate
limiting), bounded by `max` retries and the engine's max_attempts.

    {"name": "retry_on_status", "options": {"statuses": [429, 503], "max": 2}}
"""
from __future__ import annotations

from ..mwbase import Middleware


class RetryOnStatusMiddleware(Middleware):
    name = "retry_on_status"
    description = "retry when the endpoint returns transient statuses (429/503/…)"

    def after_response(self, ctx) -> None:
        statuses = set(self.options.get("statuses", [429, 503]))
        max_retries = int(self.options.get("max", 2))
        status = getattr(ctx.response, "status_code", None)
        if status in statuses and ctx.attempt <= max_retries:
            ctx.retry()

    # also retry on transport errors up to the same bound
    def on_error(self, ctx) -> None:
        if self.options.get("retry_errors") and ctx.attempt <= int(self.options.get("max", 2)):
            ctx.retry()
