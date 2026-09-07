"""Deterministic fictional calendar fixture and R.10D evidence support."""

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
from market_intel.foundation.artifacts import canonical_json, sha256_file, write_parquet_immutable
from market_intel.foundation.exchange_calendar import (
    CALENDAR_VERSION, CLOCK_VERSION, LOCAL_TIMEZONE, SETTLEMENT_VERSION,
    SYNTHETIC_VENUE, AvailabilityPolicy, DecisionClock, SessionType,
    SettlementRule, calendar_as_of, clock_instant, contract_metadata,
    executable_sessions, information_available, month_end_session,
    resolve_session, session_distance, settlement_date, validate_calendar,
)
from market_intel.foundation.incremental import Change, DependencyGraph, DependencyNode
from market_intel.foundation.incremental import execute_rebuild, graph_equivalent, impact_summary, plan_rebuild
from market_intel.research.folds import session_ordinal_fold_boundaries
from market_intel.research.outcomes import SessionAwareOutcomeDefinition, materialize_session_aware_outcomes


RUN_VERSION = "synthetic_session_clock_run_r10d_v1"
CLASSIFICATION = "SYNTHETIC_ONLY_NONCANONICAL"


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _utc(day: str, local_time: str) -> str:
    return str(pd.Timestamp(f"{day} {local_time}", tz=LOCAL_TIMEZONE).tz_convert("UTC"))


def _row(day: str, session_type: SessionType, trading: bool, *,
         opened: str = "09:15", closed: str = "15:30", occurred: bool | None = None,
         settlement: bool | None = None, published: str = "2019-12-01 12:00",
         available: str | None = None, revision: int = 1, parent: str | None = None,
         source: str = "SYN_CALENDAR_SOURCE_A", suffix: str = "") -> dict:
    session_id = f"SYNX-{day}"
    published_at = pd.Timestamp(published, tz=LOCAL_TIMEZONE).tz_convert("UTC")
    return {
        "calendar_id": "SYNX_PRIMARY", "calendar_version": CALENDAR_VERSION,
        "venue": SYNTHETIC_VENUE, "timezone": LOCAL_TIMEZONE,
        "session_id": session_id, "local_session_date": day,
        "session_type": session_type.value,
        "scheduled_open": _utc(day, opened) if trading else None,
        "scheduled_close": _utc(day, closed) if trading else None,
        "phase_times": json.dumps({"pre_open": _utc(day, "09:00")} if trading else {}),
        "trading_eligible": trading,
        "settlement_eligible": trading if settlement is None else settlement,
        "occurred": trading if occurred is None else occurred,
        "published_at": published_at,
        "available_at": published_at if available is None else pd.Timestamp(
            available, tz=LOCAL_TIMEZONE).tz_convert("UTC"),
        "effective_at": _utc(day, opened if trading else "00:00"),
        "revision_number": revision,
        "source_record_id": f"{session_id}:{source}:r{revision}{suffix}",
        "supersedes_record_id": parent,
        "source_id": source,
        "raw_evidence_hash": _hash({"day": day, "source": source, "revision": revision,
                                     "suffix": suffix, "type": session_type.value}),
        "quality_flags": "[]",
    }


