"""Contract tests every target module (plugin) must satisfy. Runs against all
discovered modules, so a newly-dropped module file is covered automatically."""
import pytest

from hyperject.base import TargetModule
from hyperject.core import VARIANTS, Prepared
from hyperject.registry import discover

BASE = "http://127.0.0.1:8080"
TECHNIQUES = {
    "large_payload_bytes": 128,
    "covert_field": {"enabled": True, "field": "app.version", "marker": "MARKER"},
}

MODULE_NAMES = sorted(discover().keys())


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_module_identity(registry, name):
    mod = registry[name]
    assert isinstance(mod, TargetModule)
    assert mod.name == name, "registry key must match module.name"
    assert mod.description, "module must have a description"
    assert set(mod.supported_techniques) <= set(VARIANTS)


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_default_config_shape(registry, name):
    mcfg = registry[name].default_config(BASE)
    assert isinstance(mcfg, dict)
    assert mcfg.get("enabled") is True
    # must declare at least one target endpoint field
    assert any(k in mcfg for k in ("base_url", "endpoint", "endpoints"))
    # generated endpoints must point at the base we asked for
    blob = str(mcfg)
    assert BASE in blob


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_plan_contract(registry, name):
    mod = registry[name]
    mcfg = mod.default_config(BASE)
    cfg = {"run": {"count": 3}, "modules": {name: mcfg}, "techniques": TECHNIQUES}
    variants = mod.supported_techniques

    plans = mod.plan(mcfg, cfg, variants)
    assert isinstance(plans, list) and plans, "plan() must return a non-empty list"

    for technique, url, preps in plans:
        assert technique in variants
        assert isinstance(url, str) and url.startswith("http")
        assert isinstance(preps, list) and preps
        for pr in preps:
            assert isinstance(pr, Prepared)
            assert pr.method in ("GET", "POST", "PUT")
            assert pr.url.startswith("http")
            assert isinstance(pr.kwargs, dict)
            assert callable(pr.accept)


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_bulk_uses_run_count(registry, name):
    mod = registry[name]
    if "bulk" not in mod.supported_techniques:
        pytest.skip("module does not support bulk")
    mcfg = mod.default_config(BASE)
    cfg = {"run": {"count": 7}, "modules": {name: mcfg}, "techniques": TECHNIQUES}
    plans = mod.plan(mcfg, cfg, ("bulk",))
    bulk_preps = [preps for tech, _url, preps in plans if tech == "bulk"]
    assert bulk_preps and all(len(p) == 7 for p in bulk_preps)


def test_techniques_for_filters(registry):
    for mod in registry.values():
        got = mod.techniques_for(VARIANTS)
        assert set(got) == set(mod.supported_techniques) & set(VARIANTS)
        assert mod.techniques_for(("nonexistent",)) == []
