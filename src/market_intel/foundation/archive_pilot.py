"""Readiness and completeness gates for a bounded calendar-year archive pilot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PilotGate:
    required_sessions: int
    price_sessions: int
    security_sessions: int
    benchmark_pri_sessions: int
    benchmark_tri_sessions: int
    cost_coverage_complete: bool
    access_quarantines: int = 0
    schema_failures: int = 0


def pilot_readiness(mandatory_evidence: dict[str, bool]) -> tuple[str, list[str]]:
    missing = sorted(key for key, present in mandatory_evidence.items() if not present)
    return ("READY", []) if not missing else ("BLOCKED", missing)


def evaluate_pilot(gate: PilotGate) -> tuple[str, list[str]]:
    failures: list[str] = []
    for name, count in (("price", gate.price_sessions), ("security", gate.security_sessions),
                        ("benchmark_pri", gate.benchmark_pri_sessions),
                        ("benchmark_tri", gate.benchmark_tri_sessions)):
        if count != gate.required_sessions:
            failures.append(f"{name}_sessions={count}/{gate.required_sessions}")
    if not gate.cost_coverage_complete:
        failures.append("cost_schedule_gap")
    if gate.access_quarantines:
        failures.append(f"access_quarantines={gate.access_quarantines}")
    if gate.schema_failures:
        failures.append(f"schema_failures={gate.schema_failures}")
    return ("PASS", []) if not failures else ("ABORT", failures)


def validate_benchmark_pair(pri: dict, tri: dict) -> None:
    if pri.get("return_classification") != "PRI" or tri.get("return_classification") != "TRI":
        raise ValueError("benchmark classifications are not an explicit PRI/TRI pair")
    if not pri.get("index_id") or not tri.get("index_id") or pri["index_id"] == tri["index_id"]:
        raise ValueError("PRI and TRI require distinct stable index identifiers")
