"""
Middleware contract — the interception model for requests and responses.

A middleware can, per exchange:
  * mutate the outgoing request           (before_request)
  * short-circuit it (answer without sending, e.g. block / fake / cache)
  * inspect and REPLACE the response       (after_response)
  * ask the engine to RETRY (bounded)      (ctx.retry())
  * recover from a transport error         (on_error)

Execution order is an onion: before_request runs in ascending `priority`,
after_response / on_error run in the reverse order — so an outer middleware
wraps the inner ones. Scope a middleware to certain traffic with applies_to().

Drop a file in middleware/ with a subclass and it is auto-discovered; enable it
per-config under the "middleware" key:

    "middleware": [
        {"name": "extra_headers", "options": {"headers": {"Authorization": "Bearer X"}}}
    ]
"""
from __future__ import annotations

import json


class SyntheticResponse:
    """A response-like object middleware can inject (short-circuit / fail-closed /
    error recovery). Quacks like requests.Response for accept()/transcript use."""

    def __init__(self, status_code: int = 0, body="", headers=None, reason: str = ""):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body, default=str)
        self.headers = dict(headers or {})
        self.reason = reason
        self.synthetic = True

    def json(self):
        try:
            return json.loads(self.text)
        except Exception:
            return {}


class RequestContext:
    """Carried through every hook for one exchange. Middleware read/mutate
    `request`, read `response`/`error`/`attempt`/`meta`, and steer the engine
    with short_circuit() / replace_response() / retry()."""

    #: control actions a middleware can request of the engine
    SHORT_CIRCUIT = "short_circuit"
    RETRY = "retry"

    def __init__(self, request: dict, meta=None):
        self.request = request        # {method,url,headers,params,json,data,allow_redirects}
        self.response = None          # requests.Response | SyntheticResponse | None
        self.error = None             # Exception | None
        self.attempt = 0              # 1-based try counter (0 before first send)
        self.elapsed_ms = 0
        self.meta = dict(meta or {})  # {module, technique, ...}
        self.action = None            # None | SHORT_CIRCUIT | RETRY

    # -- control -----------------------------------------------------------
    def short_circuit(self, response) -> None:
        """Answer this exchange with `response` WITHOUT hitting the network."""
        self.response = response
        self.action = self.SHORT_CIRCUIT

    def replace_response(self, response) -> None:
        """Swap in a different response (no retry)."""
        self.response = response

    def retry(self) -> None:
        """Re-send the (possibly mutated) request; bounded by engine.max_attempts."""
        self.action = self.RETRY

    def clear_action(self) -> None:
        self.action = None

    # -- convenience -------------------------------------------------------
    @property
    def module(self) -> str:
        return self.meta.get("module", "")

    @property
    def technique(self) -> str:
        return self.meta.get("technique", "")


class Middleware:
    #: unique name used in config and CLI
    name: str = ""
    #: one-liner shown by `hyperject list`
    description: str = ""
    #: lower runs earlier in before_request (and later in after_response)
    priority: int = 100

    def __init__(self, **options):
        self.options = options

    def applies_to(self, ctx: RequestContext) -> bool:
        """Return False to skip this middleware for a given exchange."""
        return True

    def before_request(self, ctx: RequestContext) -> None:
        """Inspect/modify ctx.request, or ctx.short_circuit(resp) to skip sending."""

    def after_response(self, ctx: RequestContext) -> None:
        """Inspect ctx.response; may ctx.replace_response(...) or ctx.retry()."""

    def on_error(self, ctx: RequestContext) -> None:
        """Handle ctx.error; may ctx.replace_response(...) to recover or ctx.retry()."""
