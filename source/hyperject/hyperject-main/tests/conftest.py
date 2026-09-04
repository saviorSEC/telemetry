import pytest

from hyperject import ui
from hyperject.registry import discover


@pytest.fixture(autouse=True)
def _no_color():
    """Disable color so output assertions are stable regardless of TTY."""
    ui.set_color_mode("never")
    yield

BASE = "http://127.0.0.1:8080"

# Minimal techniques block so covert/large payload builders have what they need.
TECHNIQUES = {
    "large_payload_bytes": 128,
    "covert_field": {"enabled": True, "field": "app.version", "marker": "MARKER"},
}


@pytest.fixture(scope="session")
def registry():
    return discover()


@pytest.fixture
def full_config(registry):
    """A complete, valid config built from every discovered module."""
    return {
        "run": {"count": 3, "timeout": 5, "rate_limit_delay": 0},
        "modules": {name: mod.default_config(BASE) for name, mod in registry.items()},
        "techniques": TECHNIQUES,
    }
