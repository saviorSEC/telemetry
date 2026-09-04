# Middleware

[← Docs home](README.md)

Middleware are auto-discovered plugins that **intercept every exchange**. They can
mutate the request, short-circuit it (answer without sending), replace the
response, retry (bounded), or recover from an error — the hook point for
proxy-style tooling and safety guards.

Enable them per-config (ordered):

```json
"middleware": [
  { "name": "allowlist", "options": { "hosts": ["your-host.com"] } }
]
```

`hyperject list --middleware-only` shows what's installed.

## Built-in middleware

| Name | What it does | Options |
|------|--------------|---------|
| `allowlist` | **Safety** — blocks any request whose host isn't listed, with no network hit | `hosts: [ ... ]` |
| `extra_headers` | Add fixed headers to every request (auth, tags) | `headers: { ... }` |
| `tag_correlation` | Stamp a correlation-id header for log review | `header`, `value` |
| `retry_on_status` | Retry on transient statuses (bounded) | `statuses: [429,503]`, `max`, `retry_errors` |

`allowlist` runs at low `priority` (early) so it can veto before anything else.
`--max-attempts` (or `run.max_attempts`) is the hard cap that bounds all retries.

## The hook contract

Every hook receives a `RequestContext` (`ctx`):

| Hook | When | Can do |
|------|------|--------|
| `before_request(ctx)` | before sending | mutate `ctx.request`; `ctx.short_circuit(resp)` to skip the network |
| `after_response(ctx)` | after a response | read `ctx.response`; `ctx.replace_response(r)`; `ctx.retry()` |
| `on_error(ctx)` | on transport error | recover via `ctx.replace_response(r)` or `ctx.retry()` |
| `applies_to(ctx)` | filter | return `False` to skip this middleware for the exchange |

`ctx` fields: `request` (`{method,url,headers,params,json,data,allow_redirects}`),
`response`, `error`, `attempt`, `module`, `technique`, `meta`.

**Ordering** is an onion: `before_request` runs in ascending `priority`;
`after_response`/`on_error` run in reverse. Set `priority` (default 100) to place
your middleware relative to others.

Use `SyntheticResponse(status_code, body, headers, reason)` to inject or block a
response — it quacks like a `requests.Response` for the accept predicate and the
transcript.

## Example — block writes unless explicitly allowed

```python
# src/hyperject/middleware/block_writes.py
from ..mwbase import Middleware, SyntheticResponse

class BlockWrites(Middleware):
    name = "block_writes"
    description = "short-circuit POSTs unless allow_post is set"
    priority = 20

    def before_request(self, ctx):
        if ctx.request["method"] == "POST" and not self.options.get("allow_post"):
            ctx.short_circuit(SyntheticResponse(0, {"blocked": "write"}))
```

Enable it: `{ "name": "block_writes", "options": { "allow_post": false } }`.

See [Extending](extending.md) for the full add-a-plugin workflow.
