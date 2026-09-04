import json

from hyperject.cli import main


def test_list_runs(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "Modules" in out and "Techniques" in out and "Middleware" in out


def test_export_beautifies_any_json(tmp_path, capsys):
    f = tmp_path / "results.json"
    f.write_text(json.dumps([{"module": "m", "technique": "basic", "sent": 1}]))
    assert main(["export", str(f)]) == 0
    out = capsys.readouterr().out
    assert '"module"' in out and '"sent"' in out


def test_export_transcript_to_har(tmp_path, capsys):
    tr = [{"module": "checkin", "technique": "basic",
           "request": {"method": "POST", "url": "http://h/checkin",
                       "headers": {}, "params": None, "body": {"a": 1}},
           "response": {"status": 200, "headers": {}, "body": "{}", "elapsed_ms": 3}}]
    f = tmp_path / "transcript.json"
    f.write_text(json.dumps(tr))
    out_file = tmp_path / "out.har"
    assert main(["export", str(f), "--format", "har", "-o", str(out_file)]) == 0
    har = json.loads(out_file.read_text())
    assert har["log"]["entries"][0]["request"]["url"] == "http://h/checkin"


def test_export_reads_jsonl(tmp_path, capsys):
    f = tmp_path / "log.jsonl"
    f.write_text('{"a": 1}\n{"b": 2}\n')
    assert main(["export", str(f)]) == 0
    assert '"a"' in capsys.readouterr().out


def test_run_dry_run_transcript_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    rc = main(["run", "--dry-run", "-m", "checkin", "-t", "basic",
               "--transcript", "t.json", "--export", "json"])
    assert rc == 0
    data = json.loads((tmp_path / "t.json").read_text())
    assert data and data[0]["request"]["url"].endswith("/checkin")


def test_init_then_validate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert (tmp_path / "config.json").exists()
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["modules"], "init must populate modules from the registry"
    assert main(["validate"]) == 0


def test_init_no_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert main(["init"]) == 2          # refuses to clobber
    assert main(["init", "--force"]) == 0


def test_run_dry_run_sends_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])
    assert main(["run", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    assert not (tmp_path / "results.json").exists()   # dry-run writes nothing


def test_run_refuses_placeholder_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = {
        "run": {"count": 1, "rate_limit_delay": 0},
        "modules": {"app_insights": {"enabled": True,
                                     "endpoints": ["http://127.0.0.1:1/track"],
                                     "ikeys": ["REPLACE_WITH_YOUR_OWN_TEST_IKEY"]}},
        "techniques": {"large_payload_bytes": 8,
                       "covert_field": {"field": "app.version", "marker": "M"}},
    }
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    assert main(["run"]) == 2           # placeholder guard blocks the run
