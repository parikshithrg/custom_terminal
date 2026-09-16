"""Offline tests and evidence governance for R10N-I requalification."""

from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import pytest

import tools.requalify_nse_fno_r10ni as r10ni


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "investigations" / "r10n_i" / "requalification_v1"
SEALED = [
    ROOT / "docs" / "investigations" / name / subdir
    for name, subdir in (
        ("r10n_b", "qualification_v1"),
        ("r10n_c", "adapter_v1"),
        ("r10n_d", "plan_v1"),
        ("r10n_d", "amendment_v1"),
        ("r10n_e", "preflight_v1"),
        ("r10n_e", "qualification_v1"),
        ("r10n_f", "diagnosis_v1"),
        ("r10n_g", "semantics_v1"),
        ("r10n_h", "implementation_v1"),
    )
]


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _assessment(day: str, *, fatal: int = 0, blocking: int = 0, nonblocking: int = 2) -> dict:
    row = {
        "trading_date": day,
        "package_integrity": "PASS",
        "required_schemas": "PASS",
        "identity_join_rate": "1",
        "expiry_agreement_rate": "1",
        "fatal_count": fatal,
        "blocking_diagnostic_count": blocking,
        "nonblocking_diagnostic_count": nonblocking,
        "diagnostic_counts": {"ZERO_VOLUME_PRICE_STATE": nonblocking} if nonblocking else {},
        "price_immutability": True,
        "required_fields_explicit": True,
    }
    row["acceptance"] = r10ni.date_acceptance(row)
    return row


def test_fatal_and_blocking_diagnostics_prevent_date_acceptance() -> None:
    assert r10ni.date_acceptance(_assessment("2026-09-09", fatal=1))["accepted"] is False
    assert r10ni.date_acceptance(_assessment("2026-09-10", blocking=1))["accepted"] is False


def test_nonblocking_diagnostics_remain_visible_and_do_not_block() -> None:
    row = _assessment("2026-09-09", nonblocking=7)
    assert row["diagnostic_counts"] == {"ZERO_VOLUME_PRICE_STATE": 7}
    assert row["acceptance"]["accepted"] is True


@pytest.mark.parametrize("field", ["price_immutability", "required_fields_explicit"])
def test_price_immutability_and_explicit_fields_are_required(field: str) -> None:
    row = _assessment("2026-09-09")
    row[field] = False
    assert r10ni.date_acceptance(row)["accepted"] is False


def test_full_expiry_agreement_is_required() -> None:
    row = _assessment("2026-09-09")
    row["expiry_agreement_rate"] = "0.999"
    assert r10ni.date_acceptance(row)["accepted"] is False


def test_integrity_failure_stops_before_qualification(tmp_path: Path) -> None:
    inputs = tuple(r10ni.PackageInput(
        day, f"artifacts/nse_fno_reports/{day}", "0" * 64,
        ({"filename": "a", "byte_length": 1, "sha256": "0" * 64},
         {"filename": "b", "byte_length": 1, "sha256": "0" * 64}),
    ) for day in r10ni.EXPECTED_DATES)
    with pytest.raises(r10ni.RequalificationError, match="PACKAGE_OR_MANIFEST_MISSING"):
        r10ni.preflight_packages(tmp_path, inputs)


def test_all_three_dates_are_evaluated_offline_and_partial_success_does_not_qualify(monkeypatch) -> None:
    calls = []
    descriptors = {day: object() for day in r10ni.EXPECTED_DATES}
    monkeypatch.setattr(r10ni, "preflight_packages", lambda root, inputs: ({"network_requests": 0}, descriptors))

    def fake_evaluate(descriptor):
        day = next(day for day, value in descriptors.items() if value is descriptor)
        calls.append(day)
        return _assessment(day, blocking=1 if day == "2026-09-10" else 0), {day}

    monkeypatch.setattr(r10ni, "evaluate_package", fake_evaluate)
    monkeypatch.setattr(r10ni, "compare_schemas", lambda rows: {"stable": True})
    monkeypatch.setattr(r10ni, "compare_contract_populations", lambda ids: {"dates": sorted(ids)})
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    result = r10ni.run_requalification(Path("."), tuple())
    assert calls == list(r10ni.EXPECTED_DATES)
    assert result["preflight"]["network_requests"] == 0
    assert result["decision"]["source_qualified"] is False
    assert result["decision"]["decision"] == "MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"


def test_cross_date_schema_and_population_comparisons_are_deterministic() -> None:
    rows = []
    for day in r10ni.EXPECTED_DATES:
        rows.append({
            "trading_date": day,
            "required_schemas": "PASS",
            "schemas": {"udiff_columns": sorted(r10ni.UDIFF_REQUIRED), "mii_columns": sorted(r10ni.MII_REQUIRED)},
            "decimal_scales_observed": {"open": [2]},
        })
    assert r10ni.compare_schemas(rows) == r10ni.compare_schemas(rows)
    populations = {day: {"1", "2", day} for day in r10ni.EXPECTED_DATES}
    result = r10ni.compare_contract_populations(populations)
    assert result == r10ni.compare_contract_populations(populations)
    assert result["all_three_intersection_count"] == 2
    assert result["raw_identifiers_persisted"] is False


def test_recorded_requalification_evaluates_all_dates_without_partial_qualification() -> None:
    dates = _load("per_date_qualification_results.json")["dates"]
    assert [row["trading_date"] for row in dates] == list(r10ni.EXPECTED_DATES)
    assert [row["accepted"] for row in dates] == [True, False, True]
    lifecycle = _load("source_lifecycle_decision.json")
    assert lifecycle["schemas_stable"] is True
    assert lifecycle["source_qualified"] is False
    assert lifecycle["decision"] == "MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"


def test_recorded_integrity_expiry_price_and_diagnostics_reconcile() -> None:
    assert _load("source_integrity_preflight.json")["integrity_state"] == "PASS"
    expiry = _load("expiry_agreement_results.json")
    assert expiry["totals"] == {"matched": 99026, "mismatched": 0, "rate": "1"}
    assert _load("price_immutability_results.json")["all_dates_exact_match"] is True
    diagnostics = _load("fatal_diagnostic_counts.json")
    assert diagnostics["totals"]["fatal"] == 0
    assert diagnostics["dates"][1]["blocking"] == 3


def test_sealed_r10na_through_r10nh_artifacts_remain_byte_exact() -> None:
    for evidence_dir in SEALED:
        manifest_path = evidence_dir / "root_manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["artifacts"]:
            payload = (evidence_dir / item["path"]).read_bytes()
            assert len(payload) == item["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_r10ni_evidence_is_sanitized_and_root_manifest_complete() -> None:
    encoded = "\n".join(path.read_text(encoding="utf-8") for path in EVIDENCE.glob("*.json")).lower()
    for marker in ("c:\\users\\", "/users/", "/home/", "authorization:", "cookie:", "bearer ", "financial_instrument_id_sha256"):
        assert marker not in encoded
    manifest = _load("root_manifest.json")
    expected = sorted(path.name for path in EVIDENCE.glob("*.json") if path.name != "root_manifest.json")
    assert [item["path"] for item in manifest["artifacts"]] == expected
    for item in manifest["artifacts"]:
        payload = (EVIDENCE / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
