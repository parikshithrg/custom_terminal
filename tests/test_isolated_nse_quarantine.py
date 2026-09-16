"""Synthetic offline coverage experiment safeguards."""
import ast
import json
import socket
import sqlite3
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
import tools.run_isolated_nse_quarantine as e
from market_intel.foundation.nse_fno_candidate import FieldValue, NormalizedFnoRecord, ProvenanceBinding, ValueState

ROOT = Path(__file__).resolve().parents[1]
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket,"create_connection",lambda *a,**k:pytest.fail("network"))

def record(fid="synthetic"):
    na = FieldValue(ValueState.NOT_APPLICABLE)
    return NormalizedFnoRecord(date(2026,9,10),fid,"STF",FieldValue(ValueState.PRESENT,"SYNTHETIC"),na,
        date(2026,9,24),na,na,25,Decimal("10"),Decimal("10"),Decimal("10"),Decimal("11"),
        Decimal("12"),3,2,"NSE_FO_PAIRED_REPORTS","UDIFF_V1_MII_CONTRACT_V1",
        ProvenanceBinding("nse_fno_single_date_download_v2","synthetic.zip","0"*64,"synthetic.gz","1"*64))
def diagnostics():
    return [
      {"code":e.CLOSE,"row_number":2,"qualification_blocking":True,"values":{}},
      {"code":e.ATTRIBUTION,"row_number":None,"qualification_blocking":True,"values":{}},
      {"code":"SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS","row_number":2,"qualification_blocking":False,"values":{}}]
def copy_approval(tmp):
    for folder,name in ((e.PROTOCOL,"protocol.json"),(e.EXEC,"owner_authorization.json")):
        target = tmp / folder / name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/folder/name).read_bytes())
    return tmp/e.EXEC/"owner_authorization.json"

@pytest.mark.parametrize("gate",["experiment_implementation","consumer_scope","materiality_thresholds"])
def test_approval_required_before_evaluation(tmp_path,gate):
    path = copy_approval(tmp_path)
    a = json.loads(path.read_text()); a[gate] = False; path.write_text(json.dumps(a))
    with pytest.raises(e.ExperimentStop,match="OWNER_APPROVAL_REQUIRED"):
        e.execute(tmp_path,normalizer=lambda *a:pytest.fail("normalized"))

def test_integrity_before_normalization(monkeypatch,tmp_path):
    copy_approval(tmp_path)
    def fail(*a): raise e.ExperimentStop("INTEGRITY_MISMATCH")
    monkeypatch.setattr(e,"preflight",fail)
    with pytest.raises(e.ExperimentStop,match="INTEGRITY"):
        e.execute(tmp_path,normalizer=lambda *a:pytest.fail("normalized"))
def test_real_binding_mismatch_prevents_evaluation(tmp_path):
    copy_approval(tmp_path)
    target=tmp_path/"corrupt.json"; target.write_text("corrupt")
    manifest=tmp_path/e.PROTOCOL/"root_manifest.json"
    manifest.write_text(json.dumps({"files":[{"path":"corrupt.json","sha256":"0"*64}]}))
    with pytest.raises(e.ExperimentStop,match="EVIDENCE_BINDING_MISMATCH"):
        e.execute(tmp_path,normalizer=lambda *a:pytest.fail("normalized after corrupt binding"))
def test_protocol_and_thresholds_cannot_change(tmp_path):
    path = copy_approval(tmp_path)
    a=json.loads(path.read_text()); a["thresholds"]="TUNED"; path.write_text(json.dumps(a))
    with pytest.raises(e.ExperimentStop,match="THRESHOLD"): e.approval(tmp_path)
    (tmp_path/e.PROTOCOL/"protocol.json").write_text("{}")
    with pytest.raises(e.ExperimentStop,match="PROTOCOL_HASH"): e.approval(tmp_path)
def test_path_escape_fail_closed(tmp_path):
    with pytest.raises(e.ExperimentStop,match="UNSAFE"): e.safe_path(tmp_path,"../elsewhere")

def test_quarantine_count_reconciliation():
    r=record(); mask,restrictions=e.mapping((r,),diagnostics(),{2:r.financial_instrument_id})
    assert len(mask)==len(restrictions)==1
    assert e.mapping((r,),diagnostics(),{2:r.financial_instrument_id})==(mask,restrictions)
    a=e.audit((r,),mask,True)
    assert a["quarantined_contract_dates"]==1 and a["filtered_contract_dates"]==0
    assert a["coverage_materiality"]=="MATERIAL_FOR_COVERAGE"
def test_field_missingness_denominators():
    r=record(); a=e.audit((r,),{r.financial_instrument_id:diagnostics()[0]},True)
    assert a["row_coverage_loss_percent"]=="100"
    assert a["field_missingness"]["close"]["experimental_unavailable_including_gaps"]==1
    assert a["field_missingness"]["option_type"]["baseline_states"]=={"NOT_APPLICABLE":1}
    assert e.audit((),{},False)["row_coverage_loss_percent"] is None
