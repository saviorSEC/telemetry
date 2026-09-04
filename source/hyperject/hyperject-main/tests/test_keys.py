"""The config's key fields must support the shapes from source-files/: multiple
App Insights iKeys (bare or annotated) and OneCollector {key,ikey,origin}."""
from hyperject.core import validate_config
from hyperject.registry import discover

TECH = {"large_payload_bytes": 8,
        "covert_field": {"enabled": True, "field": "ai.application.ver", "marker": "M"}}


def _ai():
    return discover()["app_insights"]


def _oc():
    return discover()["one_collector"]


def test_app_insights_multiple_endpoints_and_ikeys():
    mcfg = {"enabled": True, "accept_field": "itemsAccepted",
            "endpoints": ["http://a/v2.1/track", "http://b/v2.1/track"],
            "ikeys": ["k1", {"ikey": "k2", "label": "Power BI WFE"}]}
    cfg = {"run": {"count": 2}, "modules": {"app_insights": mcfg}, "techniques": TECH}
    plans = _ai().plan(mcfg, cfg, ("basic",))
    # 2 endpoints x 2 keys = 4 basic rows
    assert len(plans) == 4
    # the annotated key's label flows into the result target
    assert any("[Power BI WFE]" in target for _t, target, _p in plans)
    # the bare key still works (no label)
    assert any(target.endswith("/v2.1/track") for _t, target, _p in plans)


def test_annotated_ikey_used_in_payload():
    mcfg = {"enabled": True, "endpoints": ["http://a/v2.1/track"],
            "ikeys": [{"ikey": "abc-123", "label": "L"}]}
    cfg = {"run": {"count": 1}, "modules": {"app_insights": mcfg}, "techniques": TECH}
    _t, _target, preps = _ai().plan(mcfg, cfg, ("basic",))[0]
    assert preps[0].kwargs["json"]["iKey"] == "abc-123"


def test_one_collector_key_shape_and_origin_header():
    mcfg = {"enabled": True, "accept_status": 204,
            "endpoints": ["http://a/OneCollector/1.0/"],
            "keys": [{"key": "K-composite", "ikey": "IK",
                      "origin": "portal.azure.com (Azure Portal)"}]}
    cfg = {"run": {"count": 1}, "modules": {"one_collector": mcfg}, "techniques": TECH}
    _t, target, preps = _oc().plan(mcfg, cfg, ("basic",))[0]
    kw = preps[0].kwargs
    assert kw["params"]["apikey"] == "K-composite"
    assert kw["json"]["iKey"] == "o:IK"
    # 'portal' origin => Azure Portal Origin/Referer spoof (matches the source)
    assert kw["headers"]["Origin"] == "https://portal.azure.com"
    assert "[portal.azure.com (Azure Portal)]" in target


def test_validation_flags_placeholder_inside_annotated_ikey():
    cfg = {"modules": {"app_insights": {
        "enabled": True, "endpoints": ["http://a/v2.1/track"],
        "ikeys": [{"ikey": "REPLACE_WITH_YOUR_OWN_TEST_IKEY", "label": "x"}]}}}
    problems = validate_config(cfg, known_modules={"app_insights"})
    assert any("placeholder" in p.lower() for p in problems)
