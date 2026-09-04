from hyperject import ui


def test_color_never_is_plain():
    ui.set_color_mode("never")
    assert ui.paint("x", "red") == "x"
    assert "\033" not in ui.pretty_json({"a": 1})


def test_color_always_emits_codes():
    ui.set_color_mode("always")
    try:
        assert "\033[" in ui.paint("x", "red")
        assert "\033[" in ui.pretty_json({"a": 1})
    finally:
        ui.set_color_mode("never")


def test_pretty_json_accepts_string():
    ui.set_color_mode("never")
    out = ui.pretty_json('{"a": 1, "b": [1, 2]}')
    assert out.strip().startswith("{") and '"a"' in out


def test_banner_nonempty():
    assert "breach" in ui.banner().lower()
