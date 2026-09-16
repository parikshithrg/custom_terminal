"""Preparation-only read-only verification of two quarantined identities."""
import hashlib
import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from tools.run_isolated_nse_quarantine import ExperimentStop, PROTOCOL_HASH, safe_path, sha

POLICY = Path("docs/investigations/post_r10ni_policy")
AUTH = POLICY / "alternative_proposal_v1/owner_authorization.json"

def verify_targets(db_path, expected_sha, expected_provenance):
    if sha(db_path) != expected_sha:
        raise ExperimentStop("DATABASE_HASH_MISMATCH")
    if any(Path(str(db_path)+suffix).exists() for suffix in ("-wal","-journal")):
        raise ExperimentStop("DATABASE_SIDECAR_PRESENT")
    targets = []
    with sqlite3.connect(db_path.as_uri()+"?mode=ro&immutable=1",uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ExperimentStop("DATABASE_INTEGRITY_FAILURE")
        metadata = dict(conn.execute("SELECT key,value FROM metadata"))
        if metadata.get("protocol_sha256") != PROTOCOL_HASH or metadata.get("status") != "EXPERIMENTAL_UNAVAILABLE_TO_PRODUCTION_OR_RESEARCH":
            raise ExperimentStop("DATABASE_PROVENANCE_MISMATCH")
        if metadata.get("retention_deadline") != "2026-12-31":
            raise ExperimentStop("RETENTION_MISMATCH")
        if conn.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'lock_%'").fetchone()[0] != 15:
            raise ExperimentStop("IMMUTABILITY_TRIGGERS_MISSING")
        if conn.execute("SELECT count(*) FROM quarantine").fetchone()[0] != 2:
            raise ExperimentStop("TARGET_COUNT_MISMATCH")
        rows = conn.execute("SELECT q.day,q.fid,q.reason,q.source_row,q.provenance_json,f.fact_json FROM quarantine q JOIN facts f ON q.day=f.day AND q.fid=f.fid ORDER BY q.day,q.fid").fetchall()
        if len(rows) != 2:
            raise ExperimentStop("TARGET_JOIN_MISMATCH")
        if conn.execute("SELECT reason FROM date_restrictions WHERE day='2026-09-10'").fetchone() != ("TRADE_STATE_ATTRIBUTION_UNAVAILABLE",):
            raise ExperimentStop("DATE_RESTRICTION_MISSING")
        for day,fid,reason,source_row,provenance_json,fact_json in rows:
            fact, provenance = json.loads(fact_json),json.loads(provenance_json)
            if day != "2026-09-10" or reason != "CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS" or fact["instrument_type"] != "STF":
                raise ExperimentStop("TARGET_SCOPE_MISMATCH")
            if fact["financial_instrument_id"] != fid or fact["trading_date"] != day or fact["provenance"] != provenance:
                raise ExperimentStop("TARGET_PROVENANCE_MISMATCH")
            if any(provenance[k] != v for k,v in expected_provenance.items()):
                raise ExperimentStop("SOURCE_BINDING_MISMATCH")
            if not isinstance(source_row,int) or source_row < 2:
                raise ExperimentStop("ROW_LOCATOR_MISMATCH")
            targets.append({
                "exchange":"NSE","segment":"FO","instrument_class":"STF",
                "financial_instrument_id":fid,"underlying_symbol":fact["ticker"],
                "underlying_financial_instrument_id":fact["underlying_financial_instrument_id"],
                "expiry":fact["expiry"],"option_type":fact["option_type"],"strike":fact["strike"],
                "trading_date":day,"session_scope":"FINAL_DAILY_REPORT_ELIGIBLE_TRADE_UNIVERSE_UNRESOLVED",
                "units_and_adjustment":"REQUIRES_PROVIDER_DOCUMENTATION_BEFORE_COMPARISON",
                "provenance":provenance,"source_row":source_row,
                "requested_fields":["open","high","low","close","quantity","settlement"],
            })
    if sha(db_path) != expected_sha:
        raise ExperimentStop("DATABASE_BYTES_CHANGED")
    return targets

def prepare(root):
    root = Path(root).absolute()
    auth = json.loads((root/AUTH).read_text())
    if auth.get("preparation") is not True or auth.get("read_only_quarantined_identity_verification") is not True:
        raise ExperimentStop("PREPARATION_APPROVAL_REQUIRED")
    if any(auth.get(k) is not False for k in ("network","acquisition","comparison_execution","research","production_activation","qualification","deletion")):
        raise ExperimentStop("AUTHORIZATION_EXPANSION")
    if auth.get("retention_deadline") != "2026-12-31" or date.today() > date(2026,12,31):
        raise ExperimentStop("RETENTION_EXPIRED_OR_MISMATCH")
    # Check sealed execution evidence and its transitive historical protocol bindings.
    for manifest in (POLICY/"quarantine_execution_v1/root_manifest.json", POLICY/"quarantine_protocol_v1/root_manifest.json"):
        for e in json.loads((root/manifest).read_text())["files"]:
            if sha(safe_path(root,e["path"])) != e["sha256"]:
                raise ExperimentStop("HISTORICAL_BINDING_MISMATCH")
    results = json.loads((root/POLICY/"quarantine_execution_v1/measured_results.json").read_text())
    db_path = safe_path(root,results["output_relative_path"])
    source = json.loads((root/POLICY/"isolated_comparison_v1/reacquisition_receipt.json").read_text())["packages"][1]
    expected = {
      "facts_filename":source["files"][0]["filename"],
      "facts_sha256":source["files"][0]["sha256"],
      "contracts_filename":source["files"][1]["filename"],
      "contracts_sha256":source["files"][1]["sha256"],
    }
    # Names in ProvenanceBinding are obtained from the existing implementation.
    targets = verify_targets(db_path,results["database_sha256"],expected)
    destination = Path(tempfile.mkdtemp(prefix="alternative-proposal-",dir=db_path.parent))
    target_path = destination/"private_targets.json"
    target_path.write_text(json.dumps({"status":"PRIVATE_PREPARATION_ONLY_NO_QUERY_AUTHORIZED","targets":targets},indent=2),encoding="utf-8")
    return {
      "schema_version":"alternative_target_verification_v1","status":"PASS_READ_ONLY_TWO_CONTRACT_DATES",
      "target_count":len(targets),"database_sha256":results["database_sha256"],
      "database_hash_before_after_match":True,"database_integrity":"PASS",
      "protocol_and_source_provenance":"PASS","date_restriction_preserved":True,
      "private_target_reference":target_path.relative_to(root).as_posix(),
      "private_target_sha256":sha(target_path),"identities_tracked":False,
      "network_transactions":0,"acquisition":False,"comparison_execution":False,
      "retention_deadline":"2026-12-31",
    }

if __name__ == "__main__":
    print(json.dumps(prepare(Path(__file__).resolve().parents[1]),indent=2))
