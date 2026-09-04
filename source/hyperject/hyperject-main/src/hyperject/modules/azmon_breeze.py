"""Azure Monitor "Breeze" envelope ingest target (the OpenTelemetry -> Azure
Monitor path).

The Azure Monitor OpenTelemetry exporter does not send OTLP to Azure; it maps
OTel signals into Application Insights "Breeze" telemetry envelopes and POSTs
them to ``{IngestionEndpoint}/v2.1/track``:

    OTel server span     -> RequestData         (Microsoft.ApplicationInsights.Request)
    OTel client span     -> RemoteDependencyData(Microsoft.ApplicationInsights.RemoteDependency)
    OTel log record      -> MessageData         (Microsoft.ApplicationInsights.Message)
    OTel metric          -> MetricData          (Microsoft.ApplicationInsights.Metric)

This module exercises that ingestion surface with the envelope shapes the
exporter really emits (the sibling ``app_insights`` module sends raw EventData).
It reuses the ``itemsAccepted`` acceptance contract and accepts an Azure Monitor
connection string as an alternative to a bare endpoint+ikey.

The ``covert`` variant emits a ``gen_ai.evaluation.result`` MessageData carrying
``gen_ai.*`` attributes -- the exact shape Azure AI Foundry continuous agent
evaluation writes to Application Insights -- to demonstrate poisoning an agent
observability dashboard with forged evaluation scores.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import (Prepared, variant_count, covert_marker, large_blob,
                    now_iso, sample_hex, connection_string_target)

#: Breeze envelope name for each baseData type
ENVELOPE_NAME = {
    "RequestData": "Microsoft.ApplicationInsights.Request",
    "RemoteDependencyData": "Microsoft.ApplicationInsights.RemoteDependency",
    "MessageData": "Microsoft.ApplicationInsights.Message",
    "MetricData": "Microsoft.ApplicationInsights.Metric",
}


def _guid() -> str:
    return (f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
            f"{sample_hex(4)}-{sample_hex(12)}")


class AzureMonitorBreezeModule(TargetModule):
    name = "azmon_breeze"
    description = "azure-monitor OTel breeze envelope ingest"

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("Sends the Breeze envelopes the Azure Monitor OpenTelemetry "
                      "exporter emits. Configure with endpoints+ikeys, or paste an "
                      "Azure Monitor 'connection_strings' entry "
                      "(InstrumentationKey=...;IngestionEndpoint=...). "
                      "envelope_types picks which telemetry types to send."),
            "endpoints": [f"{base_url}/v2.1/track"],
            "ikeys": [f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
                      f"{sample_hex(4)}-{sample_hex(12)}"],
            "connection_strings": [],
            "envelope_types": ["RequestData", "RemoteDependencyData", "MessageData"],
            "cloud_role": "hyperject-bas",
            "accept_field": "itemsAccepted",
        }

    # ---- envelope construction --------------------------------------------
    def _tags(self, mcfg, trace_id) -> dict:
        return {
            "ai.internal.sdkVersion": "otel:hyperject",
            "ai.cloud.role": mcfg.get("cloud_role", "hyperject-bas"),
            "ai.operation.id": trace_id,
        }

    def _base_data(self, etype, cfg, variant, index) -> dict:
        span_id = sample_hex(16)
        if etype == "RequestData":
            data = {"ver": 2, "id": span_id, "name": f"GET /bas/{variant}",
                    "duration": "00:00:00.123", "responseCode": "200",
                    "success": True, "url": f"http://bas.local/{variant}",
                    "properties": {"bas.index": str(index)}}
        elif etype == "RemoteDependencyData":
            data = {"ver": 2, "id": span_id, "name": f"BAS {variant} dep",
                    "duration": "00:00:00.045", "resultCode": "200",
                    "success": True, "type": "HTTP", "target": "bas.local",
                    "data": f"http://bas.local/{variant}",
                    "properties": {"bas.index": str(index)}}
        elif etype == "MetricData":
            data = {"ver": 2, "metrics": [{"name": f"bas.{variant}",
                    "kind": 0, "value": 1}], "properties": {"bas.index": str(index)}}
        else:  # MessageData
            data = {"ver": 2, "message": f"BAS {variant} {index}",
                    "severityLevel": 1, "properties": {"bas.index": str(index)}}

        if variant == "large":
            data.setdefault("properties", {})["blob"] = large_blob(cfg)
        if variant == "covert":
            self._make_covert(etype, data, cfg)
        return data

    def _make_covert(self, etype, data, cfg) -> None:
        """Covert variant: forge a Foundry continuous-evaluation result and hide
        a marker in the configured covert field. Foundry writes evaluation
        results as a MessageData whose message is 'gen_ai.evaluation.result'."""
        props = data.setdefault("properties", {})
        marker_field = cfg["techniques"]["covert_field"]["field"]
        props[marker_field] = covert_marker(cfg)
        if etype == "MessageData":
            data["message"] = "gen_ai.evaluation.result"
            props.update({
                "gen_ai.thread.run.id": _guid(),
                "gen_ai.evaluation.name": "Relevance",
                "gen_ai.evaluation.score": "5",
                "gen_ai.response.id": _guid(),
            })

    def _envelope(self, ikey, mcfg, etype, cfg, variant, index) -> dict:
        base_data = self._base_data(etype, cfg, variant, index)
        return {
            "name": ENVELOPE_NAME[etype],
            "time": now_iso(),
            "iKey": ikey,
            "tags": self._tags(mcfg, sample_hex(32)),
            "data": {"baseType": etype, "baseData": base_data},
        }

    # ---- target enumeration ------------------------------------------------
    @staticmethod
    def _ikey_entries(mcfg):
        for item in mcfg.get("ikeys", []):
            if isinstance(item, dict):
                yield (item.get("ikey") or item.get("value") or ""), item.get("label", "")
            else:
                yield item, ""

    def _targets(self, mcfg):
        """Yield (endpoint, ikey, label) from endpoints x ikeys plus any
        connection strings (each carries its own endpoint + ikey)."""
        for endpoint in mcfg.get("endpoints", []):
            for ikey, label in self._ikey_entries(mcfg):
                yield endpoint, ikey, label
        for cs in mcfg.get("connection_strings", []) or []:
            raw = cs.get("value", "") if isinstance(cs, dict) else cs
            label = cs.get("label", "conn-str") if isinstance(cs, dict) else "conn-str"
            ikey, url = connection_string_target(raw)
            yield url, ikey, label

    def plan(self, mcfg, cfg, variants):
        accept_field = mcfg.get("accept_field", "itemsAccepted")
        etypes = [e for e in mcfg.get("envelope_types", ["RequestData"])
                  if e in ENVELOPE_NAME]

        def check(r):
            try:
                return r.status_code == 200 and r.json().get(accept_field, 0) >= 1
            except Exception:
                return False

        out = []
        for endpoint, ikey, label in self._targets(mcfg):
            for etype in etypes:
                tag = f"{label}/{etype}" if label else etype
                target = f"{endpoint} [{tag}]"
                for v in variants:
                    preps = [Prepared("POST", endpoint,
                                      {"json": self._envelope(ikey, mcfg, etype,
                                                              cfg, v, i)}, check)
                             for i in range(variant_count(v, cfg))]
                    out.append((v, target, preps))
        return out
