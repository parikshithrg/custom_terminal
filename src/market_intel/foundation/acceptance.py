"""Provider-independent dataset acceptance and trust-capability evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .quality import CapabilityStatus, DatasetTrustContract
from .reconciliation import (CheckResult, population_by_year, reconcile_benchmarks,
                             reconcile_corporate_actions, reconcile_costs, reconcile_daily,
                             reconcile_identity, reconcile_listing_gaps, reconcile_terminal)


@dataclass(frozen=True)
class CanonicalDatasetBundle:
    dataset_id: str
    version: str
    prices: pd.DataFrame
    security_master: pd.DataFrame
    aliases: pd.DataFrame
    corporate_actions: pd.DataFrame
    terminal_outcomes: pd.DataFrame
    benchmarks: pd.DataFrame
    costs: pd.DataFrame
    independent_population_counts: pd.DataFrame | None = None
    population_reference_complete: bool = False
    raw_manifest_count: int = 0


@dataclass(frozen=True)
class CapabilityEvidence:
    capability: str
    status: CapabilityStatus
    evidence: str


def assess_bundle(bundle: CanonicalDatasetBundle) -> tuple[DatasetTrustContract, list[CapabilityEvidence], list[CheckResult], pd.DataFrame]:
    checks: list[CheckResult] = []
    checks += reconcile_daily(bundle.prices)
    checks += [reconcile_listing_gaps(bundle.prices, bundle.benchmarks)]
    checks += reconcile_identity(bundle.security_master, bundle.aliases)
    checks += reconcile_terminal(bundle.security_master, bundle.terminal_outcomes)
    checks += reconcile_corporate_actions(bundle.corporate_actions, bundle.aliases)
    checks += reconcile_benchmarks(bundle.benchmarks)
    start, end = bundle.prices.trade_date.min(), bundle.prices.trade_date.max()
    checks += reconcile_costs(bundle.costs, start, end)
    check_map = {c.check_id: c for c in checks}
    population = population_by_year(bundle.security_master, bundle.independent_population_counts)
    ended = int(bundle.security_master.end_date.notna().sum())
    history_years = pd.to_datetime(bundle.prices.trade_date).dt.year.nunique()
    all_survive = ended == 0 and history_years >= 5
    missing_turnover = check_map["missing_exchange_turnover"].count
    unresolved_identity = check_map["unresolved_stable_identity"].count
    publication_missing = int(bundle.prices.published_at.isna().sum())

    evidence = [
        CapabilityEvidence("price_history_complete", CapabilityStatus.PASS if bundle.population_reference_complete else CapabilityStatus.FAIL,
                           "Independent historical population reconciliation is complete." if bundle.population_reference_complete else "No complete independent historical listing population was supplied."),
        CapabilityEvidence("survivorship_safe", CapabilityStatus.FAIL if all_survive else CapabilityStatus.UNKNOWN,
                           "Multi-year panel has no terminated listings; it behaves like a survivor snapshot." if all_survive else "Termination coverage cannot be proved from supplied evidence."),
        CapabilityEvidence("historical_universe_reconstructible", CapabilityStatus.FAIL if (not bundle.population_reference_complete or missing_turnover or unresolved_identity) else CapabilityStatus.PASS,
                           "Requires complete population, exchange turnover, and resolved identity."),
        CapabilityEvidence("corporate_actions_verified", CapabilityStatus.UNKNOWN if bundle.corporate_actions.empty else
                           (CapabilityStatus.PASS if all(c.status == "PASS" for c in checks if c.check_id.startswith("corporate_action")) else CapabilityStatus.FAIL),
                           "No authoritative corporate-action ledger supplied." if bundle.corporate_actions.empty else "Canonical action ledger reconciled."),
        CapabilityEvidence("delisting_outcomes_available", CapabilityStatus.FAIL if bundle.terminal_outcomes.empty else
                           (CapabilityStatus.PASS if check_map["unresolved_terminal_treatment"].count == 0 else CapabilityStatus.FAIL),
                           "No authoritative terminal-outcome dataset supplied." if bundle.terminal_outcomes.empty else "Terminal records reconciled."),
        CapabilityEvidence("exchange_turnover_available", CapabilityStatus.FAIL if missing_turnover else CapabilityStatus.PASS,
                           f"{missing_turnover} canonical price rows lack exchange turnover."),
        CapabilityEvidence("publication_timing_known", CapabilityStatus.UNKNOWN if publication_missing else CapabilityStatus.PASS,
                           f"{publication_missing} price rows lack provider publication timestamps."),
        CapabilityEvidence("stable_security_identity_verified", CapabilityStatus.FAIL if unresolved_identity else CapabilityStatus.PASS,
                           f"{unresolved_identity} identity records are unresolved or conflicting."),
    ]
    values = {item.capability: item.status for item in evidence}
    contract = DatasetTrustContract(bundle.dataset_id, bundle.version, **values)
    return contract, evidence, checks, population


def write_acceptance_report(bundle: CanonicalDatasetBundle, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract, evidence, checks, population = assess_bundle(bundle)
    machine = {"dataset_id": bundle.dataset_id, "version": bundle.version,
               "raw_manifest_count": bundle.raw_manifest_count,
               "capabilities": [asdict(x) for x in evidence], "checks": [asdict(x) for x in checks]}
    (output_dir / "acceptance_report.json").write_text(json.dumps(machine, indent=2, default=str) + "\n", encoding="utf-8")
    population.to_parquet(output_dir / "population_by_year.parquet", index=False)
    population.to_csv(output_dir / "population_by_year.csv", index=False)
    lines = [f"# Dataset Acceptance — {bundle.dataset_id}", "", f"Version: `{bundle.version}`", "",
             "## Trust capabilities", "", "| Capability | Status | Evidence |", "|---|---|---|"]
    lines += [f"| `{x.capability}` | **{x.status}** | {x.evidence} |" for x in evidence]
    lines += ["", "## Reconciliation checks", "", "| Check | Status | Count | Evidence |", "|---|---|---:|---|"]
    lines += [f"| `{x.check_id}` | {x.status} | {x.count} | {x.evidence} |" for x in checks]
    lines += ["", "## Decision", "", "**REJECTED FOR EDGE RESEARCH**" if any(x.status != CapabilityStatus.PASS for x in evidence)
              else "**ACCEPTED FOR DECLARED CAPABILITIES**", ""]
    (output_dir / "acceptance_report.md").write_text("\n".join(lines), encoding="utf-8")
