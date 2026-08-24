# Indian Delivery Cost-Model Audit

The Slice A compatibility cost definition is preserved as `india_delivery_2026_08_13_slippage_5bps_v1`; no rate or golden-fixture output was changed.

| Component | Historical status |
|---|---|
| Brokerage | Broker/product-specific; current zero-delivery assumption, not historically universal |
| STT | Statutory and potentially date-varying |
| Exchange transaction charge | Date-varying |
| SEBI charge | Date-varying |
| Stamp duty | Date- and jurisdiction/schedule-sensitive |
| GST/service tax | Tax regime and rate changed historically |
| Slippage | Approximate; 5 bps per side assumption |
| Spread/market impact | Unknown from daily bars |

`DatedCostSchedule` now supports explicit effective intervals and fails when no dated schedule exists. Historical schedules must be sourced and versioned before costs can be described as historically accurate.