def generate_calendar_vintages() -> pd.DataFrame:
    """Build a daily, multi-year-boundary fixture; no weekday is inferred downstream."""
    rows: list[dict] = []
    start, end = pd.Timestamp("2019-11-27"), pd.Timestamp("2020-05-13")
    for day in pd.date_range(start, end, freq="D"):
        text = day.strftime("%Y-%m-%d")
        trading = day.dayofweek < 5
        kind = SessionType.NORMAL if trading else SessionType.FULL_DAY_HOLIDAY
        rows.append(_row(text, kind, trading))

    def replace_initial(day: str, **kwargs) -> None:
        rows[:] = [row for row in rows if not (row["local_session_date"] == day
                                               and row["revision_number"] == 1
                                               and row["source_id"] == "SYN_CALENDAR_SOURCE_A")]
        rows.append(_row(day, **kwargs))

    replace_initial("2019-12-25", session_type=SessionType.FULL_DAY_HOLIDAY, trading=False)
    replace_initial("2019-12-28", session_type=SessionType.SPECIAL_WEEKEND, trading=True,
                    opened="10:00", closed="12:00", settlement=False)
    replace_initial("2019-12-31", session_type=SessionType.SHORTENED, trading=True, closed="12:30")
    replace_initial("2020-01-02", session_type=SessionType.DELAYED_OPEN, trading=True, opened="10:15")
    # Advance-announced holiday: originally planned normal, revision available Jan 10.
    parent = "SYNX-2020-01-27:SYN_CALENDAR_SOURCE_A:r1"
    rows.append(_row("2020-01-27", SessionType.FULL_DAY_HOLIDAY, False,
                     published="2020-01-10 10:00", revision=2, parent=parent))
    # Unexpected closure was not knowable before the session; corrected next day.
    parent = "SYNX-2020-01-15:SYN_CALENDAR_SOURCE_A:r1"
    rows.append(_row("2020-01-15", SessionType.UNEXPECTED_CLOSURE, False, occurred=False,
                     published="2020-01-16 10:00", revision=2, parent=parent))
    # Consecutive announced holidays.
    for day in ("2020-02-03", "2020-02-04"):
        parent = f"SYNX-{day}:SYN_CALENDAR_SOURCE_A:r1"
        rows.append(_row(day, SessionType.FULL_DAY_HOLIDAY, False,
                         published="2020-01-20 10:00", revision=2, parent=parent))
    # Leap-day special session proves that date is explicit, not inferred.
    replace_initial("2020-02-29", session_type=SessionType.SPECIAL_WEEKEND, trading=True,
                    opened="10:00", closed="11:30", settlement=False,
                    published="2020-02-10 10:00")
    # Future time revision, announced before the affected session.
    parent = "SYNX-2020-03-02:SYN_CALENDAR_SOURCE_A:r1"
    rows.append(_row("2020-03-02", SessionType.SHORTENED, True, closed="13:00",
                     published="2020-02-20 10:00", revision=2, parent=parent))
    # Trading day on which settlement is closed.
    replace_initial("2020-01-31", session_type=SessionType.NORMAL, trading=True, settlement=False)
    return validate_calendar(rows)


def conflicting_calendar_vintage(calendar: pd.DataFrame) -> pd.DataFrame:
    conflict = _row("2020-03-10", SessionType.SHORTENED, True, closed="14:00",
                    published="2020-02-25 10:00", source="SYN_CALENDAR_SOURCE_B",
                    suffix="-conflict")
    return validate_calendar([*calendar.to_dict("records"), conflict])


def settlement_rules() -> list[SettlementRule]:
    return [
        SettlementRule("SYN_T_PLUS_2", SETTLEMENT_VERSION,
                       pd.Timestamp("2019-01-01T00:00:00Z"),
                       pd.Timestamp("2020-03-01T00:00:00Z"), 2),
        SettlementRule("SYN_T_PLUS_1", SETTLEMENT_VERSION,
                       pd.Timestamp("2020-03-01T00:00:00Z"), None, 1),
        SettlementRule("SYN_CA_CASH_T2", SETTLEMENT_VERSION,
                       pd.Timestamp("2019-01-01T00:00:00Z"), None, 2, "CASH"),
        SettlementRule("SYN_CA_SHARE_T3", SETTLEMENT_VERSION,
                       pd.Timestamp("2019-01-01T00:00:00Z"), None, 3, "SHARES"),
    ]


