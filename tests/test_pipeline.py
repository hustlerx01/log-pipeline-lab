import json, os, shutil, subprocess, sys, time
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gen"))
from generate_logs import main as gen
FB = shutil.which("fluent-bit") or ("/opt/fluent-bit/bin/fluent-bit" if Path("/opt/fluent-bit/bin/fluent-bit").exists() else None)

def test_generator_deterministic(tmp_path):
    import datetime as dt
    now = dt.datetime(2026, 10, 11, 10, 0, tzinfo=dt.timezone.utc)
    a = gen(tmp_path / "a", 500, now=now); b = gen(tmp_path / "b", 500, now=now)
    assert a == b and (tmp_path / "a/access.log").read_text() == (tmp_path / "b/access.log").read_text()
    assert a["nginx_5xx"] > 0 and a["ssh_failed_bruteforce_ip"] > 0

@pytest.mark.skipif(not FB, reason="fluent-bit not installed")
def test_fluentbit_parses_and_filters(tmp_path):
    logs, state = tmp_path / "logs", tmp_path / "state"; state.mkdir()
    truth = gen(logs, 400)
    conf = (ROOT / "fluent-bit/fluent-bit.conf").read_text()
    conf = conf[:conf.index("[OUTPUT]\n    Name          loki")] + conf[conf.index("[OUTPUT]\n    Name          file"):]
    (tmp_path / "fb.conf").write_text(conf)
    for f in ("parsers.conf", "enrich.lua"): shutil.copy(ROOT / "fluent-bit" / f, tmp_path / f)
    env = dict(os.environ, LOG_DIR=str(logs), STATE_DIR=str(state), LOKI_HOST="127.0.0.1", LOKI_PORT="0", FB_HTTP_PORT="2029")
    p = subprocess.Popen([FB, "-c", "fb.conf"], cwd=tmp_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    archive = state / "archive.jsonl"
    try:
        for _ in range(50):
            time.sleep(0.3)
            if archive.exists() and archive.read_text().count("\n") >= 400 + 400 - truth["healthz"] + 40: break
    finally:
        p.terminate(); p.wait()
    recs = [json.loads(l) for l in archive.read_text().splitlines()]
    nginx = [r for r in recs if "status" in r]
    assert len(nginx) == truth["nginx_total"] - truth["healthz"]          # healthz dropped by grep filter
    assert sum(r["status_class"] == "5xx" for r in nginx) == truth["nginx_5xx"]  # lua enrichment
    assert all(isinstance(r["status"], int) for r in nginx)               # Types cast
    ssh = [r for r in recs if r.get("ssh_event") == "Failed password"]
    assert len(ssh) == truth["ssh_failed_bruteforce_ip"] and ssh[0]["src_ip"] == "203.0.113.50"
    assert all(r["env"] == "lab" for r in recs)
