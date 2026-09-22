# Kite REST NSE-equity currency binding review v1

Reviewed 2026-09-22 as the next bounded Dashboard prerequisite test. This was a
public-documentation review only. No authenticated endpoint, market-data request,
credential, account state, response payload or local market database was accessed.

## Question

Do current official documents explicitly bind Kite REST `/quote` `last_price` for
an `NSE` `EQ` target to Indian rupees in major currency units, strongly enough to
clear the frozen `CURRENCY_UNITS` Dashboard gate without inference?

## Evidence

- Kite's official market-quotes documentation defines REST `last_price` as the
  last traded market price and identifies instruments by an exchange-symbol pair.
  Its response schema does not include a currency
  field or a REST price-unit declaration.
- Kite's official WebSocket documentation states that binary quote prices are
  integer paise for non-currency instruments and are divided by 100. This is an
  explicit WebSocket wire-format rule, not an explicit REST JSON-field rule.
- Official NSE capital-market material identifies cash-segment tick sizes in
  rupees or INR. This establishes exchange-level cash-market denomination, but it
  does not specify Kite's REST serialization contract.

Official pages reviewed:

- <https://kite.trade/docs/connect/v3/market-quotes/>
- <https://kite.trade/docs/connect/v3/websocket/>
- <https://nsearchives.nseindia.com/content/circulars/CMTR62174.pdf>
- <https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Real%20time_CM-L1_L2_L3_V1.29_2.pdf>

No copies of the pages or documents were retained.

## Result

`UNRESOLVED_EXPLICIT_REST_CURRENCY_UNIT_BINDING_ABSENT`.

It is reasonable to infer that an NSE cash-equity REST value such as a decimal
last traded market price represents INR major units. The project does not promote
that inference to an authoritative REST field contract. Agreement with WebSocket
scaling, tick size or a sample number would not prove the REST serialization rule.

The current exact-price decoder must therefore retain `currency_state=NOT_VERIFIED`.
No currency label, conversion, multiplication, division, fallback or substitution
is authorized. The Dashboard remains synthetic and
`NOT_ELIGIBLE_FOR_DASHBOARD_WIRING`.

## Next bounded decision

The smallest authoritative resolution is a provider-issued statement or
documentation change explicitly binding NSE cash-equity REST quote price fields to
INR major units. Until then, an operational transport test may validate bounded
request/response behavior and exact decoding only; it cannot clear currency or
authorize Dashboard display. Such transport implementation and execution remain
separately gated by the frozen exact-test scope and its local target binding.
