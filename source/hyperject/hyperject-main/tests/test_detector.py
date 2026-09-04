import base64
import json

from hyperject import detector


def _write(tmp_path, events):
    log = tmp_path / "ingest.log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in events))
    return str(log)


def test_flags_all_techniques(tmp_path, capsys):
    covert_body = json.dumps({"app.version": base64.b64encode(b"whoami").decode()})
    events = [
        # oversized + unauth + covert in one event
        {"ts": "t0", "method": "POST", "path": "/v2.1/track", "query": {},
         "client": "1.1.1.1", "headers": {}, "body_len": 40000, "body": covert_body},
    ]
    # add a flood: 9 events to the same (client, path)
    for i in range(9):
        events.append({"ts": f"t{i}", "method": "POST", "path": "/checkin", "query": {},
                       "client": "2.2.2.2", "headers": {}, "body_len": 100, "body": "{}"})

    n = detector.detect(_write(tmp_path, events))
    out = capsys.readouterr().out
    assert "UNAUTH_INGEST" in out
    assert "OVERSIZED_PAYLOAD" in out
    assert "COVERT_FIELD_C2" in out
    assert "BULK_FLOOD" in out
    assert n > 0


def test_authenticated_not_flagged_unauth(tmp_path, capsys):
    events = [{"ts": "t", "method": "POST", "path": "/x", "query": {},
               "client": "3.3.3.3", "headers": {"Authorization": "Bearer z"},
               "body_len": 10, "body": "{}"}]
    detector.detect(_write(tmp_path, events))
    out = capsys.readouterr().out
    assert "UNAUTH_INGEST" not in out


def test_missing_log_is_graceful(tmp_path, capsys):
    n = detector.detect(str(tmp_path / "nope.jsonl"))
    assert n == 0
    assert "not found" in capsys.readouterr().out.lower()