def test_contract_date_unique_mapping():
    r=record()
    with pytest.raises(e.ExperimentStop,match="DUPLICATE"): e.mapping((r,r),diagnostics(),{2:r.financial_instrument_id})
    with pytest.raises(e.ExperimentStop,match="QUARANTINE_IDENTITY"): e.mapping((r,),diagnostics(),{2:"unmatched"})
def test_date_attribution_persists(tmp_path):
    r,other=record(),record("other")
    mask,restrictions=e.mapping((r,other),diagnostics(),{2:r.financial_instrument_id})
    db=tmp_path/"experiment.sqlite"
    e.store(db,[("2026-09-10",(r,other),diagnostics(),mask,restrictions)])
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM experimental_row_filtered WHERE date_restricted=1").fetchone()[0]==1
        assert conn.execute("SELECT count(*) FROM date_restrictions").fetchone()[0]==1
        assert conn.execute("SELECT count(*) FROM diagnostics").fetchone()[0]==3
        for table in ("facts","quarantine","diagnostics","date_restrictions","metadata"):
            with pytest.raises(sqlite3.IntegrityError,match="IMMUTABLE"): conn.execute(f"DELETE FROM {table}")
    with pytest.raises(e.ExperimentStop,match="OVERWRITE"): e.store(db,[])
def test_no_fill_or_price_mutation():
    r,other=record(),record("other"); before=r.deterministic()
    mask,restrictions=e.mapping((r,other),diagnostics(),{2:r.financial_instrument_id})
    checks=e.consumer_checks((r,other),mask,restrictions,diagnostics(),{2:r.financial_instrument_id,3:other.financial_instrument_id},True)
    assert all(c["baseline"]==c["experimental"]=="PASS" for c in checks)
    assert r.deterministic()==before and r.close==Decimal("11")
def test_date_diagnostic_cannot_be_cleared():
    r=record()
    with pytest.raises(e.ExperimentStop,match="DATE_ATTRIBUTION"): e.mapping((r,),[diagnostics()[0]],{2:r.financial_instrument_id})
    bad=dict(diagnostics()[0],code="OPEN_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS")
    with pytest.raises(e.ExperimentStop,match="UNEXPECTED"): e.mapping((r,),[bad],{2:r.financial_instrument_id})
def test_nonblocking_zero_state_remains_visible():
    r=replace(record(),volume=0)
    d=[{"code":"ZERO_VOLUME_PRICE_STATE","row_number":2,"qualification_blocking":False,"values":{}}]
    mask,restrictions=e.mapping((r,),d,{2:r.financial_instrument_id})
    assert not mask and not restrictions
    assert e.audit((r,),mask,False)["field_missingness"]["volume"]["baseline_states"]["ZERO_VALUE"]==1
@pytest.mark.parametrize("key",e.MATCH_KEYS)
def test_corroboration_requires_every_key(key):
    a={k:"synthetic" for k in e.MATCH_KEYS}; b=dict(a,authorized=True,provenance="synthetic"); b[key]=None
    with pytest.raises(e.ExperimentStop,match="CORROBORATION"): e.corroborate(a,b)
def test_corroboration_never_proves_independence():
    a={k:"synthetic" for k in e.MATCH_KEYS}; b=dict(a,authorized=True,provenance="synthetic")
    assert e.corroborate(a,b)["independence"]=="NOT_ESTABLISHED"
    with pytest.raises(e.ExperimentStop,match="PERMISSION"): e.corroborate(a,a)
def test_no_production_research_or_fingerprint_connection():
    tree=ast.parse((ROOT/"tools/run_isolated_nse_quarantine.py").read_text())
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any(m and any(x in m for x in ("research","kite","yfinance","fingerprint")) for m in imports)
    assert e.RESULT=="MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"
def test_execution_hashes():
    path=ROOT/e.EXEC/"root_manifest.json"
    if not path.exists(): pytest.skip("closeout pending")
    for item in json.loads(path.read_text())["files"]: assert e.sha(ROOT/item["path"])==item["sha256"]
def test_measured_results_preserve_original_acceptance():
    path=ROOT/e.EXEC/"measured_results.json"
    if not path.exists(): pytest.skip("closeout pending")
    data=json.loads(path.read_text())
    assert data["pooled"]["baseline_contract_dates"]==99026
    assert data["pooled"]["quarantined_contract_dates"]==2
    assert data["pooled"]["filtered_contract_dates"]==99024
    assert data["pooled"]["restricted_date_baseline_rows"]==33729
    affected=data["dates"][1]
    assert affected["date_attribution_diagnostic_preserved"]
    assert affected["diagnostic_counts"][e.ATTRIBUTION]==1
    assert [d["original_acceptance"] for d in data["dates"]]==["DATE_ACCEPTED","DATE_NOT_ACCEPTED","DATE_ACCEPTED"]
    assert data["source_result"]==e.RESULT and not data["historical_acceptance_changed"]
    assert not data["source_qualified"] and not data["production_exposed"] and not data["research"]
    assert data["network_requests"]==0 and not data["price_substitution"] and not data["fingerprint_refreshed"]
