"""Elasticsearch / OpenSearch bulk ingest target.

Documents are indexed at ``POST /_bulk`` (default port 9200) as newline-delimited
JSON (NDJSON): an action line then a source line, repeated. A cluster that accepts
an unauthenticated bulk index is EXPOSED; success is ``200`` with an
``{"errors": false, "items": [...]}`` body.
"""
from __future__ import annotations

import json

from ..base import TargetModule
from ..core import Prepared, variant_count, covert_marker, large_blob, now_iso


class ElasticsearchModule(TargetModule):
    name = "elasticsearch"
    description = "elasticsearch/opensearch bulk index"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Elasticsearch/OpenSearch bulk API (real: /_bulk on :9200). "
                      "NDJSON action/source pairs. 'index' names the target index."),
            "endpoint": f"{base_url}/_bulk",
            "index": "hyperject-bas",
        }

    def _doc(self, cfg, variant, index) -> dict:
        doc = {"@timestamp": now_iso(short=True),
               "message": f"BAS document {variant} {index}",
               "variant": variant, "event.action": "simulation"}
        if variant == "large":
            doc["blob"] = large_blob(cfg)
        if variant == "covert":
            doc[cfg["techniques"]["covert_field"]["field"]] = covert_marker(cfg)
        return doc

    def _ndjson(self, mcfg, cfg, variant, index) -> bytes:
        idx = mcfg.get("index", "hyperject-bas")
        action = json.dumps({"index": {"_index": idx}})
        source = json.dumps(self._doc(cfg, variant, index))
        return (action + "\n" + source + "\n").encode("utf-8")

    def plan(self, mcfg, cfg, variants):
        endpoint = mcfg["endpoint"]
        headers = {"Content-Type": "application/x-ndjson"}

        def check(r):
            try:
                return r.status_code == 200 and r.json().get("errors") is False
            except Exception:
                return False

        out = []
        for v in variants:
            preps = [Prepared("POST", endpoint,
                              {"data": self._ndjson(mcfg, cfg, v, i), "headers": headers},
                              check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, endpoint, preps))
        return out
