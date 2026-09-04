import json

from hyperject.transcript import Transcript, Exchange, FORMATS


def _tr():
    tr = Transcript(redact=["security_token"])
    tr.add(Exchange(
        "checkin", "basic",
        {"method": "POST", "url": "http://h/checkin", "params": None,
         "headers": {"Authorization": "Bearer x"},
         "body": {"security_token": "secret", "a": 1}},
        {"status": 200, "headers": {}, "body": '{"stats_ok": true}', "elapsed_ms": 5}))
    return tr


def test_redaction():
    d = _tr().as_dicts()[0]
    assert d["request"]["body"]["security_token"] == "***REDACTED***"
    assert d["request"]["body"]["a"] == 1


def test_json_and_jsonl():
    tr = _tr()
    assert isinstance(json.loads(tr.render("json")), list)
    assert len(tr.render("jsonl").splitlines()) == 1


def test_har_shape():
    har = json.loads(_tr().render("har"))
    assert har["log"]["version"] == "1.2"
    entry = har["log"]["entries"][0]
    assert entry["request"]["method"] == "POST"
    assert entry["request"]["url"] == "http://h/checkin"


def test_pretty_contains_url():
    assert "http://h/checkin" in _tr().render("pretty")


def test_responses_only():
    r = _tr().responses_only()[0]
    assert r["status"] == 200 and r["url"] == "http://h/checkin"


def test_all_formats_supported():
    tr = _tr()
    for fmt in FORMATS:
        assert tr.render(fmt)
