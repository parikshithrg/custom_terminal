"""Owner-gated offline coverage experiment; never a source provider."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import stat
import tempfile
import zipfile
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from market_intel.foundation.nse_fno_candidate import (
    FieldValue, adapt_package, build_package_descriptor, verify_package,
)
from tools.download_nse_fno_reports import ArchiveLimits, _validate_archive, build_plan
from tools.validate_nse_fno_r10nh import _digest, _source_price_digest

POLICY = Path("docs/investigations/post_r10ni_policy")
EXEC = POLICY / "quarantine_execution_v1"
PROTOCOL = POLICY / "quarantine_protocol_v1"
PROTOCOL_HASH = "1178cceee77ad5e95ebc67e54466a4a8ceafbbddde2cdfede0e2b4b0098dd658"
FIELDS = ("open", "high", "low", "close", "settlement_price", "volume",
          "open_interest", "expiry", "strike", "option_type", "lot_size")
CLOSE = "CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS"
ATTRIBUTION = "TRADE_STATE_ATTRIBUTION_UNAVAILABLE"
ALLOWED_CODES = {CLOSE, ATTRIBUTION, "ZERO_VOLUME_PRICE_STATE",
                 "SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS"}
MATCH_KEYS = ("exchange", "instrument_class", "underlying", "expiry", "option_type",
              "strike", "trading_date", "session", "units", "field_semantics")
RESULT = "MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"

class ExperimentStop(RuntimeError):
    pass

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def safe_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ExperimentStop("UNSAFE_PATH")
    root = root.absolute()
    path = root / relative
    for p in (root, *root.parents):
        if p.exists():
            s = p.lstat()
            if p.is_symlink() or getattr(s, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ExperimentStop("REPARSE_PATH")
    current = root
    for part in relative.parts:
        current /= part
        if current.exists() or current.is_symlink():
            s = current.lstat()
            if current.is_symlink() or getattr(s, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ExperimentStop("REPARSE_PATH")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ExperimentStop("PATH_ESCAPE")
    return path

def approval(root):
    p = root / PROTOCOL / "protocol.json"
    a = load(root / EXEC / "owner_authorization.json")
    if sha(p) != PROTOCOL_HASH or a.get("protocol_sha256") != PROTOCOL_HASH:
        raise ExperimentStop("PROTOCOL_HASH_MISMATCH")
    for gate in ("experiment_implementation", "consumer_scope", "materiality_thresholds"):
        if a.get(gate) is not True:
            raise ExperimentStop("OWNER_APPROVAL_REQUIRED")
    if a.get("consumers") != ["OFFLINE_COVERAGE_AUDIT", "OFFLINE_CONTRACT_DATE_COMPLETENESS"]:
        raise ExperimentStop("CONSUMER_SCOPE_MISMATCH")
    if a.get("thresholds") != "UNCHANGED_ZERO_LOSS_PROTOCOL_THRESHOLDS":
        raise ExperimentStop("THRESHOLD_MISMATCH")
    if any(a.get(g) is not False for g in ("network", "alternative_source_access", "research", "production", "qualification", "deletion")):
        raise ExperimentStop("AUTHORIZATION_EXPANSION")
    if date.today() > date.fromisoformat(a["retention_deadline"]):
        raise ExperimentStop("RETENTION_EXPIRED")
    protocol = load(p)
    if a["retention_deadline"] != protocol["retention_deadline"]:
        raise ExperimentStop("RETENTION_MISMATCH")
    return protocol

def preflight(root, protocol):
    # Bind historical evidence, adapter and approval inputs before any row evaluation.
    for mpath in (root / PROTOCOL / "root_manifest.json", root / EXEC / "input_root_manifest.json"):
        for entry in load(mpath)["files"]:
            if sha(safe_path(root, entry["path"])) != entry["sha256"]:
                raise ExperimentStop("EVIDENCE_BINDING_MISMATCH")
    receipt = load(root / POLICY / "isolated_comparison_v1/reacquisition_receipt.json")
    sealed = load(root / "docs/investigations/r10n_i/requalification_v1/source_integrity_preflight.json")
    bindings = load(root / EXEC / "input_manifest_bindings.json")
    days = protocol["exact_dates"]
    if days != receipt["exact_dates"] or days != [p["trading_date"] for p in sealed["packages"]]:
        raise ExperimentStop("DATE_SCOPE_MISMATCH")
    if bindings["relative_root"] != receipt["relative_root"] or [b["trading_date"] for b in bindings["manifest_bindings"]] != days:
        raise ExperimentStop("MANIFEST_SCOPE_MISMATCH")
    base = safe_path(root, receipt["relative_root"])
    if {p.name for p in base.iterdir()} != set(days):
        raise ExperimentStop("UNEXPECTED_INPUT_CONTENTS")
    evidence, descriptors = [], {}
    for received, old, binding in zip(receipt["packages"], sealed["packages"], bindings["manifest_bindings"]):
        day = received["trading_date"]
        relative = receipt["relative_root"] + "/" + day
        package = safe_path(root, relative)
        manifest_path = safe_path(root, relative + "/manifest.json")
        if binding["relative_path"] != relative + "/manifest.json" or sha(manifest_path) != binding["sha256"]:
            raise ExperimentStop("NEW_MANIFEST_HASH_MISMATCH")
        manifest = load(manifest_path)
        descriptor = build_package_descriptor(package, trading_date=day, manifest=manifest)
        expected = {f["filename"]: f for f in old["files"]}
        received_by_name = {f["filename"]: f for f in received["files"]}
        if set(expected) != set(received_by_name) or {p.name for p in package.iterdir()} != set(expected) | {"manifest.json"}:
            raise ExperimentStop("FILE_SET_MISMATCH")
        if manifest.get("report_selection") != "both":
            raise ExperimentStop("MANIFEST_SELECTION_MISMATCH")
        specs = build_plan(date.fromisoformat(day))
        archives = {}
        for item, spec in zip(descriptor.files, specs):
            path = safe_path(root, relative + "/" + item.filename)
            old_file = expected[item.filename]
            new_file = received_by_name[item.filename]
            if (item.byte_length, item.sha256) != (old_file["byte_length"], old_file["sha256"]) or (new_file["byte_length"], new_file["sha256"]) != (item.byte_length, item.sha256):
                raise ExperimentStop("PAYLOAD_BINDING_MISMATCH")
            if item.official_url != spec.url or new_file["source_url"] != spec.url:
                raise ExperimentStop("OFFICIAL_URL_MISMATCH")
            m = next(f for f in manifest["files"] if f["filename"] == item.filename)
            if m["role"] != spec.role or m["resolved_url"] != spec.url:
                raise ExperimentStop("MANIFEST_ROLE_OR_URL_MISMATCH")
            archives[item.key] = _validate_archive(path, spec, ArchiveLimits(8, 67108864, 250))
        verify_package(descriptor)
        descriptors[day] = descriptor
        evidence.append({"trading_date": day, "manifest_sha256": binding["sha256"],
                         "payload_bindings": "MATCH_RECEIPT_AND_SEALED_EVIDENCE", "archives": archives})
    return evidence, descriptors

def corroborate(left, right):
    if any(k not in left or k not in right or left[k] is None or right[k] is None or left[k] != right[k] for k in MATCH_KEYS):
        raise ExperimentStop("CORROBORATION_KEY_OR_SEMANTICS_MISMATCH")
    if right.get("authorized") is not True or not right.get("provenance"):
        raise ExperimentStop("CORROBORATION_PERMISSION_OR_PROVENANCE_MISSING")
    return {"matched": True, "independence": "NOT_ESTABLISHED"}

def mapping(records, diagnostics, row_ids):
    keyed = {r.financial_instrument_id: r for r in records}
    if len(keyed) != len(records):
        raise ExperimentStop("DUPLICATE_IDENTITY")
    quarantine, date_restrictions = {}, []
    for d in diagnostics:
        if d["code"] not in ALLOWED_CODES:
            raise ExperimentStop("UNEXPECTED_DIAGNOSTIC")
        row = d["row_number"]
        if d["code"] == ATTRIBUTION:
            if row is not None or not d["qualification_blocking"]:
                raise ExperimentStop("DATE_DIAGNOSTIC_SCOPE_MISMATCH")
            date_restrictions.append(d)
        elif d["code"] == CLOSE:
            fid = row_ids.get(row)
            if fid not in keyed or not d["qualification_blocking"] or fid in quarantine:
                raise ExperimentStop("QUARANTINE_IDENTITY_MISMATCH")
            quarantine[fid] = d
        elif row not in row_ids or row_ids[row] not in keyed or d["qualification_blocking"]:
            raise ExperimentStop("NONBLOCKING_DIAGNOSTIC_MISMATCH")
    if bool(quarantine) != bool(date_restrictions) or len(date_restrictions) > 1:
        raise ExperimentStop("DATE_ATTRIBUTION_MISSING")
    return quarantine, date_restrictions

def states(records, field):
    count = Counter()
    for r in records:
        value = getattr(r, field)
        if isinstance(value, FieldValue):
            count[value.state.value] += 1
        elif value is None:
            count["MISSING"] += 1
        else:
            count["PRESENT"] += 1
        scalar = value.value if isinstance(value, FieldValue) else value
        if isinstance(scalar, (int, Decimal)) and scalar == 0:
            count["ZERO_VALUE"] += 1
    return dict(sorted(count.items()))

def consumer_checks(records, mask, restrictions, diagnostics, row_ids, integrity_ok):
    kept = tuple(r for r in records if r.financial_instrument_id not in mask)
    original_by_id = {r.financial_instrument_id: r for r in records}
    a = audit(records, mask, bool(restrictions))
    checks = {
        "test_integrity_before_normalization": integrity_ok,
        "test_quarantine_count_reconciliation": len(mask) == sum(d["code"] == CLOSE for d in diagnostics) == a["missing_contract_dates"],
        "test_field_missingness_denominators": all(v["denominator"] == len(records) and sum(n for s,n in v["baseline_states"].items() if s != "ZERO_VALUE") == len(records) and sum(n for s,n in v["filtered_states"].items() if s != "ZERO_VALUE") + len(mask) == len(records) for v in a["field_missingness"].values()),
        "test_contract_date_unique_mapping": len({r.financial_instrument_id for r in records}) == len(records) and set(mask).issubset(row_ids.values()),
        "test_date_attribution_persists": bool(restrictions) == any(d["code"] == ATTRIBUTION for d in diagnostics),
        "test_no_fill_or_price_mutation": all(r is original_by_id[r.financial_instrument_id] for r in kept),
    }
    if not all(checks.values()):
        raise ExperimentStop("CONSUMER_INVARIANT_FAILURE")
    return [{"id": key, "baseline": "PASS", "experimental": "PASS", "expected_mask_difference": False} for key in checks]

def audit(records, mask, restricted):
    kept = tuple(r for r in records if r.financial_instrument_id not in mask)
    n, q = len(records), len(records) - len(kept)
    fields = {}
    for field in FIELDS:
        b, e = states(records, field), states(kept, field)
        bu = b.get("MISSING", 0) + b.get("MALFORMED", 0)
        eu = e.get("MISSING", 0) + e.get("MALFORMED", 0) + q
        fields[field] = {"baseline_states": b, "filtered_states": e,
            "baseline_unavailable": bu, "experimental_unavailable_including_gaps": eu,
            "quarantine_gaps": q, "denominator": n,
            "missingness_increase_percentage_points": str(Decimal(100) * (eu - bu) / n) if n else None}
    return {"baseline_contract_dates": n, "filtered_contract_dates": len(kept),
            "quarantined_contract_dates": q, "missing_contract_dates": q,
            "row_coverage_loss_percent": str(Decimal(100) * q / n) if n else None,
            "restricted_date_baseline_rows": n if restricted else 0,
            "restricted_date_filtered_rows": len(kept) if restricted else 0,
            "field_missingness": fields,
            "coverage_materiality": "NOT_EVALUATED" if not n else ("MATERIAL_FOR_COVERAGE" if q else "ZERO_LOSS_NOT_SEMANTIC_ACCEPTANCE")}

def store(db_path, days):
    if db_path.exists():
        raise ExperimentStop("OUTPUT_OVERWRITE_REFUSED")
    # Exclusive reservation prevents accidentally opening any existing database.
    with db_path.open("xb"):
        pass
    with sqlite3.connect(db_path) as db:
        db.executescript("""
        CREATE TABLE facts(day TEXT, fid TEXT, instrument_class TEXT, fact_json TEXT, PRIMARY KEY(day,fid));
        CREATE TABLE quarantine(day TEXT, fid TEXT, reason TEXT, source_row INTEGER, provenance_json TEXT, PRIMARY KEY(day,fid));
        CREATE TABLE diagnostics(day TEXT, code TEXT, source_row INTEGER, blocking INTEGER, diagnostic_json TEXT);
        CREATE TABLE date_restrictions(day TEXT PRIMARY KEY, reason TEXT);
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT);
        CREATE VIEW experimental_row_filtered AS SELECT f.*, EXISTS(SELECT 1 FROM date_restrictions d WHERE d.day=f.day) AS date_restricted
          FROM facts f WHERE NOT EXISTS(SELECT 1 FROM quarantine q WHERE q.day=f.day AND q.fid=f.fid);
        """)
        for day, records, diagnostics, mask, restrictions in days:
            db.executemany("INSERT INTO facts VALUES (?,?,?,?)",
                ((day, r.financial_instrument_id, r.instrument_type, json.dumps(r.deterministic(), sort_keys=True)) for r in records))
            keyed = {r.financial_instrument_id:r for r in records}
            db.executemany("INSERT INTO quarantine VALUES (?,?,?,?,?)",
                ((day, fid, d["code"], d["row_number"], json.dumps(keyed[fid].provenance.deterministic(), sort_keys=True)) for fid,d in mask.items()))
            db.executemany("INSERT INTO diagnostics VALUES (?,?,?,?,?)",
                ((day,d["code"],d["row_number"],int(d["qualification_blocking"]),json.dumps(d,sort_keys=True)) for d in diagnostics))
            if restrictions:
                db.execute("INSERT INTO date_restrictions VALUES (?,?)",(day,ATTRIBUTION))
        db.executemany("INSERT INTO metadata VALUES (?,?)", [
            ("status","EXPERIMENTAL_UNAVAILABLE_TO_PRODUCTION_OR_RESEARCH"),("protocol_sha256",PROTOCOL_HASH),
            ("source_result",RESULT),("retention_deadline","2026-12-31")])
        for table in ("facts","quarantine","diagnostics","date_restrictions","metadata"):
            for operation in ("UPDATE","DELETE","INSERT"):
                db.execute(f"CREATE TRIGGER lock_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_EXPERIMENT'); END")
        for day,records,diagnostics,mask,restrictions in days:
            stored = dict(db.execute("SELECT fid,fact_json FROM facts WHERE day=?",(day,)))
            if stored != {r.financial_instrument_id:json.dumps(r.deterministic(),sort_keys=True) for r in records}:
                raise ExperimentStop("STORED_FACT_MUTATION")
            if db.execute("SELECT count(*) FROM experimental_row_filtered WHERE day=?",(day,)).fetchone()[0] != len(records)-len(mask):
                raise ExperimentStop("STORED_MASK_MISMATCH")
            if dict(db.execute("SELECT code,count(*) FROM diagnostics WHERE day=? GROUP BY code",(day,))) != dict(Counter(d["code"] for d in diagnostics)):
                raise ExperimentStop("STORED_DIAGNOSTIC_MISMATCH")
            if db.execute("SELECT count(*) FROM experimental_row_filtered WHERE day=? AND date_restricted=1",(day,)).fetchone()[0] != (len(records)-len(mask) if restrictions else 0):
                raise ExperimentStop("STORED_DATE_RESTRICTION_MISMATCH")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ExperimentStop("DATABASE_INTEGRITY_FAILURE")

def execute(root, normalizer=adapt_package):
    root = Path(root)
    protocol = approval(root)
    integrity, descriptors = preflight(root, protocol)
    old = {r["trading_date"]: r for r in load(root / "docs/investigations/r10n_i/requalification_v1/per_date_qualification_results.json")["dates"]}
    prices = {r["trading_date"]: r["source_and_normalized_digest"] for r in load(root / "docs/investigations/r10n_i/requalification_v1/price_immutability_results.json")["dates"]}
    days, reports, all_records, all_mask = [], [], [], {}
    columns = None
    for day, descriptor in descriptors.items():
        result = normalizer(descriptor)
        quality, records = result.quality, result.records
        schemas = quality["schemas"]
        schema_tuple = (tuple(schemas["udiff_columns"]),tuple(schemas["mii_columns"]))
        if columns is None:
            columns = schema_tuple
        if schema_tuple != columns or tuple(map(len,schema_tuple)) != (34,150):
            raise ExperimentStop("SCHEMA_MISMATCH")
        if len(records) != old[day]["normalized_rows"] or dict(quality["diagnostic_counts"]) != old[day]["diagnostic_counts"]:
            raise ExperimentStop("DIAGNOSTIC_OR_ROW_COUNT_MISMATCH")
        if quality["identity_join"]["rate"] != 1 or quality["expiry_encoding"]["agreement"]["mismatched"] != 0:
            raise ExperimentStop("JOIN_OR_EXPIRY_MISMATCH")
        facts = next(f for f in descriptor.files if f.key == "udiff")
        source_digest = _source_price_digest(descriptor.package_dir, facts.filename)
        digest = _digest([(r.financial_instrument_id,tuple(format(getattr(r,f),"f") for f in FIELDS[:5])) for r in records])
        if digest != source_digest or digest != prices[day]:
            raise ExperimentStop("PRICE_DIGEST_CHANGE")
        row_ids = {}
        with zipfile.ZipFile(descriptor.package_dir / facts.filename) as archive:
            with archive.open(facts.filename.removesuffix(".zip")) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8-sig",newline=""))
                for row_number,row in enumerate(reader,start=2):
                    if row["TradDt"].strip() != day:
                        raise ExperimentStop("EMBEDDED_DATE_MISMATCH")
                    row_ids[row_number] = row["FinInstrmId"].strip()
        if len(row_ids) != len(records) or len(set(row_ids.values())) != len(records):
            raise ExperimentStop("ROW_LOCATOR_MISMATCH")
        diagnostics = list(quality["diagnostics"])
        mask, restrictions = mapping(records,diagnostics,row_ids)
        # Synthetic pooled keys are transient; no identifiers appear in reports.
        pooled_records = []
        from dataclasses import replace
        for r in records:
            pooled_records.append(replace(r,financial_instrument_id=day+":"+r.financial_instrument_id))
        all_records.extend(pooled_records)
        all_mask.update({day+":"+fid:d for fid,d in mask.items()})
        by_class = {kind:audit(tuple(r for r in records if r.instrument_type==kind),mask,bool(restrictions)) for kind in sorted({r.instrument_type for r in records})}
        a = audit(records,mask,bool(restrictions))
        consumer_tests = consumer_checks(records,mask,restrictions,diagnostics,row_ids,True)
        consumer_tests.append({"id":"contract_date_no_loss_threshold","baseline":"PASS","experimental":"FAIL" if mask else "PASS","expected_mask_difference":bool(mask)})
        reports.append({"trading_date":day,"audit":a,"by_instrument_class":by_class,
            "diagnostic_counts":dict(quality["diagnostic_counts"]),"date_attribution_diagnostic_preserved":bool(restrictions),
            "original_acceptance":old[day]["decision"],"source_price_digest":source_digest,"normalized_price_digest":digest,
            "embedded_dates":"PASS_ALL_ROWS","identity_and_expiry":"PASS",
            "consumer_tests":consumer_tests,"unexpected_consumer_invariant_differences":0})
        days.append((day,records,diagnostics,mask,restrictions))
    parent = safe_path(root,load(root / EXEC / "input_manifest_bindings.json")["relative_root"])
    destination = Path(tempfile.mkdtemp(prefix="experiment-",dir=parent))
    db_path = destination / "quarantine.sqlite"
    store(db_path,days)
    pooled = audit(tuple(all_records),all_mask,False)
    pooled["restricted_date_baseline_rows"] = sum(r["audit"]["restricted_date_baseline_rows"] for r in reports)
    pooled["restricted_date_filtered_rows"] = sum(r["audit"]["restricted_date_filtered_rows"] for r in reports)
    return {"schema_version":"isolated_quarantine_execution_results_v1","status":"COMPLETED_OFFLINE_AUDITS",
        "protocol_sha256":PROTOCOL_HASH,"integrity":integrity,"dates":reports,"pooled":pooled,
        "output_relative_path":db_path.relative_to(root).as_posix(),"database_sha256":sha(db_path),
        "output_status":"EXPERIMENTAL_UNAVAILABLE_TO_PRODUCTION_OR_RESEARCH",
        "corroboration":{"status":"NOT_EVALUATED_NO_AUTHORIZED_EVIDENCE","independence":"NOT_ESTABLISHED"},
        "materiality":"MATERIAL_FOR_COVERAGE_UNDER_APPROVED_ZERO_LOSS_THRESHOLDS",
        "source_result":RESULT,"source_qualified":False,"production_exposed":False,
        "network_requests":0,"price_substitution":False,"fingerprint_refreshed":False,
        "research":False,"historical_acceptance_changed":False,"retention_deadline":"2026-12-31","deletion":False}

if __name__ == "__main__":
    print(json.dumps(execute(Path(__file__).resolve().parents[1]),indent=2))
