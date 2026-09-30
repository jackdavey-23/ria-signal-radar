import json

from radar.runlog import config_hash, run_id, write_run_log


def test_run_id_shape():
    rid = run_id()
    assert "T" in rid and "-" in rid and len(rid) > 16


def test_config_hash_is_stable(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("a: 1\n")
    assert config_hash(p) == config_hash(p) and len(config_hash(p)) == 12


def test_write_run_log_roundtrip(tmp_path):
    out = tmp_path / "run_log.json"
    write_run_log(out, {"run_id": "x", "funnel": [{"gate": "all", "remaining": 3}]})
    assert json.loads(out.read_text())["funnel"][0]["remaining"] == 3
