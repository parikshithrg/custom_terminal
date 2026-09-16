"""Offline R10N-I requalification under the unchanged R10N-H contracts.

The helpers require three explicit, sealed package paths. They perform no
network access, discovery, acquisition, ingestion, research, or activation.
Raw identities are used transiently for aggregate comparison and are never
returned by the public evidence model.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from market_intel.foundation.nse_fno_candidate import (
    MII_EXPIRY_ENCODING,
    MII_REQUIRED,
    OHLC_SEMANTICS_VERSION,
    UDIFF_REQUIRED,
    CandidateAdapterError,
    PackageDescriptor,
    adapt_package,
    build_package_descriptor,
    verify_package,
)
from tools.validate_nse_fno_r10nh import _source_price_digest, _digest


MILESTONE = "R.10N-I"
EXPECTED_DATES = ("2026-09-09", "2026-09-10", "2025-07-08")
EXPECTED_RELATIVE_PATHS = {
    day: f"artifacts/nse_fno_reports/{day}" for day in EXPECTED_DATES
}


class RequalificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PackageInput:
    trading_date: str
    relative_path: str
    manifest_sha256: str
    files: tuple[Mapping[str, Any], Mapping[str, Any]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sealed_inputs(project_root: Path, binding_path: Path) -> tuple[PackageInput, ...]:
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    rows = {row["trading_date"]: row for row in binding["packages"]}
    if tuple(day for day in EXPECTED_DATES if day in rows) != EXPECTED_DATES or set(rows) != set(EXPECTED_DATES):
        raise RequalificationError("SEALED_DATE_SET_MISMATCH")
    return tuple(PackageInput(
        day,
        EXPECTED_RELATIVE_PATHS[day],
        rows[day]["manifest_sha256"],
        tuple(rows[day]["files"]),
    ) for day in EXPECTED_DATES)


def preflight_packages(project_root: Path, inputs: tuple[PackageInput, ...]) -> tuple[dict, dict[str, PackageDescriptor]]:
    if tuple(item.trading_date for item in inputs) != EXPECTED_DATES:
        raise RequalificationError("INPUT_DATE_ORDER_OR_SCOPE_MISMATCH")
    descriptors: dict[str, PackageDescriptor] = {}
    evidence = []
    for item in inputs:
        if item.relative_path != EXPECTED_RELATIVE_PATHS[item.trading_date]:
            raise RequalificationError("PACKAGE_RELATIVE_PATH_MISMATCH")
        package = project_root / Path(item.relative_path)
        manifest_path = package / "manifest.json"
        if not package.is_dir() or not manifest_path.is_file():
            raise RequalificationError("PACKAGE_OR_MANIFEST_MISSING")
        if _sha256(manifest_path) != item.manifest_sha256:
            raise RequalificationError("SEALED_MANIFEST_HASH_MISMATCH")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("schema_version", "nse_fno_single_date_download_v1")
        descriptor = build_package_descriptor(package, trading_date=item.trading_date, manifest=manifest)
        sealed_by_name = {row["filename"]: row for row in item.files}
        if set(sealed_by_name) != {row.filename for row in descriptor.files}:
            raise RequalificationError("SEALED_FILENAME_SET_MISMATCH")
        for row in descriptor.files:
            sealed = sealed_by_name[row.filename]
            if sealed["byte_length"] != row.byte_length or sealed["sha256"] != row.sha256:
                raise RequalificationError("SEALED_FILE_BINDING_MISMATCH")
        verify_package(descriptor)
        descriptors[item.trading_date] = descriptor
        evidence.append({
            "trading_date": item.trading_date,
            "relative_path": item.relative_path + "/",
            "manifest_sha256": item.manifest_sha256,
            "files": [{
                "filename": row.filename,
                "byte_length": row.byte_length,
                "sha256": row.sha256,
                "official_url": row.official_url,
            } for row in descriptor.files],
            "sealed_binding": "MATCH",
        })
    return ({
        "schema_version": "r10ni_source_integrity_preflight_v1",
        "milestone": MILESTONE,
        "verified_before_row_access": True,
        "packages": evidence,
        "integrity_state": "PASS",
        "network_requests": 0,
    }, descriptors)


def _decimal_scales(records) -> dict[str, list[int]]:
    fields = ("open", "high", "low", "close", "settlement_price", "strike")
    result: dict[str, list[int]] = {}
    for field in fields:
        scales = set()
        for record in records:
            value = getattr(record, field)
            if hasattr(value, "state"):
                value = value.value
            if isinstance(value, Decimal):
                scales.add(max(0, -value.as_tuple().exponent))
        result[field] = sorted(scales)
    return result


def _contract_ids(descriptor: PackageDescriptor) -> set[str]:
    contract = next(item for item in descriptor.files if item.key == "mii")
    with gzip.open(descriptor.package_dir / contract.filename, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return {(row.get("FinInstrmId") or "").strip() for row in reader}


def date_acceptance(assessment: Mapping[str, Any]) -> dict[str, Any]:
    criteria = {
        "package_integrity": assessment.get("package_integrity") == "PASS",
        "required_schemas": assessment.get("required_schemas") == "PASS",
        "unique_identity_join": assessment.get("identity_join_rate") == "1",
        "expiry_agreement": assessment.get("expiry_agreement_rate") == "1",
        "no_fatal_condition": assessment.get("fatal_count") == 0,
        "no_qualification_blocking_diagnostic": assessment.get("blocking_diagnostic_count") == 0,
        "price_immutability": assessment.get("price_immutability") is True,
        "required_fields_explicit": assessment.get("required_fields_explicit") is True,
    }
    return {
        "criteria": criteria,
        "accepted": all(criteria.values()),
        "decision": "DATE_ACCEPTED" if all(criteria.values()) else "DATE_NOT_ACCEPTED",
    }


def _required_fields_explicit(quality: Mapping[str, Any], row_count: int) -> bool:
    names = (
        "trading_date", "financial_instrument_id", "expiry", "lot_size", "open", "high",
        "low", "close", "settlement_price", "volume", "open_interest",
    )
    return all(quality["fact_field_states"].get(name) == {"PRESENT": row_count} for name in names)


def evaluate_package(descriptor: PackageDescriptor) -> tuple[dict[str, Any], set[str]]:
    day = descriptor.trading_date.isoformat()
    try:
        result = adapt_package(descriptor)
    except CandidateAdapterError as exc:
        assessment = {
            "trading_date": day,
            "package_integrity": "PASS",
            "required_schemas": "NOT_COMPLETED_AFTER_FATAL",
            "fatal_count": 1,
            "fatal_code": exc.code,
            "blocking_diagnostic_count": 0,
            "diagnostic_counts": {},
            "source_qualified": False,
        }
        assessment["acceptance"] = date_acceptance(assessment)
        return assessment, set()

    quality = result.quality
    facts = next(item for item in descriptor.files if item.key == "udiff")
    source_digest = _source_price_digest(descriptor.package_dir, facts.filename)
    normalized_digest = _digest([
        (record.financial_instrument_id, tuple(format(value, "f") for value in (
            record.open, record.high, record.low, record.close, record.settlement_price,
        ))) for record in result.records
    ])
    options = [record for record in result.records if record.instrument_type in {"STO", "IDO"}]
    futures = [record for record in result.records if record.instrument_type in {"STF", "IDF"}]
    assessment = {
        "trading_date": day,
        "package_integrity": "PASS",
        "required_schemas": "PASS",
        "fatal_count": 0,
        "source_rows": dict(quality["source_rows"]),
        "normalized_rows": quality["normalized_rows"],
        "identity_join_rate": format(quality["identity_join"]["rate"], "f"),
        "expiry_agreement_rate": format(quality["expiry_encoding"]["agreement"]["rate"], "f"),
        "expiry_agreement": {
            "matched": quality["expiry_encoding"]["agreement"]["matched"],
            "mismatched": quality["expiry_encoding"]["agreement"]["mismatched"],
        },
        "instrument_counts": dict(quality["instrument_counts"]),
        "diagnostic_counts": dict(quality["diagnostic_counts"]),
        "blocking_diagnostic_count": quality["qualification"]["blocking_diagnostic_count"],
        "nonblocking_diagnostic_count": quality["qualification"]["informational_diagnostic_count"],
        "value_coverage": quality["fact_value_coverage"],
        "required_fields_explicit": _required_fields_explicit(quality, len(result.records)),
        "price_immutability": source_digest == normalized_digest,
        "price_digest": source_digest,
        "decimal_scales_observed": _decimal_scales(result.records),
        "lot_size": {
            "positive_rows": sum(record.lot_size > 0 for record in result.records),
            "nonpositive_rows": sum(record.lot_size <= 0 for record in result.records),
            "distinct_count": len({record.lot_size for record in result.records}),
        },
        "option_state_semantics": {
            "option_rows": len(options),
            "options_with_present_strike_and_type": sum(
                record.strike.state.value == "PRESENT" and record.option_type.state.value == "PRESENT"
                for record in options
            ),
            "futures_rows": len(futures),
            "futures_with_not_applicable_strike_and_type": sum(
                record.strike.state.value == "NOT_APPLICABLE" and record.option_type.state.value == "NOT_APPLICABLE"
                for record in futures
            ),
        },
        "schemas": {
            "udiff_columns": list(quality["schemas"]["udiff_columns"]),
            "mii_columns": list(quality["schemas"]["mii_columns"]),
        },
        "archive_structure": quality["archives"],
        "source_qualified": False,
    }
    assessment["acceptance"] = date_acceptance(assessment)
    return assessment, _contract_ids(descriptor)


def compare_schemas(assessments: list[Mapping[str, Any]]) -> dict[str, Any]:
    successful = [row for row in assessments if row.get("required_schemas") == "PASS"]
    if len(successful) != len(EXPECTED_DATES):
        return {"state": "INCOMPLETE_DUE_TO_FATAL_DATE", "stable": False}
    anchor = successful[0]["schemas"]
    dates = []
    for row in successful:
        udiff = set(row["schemas"]["udiff_columns"])
        mii = set(row["schemas"]["mii_columns"])
        dates.append({
            "trading_date": row["trading_date"],
            "udiff_column_count": len(udiff),
            "mii_column_count": len(mii),
            "udiff_missing_required": sorted(UDIFF_REQUIRED - udiff),
            "mii_missing_required": sorted(MII_REQUIRED - mii),
            "udiff_nonrequired_added_vs_anchor": sorted(udiff - set(anchor["udiff_columns"])),
            "udiff_nonrequired_removed_vs_anchor": sorted(set(anchor["udiff_columns"]) - udiff),
            "mii_nonrequired_added_vs_anchor": sorted(mii - set(anchor["mii_columns"])),
            "mii_nonrequired_removed_vs_anchor": sorted(set(anchor["mii_columns"]) - mii),
            "decimal_scales_observed": row["decimal_scales_observed"],
        })
    stable = all(
        not any(item[key] for key in (
            "udiff_missing_required", "mii_missing_required",
            "udiff_nonrequired_added_vs_anchor", "udiff_nonrequired_removed_vs_anchor",
            "mii_nonrequired_added_vs_anchor", "mii_nonrequired_removed_vs_anchor",
        )) for item in dates
    )
    return {
        "schema_version": "r10ni_cross_date_schema_comparison_v1",
        "milestone": MILESTONE,
        "required_and_full_column_sets_stable": stable,
        "type_contract": "STRICT_ADAPTER_PARSE_PASS_ALL_DATES",
        "precision_contract": "EXACT_DECIMAL_PRESERVED_OBSERVED_SCALES_REPORTED_PER_DATE",
        "dates": dates,
        "stable": stable,
    }


def compare_contract_populations(contract_ids: Mapping[str, set[str]]) -> dict[str, Any]:
    if set(contract_ids) != set(EXPECTED_DATES):
        return {"state": "INCOMPLETE_DUE_TO_FATAL_DATE", "full_contract_inventories_persisted": False}
    anchor = contract_ids[EXPECTED_DATES[0]]
    comparisons = []
    for day in EXPECTED_DATES[1:]:
        current = contract_ids[day]
        comparisons.append({
            "anchor_date": EXPECTED_DATES[0],
            "comparison_date": day,
            "anchor_count": len(anchor),
            "comparison_count": len(current),
            "intersection_count": len(anchor & current),
            "additions_count": len(current - anchor),
            "removals_count": len(anchor - current),
        })
    return {
        "schema_version": "r10ni_contract_population_comparison_v1",
        "milestone": MILESTONE,
        "date_counts": {day: len(contract_ids[day]) for day in EXPECTED_DATES},
        "all_three_intersection_count": len(set.intersection(*(contract_ids[day] for day in EXPECTED_DATES))),
        "comparisons_to_anchor": comparisons,
        "ordinary_contract_turnover_is_correction_evidence": False,
        "full_contract_inventories_persisted": False,
        "raw_identifiers_persisted": False,
    }


def source_decision(assessments: list[Mapping[str, Any]], schema_comparison: Mapping[str, Any]) -> dict[str, Any]:
    all_accepted = len(assessments) == len(EXPECTED_DATES) and all(
        row.get("acceptance", {}).get("accepted") for row in assessments
    )
    schema_stable = schema_comparison.get("stable") is True
    if all_accepted and schema_stable:
        decision = "MULTI_DATE_SOURCE_QUALIFIED_FOR_BOUNDED_INGESTION_DESIGN"
    elif schema_stable:
        decision = "MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"
    else:
        decision = "MULTI_DATE_SOURCE_NOT_QUALIFIED"
    return {
        "schema_version": "r10ni_source_lifecycle_decision_v1",
        "milestone": MILESTONE,
        "date_decisions": [{
            "trading_date": row["trading_date"],
            "accepted": row.get("acceptance", {}).get("accepted", False),
        } for row in assessments],
        "all_dates_accepted": all_accepted,
        "schemas_stable": schema_stable,
        "partial_source_qualification_permitted": False,
        "source_qualified": all_accepted and schema_stable,
        "decision": decision,
        "production_activated": False,
        "research_authorized": False,
    }


def run_requalification(project_root: Path, inputs: tuple[PackageInput, ...]) -> dict[str, Any]:
    preflight, descriptors = preflight_packages(project_root, inputs)
    assessments = []
    contract_ids: dict[str, set[str]] = {}
    for day in EXPECTED_DATES:
        assessment, identities = evaluate_package(descriptors[day])
        assessments.append(assessment)
        if identities:
            contract_ids[day] = identities
    schemas = compare_schemas(assessments)
    populations = compare_contract_populations(contract_ids)
    decision = source_decision(assessments, schemas)
    return {
        "contracts": {
            "ohlc_semantics": OHLC_SEMANTICS_VERSION,
            "mii_expiry_encoding": MII_EXPIRY_ENCODING,
            "diagnostic_schema": "r10nh_diagnostic_schema_v1",
            "adapter_changed": False,
        },
        "preflight": preflight,
        "per_date": assessments,
        "schemas": schemas,
        "populations": populations,
        "decision": decision,
    }
