"""Offline governance for a proposed, not executed, clarification scope."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/investigations/post_r10ni_policy/scope_amendment_v1"

def test_scope_remains_preparation_only():
    p = json.loads((PACKAGE / "scope_amendment.json").read_text())
    assert p["status"] == "PREPARED_EXECUTION_NOT_AUTHORIZED"
    assert p["source_qualified"] is False
    assert p["source_result"] == "MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"
    assert p["blocking_codes"] == {"CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS": 2, "TRADE_STATE_ATTRIBUTION_UNAVAILABLE": 1}
    assert p["every_approved_date_must_pass"] and not p["partial_source_qualification_permitted"]
    assert p["recipient"]["address"] is None
    assert p["limits"]["agent_http_transactions"] == p["limits"]["agent_messages"] == 0
    assert p["limits"]["owner_proposed_messages"] == 1
    assert not p["limits"]["raw_package_reacquisition"]
    assert p["retention"]["permission_pending"] and not p["retention"]["new_copy_created"]
    assert p["retention"]["existing_review_copy_retention_unchanged"]
    for action in ("network", "messages", "deletion", "adapter_changes", "research", "fingerprint_refresh", "production_activation", "requalification"):
        assert action in p["prohibited"]
    assert "case-specific" in p["exact_message"]
    assert "Owner approval is not authoritative source evidence" in p["later_gates"]

def test_manifest_and_historical_bytes():
    manifest = json.loads((PACKAGE / "root_manifest.json").read_text())
    assert manifest["status"] == "PREPARED_EXECUTION_NOT_AUTHORIZED"
    for entry in manifest["files"]:
        assert hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    text = (PACKAGE / "scope_amendment.json").read_text()
    for forbidden in ("C:\\\\Users", "Authorization:", "Cookie:", "password", "access_token"):
        assert forbidden not in text
