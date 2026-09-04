"""Tests for the OpenTelemetry / Azure Monitor integrations: connection-string
parsing, the OTLP and Breeze modules, the availability web-test module, and the
detector classifications for OTLP + gen_ai evaluation poisoning."""
import json

import pytest

from hyperject import core, detector
from hyperject.registry import discover

BASE = "http://127.0.0.1:8080"
TECHNIQUES = {
    "large_payload_bytes": 128,
    "covert_field": {"enabled": True, "field": "app.version", "marker": "MARKER"},
}


def _cfg(name, mcfg, count=3):
    return {"run": {"count": count}, "modules": {name: mcfg}, "techniques": TECHNIQUES}


# --- connection strings ------------------------------------------------------

def test_parse_connection_string_explicit_endpoint():
    cs = ("InstrumentationKey=00000000-0000-0000-0000-000000000000;"
          "IngestionEndpoint=https://southcentralus.in.applicationinsights.azure.com/")
    ikey, url = core.connection_string_target(cs)
    assert ikey == "00000000-0000-0000-0000-000000000000"
    assert url == ("https://southcentralus.in.applicationinsights.azure.com"
                   "/v2.1/track")


def test_parse_connection_string_endpoint_suffix():
    ikey, url = core.connection_string_target(
        "InstrumentationKey=abc;EndpointSuffix=ai.contoso.com")
    assert ikey == "abc"
    assert url == "https://dc.ai.contoso.com/v2.1/track"


def test_connection_string_default_endpoint():
    _, url = core.connection_string_target("InstrumentationKey=abc")
    assert url.startswith(core.DEFAULT_INGESTION_ENDPOINT)


def test_connection_string_ikey_surfaced_for_placeholder_guard():
    cfg = {"modules": {"azmon_breeze": {"enabled": True, "connection_strings": [
        "InstrumentationKey=REPLACE_WITH_YOUR_OWN_TEST_IKEY;EndpointSuffix=x.y"]}}}
    problems = core.validate_config(cfg)
    assert any("placeholder" in p.lower() for p in problems)


# --- OTLP module -------------------------------------------------------------

def test_otlp_builds_signal_payloads():
    mod = discover()["otlp"]
    mcfg = mod.default_config(BASE)
    plans = mod.plan(mcfg, _cfg("otlp", mcfg), ("basic",))
    by_signal = {t.split("[")[-1].rstrip("] ").split("/")[0]: preps
                 for _, t, preps in plans}
    assert set(by_signal) == {"traces", "metrics", "logs"}

    trace_body = by_signal["traces"][0].kwargs["json"]
    span = trace_body["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert len(span["traceId"]) == 32 and len(span["spanId"]) == 16
    assert by_signal["traces"][0].url.endswith("/v1/traces")
    assert "resourceMetrics" in by_signal["metrics"][0].kwargs["json"]
    assert "resourceLogs" in by_signal["logs"][0].kwargs["json"]


def test_otlp_covert_hides_marker_in_attribute():
    mod = discover()["otlp"]
    mcfg = mod.default_config(BASE)
    mcfg["signals"] = ["traces"]
    plans = mod.plan(mcfg, _cfg("otlp", mcfg), ("covert",))
    body = json.dumps(plans[0][2][0].kwargs["json"])
    assert "app.version" in body


# --- Azure Monitor Breeze module + gen_ai poison -----------------------------

def test_breeze_envelope_types_and_connection_string():
    mod = discover()["azmon_breeze"]
    mcfg = mod.default_config(BASE)
    mcfg["connection_strings"] = [
        "InstrumentationKey=aaa;IngestionEndpoint=https://dc.example.com/"]
    plans = mod.plan(mcfg, _cfg("azmon_breeze", mcfg), ("basic",))
    urls = {preps[0].url for _, _, preps in plans}
    assert any(u.endswith("/v2.1/track") for u in urls)
    # connection-string target is probed alongside the endpoint+ikey target
    assert "https://dc.example.com/v2.1/track" in urls
    env = plans[0][2][0].kwargs["json"]
    assert env["name"].startswith("Microsoft.ApplicationInsights.")


def test_breeze_covert_forges_genai_eval_result():
    mod = discover()["azmon_breeze"]
    mcfg = mod.default_config(BASE)
    mcfg["envelope_types"] = ["MessageData"]
    plans = mod.plan(mcfg, _cfg("azmon_breeze", mcfg), ("covert",))
    base_data = plans[0][2][0].kwargs["json"]["data"]["baseData"]
    assert base_data["message"] == "gen_ai.evaluation.result"
    assert "gen_ai.thread.run.id" in base_data["properties"]


# --- availability web-test module -------------------------------------------

def test_availability_webtest_builds_arm_put():
    mod = discover()["availability_webtest"]
    mcfg = mod.default_config(BASE)
    mcfg.update({"subscription_id": "sub", "resource_group": "rg"})
    plans = mod.plan(mcfg, _cfg("availability_webtest", mcfg), ("basic",))
    prep = plans[0][2][0]
    assert prep.method == "PUT"
    assert "/providers/Microsoft.Insights/webtests/" in prep.url
    assert "api-version=2022-06-15" in prep.url
    assert "WebTest" in prep.kwargs["json"]["properties"]["Configuration"]


def test_availability_webtest_bulk_unique_names():
    mod = discover()["availability_webtest"]
    mcfg = mod.default_config(BASE)
    plans = mod.plan(mcfg, _cfg("availability_webtest", mcfg, count=4), ("bulk",))
    names = [p.kwargs["json"]["properties"]["Name"] for p in plans[0][2]]
    assert len(set(names)) == 4


# --- detector ----------------------------------------------------------------

def test_detector_flags_otlp_and_genai(tmp_path, capsys):
    events = [
        {"ts": "t0", "method": "POST", "path": "/v1/traces", "query": {},
         "client": "1.1.1.1", "headers": {},
         "body_len": 50, "body": json.dumps({"resourceSpans": []})},
        {"ts": "t1", "method": "POST", "path": "/v2.1/track", "query": {},
         "client": "1.1.1.1", "headers": {},
         "body_len": 80, "body": json.dumps(
             {"data": {"baseData": {"message": "gen_ai.evaluation.result",
                                    "properties": {"gen_ai.thread.run.id": "x"}}}})},
    ]
    log = tmp_path / "ingest.log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in events))
    detector.detect(str(log))
    out = capsys.readouterr().out
    assert "OTLP_INGEST" in out
    assert "GENAI_EVAL_POISON" in out
