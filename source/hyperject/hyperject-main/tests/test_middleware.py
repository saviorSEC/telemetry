import pytest

from hyperject.registry import discover_middleware
from hyperject.core import Engine
from hyperject.mwbase import Middleware, RequestContext, SyntheticResponse
from hyperject.transcript import Transcript

MW = discover_middleware()


class FakeResp:
    def __init__(self, status=200, body="{}"):
        self.status_code = status
        self.text = body
        self.headers = {}


def _engine(monkeypatch, responder, **kw):
    """Engine whose network call is driven by `responder(call_n) -> FakeResp`."""
    state = {"n": 0}

    def fake_request(method, url, **kwargs):
        state["n"] += 1
        r = responder(state["n"])
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr("hyperject.core.requests.request", fake_request)
    eng = Engine(timeout=1, rate_delay=0, dry_run=False, **kw)
    eng._calls = state
    return eng


# ---- discovery / contract --------------------------------------------------

@pytest.mark.parametrize("name", sorted(MW))
def test_middleware_contract(name):
    cls = MW[name]
    assert issubclass(cls, Middleware) and cls.name == name
    inst = cls()                          # instantiable with no options
    assert isinstance(inst.priority, int)
    assert inst.applies_to(RequestContext({"url": "http://x"})) is True


def test_builtins_present():
    for n in ("extra_headers", "tag_correlation", "allowlist", "retry_on_status"):
        assert n in MW


# ---- before_request mutation ----------------------------------------------

def test_extra_headers_injected(monkeypatch):
    mw = MW["extra_headers"](headers={"Authorization": "Bearer T", "X-Env": "lab"})
    tr = Transcript()
    captured = {}
    monkeypatch.setattr("hyperject.core.requests.request",
                        lambda m, u, **k: captured.update(k) or FakeResp())
    eng = Engine(1, 0, False, transcript=tr, middlewares=[mw])
    eng.send("POST", "http://h/x", json={"a": 1})
    assert captured["headers"]["Authorization"] == "Bearer T"
    assert tr.exchanges[0].request["headers"]["X-Env"] == "lab"


# ---- short-circuit (allowlist safety guard) --------------------------------

def test_allowlist_blocks_and_skips_network(monkeypatch):
    called = {"n": 0}

    def boom(m, u, **k):
        called["n"] += 1
        raise AssertionError("network must not be hit for a blocked host")
    monkeypatch.setattr("hyperject.core.requests.request", boom)

    mw = MW["allowlist"](hosts=["good.com"])
    eng = Engine(1, 0, False, middlewares=[mw])
    resp = eng.send("POST", "http://evil.com/x", json={})
    assert called["n"] == 0
    assert isinstance(resp, SyntheticResponse)
    assert resp.status_code == 0 and resp.json()["host"] == "evil.com"


def test_allowlist_allows_listed_host(monkeypatch):
    mw = MW["allowlist"](hosts=["good.com"])
    eng = _engine(monkeypatch, lambda n: FakeResp(200), middlewares=[mw])
    resp = eng.send("POST", "http://good.com/x", json={})
    assert resp.status_code == 200 and eng._calls["n"] == 1


# ---- retry (bounded) -------------------------------------------------------

def test_retry_on_status_retries_then_succeeds(monkeypatch):
    mw = MW["retry_on_status"](statuses=[503], max=3)
    eng = _engine(monkeypatch,
                  lambda n: FakeResp(503) if n < 3 else FakeResp(200),
                  middlewares=[mw], max_attempts=5)
    resp = eng.send("POST", "http://h/x", json={})
    assert resp.status_code == 200 and eng._calls["n"] == 3


def test_retry_bounded_by_max_attempts(monkeypatch):
    mw = MW["retry_on_status"](statuses=[503], max=99)
    eng = _engine(monkeypatch, lambda n: FakeResp(503),
                  middlewares=[mw], max_attempts=3)
    resp = eng.send("POST", "http://h/x", json={})
    assert resp.status_code == 503 and eng._calls["n"] == 3     # capped


# ---- on_error recovery -----------------------------------------------------

def test_on_error_recovery(monkeypatch):
    class Recover(Middleware):
        name = "recover"
        def on_error(self, ctx):
            ctx.replace_response(SyntheticResponse(status_code=200, body="recovered"))

    eng = _engine(monkeypatch, lambda n: RuntimeError("boom"),
                  middlewares=[Recover()])
    resp = eng.send("POST", "http://h/x", json={})
    assert resp.status_code == 200 and resp.text == "recovered"


# ---- ordering / scoping ----------------------------------------------------

def test_priority_orders_before_request(monkeypatch):
    order = []

    class A(Middleware):
        name = "a"; priority = 50
        def before_request(self, ctx): order.append("a")

    class B(Middleware):
        name = "b"; priority = 10
        def before_request(self, ctx): order.append("b")

    eng = _engine(monkeypatch, lambda n: FakeResp(), middlewares=[A(), B()])
    eng.send("POST", "http://h/x", json={})
    assert order == ["b", "a"]      # lower priority first


def test_applies_to_scopes(monkeypatch):
    hits = []

    class OnlyCheckin(Middleware):
        name = "only"
        def applies_to(self, ctx): return ctx.module == "checkin"
        def before_request(self, ctx): hits.append(ctx.module)

    eng = _engine(monkeypatch, lambda n: FakeResp(), middlewares=[OnlyCheckin()])
    eng.send("POST", "http://h/x", ctx={"module": "kv_trace"}, json={})
    eng.send("POST", "http://h/x", ctx={"module": "checkin"}, json={})
    assert hits == ["checkin"]


def test_proxy_and_verify_passed(monkeypatch):
    captured = {}
    monkeypatch.setattr("hyperject.core.requests.request",
                        lambda m, u, **k: captured.update(k) or FakeResp())
    eng = Engine(1, 0, False, proxies={"http": "http://p:8080", "https": "http://p:8080"},
                 verify=False)
    eng.send("POST", "http://h/x", json={})
    assert captured["proxies"]["https"] == "http://p:8080"
    assert captured["verify"] is False