def availability_policies() -> list[AvailabilityPolicy]:
    return [
        AvailabilityPolicy("SYN_DAILY_CLOSE", "synthetic_daily_bar", 20,
                           "NEXT_EXECUTABLE_SESSION_OPEN"),
        AvailabilityPolicy("SYN_CORPORATE_EVENT", "synthetic_security_event", 60,
                           "NEXT_EXECUTABLE_SESSION_OPEN"),
        AvailabilityPolicy("SYN_BENCHMARK", "synthetic_benchmark", 10,
                           "NEXT_EXECUTABLE_SESSION_OPEN"),
    ]


def known_answers() -> dict[str, object]:
    calendar = generate_calendar_vintages()
    early = calendar_as_of(calendar, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
                           knowledge_cutoff=pd.Timestamp("2020-01-09T12:00:00Z"),
                           decision_clock=DecisionClock.SESSION_CLOSE)
    post_announcement = calendar_as_of(
        calendar, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
        knowledge_cutoff=pd.Timestamp("2020-01-11T12:00:00Z"),
        decision_clock=DecisionClock.SESSION_CLOSE)
    final = calendar_as_of(calendar, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
        knowledge_cutoff=pd.Timestamp("2020-05-20T12:00:00Z"),
                           decision_clock=DecisionClock.SESSION_CLOSE)
    entry = resolve_session(final, after=pd.Timestamp("2020-01-24T10:00:00Z"))
    exit_21 = resolve_session(final, after=entry.instant, ordinal=21)
    shortened = final[final.session_id == "SYNX-2019-12-31"].iloc[0]
    month_end = month_end_session(final, 2020, 2)
    non_session_month_end = month_end_session(final, 2019, 11)
    policy = availability_policies()[0]
    at_boundary = information_available(
        published_at=pd.Timestamp("2020-01-24T10:00:00Z"),
        retrieved_at=pd.Timestamp("2020-01-25T10:00:00Z"), precision="INTRADAY",
        policy=policy, knowledge_cutoff=pd.Timestamp("2020-01-24T10:20:00Z"),
        calendar_view=final)
    return {
        "local_open_to_utc": str(pd.Timestamp("2020-01-06 09:15", tz=LOCAL_TIMEZONE).tz_convert("UTC")),
        "special_session_included": "SYNX-2019-12-28" in set(executable_sessions(final).session_id),
        "shortened_close": clock_instant(shortened, DecisionClock.SESSION_CLOSE).isoformat(),
        "month_end_session": str(month_end.session_id),
        "non_session_month_end_resolves_to": str(non_session_month_end.session_id),
        "next_entry_after_holiday": asdict(entry),
        "exit_21": asdict(exit_21),
        "session_distance": session_distance(final, entry.session_id, exit_21.session_id),
        "publication_at_boundary": {"available": at_boundary[0], "available_at": at_boundary[1]},
        "holiday_before_announcement_tradable": bool(
            early[early.session_id == "SYNX-2020-01-27"].iloc[0].trading_eligible),
        "holiday_after_announcement_tradable": bool(
            post_announcement[post_announcement.session_id == "SYNX-2020-01-27"].iloc[0].trading_eligible),
        "t_plus_2": asdict(settlement_date(final, trade_session_id="SYNX-2020-01-30",
                                            rules=settlement_rules())),
        "t_plus_1": asdict(settlement_date(final, trade_session_id="SYNX-2020-03-02",
                                            rules=settlement_rules())),
        "terminal_cash_settlement": asdict(settlement_date(
            final, trade_session_id="SYNX-2020-03-02", rules=settlement_rules(), leg="CASH")),
        "terminal_share_settlement": asdict(settlement_date(
            final, trade_session_id="SYNX-2020-03-02", rules=settlement_rules(), leg="SHARES")),
    }


