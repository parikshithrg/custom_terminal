"""Compose existing synthetic parsing and readiness contracts without activation."""
from dataclasses import dataclass, replace
import hashlib
import json

from .offline_equity_quote_parser_v1 import SyntheticTarget, parse_fixture_quotes
from .dashboard_current_equity_readiness_v1 import EquityFixtureRecord, evaluate


@dataclass(frozen=True, slots=True)
class ValidationResult:
    parsed: object
    readiness: object

    def to_bytes(self):
        if (self.parsed.readiness_state != "SYNTHETIC_NOT_MARKET_READY" or
                self.readiness.readiness_state != "SYNTHETIC_NOT_MARKET_READY" or
                self.parsed.can_fetch or self.readiness.can_fetch or
                self.parsed.can_expose_real_data or self.readiness.can_expose_real_data):
            raise ValueError("Offline synthetic validation only")
        return json.dumps({"schema_version": "offline_equity_validation_v1",
                           "parsed": json.loads(self.parsed.to_bytes()),
                           "readiness": json.loads(self.readiness.to_bytes())},
                          sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def validate(*, mode, fixture_version, payload, bindings, retrieval_completed_at,
             as_of, policy, timezone_policy=None):
    """Bindings explicitly pair parser targets with synthetic metadata placeholders."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic fixtures only")
    if type(bindings) is not tuple or not 1 <= len(bindings) <= 25:
        raise ValueError("One to 25 immutable bindings required")
    targets, metadata = [], []
    for binding in bindings:
        if type(binding) is not tuple or len(binding) != 2:
            raise ValueError("Explicit target/metadata pair required")
        target, record = binding
        if type(target) is not SyntheticTarget or type(record) is not EquityFixtureRecord:
            raise ValueError("Synthetic target and metadata required")
        target.__post_init__()
        record.__post_init__()
        if (target.instrument_key != record.instrument_key or
                record.exchange != "SIMULATED" or record.instrument_class != "EQ" or
                record.currency != "INR" or record.source_state != "AVAILABLE" or
                record.last_price is not None or record.missing_reason != "INPUT_NOT_PARSED" or
                record.provider_quote_time is not None or record.last_trade_time is not None or
                record.retrieval_completed_at is not None):
            raise ValueError("Eligible empty synthetic metadata required")
        targets.append(target)
        metadata.append(record)
    if len({item.provider_token for item in metadata}) != len(metadata):
        raise ValueError("Ambiguous metadata token binding")
    parsed = parse_fixture_quotes(mode=mode, fixture_version=fixture_version, payload=payload,
        targets=tuple(targets), retrieval_completed_at=retrieval_completed_at, as_of=as_of,
        timezone_policy=timezone_policy)
    records = tuple(replace(record, last_price=row.original_price,
        missing_reason="MISSING_ROW" if "MISSING_ROW" in row.reason_codes else
                       ("MISSING_PRICE" if row.original_price is None else None),
        provider_quote_time=row.provider_quote_time, last_trade_time=row.last_trade_time,
        retrieval_completed_at=retrieval_completed_at,
        source_state="MISSING_ROW" if "MISSING_ROW" in row.reason_codes else "AVAILABLE",
        parser_version=parsed.schema_version) for record, row in zip(metadata, parsed.records))
    readiness = evaluate(mode=mode, fixture_version=fixture_version, as_of=as_of,
                         policy=policy, records=records)
    # Parser diagnostics are never cleared merely because a readiness check passes.
    combined = []
    for row, checked in zip(parsed.records, readiness.records):
        reasons = tuple(dict.fromkeys(row.reason_codes + checked.reason_codes))
        combined.append(replace(checked, reason_codes=reasons,
            value_state="UNAVAILABLE" if reasons else checked.value_state,
            display_price=None if reasons else checked.display_price))
    return ValidationResult(parsed, replace(readiness, records=tuple(combined)))
