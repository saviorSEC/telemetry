from hyperject.core import validate_config, apply_target_override, collect_target_strings


def test_placeholder_is_flagged():
    cfg = {"modules": {"m": {"enabled": True, "endpoint": "http://h/x",
                             "ikeys": ["REPLACE_WITH_YOUR_OWN_TEST_IKEY"]}}}
    problems = validate_config(cfg, known_modules={"m"})
    assert any("placeholder" in p.lower() for p in problems)


def test_unknown_module_is_flagged():
    cfg = {"modules": {"ghost": {"enabled": True, "endpoint": "http://h/x"}}}
    problems = validate_config(cfg, known_modules=set())
    assert any("Unknown module" in p for p in problems)


def test_disabled_module_ignored():
    cfg = {"modules": {"m": {"enabled": False, "endpoint": "http://h/REPLACE_ME"}}}
    # disabled module's placeholder should not count
    problems = validate_config(cfg, known_modules={"m"})
    assert all("placeholder" not in p.lower() for p in problems)


def test_target_override_preserves_paths():
    cfg = {"modules": {"m": {
        "endpoint": "https://real.example.com/api",
        "endpoints": ["https://a.example.com/v1/track"],
        "base_url": "https://b.example.com/checkin",
    }}}
    apply_target_override(cfg, "http://127.0.0.1:9000")
    m = cfg["modules"]["m"]
    assert m["endpoint"] == "http://127.0.0.1:9000/api"
    assert m["endpoints"][0] == "http://127.0.0.1:9000/v1/track"
    assert m["base_url"] == "http://127.0.0.1:9000/checkin"


def test_valid_generated_config_has_no_problems(full_config, registry):
    problems = validate_config(full_config, known_modules=set(registry))
    assert problems == []


def test_collect_targets_skips_disabled():
    cfg = {"modules": {
        "on": {"enabled": True, "endpoint": "http://h/1"},
        "off": {"enabled": False, "endpoint": "http://h/2"},
    }}
    targets = collect_target_strings(cfg)
    assert "http://h/1" in targets and "http://h/2" not in targets
