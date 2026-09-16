"""Offline integrity checks for the bounded reacquisition receipt."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/investigations/post_r10ni_policy/isolated_comparison_v1"

def test_receipt_is_exact_scope_not_qualification():
    r = json.loads((PACKAGE / "reacquisition_receipt.json").read_text())
    old = json.loads((ROOT / "docs/investigations/r10n_i/requalification_v1/source_integrity_preflight.json").read_text())
    assert r["exact_dates"] == [p["trading_date"] for p in old["packages"]]
    assert r["result"] == "THREE_PACKAGES_REACQUIRED_HASH_IDENTICAL"
    assert r["retention_deadline"] == "2026-12-31"
    assert len(r["requests"]) == 6
    assert all(x["method"] == "GET" and x["status"] == 200 for x in r["requests"])
    assert r["limits"]["redirects"] == r["limits"]["retries"] == 0
    assert not r["source_qualified"] and not r["production_activated"]
    assert not r["comparison_performed"] and not r["quarantine_table_created"]
    assert not r["historical_results_changed"]
    for new, sealed in zip(r["packages"], old["packages"]):
        assert new["historical_payloads_match"]
        assert [{k: f[k] for k in ("filename", "byte_length", "sha256")} for f in new["files"]] == sealed["files"]

def test_hash_bindings_and_sanitization():
    m = json.loads((PACKAGE / "root_manifest.json").read_text())
    for e in m["files"]:
        assert hashlib.sha256((ROOT / e["path"]).read_bytes()).hexdigest() == e["sha256"]
    text = (PACKAGE / "reacquisition_receipt.json").read_text()
    assert "C:" not in text and "Cookie:" not in text and "Authorization:" not in text
