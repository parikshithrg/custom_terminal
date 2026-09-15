"""Offline governance checks for the R10N-G semantics decision."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "investigations" / "r10n_g" / "semantics_v1"
ADAPTER = ROOT / "src" / "market_intel" / "foundation" / "nse_fno_candidate.py"
PRIOR = [
    ROOT / "docs" / "investigations" / "r10n_b" / "qualification_v1",
    ROOT / "docs" / "investigations" / "r10n_c" / "adapter_v1",
    ROOT / "docs" / "investigations" / "r10n_d" / "plan_v1",
    ROOT / "docs" / "investigations" / "r10n_d" / "amendment_v1",
    ROOT / "docs" / "investigations" / "r10n_e" / "preflight_v1",
    ROOT / "docs" / "investigations" / "r10n_e" / "qualification_v1",
    ROOT / "docs" / "investigations" / "r10n_f" / "diagnosis_v1",
]
R10NA = ROOT / "docs" / "investigations" / "r10n_a" / "hardening_v1"
R10NA_BINDINGS = {
    "completion.json": (1421, "78006e9425bd2c3436cde2fb50161e3a78e94c1b73fc29d8744fee78131d484f"),
    "dry_run_plan.json": (873, "9ee5caf1d828263234b181c951a13883906a09a7f974b89d193aa1d61e507506"),
}


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_only_official_sources_are_authoritative_and_no_report_url_is_present() -> None:
    inventory = _load("official_evidence_inventory.json")
    assert inventory["market_report_urls_accessed"] == 0
    assert inventory["market_report_payloads_downloaded"] == 0
    for source in inventory["sources"]:
        assert source["authority"].startswith("OFFICIAL_")
        assert re.fullmatch(r"https://(?:www\.)?nseindia\.com/.*|https://nsearchives\.nseindia\.com/.*", source["url"])
        assert "/content/fo/" not in source["url"]


def test_every_semantic_claim_is_cited_or_explicitly_unresolved() -> None:
    matrix = _load("field_semantics_matrix.json")
    for field in matrix["fields"]:
        assert field["citations"] or "UNRESOLVED" in json.dumps(field)
    distinctions = _load("documented_vs_inferred.json")["distinctions"]
    for claim in distinctions:
        assert claim["citations"] or "UNRESOLVED" in claim["classification"]


def test_close_containment_is_not_asserted_without_evidence() -> None:
    matrix = _load("field_semantics_matrix.json")
    assert matrix["authoritative_close_within_high_low_rule_found"] is False
    close = next(item for item in matrix["fields"] if item["field"] == "ClsPric")
    assert close["must_be_inside_low_high"] == "NOT_STATED_BY_AUTHORITY"
    contract = _load("proposed_ohlc_rule_contract.json")
    diagnostic = next(item for item in contract["diagnostic_conditions"] if item["code"].startswith("CLOSE_OUTSIDE"))
    assert diagnostic == {"code": "CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS", "parse_fatal": False, "source_qualification_blocking": True}


def test_structural_protection_visibility_and_no_price_mutation_are_preserved() -> None:
    contract = _load("proposed_ohlc_rule_contract.json")
    assert "HIGH_BELOW_LOW" in contract["fatal_conditions"]
    assert contract["price_mutation"] == "FORBIDDEN"
    assert contract["silent_qualification"] == "FORBIDDEN"
    assert len({item["code"] for item in contract["diagnostic_conditions"]}) == len(contract["diagnostic_conditions"])


def test_expiry_disagreement_is_separate_and_fail_closed() -> None:
    finding = _load("expiry_side_finding.json")
    assert finding["timezone_boundary_explains_disagreement"] is False
    assert finding["ten_year_offset_observed"] is True
    assert finding["relationship_to_ohlc"] == "SEPARATE_AND_NON_CAUSAL"
    assert finding["adapter_behavior_modified"] is False
    assert all(item["calendar_day_delta"] == 3652 for item in finding["examples"])


def test_r10nf_counts_reconcile_and_source_remains_unqualified() -> None:
    reconciliation = _load("r10nf_reconciliation.json")
    rows = {item["trading_date"]: item for item in reconciliation["dates"]}
    assert rows["2026-09-10"]["nonzero_volume_ohlc_violations"] == 2
    assert rows["2026-09-09"]["nonzero_volume_ohlc_violations"] == 0
    assert rows["2025-07-08"]["nonzero_volume_ohlc_violations"] == 0
    assert reconciliation["source_qualified"] is False


def test_adapter_and_prior_sealed_evidence_are_byte_identical() -> None:
    assert hashlib.sha256(ADAPTER.read_bytes()).hexdigest() == "93780824f87bd80b67269636fe22b7c11fa2379fbda85537d07565f942e0a6af"
    for name, (size, digest) in R10NA_BINDINGS.items():
        payload = (R10NA / name).read_bytes()
        assert len(payload) == size
        assert hashlib.sha256(payload).hexdigest() == digest
    for evidence_dir in PRIOR:
        manifest = json.loads((evidence_dir / "root_manifest.json").read_text(encoding="utf-8"))
        for item in manifest["artifacts"]:
            payload = (evidence_dir / item["path"]).read_bytes()
            assert len(payload) == item["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_lifecycle_remains_closed_and_implementation_needs_owner_authority() -> None:
    lifecycle = _load("lifecycle_non_authorization.json")
    decision = _load("owner_decision_schema.json")
    assert lifecycle["adapter_state"] == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    assert lifecycle["source_state"] == "MULTI_DATE_SOURCE_NOT_QUALIFIED"
    assert lifecycle["report_archive_head_or_get_requests"] == 0
    assert decision["owner_answer"] == "PENDING"
    assert decision["this_file_authorizes_implementation"] is False


def test_tracked_evidence_is_sanitized() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in EVIDENCE.glob("*.json")).lower()
    for marker in ("c:\\users\\", "/users/", "/home/", "authorization:", "cookie:", "bearer ", "tckrsymb"):
        assert marker not in text
    assert "nsearchives.nseindia.com/content/fo/" not in text


def test_root_manifest_binds_every_sibling_json() -> None:
    manifest = _load("root_manifest.json")
    expected = sorted(path.name for path in EVIDENCE.glob("*.json") if path.name != "root_manifest.json")
    assert [item["path"] for item in manifest["artifacts"]] == expected
    for item in manifest["artifacts"]:
        payload = (EVIDENCE / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
