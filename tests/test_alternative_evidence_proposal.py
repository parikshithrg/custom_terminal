"""Preparation-only governance and synthetic read-only verification."""
import hashlib
import json
import socket
from pathlib import Path
import pytest
import support_alternative_evidence_proposal as support
import tools.run_isolated_nse_quarantine as experiment
from test_isolated_nse_quarantine import record, diagnostics

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/investigations/post_r10ni_policy/alternative_proposal_v1"

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket,"create_connection",lambda *a,**kw:pytest.fail("network forbidden"))

def load(name):
    return json.loads((PACKAGE/name).read_text())

def test_preparation_authority_not_execution():
    a=load("owner_authorization.json")
    assert a["preparation"] and a["read_only_quarantined_identity_verification"]
    for gate in ("network","acquisition","comparison_execution","research","production_activation","qualification","deletion"):
        assert a[gate] is False
    p=load("proposal.json")
    assert p["selected_external_source"] is None and p["external_urls"]==[] and p["provider_query"] is None
    assert p["execution_approval_question"]["status"].startswith("NOT_REQUESTABLE")
    assert not p["network_authorized"] and not p["acquisition_authorized"]

def test_absent_preparation_approval_prevents_database_access(tmp_path,monkeypatch):
    target=tmp_path/support.AUTH; target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"preparation":False}))
    monkeypatch.setattr(support,"verify_targets",lambda *a:pytest.fail("database read before approval"))
    with pytest.raises(experiment.ExperimentStop,match="PREPARATION_APPROVAL"): support.prepare(tmp_path)

def synthetic_database(tmp_path):
    r,other=record("synthetic_A"),record("synthetic_B")
    ds=diagnostics()+[dict(diagnostics()[0],row_number=3)]
    rows={2:r.financial_instrument_id,3:other.financial_instrument_id}
    mask,restricted=experiment.mapping((r,other),ds,rows)
    db=tmp_path/"synthetic.sqlite"
    experiment.store(db,[("2026-09-10",(r,other),ds,mask,restricted)])
    expected=r.provenance.deterministic()
    return db,expected

def test_database_hash_failure_before_open(tmp_path,monkeypatch):
    db=tmp_path/"bad.sqlite"; db.write_bytes(b"bad")
    monkeypatch.setattr(support.sqlite3,"connect",lambda *a,**k:pytest.fail("opened unbound database"))
    with pytest.raises(experiment.ExperimentStop,match="DATABASE_HASH"): support.verify_targets(db,"0"*64,{})

def test_read_only_verification_immutable_and_exact_count(tmp_path):
    db,expected=synthetic_database(tmp_path); before=experiment.sha(db)
    targets=support.verify_targets(db,before,expected)
    assert len(targets)==2 and all(t["trading_date"]=="2026-09-10" for t in targets)
    assert experiment.sha(db)==before
    assert all(t["option_type"]["state"]=="NOT_APPLICABLE" for t in targets)
    with pytest.raises(experiment.ExperimentStop,match="SOURCE_BINDING"):
        support.verify_targets(db,before,dict(expected,facts_sha256="f"*64))

def test_sidecar_fails_closed(tmp_path):
    db,expected=synthetic_database(tmp_path)
    Path(str(db)+"-wal").write_bytes(b"sidecar")
    with pytest.raises(experiment.ExperimentStop,match="SIDECAR"): support.verify_targets(db,experiment.sha(db),expected)

def test_no_capability_or_permission_invention():
    c=load("candidate_assessment.json")
    assert len(c["candidates"])==5
    for source in c["candidates"]:
        assert source["historical_target_availability"].startswith("UNVERIFIED")
        assert source["independence"].startswith("NOT_ESTABLISHED")
        assert source["permission_retention"]
    p=load("proposal.json")["conditional_local_review"]
    assert p["incoming_file_path"] is None and p["incoming_file_sha256"] is None and p["publisher"] is None
    assert p["retention_permission"].startswith("PENDING")
    assert p["limits"]=={"agent_http_transactions":0,"agent_messages":0,"new_provider_downloads":0,"payload_files":1,"max_file_bytes":65536,"max_contract_date_records":2,"redirects":0,"retries":0,"offline_review_timeout_seconds":10,"session_minutes":10,"archive_processing":False,"enumeration":False}

def test_rules_frozen_no_narrow_qualification():
    rules=load("comparison_rules.json")
    assert rules["price_tolerance"]=="0"
    assert rules["matching_keys"]==["exchange","instrument_class","underlying","expiry","option_type","strike","trading_date","session","units","adjustment_convention"]
    assert set(rules["classifications"])=={"AGREEMENT","DISAGREEMENT","INDETERMINATE","NOT_EVALUATED"}
    assert "Duplicate feeds cannot establish independence" in rules["feed_lineage"]
    assert "source qualification" in rules["permitted_conclusions"]
    c=load("completion.json")
    assert c["source_result"]=="MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"
    assert c["date_attribution_restriction_preserved"] and c["original_acceptance_unchanged"]
    assert c["retention_deadline"]=="2026-12-31" and not c["retention_amended"] and not c["deletion"]
    assert c["network_transactions"]==0 and not c["comparison_execution"]

def test_identity_privacy_and_references_only():
    v=load("target_verification.json")
    assert v["target_count"]==2 and not v["identities_tracked"]
    assert v["private_target_reference"].startswith("artifacts/")
    assert v["database_hash_before_after_match"]
    for path in PACKAGE.glob("*.json"):
        data=path.read_text()
        for marker in ("synthetic_A","synthetic_B","C:","Cookie:","Authorization:","financial_instrument_id","underlying_symbol","source_row","access_token"):
            assert marker not in data

def test_root_hashes_and_historical_evidence():
    m=load("root_manifest.json")
    entries={x["path"]:x["sha256"] for x in m["files"]}
    expected={str(p.relative_to(ROOT)).replace(chr(92),"/") for p in PACKAGE.glob("*.json") if p.name!="root_manifest.json"}
    assert expected.issubset(entries)
    for path,h in entries.items():
        assert experiment.sha(ROOT/path)==h
