from hyperject.core import Engine, execute, Prepared


class FakeResp:
    def __init__(self, status, body="{}"):
        self.status_code = status
        self.text = body
        self.headers = {}

    def json(self):
        return {"ok": True}


def test_dry_run_sends_nothing(capsys):
    engine = Engine(timeout=1, rate_delay=0, dry_run=True)
    preps = [Prepared("POST", "http://x/y", {"json": {"a": 1}}, lambda r: True)]
    res = execute(engine, "m", "basic", "http://x/y", preps, concurrency=1)
    assert res.sent == 1
    assert res.accepted == 0          # nothing sent -> nothing accepted
    assert "[dry-run]" in capsys.readouterr().out


def test_execute_tallies_accept(monkeypatch):
    engine = Engine(timeout=1, rate_delay=0, dry_run=False)
    monkeypatch.setattr(engine, "send", lambda *a, **k: FakeResp(200))
    preps = [Prepared("POST", "http://x", {}, lambda r: r.status_code == 200)
             for _ in range(4)]
    res = execute(engine, "m", "bulk", "http://x", preps, concurrency=1)
    assert res.sent == 4 and res.accepted == 4 and res.accepted_all
    assert res.status_codes == [200, 200, 200, 200]


def test_execute_classifies_auth_accept_reject(monkeypatch):
    engine = Engine(timeout=1, rate_delay=0, dry_run=False)
    seq = iter([FakeResp(401), FakeResp(200), FakeResp(500)])
    monkeypatch.setattr(engine, "send", lambda *a, **k: next(seq))
    preps = [Prepared("POST", "http://x", {}, lambda r: r.status_code == 200)
             for _ in range(3)]
    res = execute(engine, "m", "basic", "http://x", preps, concurrency=1)
    assert res.auth_required == 1 and res.accepted == 1 and res.rejected == 1
    assert res.verdict == "EXPOSED"          # any accept => exposed


def test_verdict_auth_required(monkeypatch):
    engine = Engine(timeout=1, rate_delay=0, dry_run=False)
    monkeypatch.setattr(engine, "send", lambda *a, **k: FakeResp(403))
    preps = [Prepared("POST", "http://x", {}, lambda r: False) for _ in range(2)]
    res = execute(engine, "m", "basic", "http://x", preps, concurrency=1)
    assert res.auth_required == 2 and res.accepted == 0
    assert res.verdict == "auth-required"


def test_execute_counts_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    engine = Engine(timeout=1, rate_delay=0, dry_run=False)
    monkeypatch.setattr(engine, "send", boom)
    preps = [Prepared("POST", "http://x", {}, lambda r: True) for _ in range(3)]
    res = execute(engine, "m", "basic", "http://x", preps, concurrency=1)
    assert res.errors == 3 and res.sent == 0 and not res.accepted_all


def test_transcript_records_full_exchange(monkeypatch):
    from hyperject.transcript import Transcript
    tr = Transcript()
    engine = Engine(timeout=1, rate_delay=0, dry_run=False, transcript=tr)
    monkeypatch.setattr("hyperject.core.requests.request",
                        lambda *a, **k: FakeResp(204, body="accepted"))
    engine.send("POST", "http://ep/track", ctx={"module": "m", "technique": "basic"},
                json={"x": 1}, headers={"H": "1"})
    assert len(tr) == 1
    ex = tr.exchanges[0]
    assert ex.request["method"] == "POST" and ex.request["url"] == "http://ep/track"
    assert ex.request["headers"]["H"] == "1"
    assert ex.response["status"] == 204 and ex.response["body"] == "accepted"
    assert tr.responses_only()[0]["status"] == 204
