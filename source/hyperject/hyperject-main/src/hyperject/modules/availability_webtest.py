"""Application Insights availability web-test target (management plane).

Unlike the ingest modules, this exercises the Azure Resource Manager control
plane: WebTests Create-Or-Update
(``PUT .../Microsoft.Insights/webtests/{name}?api-version=2022-06-15``), which
provisions a synthetic availability (ping/standard) test that Azure runs from
its global agents against a URL you choose.

Different trust model from telemetry ingestion: ARM writes require a Microsoft
Entra bearer token, so the secure outcome is 401/403 (auth-required). An
accepted create (200/201) against an endpoint that should be authenticated is
the exposure. Set 'bearer_token' to test an authorized create; leave it empty
to confirm the endpoint rejects anonymous writes. Points at the mock collector
by default (which answers PUT), so the loop stays offline and safe.

Only 'basic' (one create) and 'bulk' (N creates) apply; large/covert do not map
to a control-plane resource create.
"""
from __future__ import annotations

from ..base import TargetModule
from ..core import Prepared, variant_count, sample_hex

WEBTEST_XML = (
    '<WebTest Name="{name}" Id="{guid}" Enabled="True" CssProjectStructure="" '
    'CssIteration="" Timeout="{timeout}" WorkItemIds="" '
    'xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010" '
    'Description="" CredentialUserName="" CredentialPassword="" '
    'PreAuthenticate="True" Proxy="default" StopOnError="False" '
    'RecordedResultFile="" ResultsLocale="">'
    '<Items><Request Method="{verb}" Guid="{req_guid}" Version="1.1" '
    'Url="{url}" ThinkTime="0" Timeout="{timeout}" ParseDependentRequests="True" '
    'FollowRedirects="True" RecordResult="True" Cache="False" '
    'ResponseTimeGoal="0" Encoding="utf-8" ExpectedHttpStatusCode="{expect}" '
    'ExpectedResponseUrl="" ReportingName="" IgnoreHttpStatusCode="False" />'
    '</Items></WebTest>'
)


class AvailabilityWebTestModule(TargetModule):
    name = "availability_webtest"
    description = "app-insights availability web-test (ARM control plane)"
    supported_techniques = ("basic", "bulk")

    def default_config(self, base_url: str) -> dict:
        return {
            "enabled": True,
            "description": self.description,
            "_note": ("ARM management root (real: https://management.azure.com). "
                      "Set subscription_id/resource_group/component_id and a "
                      "'bearer_token' for an authorized create. 'request_url' is "
                      "the URL the synthetic test will ping."),
            "base_url": base_url,
            "api_version": "2022-06-15",
            "subscription_id": "REPLACE_WITH_YOUR_SUBSCRIPTION_ID",
            "resource_group": "REPLACE_WITH_YOUR_RESOURCE_GROUP",
            "component_id": "REPLACE_WITH_YOUR_APPINSIGHTS_RESOURCE_ID",
            "webtest_name": "hyperject-availability",
            "kind": "ping",
            "location": "South Central US",
            "geo_locations": ["us-fl-mia-edge"],
            "request_url": f"{base_url}/health",
            "http_verb": "GET",
            "expected_status": 200,
            "frequency": 300,
            "timeout": 30,
            "bearer_token": "",
        }

    def _arm_url(self, mcfg, name) -> str:
        base = mcfg.get("base_url", "").rstrip("/")
        api = mcfg.get("api_version", "2022-06-15")
        return (f"{base}/subscriptions/{mcfg.get('subscription_id')}"
                f"/resourceGroups/{mcfg.get('resource_group')}"
                f"/providers/Microsoft.Insights/webtests/{name}"
                f"?api-version={api}")

    def _body(self, mcfg, name) -> dict:
        xml = WEBTEST_XML.format(
            name=name, guid=self._guid(), req_guid=self._guid(),
            url=mcfg.get("request_url", ""), verb=mcfg.get("http_verb", "GET"),
            expect=mcfg.get("expected_status", 200), timeout=mcfg.get("timeout", 30))
        component = mcfg.get("component_id", "")
        return {
            "location": mcfg.get("location", "South Central US"),
            "kind": mcfg.get("kind", "ping"),
            "tags": {f"hidden-link:{component}": "Resource"} if component else {},
            "properties": {
                "SyntheticMonitorId": name,
                "Name": name,
                "Description": "hyperject synthetic availability test",
                "Enabled": True,
                "Frequency": mcfg.get("frequency", 300),
                "Timeout": mcfg.get("timeout", 30),
                "Kind": mcfg.get("kind", "ping"),
                "RetryEnabled": True,
                "Locations": [{"Id": loc} for loc in mcfg.get("geo_locations", [])],
                "Configuration": {"WebTest": xml},
                "ValidationRules": {
                    "ExpectedHttpStatusCode": mcfg.get("expected_status", 200)},
            },
        }

    @staticmethod
    def _guid() -> str:
        return (f"{sample_hex(8)}-{sample_hex(4)}-{sample_hex(4)}-"
                f"{sample_hex(4)}-{sample_hex(12)}")

    def plan(self, mcfg, cfg, variants):
        headers = {"Content-Type": "application/json"}
        token = mcfg.get("bearer_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        def check(r):
            return r.status_code in (200, 201)

        base_name = mcfg.get("webtest_name", "hyperject-availability")
        out = []
        for v in variants:
            preps = []
            for i in range(variant_count(v, cfg)):
                name = f"{base_name}-{i}" if v == "bulk" else base_name
                preps.append(Prepared("PUT", self._arm_url(mcfg, name),
                                      {"json": self._body(mcfg, name),
                                       "headers": headers}, check))
            out.append((v, self._arm_url(mcfg, base_name), preps))
        return out
