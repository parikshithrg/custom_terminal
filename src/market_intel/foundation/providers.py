"""Provider-neutral acquisition boundary for mandatory historical datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class DatasetKind(StrEnum):
    DAILY_EQUITY = "daily_equity"
    SECURITY_MASTER = "security_master"
    CORPORATE_ACTIONS = "corporate_actions"
    TERMINAL_OUTCOMES = "terminal_outcomes"
    BENCHMARK_HISTORY = "benchmark_history"
    COST_SCHEDULES = "cost_schedules"


@dataclass(frozen=True)
class AcquisitionRequest:
    dataset: DatasetKind
    parameters: dict[str, str] = field(default_factory=dict)
    expected_event_date: str | None = None


@dataclass(frozen=True)
class ProviderObject:
    provider: str
    dataset: DatasetKind
    source_identity: str
    local_path: Path
    request_parameters: dict[str, str] = field(default_factory=dict)
    expected_event_date: str | None = None
    licensing_notes: str | None = None


class HistoricalDataProvider(Protocol):
    provider_id: str

    def discover(self, request: AcquisitionRequest) -> list[ProviderObject]: ...

    def parser_version(self, dataset: DatasetKind) -> str: ...


class DatasetNormalizer(Protocol):
    provider_id: str

    def normalize(self, dataset: DatasetKind, raw_paths: list[Path]) -> object: ...
