"""
TargetModule — the contract every target plugin implements.

To add a new target, drop a file in `modules/` with a subclass of TargetModule.
It is auto-discovered (see registry.py); nothing else needs editing.

Minimal example (modules/my_target.py):

    from ..base import TargetModule
    from ..core import Prepared, variant_count

    class MyTarget(TargetModule):
        name = "my_target"
        description = "my target ingest"

        def default_config(self, base_url):
            return {"enabled": True, "description": self.description,
                    "endpoint": f"{base_url}/ingest"}

        def plan(self, mcfg, cfg, variants):
            url = mcfg["endpoint"]
            check = lambda r: r.status_code == 200
            out = []
            for v in variants:
                preps = [Prepared("POST", url, {"json": {"n": i}}, check)
                         for i in range(variant_count(v, cfg))]
                out.append((v, url, preps))
            return out
"""
from __future__ import annotations


class TargetModule:
    #: unique config key / CLI name for this target
    name: str = ""
    #: human-readable one-liner (shown by `hyperject list`)
    description: str = ""
    #: techniques this target supports (subset of core.VARIANTS)
    supported_techniques: tuple = ("basic", "bulk", "large", "covert")

    # ---- required hooks ----------------------------------------------------
    def default_config(self, base_url: str) -> dict:
        """Return this module's config block for `hyperject init`, with targets
        pointed at `base_url` (the mock collector by default)."""
        raise NotImplementedError

    def plan(self, mcfg: dict, cfg: dict, variants) -> list:
        """Return [(technique, target_url, [Prepared, ...]), ...] for the given
        techniques. `mcfg` is this module's config block; `cfg` is the whole config."""
        raise NotImplementedError

    # ---- convenience -------------------------------------------------------
    def techniques_for(self, requested) -> list:
        """Intersect requested techniques with what this module supports."""
        return [t for t in requested if t in self.supported_techniques]
