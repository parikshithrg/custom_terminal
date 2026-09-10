"""Recorded-evidence and boundary checks for R.10N-B."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10n_b/qualification_v1"


def _load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_recorded_root_manifest_reconciles_all_artifacts_and_sources() -> None:
    root = _load("root_manifest.json")
    assert root["milestone"] == "R.10N-B"
    for item in root["artifacts"]:
        payload = (RUN / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
    assert [item["sha256"] for item in root["source_bindings"]] == [
        "50826bed50da889b90b208c9b6368d3768c0eabb416178b176f064d3f93de3f5",
        "a58c75d36a5100506c005961af181cd6ca8ed597289ffc5fdc3107920e4850cf",
    ]


def test_recorded_metrics_show_exact_join_and_typed_coverage() -> None:
    quality = _load("quality_metrics.json")
    assert quality["source_rows"] == {"udiff": 33250, "mii": 78603}
    assert quality["normalized_rows"] == {"udiff": 33250, "mii": 78603}
    assert quality["instrument_counts"] == {"futures": 647, "options": 32603, "other": 0}
    assert quality["identity_join"] == {
        "matched": 33250, "missing_key": 0, "ambiguous": 0,
        "unresolved": 0, "rate": 1.0,
    }
    assert quality["malformed_fact_rows"] == 0
    assert quality["contract_identity"]["malformed_rows"] == 0
    assert quality["ohlc_inconsistent_rows"] == 0


def test_owner_scope_is_narrow_and_existing_package_outcome_is_explicit() -> None:
    acquisition = _load("acquisition.json")
    assert acquisition["owner_confirmation_received_in_r10nb_chat"] is True
    assert acquisition["post_confirmation_acquisition_performed"] is False
    assert acquisition["post_confirmation_network_requests"] == 0
    assert acquisition["post_confirmation_downloader_outcome"] == "REFUSED_EXISTING_PACKAGE_BEFORE_NETWORK"
    for boundary in ("redistribution_authorized", "bulk_acquisition_authorized",
                     "research_or_production_authorized", "trading_authorized"):
        assert acquisition[boundary] is False


def test_completion_and_report_do_not_expand_authority() -> None:
    completion = _load("completion.json")
    report = (ROOT / "reports/NSE_FNO_SINGLE_DATE_TECHNICAL_QUALIFICATION.md").read_text(encoding="utf-8")
    assert completion["completion_decision"] == "SINGLE_DATE_PACKAGE_TECHNICALLY_QUALIFIED"
    assert completion["raw_rows_retained_in_evidence"] is False
    flattened = " ".join(report.split())
    assert "does not authorize another date" in flattened
    assert "No automatic retry" in flattened


def test_evidence_is_strict_json_and_contains_no_private_or_secret_material() -> None:
    private = re.compile(r"(?i)(?:[a-z]:\\\\users\\\\|/users/|/home/)")
    secret = re.compile(r"(?i)(?:authorization|cookie|password|token|secret)\s*[:=]")
    for path in RUN.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        assert not private.search(text)
        assert not secret.search(text)


def test_no_payloads_or_full_contract_inventory_are_tracked_in_r10nb() -> None:
    names = {path.name.lower() for path in RUN.iterdir()}
    assert not any(name.endswith((".zip", ".gz", ".csv", ".parquet")) for name in names)
    schema = _load("observed_schema.json")
    assert "rows" not in schema["mii"] and "contracts" not in schema["mii"]