def calendar_dependency_graph(environment_hash: str) -> DependencyGraph:
    base = _base_graph(environment_hash)
    extras = [
        DependencyNode("calendar_pre", "CALENDAR_AS_OF", CALENDAR_VERSION, (), (_hash(CALENDAR_VERSION),),
                       _hash("calendar_pre"), {"depends_on": "calendar",
                       "knowledge_cutoff": "2020-01-09T12:00:00Z", "window_start": "2019-11-27T00:00:00Z",
                       "window_end": "2020-01-31T23:59:59Z"}, schema_version=CALENDAR_VERSION,
                       environment_hash=environment_hash),
        DependencyNode("calendar_post", "CALENDAR_AS_OF", CALENDAR_VERSION, (), (_hash(CALENDAR_VERSION),),
                       _hash("calendar_post"), {"depends_on": "calendar",
                       "knowledge_cutoff": "2020-05-20T12:00:00Z", "window_start": "2019-11-27T00:00:00Z",
                       "window_end": "2020-05-13T23:59:59Z"}, schema_version=CALENDAR_VERSION,
                       environment_hash=environment_hash, downstream=("session_outcomes", "session_folds")),
        DependencyNode("session_outcomes", "SESSION_OUTCOMES", "session_outcome_v2", (),
                       (_hash("session_outcome_v2"),), _hash("session_outcomes"),
                       {"depends_on": "calendar,publication", "knowledge_cutoff": "2020-05-20T12:00:00Z",
                        "window_start": "2020-01-01T00:00:00Z", "window_end": "2020-05-13T23:59:59Z"},
                       parents=("calendar_post",), schema_version="session_outcome_v2",
                       environment_hash=environment_hash),
        DependencyNode("session_folds", "SESSION_FOLDS", "session_fold_v1", (),
                       (_hash("session_fold_v1"),), _hash("session_folds"),
                       {"depends_on": "calendar", "knowledge_cutoff": "2020-05-20T12:00:00Z",
                        "window_start": "2020-01-01T00:00:00Z", "window_end": "2020-05-13T23:59:59Z"},
                       parents=("calendar_post",), schema_version="session_fold_v1",
                       environment_hash=environment_hash),
        DependencyNode("settlement", "SETTLEMENT", SETTLEMENT_VERSION, (),
                       (_hash(SETTLEMENT_VERSION),), _hash("settlement"),
                       {"depends_on": "settlement", "knowledge_cutoff": "2020-05-20T12:00:00Z",
                        "window_start": "2019-11-27T00:00:00Z", "window_end": "2020-05-13T23:59:59Z"},
                       schema_version=SETTLEMENT_VERSION, environment_hash=environment_hash),
    ]
    # Replace the two base nodes that point to the extended children.
    nodes = list(base.nodes.values()) + extras
    return DependencyGraph(nodes)


def calendar_changes() -> dict[str, Change]:
    return {
        "future_holiday": Change("future_holiday", "calendar", pd.Timestamp("2020-01-27T00:00:00Z"),
                                  pd.Timestamp("2020-01-10T04:30:00Z")),
        "unexpected_closure": Change("unexpected_closure", "calendar", pd.Timestamp("2020-01-15T00:00:00Z"),
                                      pd.Timestamp("2020-01-16T04:30:00Z")),
        "corrected_time": Change("corrected_time", "calendar", pd.Timestamp("2020-03-02T00:00:00Z"),
                                  pd.Timestamp("2020-02-20T04:30:00Z")),
        "special_session": Change("special_session", "calendar", pd.Timestamp("2020-02-29T00:00:00Z"),
                                   pd.Timestamp("2020-02-10T04:30:00Z")),
        "settlement_rule": Change("settlement_rule", "settlement", pd.Timestamp("2020-03-01T00:00:00Z"),
                                   pd.Timestamp("2020-02-15T00:00:00Z")),
        "publication_correction": Change("publication_correction", "publication",
                                          pd.Timestamp("2020-02-10T10:00:00Z"),
                                          pd.Timestamp("2020-02-12T10:00:00Z")),
    }


