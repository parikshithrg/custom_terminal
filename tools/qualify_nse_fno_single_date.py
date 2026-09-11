"""Reconcile the fixed R10N-B evidence through the shared candidate adapter.

This module remains an offline evidence command. It is not an acquisition,
application, research, or production entrypoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from market_intel.foundation.nse_fno_candidate import (
    CandidateAdapterError,
    adapt_package,
    build_package_descriptor,
    expected_package_files,
)


TRADING_DATE = date(2026, 9, 9)
_PLAN = expected_package_files(TRADING_DATE)
UDIFF_FILENAME = _PLAN[0][1]
UDIFF_MEMBER = UDIFF_FILENAME.removesuffix(".zip")
MII_FILENAME = _PLAN[1][1]
EXPECTED_URLS = {item[1]: item[2] for item in _PLAN}
PRIVATE_PATH = re.compile(r"(?i)(?:[a-z]:\\\\users\\\\|/users/|/home/)")
SECRET_ASSIGNMENT = re.compile(r"(?i)(?:authorization|cookie|password|token|secret)\s*[:=]")
QualificationError = CandidateAdapterError


def _load_manifest(package: Path) -> dict:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest.setdefault("schema_version", "nse_fno_single_date_download_v1")
    return manifest


def _states(source: dict, mapping: dict[str, str]) -> dict:
    return {target: source[name] for target, name in mapping.items()}


def qualify_package(package: Path) -> dict[str, dict]:
    """Reproduce the R10N-B evidence model through the shared strict adapter."""
    manifest = _load_manifest(package)
    descriptor = build_package_descriptor(
        package, trading_date=TRADING_DATE.isoformat(), manifest=manifest,
    )
    result = adapt_package(descriptor)
    quality = result.quality
    facts = descriptor.files[0]
    udiff_archive = quality["archives"]["udiff"]
    mii_archive = quality["archives"]["mii"]
    fact_states = _states(quality["fact_field_states"], {
        "trade_date": "trading_date", "expiry": "expiry", "id": "financial_instrument_id",
        "strike": "strike", "option_type": "option_type", "lot_size": "lot_size",
        "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close",
        "SttlmPric": "settlement_price", "OpnIntrst": "open_interest", "TtlTradgVol": "volume",
    })
    contract_states = _states(quality["contract_field_states"], {
        "id": "id", "expiry": "expiry", "lot": "lot_size",
        "strike": "strike", "option": "option_type",
    })
    coverage = _states(quality["fact_value_coverage"], {
        "OpnIntrst": "open_interest", "SttlmPric": "settlement_price", "TtlTradgVol": "volume",
    })
    acquisition = {
        "schema_version": "r10nb_acquisition_v1", "milestone": "R.10N-B",
        "trading_date": TRADING_DATE.isoformat(),
        "acquisition_mode": "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION",
        "files": [{
            "filename": item.filename, "official_url": item.official_url,
            "byte_length": item.byte_length, "sha256": item.sha256,
        } for item in descriptor.files],
        "manifest_terms_acknowledged_by_operator": bool(manifest.get("terms_acknowledged_by_operator")),
        "owner_confirmation_received_in_r10nb_chat": True,
        "qualification_input": "PREEXISTING_HASH_BOUND_PACKAGE",
        "post_confirmation_acquisition_performed": False,
        "post_confirmation_downloader_outcome": "REFUSED_EXISTING_PACKAGE_BEFORE_NETWORK",
        "post_confirmation_network_requests": 0,
        "owner_scope": "NON_COMMERCIAL_INTERNAL_TECHNICAL_QUALIFICATION_ONLY",
        "redistribution_authorized": False, "bulk_acquisition_authorized": False,
        "research_or_production_authorized": False, "trading_authorized": False,
    }
    schema = {
        "schema_version": "r10nb_observed_schema_v1",
        "udiff": {
            "family": "UDIFF",
            "archive_member": {
                "name": udiff_archive["member_name"],
                "compressed_bytes": udiff_archive["compressed_bytes"],
                "expanded_bytes": udiff_archive["expanded_bytes"],
                "crc32": udiff_archive["crc32"],
            },
            "column_count": len(quality["schemas"]["udiff_columns"]),
            "columns": list(quality["schemas"]["udiff_columns"]),
        },
        "mii": {
            "family": "MII_CONTRACT", "compression": "gzip",
            "archive": {
                "compressed_bytes": mii_archive["compressed_bytes"],
                "expanded_bytes": mii_archive["expanded_bytes"],
            },
            "column_count": len(quality["schemas"]["mii_columns"]),
            "columns": list(quality["schemas"]["mii_columns"]),
        },
        "join_key": ["FinInstrmId"], "legacy_schema_parsed": False,
    }
    source_rows = quality["source_rows"]
    instrument_counts = quality["instrument_counts"]
    measured = {
        "schema_version": "r10nb_quality_metrics_v1",
        "source_rows": dict(source_rows),
        "normalized_rows": {"udiff": quality["normalized_rows"], "mii": source_rows["mii"]},
        "instrument_counts": {
            "futures": instrument_counts["futures"], "options": instrument_counts["options"], "other": 0,
        },
        "identity_join": {
            "matched": quality["identity_join"]["matched"], "missing_key": 0,
            "ambiguous": 0, "unresolved": 0, "rate": 1.0,
        },
        "contract_identity": {
            "unique_ids": source_rows["mii"], "duplicate_keys": 0, "malformed_rows": 0,
        },
        "malformed_fact_rows": 0, "ohlc_inconsistent_rows": 0,
        "trade_date_counts": {TRADING_DATE.isoformat(): source_rows["udiff"]},
        "fact_field_states": fact_states,
        "contract_field_states": contract_states,
        "fact_value_coverage": coverage,
        "bounded_sanitized_examples": [],
        "correction_finality": {
            "filename_marks_final": "_F_" in facts.filename,
            "single_observation_can_establish_later_corrections": False,
        },
    }
    completion = {
        "schema_version": "r10nb_completion_v1", "milestone": "R.10N-B",
        "single_date_only": True, "files_qualified": 2,
        "post_confirmation_acquisition_performed": False,
        "qualified_preexisting_hash_bound_package": True,
        "raw_rows_retained_in_evidence": False, "holdout_accessed": False,
        "local_fno_database_accessed": False, "kite_used": False, "apsw_used": False,
        "research_backtest_scoring_recommendation_or_trading": False,
        "validation": {
            "focused_r10nb_downloader_r10na": "46_PASS",
            "relevant_fno_governance": "41_PASS",
            "root_pre_entrypoint_correction": "830_PASS_4_FAIL_4_SKIP_7_WARN",
            "root_pre_entrypoint_failures": [
                "TWO_NEW_ENTRYPOINT_INVENTORY_DIAGNOSTICS_CORRECTED_WITHOUT_CHANGING_INVENTORY",
                "TWO_PRE_EXISTING_R9K_NATIVE_SLEEP_NEGATIVE_0_003_SECOND_DIAGNOSTICS",
            ],
            "root_final": "833_PASS_1_FAIL_4_SKIP_7_WARN",
            "root_final_failure": "PRE_EXISTING_R9K_JOB_CLOSE_NEGATIVE_0_003_SECOND_TIMING_DIAGNOSTIC",
            "r10nb_related_root_failures": 0,
        },
        "reproducibility_limitations": [
            "Source payloads remain local and ignored by Git.",
            "One date cannot establish historical schema stability or correction behavior.",
            "Permission is limited to the owner's stated non-commercial technical qualification scope.",
        ],
        "completion_decision": "SINGLE_DATE_PACKAGE_TECHNICALLY_QUALIFIED",
    }
    return {
        "acquisition.json": acquisition, "observed_schema.json": schema,
        "quality_metrics.json": measured, "completion.json": completion,
    }


def _canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()


def write_evidence(package: Path, output: Path) -> dict:
    artifacts = qualify_package(package)
    output.mkdir(parents=True, exist_ok=False)
    bindings = []
    for name, value in artifacts.items():
        payload = _canonical_bytes(value)
        (output / name).write_bytes(payload)
        bindings.append({"path": name, "sha256": hashlib.sha256(payload).hexdigest(), "byte_length": len(payload)})
    root = {
        "schema_version": "r10nb_root_manifest_v1", "milestone": "R.10N-B",
        "artifacts": sorted(bindings, key=lambda item: item["path"]),
        "source_bindings": artifacts["acquisition.json"]["files"],
    }
    text = _canonical_bytes(root).decode()
    if PRIVATE_PATH.search(text) or SECRET_ASSIGNMENT.search(text):
        raise QualificationError("UNSANITIZED_EVIDENCE", "evidence contains private-path or credential material")
    (output / "root_manifest.json").write_text(text, encoding="utf-8", newline="\n")
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    write_evidence(args.package, args.output)
    return 0
