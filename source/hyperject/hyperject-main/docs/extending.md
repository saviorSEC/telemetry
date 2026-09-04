# Extending

[← Docs home](README.md)

hyperject is modular: **adding a target or a hook is one file.** Both are
auto-discovered — no edits to the engine, CLI, `init`, or `list`.

## Add a target module

Drop a file in [`../src/hyperject/modules/`](../src/hyperject/modules/) with a
`TargetModule` subclass. Two required hooks:

- `default_config(base_url)` — the config block `hyperject init` writes for it.
- `plan(mcfg, cfg, variants)` — returns `[(technique, target_label, [Prepared]), ...]`.

```python
# src/hyperject/modules/my_target.py
from ..base import TargetModule
from ..core import Prepared, variant_count

class MyTarget(TargetModule):
    name = "my_target"
    description = "my target ingest"
    supported_techniques = ("basic", "bulk")     # optional; default is all four

    def default_config(self, base_url):
        return {"enabled": True, "description": self.description,
                "endpoint": f"{base_url}/ingest"}

    def plan(self, mcfg, cfg, variants):
        url = mcfg["endpoint"]
        check = lambda r: r.status_code in (200, 204)
        out = []
        for v in variants:
            preps = [Prepared("POST", url, {"json": {"n": i}}, check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, url, preps))
        return out
```

Then `hyperject list` shows it, `hyperject init` includes it, and `hyperject run`
executes it.

### Notes

- **`Prepared(method, url, kwargs, accept)`** — `kwargs` are passed to the HTTP
  send (`json=`, `data=`, `params=`, `headers=`, `allow_redirects=`). `accept(r)`
  returns `True` when the endpoint took the telemetry. (401/403 are classified as
  `auth-required` automatically — your `accept` doesn't need to handle them.)
- **Formats** — to probe multiple encodings, emit several rows under one technique
  with distinct `target_label`s, e.g. `f"{url} [form]"`. See `kv_trace.py`.
- **Payload helpers** in `core.py`: `variant_count`, `covert_marker`, `large_blob`,
  `now_iso`, `rand_hex_id`, `sample_hex`.

## Add a middleware

Drop a file in [`../src/hyperject/middleware/`](../src/hyperject/middleware/) with
a `Middleware` subclass. See the [hook contract](middleware.md#the-hook-contract).

```python
# src/hyperject/middleware/my_mw.py
from ..mwbase import Middleware

class MyMiddleware(Middleware):
    name = "my_mw"
    description = "what it does"
    priority = 100
    def before_request(self, ctx):
        ctx.request["headers"]["X-Custom"] = self.options.get("value", "1")
```

Enable it in config: `{ "name": "my_mw", "options": { "value": "abc" } }`.

## External plugins (separate package)

Ship targets or middleware from another pip package via entry points:

```toml
# in your plugin package's pyproject.toml
[project.entry-points."hyperject.modules"]
my_target = "my_pkg.module:MyTarget"

[project.entry-points."hyperject.middleware"]
my_mw = "my_pkg.mw:MyMiddleware"
```

Once that package is installed in the same environment, hyperject discovers it
automatically.

## Test your plugin

The suite includes contract tests that run against **every** discovered module
and middleware, so a new file is checked automatically:

```bash
make test
```

See [Development](development.md).