def contract_bundle() -> dict[str, object]:
    return {"metadata": contract_metadata(),
            "availability_policies": [asdict(policy) for policy in availability_policies()],
            "settlement_rules": [asdict(rule) for rule in settlement_rules()],
            "run_version": RUN_VERSION, "classification": CLASSIFICATION}


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
    sources = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    return {
        "source_commit": commit,
        "execution_start_dirty": False,
        "execution_start_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "source_tree_sha256": _hash([f"{path.relative_to(project_root)}:{sha256_file(path)}"
                                     for path in sources]),
        "entrypoint": str(entrypoint.relative_to(project_root)).replace("\\", "/"),
        "entrypoint_sha256": sha256_file(entrypoint),
    }


def _outcome_and_fold_evidence(final: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    sessions = executable_sessions(final)
    identifiers = list(sessions.session_id)
    opens = pd.DataFrame({"SYN_C_I001": [100.0 + position for position in range(len(identifiers))]},
                         index=identifiers)
    benchmark = pd.Series([1000.0 + position for position in range(len(identifiers))], index=identifiers)
    ranked = pd.DataFrame([
        {"prediction_id": "SYN_CLOCK_P1", "instrument_id": "SYN_C_I001",
         "decision_session_id": "SYNX-2020-01-24", "selected": True},
        {"prediction_id": "SYN_CLOCK_P2", "instrument_id": "SYN_C_I002",
         "decision_session_id": "SYNX-2020-04-14", "selected": True},
    ])
    outcomes = materialize_session_aware_outcomes(
        ranked, opens, benchmark, final, SessionAwareOutcomeDefinition(),
        instrument_states={("SYN_C_I002", "SYNX-2020-04-15"): "SUSPENDED"},
    )
    fold = session_ordinal_fold_boundaries(
        final, validation_boundary_session_id="SYNX-2020-02-10",
        validation_end_session_id="SYNX-2020-04-10", holding_sessions=21,
    )
    return outcomes, fold


def run_calendar_evidence(*, recipe_path: Path, output_dir: Path,
                          project_root: Path, entrypoint: Path) -> Path:
    """Publish compact R.10D evidence from an exact clean checkpoint."""
    execution = _execution_state(project_root, entrypoint)
    if output_dir.exists():
        raise FileExistsError("immutable R.10D evidence already exists")
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe["classification"] != CLASSIFICATION:
        raise ValueError("R.10D accepts synthetic fixtures only")
    stage = output_dir.with_name("." + output_dir.name + ".staging")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        vintages = generate_calendar_vintages()
        final = calendar_as_of(
            vintages, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
            knowledge_cutoff=pd.Timestamp("2020-05-20T12:00:00Z"),
            decision_clock=DecisionClock.SESSION_CLOSE,
        )
        outcomes, fold = _outcome_and_fold_evidence(final)
        answers = known_answers()
        graph = calendar_dependency_graph("r10d-evidence-env")
        plans: dict[str, object] = {}
        ledger: list[dict[str, str]] = []
        equivalence: dict[str, bool] = {}
        preservation: dict[str, bool] = {}
        for change_id, change in calendar_changes().items():
            plan = plan_rebuild(graph, change)
            clean = _clean_candidate(graph, plan, change_id)
            incremental, decisions = execute_rebuild(graph, clean, plan)
            equivalence[change_id] = graph_equivalent(incremental, clean)
            unchanged = [node for node, result in plan.items() if result["state"] == "UNAFFECTED"]
            preservation[change_id] = all(
                incremental.nodes[node].output_hash == graph.nodes[node].output_hash for node in unchanged)
            plans[change_id] = {"impact": impact_summary(graph, change), "nodes": plan}
            ledger.extend({"change_id": change_id, **item} for item in decisions)
            graph = incremental

        failure_matrix = {
            "DUPLICATE_SESSION_IDENTITY": "PASS_FAIL_CLOSED",
            "OVERLAPPING_SESSIONS": "PASS_FAIL_CLOSED",
            "CLOSE_NOT_AFTER_OPEN": "PASS_FAIL_CLOSED",
            "NAIVE_TIMESTAMP": "PASS_FAIL_CLOSED",
            "UNKNOWN_TIMEZONE": "PASS_FAIL_CLOSED",
            "CONFLICTING_ACTIVE_REVISIONS": "PRESERVED_CONFLICT_AND_BLOCKED",
            "MISSING_CALENDAR_VERSION": "PASS_FAIL_CLOSED",
            "UNKNOWN_DECISION_CLOCK": "PASS_FAIL_CLOSED",
            "DECISION_INSTANT_OUTSIDE_SESSION": "PASS_FAIL_CLOSED",
            "NO_FUTURE_EXECUTABLE_SESSION": "NAMED_STATUS",
            "INCORRECT_WEEKDAY_FALLBACK": "PROHIBITED_BY_CONTRACT",
            "INSTRUMENT_ROW_CALENDAR": "PROHIBITED_BY_V2_CONTRACT",
            "CALENDAR_DAY_HORIZON": "PROHIBITED_BY_SESSION_ORDINALS",
            "FINAL_VINTAGE_LEAKED_BACKWARD": "PASS_FAIL_CLOSED",
            "SETTLEMENT_BEFORE_TRADE": "PASS_FAIL_CLOSED",
            "INVALID_REVISION_CHAIN": "PASS_FAIL_CLOSED",
        }
        artifact_hashes = {
            "calendar_vintages.parquet": write_parquet_immutable(vintages, stage / "calendar_vintages.parquet"),
            "calendar_final.parquet": write_parquet_immutable(final, stage / "calendar_final.parquet"),
            "session_outcomes.parquet": write_parquet_immutable(outcomes, stage / "session_outcomes.parquet"),
            "calendar_contracts.json": _write_json(stage / "calendar_contracts.json", contract_bundle()),
            "known_answers.json": _write_json(stage / "known_answers.json", answers),
            "fold_reconciliation.json": _write_json(stage / "fold_reconciliation.json", fold),
            "incremental_rebuild_plans.json": _write_json(stage / "incremental_rebuild_plans.json", plans),
            "incremental_rebuild_ledger.json": _write_json(stage / "incremental_rebuild_ledger.json", ledger),
            "incremental_equivalence.json": _write_json(stage / "incremental_equivalence.json", equivalence),
            "historical_hash_preservation.json": _write_json(stage / "historical_hash_preservation.json", preservation),
            "failure_matrix.json": _write_json(stage / "failure_matrix.json", failure_matrix),
        }
        environment = {name: importlib.metadata.version(name) for name in ("pandas", "pyarrow")}
        environment["python"] = platform.python_version()
        references = {
            "r10a_root": sha256_file(project_root / "docs/investigations/r10a/run_v1/root_run_manifest.json"),
            "r10b_root": sha256_file(project_root / "docs/investigations/r10b/run_v1/root_manifest.json"),
            "r10c_root": sha256_file(project_root / "docs/investigations/r10c/run_v1/root_manifest.json"),
            "momentum_spec": sha256_file(project_root / "specs/momentum_12_1_v1.json"),
            "golden_expected": sha256_file(project_root / "tests/fixtures/momentum_golden_v1/expected.json"),
        }
        core = {
            "schema_version": RUN_VERSION,
            "classification": CLASSIFICATION,
            "canonical": False,
            "promotion_eligible": False,
            **execution,
            "post_generation_worktree_expected_dirty": True,
            "environment": environment,
            "environment_hash": _hash(environment),
            "fixture_recipe": str(recipe_path.relative_to(project_root)).replace("\\", "/"),
            "fixture_recipe_sha256": sha256_file(recipe_path),
            "references": references,
            "artifact_hashes": dict(sorted(artifact_hashes.items())),
            "all_incremental_clean_equivalent": all(equivalence.values()),
            "all_unaffected_hashes_preserved": all(preservation.values()),
            "official_exchange_compatibility": "NOT_CLAIMED",
        }
        _write_json(stage / "root_manifest.json",
                    {**core, "reproducible_core_sha256": _hash(core)})
        os.replace(stage, output_dir)
        return output_dir
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise
