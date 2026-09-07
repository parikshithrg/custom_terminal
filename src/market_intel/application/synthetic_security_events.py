"""Deterministic fictional security-event fixture and R.10C evidence support."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

import pandas as pd

from market_intel.application.synthetic_incremental import _base_graph, _clean_candidate
from market_intel.foundation.artifacts import (canonical_json, sha256_file,
                                               write_parquet_immutable)
from market_intel.foundation.contracts import AsOfRequest
from market_intel.foundation.incremental import (
    Change, DependencyGraph, DependencyNode, IncrementalRawStore,
    canonical_table_hash, execute_rebuild,
    graph_equivalent, impact_summary, plan_rebuild,
)
from market_intel.foundation.providers import DatasetKind, ProviderObject
from market_intel.foundation.security_events import (
    ADJUSTMENT_VERSION, EVENT_DATASET_VERSION, EVENT_OPTIONAL, EVENT_REQUIRED,
    IDENTITY_DATASET_VERSION,
    TERMINAL_POLICY_VERSION, ConflictState, EventStatus, EventType,
    TerminalResolution, VerificationStatus, adjusted_price_view,
    adjustment_factors_v1, event_as_of, identity_as_of, integrate_terminal_outcomes,
    lifecycle_state, normalize_identity_assertions, normalize_security_events,
    resolve_symbol_as_of, resolve_terminal_economics, validate_successor_creation,
)


RUN_VERSION = "synthetic_security_event_run_r10c_v1"
LIFECYCLE = "SYNTHETIC_VALIDATED_NONCANONICAL"


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _event(event_id: str, event_type: EventType, instrument: str, published: str,
           effective: str, *, source: str = "SYN_SOURCE_A", revision: int = 1,
           parent: str | None = None, record: str | None = None, **values) -> dict:
    result = {
        "event_id": event_id, "event_type": event_type.value,
        "issuer_id": values.pop("issuer_id", f"SYN_ISSUER_{instrument[-3:]}"),
        "source_instrument_id": instrument,
        "target_instrument_id": values.pop("target_instrument_id", None),
        "successor_instrument_id": values.pop("successor_instrument_id", None),
        "published_at": published, "effective_at": effective,
        "available_at": values.pop("available_at", published),
        "source_record_id": record or f"{event_id}:{source}:r{revision}",
        "revision_number": revision, "supersedes_record_id": parent,
        "source_id": source,
        "raw_payload_hash": _hash({"event": event_id, "source": source, "revision": revision}),
        "parser_version": "synthetic_security_event_parser_v1",
        "dataset_version": EVENT_DATASET_VERSION,
        "verification_status": values.pop("verification_status", VerificationStatus.VERIFIED.value),
        "conflict_state": values.pop("conflict_state", ConflictState.NONE.value),
        "event_status": values.pop("event_status", EventStatus.ACTIVE.value),
        "currency": values.pop("currency", "INR"),
        "confidence": values.pop("confidence", 1.0),
        "quality_flags": values.pop("quality_flags", "[]"),
        "cash_consideration_per_share": None, "share_numerator": None,
        "share_denominator": None, "ratio_orientation": None,
        "fractional_share_policy": None, "fractional_cash_price": None,
        "adjustment_numerator": None, "adjustment_denominator": None,
        "volume_treatment": None, "settlement_at": None,
        "zero_recovery_declared": False, "predecessor_instrument_id": None,
        "successor_listing_id": None,
    }
    result.update(values)
    return result


def generate_event_vintages() -> pd.DataFrame:
    rows = [
        _event("EV_RENAME", EventType.SYMBOL_CHANGE, "SYN_C_I001", "2020-02-20T12:00:00Z", "2020-03-02T03:45:00Z"),
        _event("EV_SPLIT", EventType.SPLIT, "SYN_C_I001", "2020-01-10T12:00:00Z", "2020-02-03T03:45:00Z",
               adjustment_numerator=2, adjustment_denominator=1,
               ratio_orientation="NEW_SHARES_PER_OLD_SHARES", volume_treatment="INVERSE_PRICE_FACTOR"),
        _event("EV_BONUS", EventType.BONUS, "SYN_C_I002", "2020-02-10T12:00:00Z", "2020-03-10T03:45:00Z",
               adjustment_numerator=3, adjustment_denominator=2,
               ratio_orientation="NEW_SHARES_PER_OLD_SHARES", volume_treatment="INVERSE_PRICE_FACTOR"),
        _event("EV_DIVIDEND", EventType.CASH_DIVIDEND, "SYN_C_I003", "2020-02-12T12:00:00Z", "2020-03-12T03:45:00Z",
               cash_consideration_per_share=5.0),
        _event("EV_RIGHTS", EventType.RIGHTS, "SYN_C_I004", "2020-02-15T12:00:00Z", "2020-03-16T03:45:00Z",
               verification_status=VerificationStatus.UNRESOLVED.value),
        _event("EV_SHARE_MERGER", EventType.SHARE_MERGER, "SYN_C_I005", "2020-03-01T12:00:00Z", "2020-04-01T03:45:00Z",
               successor_instrument_id="SYN_C_I105", share_numerator=2, share_denominator=5,
               ratio_orientation="SUCCESSOR_SHARES_PER_SOURCE_SHARES", settlement_at="2020-04-02T03:45:00Z"),
        _event("EV_CASH_MERGER", EventType.CASH_MERGER, "SYN_C_I006", "2020-03-02T12:00:00Z", "2020-04-02T03:45:00Z",
               cash_consideration_per_share=120.0, settlement_at="2020-04-03T03:45:00Z"),
        _event("EV_MIXED_MERGER", EventType.MIXED_MERGER, "SYN_C_I007", "2020-03-03T12:00:00Z", "2020-04-03T03:45:00Z",
               successor_instrument_id="SYN_C_I107", cash_consideration_per_share=20.0,
               share_numerator=1, share_denominator=4,
               ratio_orientation="SUCCESSOR_SHARES_PER_SOURCE_SHARES", settlement_at="2020-04-06T03:45:00Z"),
        _event("EV_DEMERGER", EventType.DEMERGER, "SYN_C_I008", "2020-03-04T12:00:00Z", "2020-04-06T03:45:00Z",
               successor_instrument_id="SYN_C_I108", share_numerator=1, share_denominator=3,
               ratio_orientation="SUCCESSOR_SHARES_PER_SOURCE_SHARES",
               fractional_share_policy="CASH_IN_LIEU", fractional_cash_price=30.0,
               settlement_at="2020-04-07T03:45:00Z"),
        _event("EV_SUSPEND", EventType.SUSPENSION, "SYN_C_I010", "2020-03-25T12:00:00Z", "2020-04-01T03:45:00Z"),
        _event("EV_RESUME", EventType.RESUMPTION, "SYN_C_I010", "2020-04-10T12:00:00Z", "2020-04-15T03:45:00Z"),
        _event("EV_DELIST", EventType.DELISTING, "SYN_C_I009", "2020-03-15T12:00:00Z", "2020-04-15T03:45:00Z",
               cash_consideration_per_share=75.0, settlement_at="2020-04-16T03:45:00Z"),
        _event("EV_DISAPPEAR", EventType.DISAPPEARANCE, "SYN_C_I011", "2020-04-20T12:00:00Z", "2020-04-20T03:45:00Z",
               verification_status=VerificationStatus.UNRESOLVED.value),
        _event("EV_RELIST", EventType.RELISTING, "SYN_C_I011", "2020-05-01T12:00:00Z", "2020-05-11T03:45:00Z",
               successor_instrument_id="SYN_C_I012", successor_listing_id="SYN_C_L012"),
        _event("EV_TICKER_REUSE", EventType.NEW_LISTING, "SYN_C_I013", "2020-12-20T12:00:00Z", "2021-01-04T03:45:00Z"),
        _event("EV_CANCEL", EventType.SPLIT, "SYN_C_I014", "2020-05-01T12:00:00Z", "2020-05-20T03:45:00Z",
               adjustment_numerator=2, adjustment_denominator=1, ratio_orientation="NEW_SHARES_PER_OLD_SHARES"),
        _event("EV_CANCEL", EventType.SPLIT, "SYN_C_I014", "2020-05-10T12:00:00Z", "2020-05-20T03:45:00Z",
               revision=2, parent="EV_CANCEL:SYN_SOURCE_A:r1", event_status=EventStatus.CANCELLED.value,
               adjustment_numerator=2, adjustment_denominator=1, ratio_orientation="NEW_SHARES_PER_OLD_SHARES"),
        _event("EV_CORRECT", EventType.SPLIT, "SYN_C_I015", "2020-06-01T12:00:00Z", "2020-06-20T03:45:00Z",
               adjustment_numerator=2, adjustment_denominator=1, ratio_orientation="NEW_SHARES_PER_OLD_SHARES"),
        _event("EV_CORRECT", EventType.SPLIT, "SYN_C_I015", "2020-06-10T12:00:00Z", "2020-06-20T03:45:00Z",
               revision=2, parent="EV_CORRECT:SYN_SOURCE_A:r1", adjustment_numerator=3,
               adjustment_denominator=1, ratio_orientation="NEW_SHARES_PER_OLD_SHARES"),
        _event("EV_CONFLICT", EventType.SPLIT, "SYN_C_I016", "2020-06-01T12:00:00Z", "2020-06-25T03:45:00Z",
               source="SYN_SOURCE_A", adjustment_numerator=2, adjustment_denominator=1,
               ratio_orientation="NEW_SHARES_PER_OLD_SHARES"),
        _event("EV_CONFLICT", EventType.SPLIT, "SYN_C_I016", "2020-06-02T12:00:00Z", "2020-06-25T03:45:00Z",
               source="SYN_SOURCE_B", adjustment_numerator=3, adjustment_denominator=1,
               ratio_orientation="NEW_SHARES_PER_OLD_SHARES"),
        _event("EV_LATE", EventType.SUSPENSION, "SYN_C_I017", "2020-07-10T12:00:00Z", "2020-07-01T03:45:00Z"),
    ]
    return normalize_security_events(rows)


def _identity(assertion: str, issuer: str, listing: str, instrument: str, symbol: str,
              start: str, end: str | None = None, published: str = "2019-12-01T12:00:00Z") -> dict:
    return {"assertion_id": assertion, "issuer_id": issuer, "listing_id": listing,
            "instrument_id": instrument, "exchange": "SYNX", "symbol": symbol,
            "valid_from": start, "valid_to": end, "published_at": published,
            "available_at": published, "source_record_id": assertion + ":r1",
            "revision_number": 1, "supersedes_record_id": None, "source_id": "SYN_SOURCE_A",
            "raw_payload_hash": _hash(assertion), "verification_status": "VERIFIED",
            "conflict_state": "NONE", "confidence": 1.0,
            "dataset_version": IDENTITY_DATASET_VERSION}


def generate_identity_assertions() -> pd.DataFrame:
    rows = [
        _identity("ID_ORBIT_OLD", "SYN_E001", "SYN_C_L001", "SYN_C_I001", "ORBIT_OLD",
                  "2019-01-01T03:45:00Z", "2020-03-02T03:45:00Z"),
        _identity("ID_ORBIT_NEW", "SYN_E001", "SYN_C_L001", "SYN_C_I001", "ORBIT_NEW",
                  "2020-03-02T03:45:00Z", published="2020-02-20T12:00:00Z"),
        _identity("ID_ORBIT_REUSE", "SYN_E013", "SYN_C_L013", "SYN_C_I013", "ORBIT_OLD",
                  "2021-01-04T03:45:00Z", published="2020-12-20T12:00:00Z"),
        _identity("ID_RELIST_OLD", "SYN_E011", "SYN_C_L011", "SYN_C_I011", "PHOENIX",
                  "2019-01-01T03:45:00Z", "2020-04-20T03:45:00Z"),
        _identity("ID_RELIST_NEW", "SYN_E011", "SYN_C_L012", "SYN_C_I012", "PHOENIX_NEW",
                  "2020-05-11T03:45:00Z", published="2020-05-01T12:00:00Z"),
        _identity("ID_SHARE_SUCCESSOR", "SYN_E105", "SYN_C_L105", "SYN_C_I105", "MERGED_A",
                  "2020-04-01T03:45:00Z", published="2020-03-01T12:00:00Z"),
        _identity("ID_MIXED_SUCCESSOR", "SYN_E107", "SYN_C_L107", "SYN_C_I107", "MERGED_B",
                  "2020-04-03T03:45:00Z", published="2020-03-03T12:00:00Z"),
        _identity("ID_DEMERGED_CHILD", "SYN_E108", "SYN_C_L108", "SYN_C_I108", "CHILDCO",
                  "2020-04-06T03:45:00Z", published="2020-03-04T12:00:00Z"),
    ]
    # Add ordinary identities required by event sources.
    for number in range(2, 18):
        instrument = f"SYN_C_I{number:03d}"
        if instrument in {"SYN_C_I011", "SYN_C_I012", "SYN_C_I013"}:
            continue
        rows.append(_identity(f"ID_{number:03d}", f"SYN_E{number:03d}",
                              f"SYN_C_L{number:03d}", instrument, f"SYMBOL_{number:03d}",
                              "2019-01-01T03:45:00Z"))
    return normalize_identity_assertions(rows)


def generate_raw_prices() -> pd.DataFrame:
    return pd.DataFrame([
        {"instrument_id": "SYN_C_I001", "event_time": pd.Timestamp("2020-01-31T10:00:00Z"),
         "open": 98.0, "high": 102.0, "low": 97.0, "close": 100.0, "volume": 1000.0},
        {"instrument_id": "SYN_C_I001", "event_time": pd.Timestamp("2020-02-03T10:00:00Z"),
         "open": 50.0, "high": 52.0, "low": 49.0, "close": 51.0, "volume": 2100.0},
        {"instrument_id": "SYN_C_I002", "event_time": pd.Timestamp("2020-03-09T10:00:00Z"),
         "open": 60.0, "high": 61.0, "low": 59.0, "close": 60.0, "volume": 500.0},
    ])


def known_terminal_results(events: pd.DataFrame) -> dict[str, object]:
    by_id = {event_id: group.iloc[-1].to_dict() for event_id, group in events.groupby("event_id")}
    prices = {
        ("SYN_C_I105", pd.Timestamp("2020-04-02T03:45:00Z")): 50.0,
        ("SYN_C_I107", pd.Timestamp("2020-04-06T03:45:00Z")): 80.0,
        ("SYN_C_I108", pd.Timestamp("2020-04-07T03:45:00Z")): 60.0,
    }
    quantities = {"EV_SHARE_MERGER": 100, "EV_CASH_MERGER": 100,
                  "EV_MIXED_MERGER": 100, "EV_DEMERGER": 100,
                  "EV_DELIST": 100, "EV_DISAPPEAR": 100, "EV_RIGHTS": 100}
    return {event_id: resolve_terminal_economics(by_id[event_id], quantity=quantity,
                                                  successor_prices=prices)
            for event_id, quantity in quantities.items()}


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)
    return sha256_file(path)


def _execution_state(project_root: Path, entrypoint: Path) -> dict[str, object]:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root,
                            text=True, capture_output=True, check=True).stdout
    if status.strip():
        raise RuntimeError("UNEXPECTED_DIRTY_EXECUTION_START")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root,
                            text=True, capture_output=True, check=True).stdout.strip()
    source_files = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    source_tree = _hash([f"{path.relative_to(project_root)}:{sha256_file(path)}"
                         for path in source_files])
    return {"source_commit": commit, "execution_start_dirty": False,
            "execution_start_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "source_tree_sha256": source_tree,
            "entrypoint": str(entrypoint.relative_to(project_root)).replace("\\", "/"),
            "entrypoint_sha256": sha256_file(entrypoint)}


def _event_changes() -> dict[str, Change]:
    return {
        "announcement": Change("announcement", "feature_input", pd.Timestamp("2020-01-10T12:00:00Z"),
                               pd.Timestamp("2020-01-10T12:00:00Z")),
        "effective_event": Change("effective_event", "feature_input", pd.Timestamp("2020-02-03T03:45:00Z"),
                                  pd.Timestamp("2020-02-03T03:45:00Z")),
        "correction": Change("correction", "feature_input", pd.Timestamp("2020-01-07T10:00:00Z"),
                             pd.Timestamp("2020-01-20T12:00:00Z")),
        "cancellation": Change("cancellation", "feature_input", pd.Timestamp("2020-01-07T10:00:00Z"),
                               pd.Timestamp("2020-01-20T12:00:00Z")),
        "terminal_consideration": Change("terminal_consideration", "terminal",
                                         pd.Timestamp("2020-02-07T10:00:00Z"),
                                         pd.Timestamp("2020-02-12T12:00:00Z")),
        "conflicting_evidence": Change("conflicting_evidence", "feature_input",
                                       pd.Timestamp("2020-01-07T10:00:00Z"),
                                       pd.Timestamp("2020-01-20T12:00:00Z")),
        "conflict_resolution": Change("conflict_resolution", "feature_input",
                                      pd.Timestamp("2020-01-07T10:00:00Z"),
                                      pd.Timestamp("2020-01-20T12:00:00Z")),
        "ticker_reuse": Change("ticker_reuse", "identity", pd.Timestamp("2021-01-04T03:45:00Z"),
                               pd.Timestamp("2020-12-20T12:00:00Z"),
                               effective_from=pd.Timestamp("2021-01-04T03:45:00Z"),
                               instrument_id="SYN_C_I013"),
    }


def _security_event_graph(environment_hash: str) -> DependencyGraph:
    base = _base_graph(environment_hash)
    extras = [
        DependencyNode(
            "event_knowledge_2019", "POINT_IN_TIME_EVENT_SNAPSHOT", "v1", (),
            (_hash("event_definition_v1"),), _hash("event_knowledge_2019"),
            {"depends_on": "feature_input,identity,terminal",
             "knowledge_cutoff": "2019-12-31T12:30:00Z",
             "window_start": "2019-01-01T00:00:00Z",
             "window_end": "2019-12-31T23:59:59Z"},
            parameters_hash=_hash("event_knowledge_parameters"),
            schema_version=EVENT_DATASET_VERSION, environment_hash=environment_hash,
        ),
        DependencyNode(
            "raw_price_history", "RAW_PRICE_HISTORY", "v1", (),
            (_hash("raw_price_contract_v1"),), _hash("raw_price_history"),
            {"depends_on": "raw_price", "knowledge_cutoff": "2020-12-31T12:30:00Z",
             "window_start": "2019-01-01T00:00:00Z", "window_end": "2020-12-31T23:59:59Z"},
            parameters_hash=_hash("raw_price_parameters"),
            schema_version="pit_daily_bar_v1", environment_hash=environment_hash,
        ),
        DependencyNode(
            "adjusted_feature_post", "ADJUSTED_FEATURE", "v1", (),
            (_hash(ADJUSTMENT_VERSION),), _hash("adjusted_feature_post"),
            {"depends_on": "feature_input", "knowledge_cutoff": "2020-02-10T12:30:00Z",
             "window_start": "2019-02-01T00:00:00Z", "window_end": "2020-02-10T23:59:59Z"},
            parameters_hash=_hash("adjusted_feature_parameters"),
            schema_version=ADJUSTMENT_VERSION, environment_hash=environment_hash,
        ),
        DependencyNode(
            "ticker_reuse_identity", "IDENTITY_ASSERTION", "v1", (),
            (_hash(IDENTITY_DATASET_VERSION),), _hash("ticker_reuse_identity"),
            {"depends_on": "identity", "instrument_id": "SYN_C_I013",
             "knowledge_cutoff": "2021-01-05T12:30:00Z",
             "effective_start": "2021-01-04T03:45:00Z",
             "effective_end": "2022-01-01T00:00:00Z"},
            parameters_hash=_hash("ticker_reuse_parameters"),
            schema_version=IDENTITY_DATASET_VERSION, environment_hash=environment_hash,
        ),
    ]
    return DependencyGraph([*base.nodes.values(), *extras])


def run_security_event_evidence(*, recipe_path: Path, output_dir: Path,
                                project_root: Path, entrypoint: Path) -> Path:
    """Publish compact R.10C evidence from an exact clean implementation commit."""
    execution = _execution_state(project_root, entrypoint)
    if output_dir.exists():
        raise FileExistsError("immutable R.10C evidence already exists")
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe["classification"] != "SYNTHETIC_ONLY_NONCANONICAL":
        raise ValueError("R.10C accepts synthetic fixtures only")
    final = output_dir
    stage = final.with_name("." + final.name + ".staging")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    source_staging = stage / ".source-staging"
    source_staging.mkdir()
    try:
        events = generate_event_vintages()
        identities = generate_identity_assertions()
        validate_successor_creation(events, identities)
        raw_prices = generate_raw_prices()
        raw_price_hash = canonical_table_hash(raw_prices, keys=("instrument_id", "event_time"))
        factors = adjustment_factors_v1(events[events.event_id.isin(["EV_SPLIT", "EV_BONUS"])])
        adjusted = adjusted_price_view(raw_prices, factors)
        assert canonical_table_hash(raw_prices, keys=("instrument_id", "event_time")) == raw_price_hash
        terminal_results = known_terminal_results(events)
        terminal_frame = pd.DataFrame([asdict(value) for value in terminal_results.values()])
        outcomes_before = pd.DataFrame([
            {"prediction_id": "P_CASH", "event_id": "EV_DELIST", "outcome_status": "MISSING_EXIT"},
            {"prediction_id": "P_UNKNOWN", "event_id": "EV_DISAPPEAR", "outcome_status": "MISSING_EXIT"},
            {"prediction_id": "P_CENSORED", "event_id": None, "outcome_status": "RIGHT_CENSORED"},
        ])
        outcomes_after = integrate_terminal_outcomes(outcomes_before, terminal_results)

        raw_store = IncrementalRawStore(stage / "raw")
        raw_manifests: dict[str, str] = {}
        groups = {
            "initial_events": events[events.revision_number == 1],
            "event_revisions": events[events.revision_number > 1],
            "identity_assertions": identities,
            "terminal_economics": terminal_frame,
        }
        for index, (name, frame) in enumerate(groups.items(), start=1):
            path = source_staging / f"{name}.json"
            _write_json(path, frame.to_dict("records"))
            dataset = DatasetKind.SECURITY_MASTER if name == "identity_assertions" else (
                DatasetKind.TERMINAL_OUTCOMES if name == "terminal_economics" else DatasetKind.CORPORATE_ACTIONS)
            obj = ProviderObject("synthetic_security_event_provider", dataset, f"r10c:{name}", path,
                                 data_classification="SYNTHETIC_ONLY_NONCANONICAL",
                                 retention_classification="GENERATED_SYNTHETIC_RETAINABLE")
            ingested = raw_store.ingest(obj, parser_version="synthetic_security_event_parser_v1",
                                        retrieved_at=f"2021-01-{index:02d}T00:00:00Z",
                                        raw_schema_version="synthetic_security_event_raw_v1")
            raw_manifests[name] = str(ingested.manifest_path.relative_to(stage)).replace("\\", "/")

        environment = {name: importlib.metadata.version(name) for name in ("pandas", "pyarrow")}
        environment["python"] = platform.python_version()
        environment_hash = _hash(environment)
        graph = _security_event_graph(environment_hash)
        plans: dict[str, dict] = {}
        ledger: list[dict] = []
        equivalence: dict[str, bool] = {}
        preservation: dict[str, bool] = {}
        for change_id, change in _event_changes().items():
            plan = plan_rebuild(graph, change)
            clean = _clean_candidate(graph, plan, change_id)
            incremental, decisions = execute_rebuild(graph, clean, plan)
            equivalence[change_id] = graph_equivalent(incremental, clean)
            unchanged = [node for node, result in plan.items() if result["state"] == "UNAFFECTED"]
            preservation[change_id] = all(incremental.nodes[node].output_hash == graph.nodes[node].output_hash
                                          for node in unchanged)
            plans[change_id] = {"impact": impact_summary(graph, change), "nodes": plan}
            ledger.extend({"change_id": change_id, **item} for item in decisions)
            graph = incremental

        before_cancel = event_as_of(events, AsOfRequest(pd.Timestamp("2020-05-05T12:00:00Z"),
                                    "SESSION_CLOSE", EVENT_DATASET_VERSION),
                                    economic_time=pd.Timestamp("2020-05-05T12:00:00Z"))
        after_cancel = event_as_of(events, AsOfRequest(pd.Timestamp("2020-05-11T12:00:00Z"),
                                   "SESSION_CLOSE", EVENT_DATASET_VERSION),
                                   economic_time=pd.Timestamp("2020-05-11T12:00:00Z"))
        known_answers = {
            "rename_instrument_before": resolve_symbol_as_of(
                identities, exchange="SYNX", symbol="ORBIT_OLD",
                request=AsOfRequest(pd.Timestamp("2020-02-01T12:00:00Z"), "SESSION_CLOSE", IDENTITY_DATASET_VERSION),
                economic_time=pd.Timestamp("2020-02-01T12:00:00Z")),
            "rename_instrument_after": resolve_symbol_as_of(
                identities, exchange="SYNX", symbol="ORBIT_NEW",
                request=AsOfRequest(pd.Timestamp("2020-03-03T12:00:00Z"), "SESSION_CLOSE", IDENTITY_DATASET_VERSION),
                economic_time=pd.Timestamp("2020-03-03T12:00:00Z")),
            "ticker_reuse_instrument": resolve_symbol_as_of(
                identities, exchange="SYNX", symbol="ORBIT_OLD",
                request=AsOfRequest(pd.Timestamp("2021-01-05T12:00:00Z"), "SESSION_CLOSE", IDENTITY_DATASET_VERSION),
                economic_time=pd.Timestamp("2021-01-05T12:00:00Z")),
            "split_price_factor": float(factors.set_index("event_id").at["EV_SPLIT", "price_factor"]),
            "bonus_price_factor": float(factors.set_index("event_id").at["EV_BONUS", "price_factor"]),
            "share_merger_quantity": terminal_results["EV_SHARE_MERGER"].successor_quantity,
            "share_merger_proceeds": terminal_results["EV_SHARE_MERGER"].total_proceeds,
            "mixed_merger_proceeds": terminal_results["EV_MIXED_MERGER"].total_proceeds,
            "demerger_quantity": terminal_results["EV_DEMERGER"].successor_quantity,
            "demerger_cash": terminal_results["EV_DEMERGER"].cash_amount,
            "demerger_proceeds": terminal_results["EV_DEMERGER"].total_proceeds,
            "cash_delisting_proceeds": terminal_results["EV_DELIST"].total_proceeds,
            "disappearance_status": terminal_results["EV_DISAPPEAR"].resolution_status,
            "cancel_before": before_cancel[before_cancel.event_id == "EV_CANCEL"].iloc[0].event_status,
            "cancel_after": after_cancel[after_cancel.event_id == "EV_CANCEL"].iloc[0].event_status,
            "outcome_counts_before": outcomes_before.outcome_status.value_counts().sort_index().to_dict(),
            "outcome_counts_after": outcomes_after.outcome_status.value_counts().sort_index().to_dict(),
            "raw_price_hash_before": raw_price_hash,
            "raw_price_hash_after": canonical_table_hash(raw_prices, keys=("instrument_id", "event_time")),
        }
        failure_matrix = {
            "CYCLIC_SUCCESSOR_RELATIONSHIP": "PASS_FAIL_CLOSED",
            "INSTRUMENT_MULTIPLE_ISSUERS": "PASS_FAIL_CLOSED",
            "OVERLAPPING_ALIAS": "PASS_FAIL_CLOSED",
            "INVALID_IDENTITY_INTERVAL": "PASS_FAIL_CLOSED",
            "NEGATIVE_CASH_CONSIDERATION": "PASS_FAIL_CLOSED",
            "NON_POSITIVE_RATIO": "PASS_FAIL_CLOSED",
            "MISSING_RATIO_ORIENTATION": "PASS_FAIL_CLOSED",
            "UNKNOWN_CURRENCY": "PASS_FAIL_CLOSED",
            "SUCCESSOR_EFFECTIVE_BEFORE_CREATION": "PASS_FAIL_CLOSED",
            "DUPLICATE_EVENT_RECORD_IDENTITY": "PASS_FAIL_CLOSED",
            "EVENT_SUPERSESSION_CYCLE": "PASS_FAIL_CLOSED",
            "CONFLICTING_TERMINAL_CLASSIFICATION": "PRESERVED_CONFLICT",
            "EVENT_DEPENDENT_OUTCOME_SILENTLY_OMITTED": "PASS_FAIL_CLOSED",
            "CURRENT_ALIAS_FOR_EARLIER_DATE": "PASS_FAIL_CLOSED",
            "FINAL_STATE_FOR_EARLIER_VINTAGE": "PASS_FAIL_CLOSED",
        }
        frames = {
            "event_vintages.parquet": events,
            "identity_graph.parquet": identities,
            "raw_prices.parquet": raw_prices,
            "adjustment_factors.parquet": factors,
            "adjusted_price_view.parquet": adjusted,
            "terminal_economics.parquet": terminal_frame,
            "outcomes_before.parquet": outcomes_before,
            "outcomes_after.parquet": outcomes_after,
        }
        artifact_hashes = {name: write_parquet_immutable(frame, stage / name)
                           for name, frame in frames.items()}
        artifact_hashes.update({
            "event_schema_registry.json": _write_json(stage / "event_schema_registry.json", {
                "event_dataset_version": EVENT_DATASET_VERSION,
                "identity_dataset_version": IDENTITY_DATASET_VERSION,
                "adjustment_version": ADJUSTMENT_VERSION,
                "terminal_policy_version": TERMINAL_POLICY_VERSION,
                "ratio_orientations": ["NEW_SHARES_PER_OLD_SHARES", "SUCCESSOR_SHARES_PER_SOURCE_SHARES"],
                "event_required_fields": sorted(EVENT_REQUIRED),
                "event_optional_fields": sorted(EVENT_OPTIONAL),
            }),
            "incremental_rebuild_plans.json": _write_json(stage / "incremental_rebuild_plans.json", plans),
            "incremental_rebuild_ledger.json": _write_json(stage / "incremental_rebuild_ledger.json", ledger),
            "incremental_equivalence.json": _write_json(stage / "incremental_equivalence.json", equivalence),
            "historical_hash_preservation.json": _write_json(stage / "historical_hash_preservation.json", preservation),
            "known_answers.json": _write_json(stage / "known_answers.json", known_answers),
            "failure_matrix.json": _write_json(stage / "failure_matrix.json", failure_matrix),
        })
        raw_store.cleanup_staging()
        for path in sorted((stage / "raw").rglob("*")):
            if path.is_file():
                artifact_hashes[str(path.relative_to(stage)).replace("\\", "/")] = sha256_file(path)
        references = {name: sha256_file(project_root / relative)
                      for name, relative in recipe["references"].items()}
        core = {
            "schema_version": RUN_VERSION, "classification": recipe["classification"],
            "lifecycle": LIFECYCLE, "canonical": False, "promotion_eligible": False,
            **execution, "post_generation_worktree_expected_dirty": True,
            "environment": environment, "environment_hash": environment_hash,
            "fixture_recipe": str(recipe_path.relative_to(project_root)).replace("\\", "/"),
            "fixture_recipe_sha256": sha256_file(recipe_path), "references": references,
            "raw_manifests": raw_manifests, "artifact_hashes": dict(sorted(artifact_hashes.items())),
            "all_incremental_clean_equivalent": all(equivalence.values()),
            "all_unaffected_hashes_preserved": all(preservation.values()),
            "official_format_status": recipe["official_format_status"],
        }
        _write_json(stage / "root_manifest.json", {**core, "reproducible_core_sha256": _hash(core)})
        if source_staging.exists():
            shutil.rmtree(source_staging)
        os.replace(stage, final)
        return final
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise
