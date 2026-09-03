# TornTrading — P0-E5 Fee-Rounding Diagnostic Result

Status: **OBSERVATION — P0-E5 remains open**  
Evidence run: GitHub Actions `33720328203`  
Source: official Torn API v2 `user/log` type 5511  
Research date: 2026-09-03

## Decision

The post-confirmation diagnostic does **not** close P0-E5 and does not revise the failed first preregistered confirmation.

It materially narrows the remaining ambiguity.

## Evidence

The diagnostic exhausted the complete available 365-day Stock sell history inside the configured cap after one page:

- pages fetched: 1;
- history exhausted within cap: yes;
- usable Stock sell observations: 100;
- rejected observations: 0;
- duplicate event IDs: 0.

Therefore the original 100-row confirmation sample was already the entire available one-year sale history for this account. Pagination cannot provide an independent larger natural-history sample.

### Logged price representation

All 100 sale logs represented `data.price` with exactly **2 decimal places**.

This is important because the receipt fee may have been calculated using a higher-precision internal execution price that is not recoverable from the public-safe logged value representation.

### Reference ceiling behavior

Frozen reference model:

`fee = ceil(logged_price × shares × 0.001)`

Aggregate result:

- matches: 99;
- mismatches: 1;
- match rate: 99%;
- mismatch magnitude: exactly +$1 relative to the logged-price prediction;
- no negative residuals;
- no mismatches larger than $1.

The mismatch is in the oldest chronological rank quartile; the other three quartiles contain zero reference mismatches.

This is insufficient evidence to claim a structural break because it is only one event.

### Logged-price precision compatibility

The single mismatch is compatible with **both** preregistered conservative price-precision envelopes:

1. logged price was nearest-rounded to cents, with possible internal price in `[p - $0.005, p + $0.005]`;
2. logged price was downward-truncated to cents, with possible internal price in `[p, p + $0.01]`.

Compatibility means only that some higher-precision price inside either interval could produce the observed fee under a total-value ceiling rule. It does not prove Torn uses hidden precision or either particular display/log rounding convention.

### Model order remains unresolved

Four ceiling-like models remain prediction-equivalent across all 100 observations and each matches 99/100:

- `total_value__fee_ceiling`;
- `gross_floor__fee_ceiling`;
- `gross_half_up__fee_ceiling`;
- `gross_half_even__fee_ceiling`.

Natural historical observations therefore do not identify whether Torn first rounds the gross sale value before applying the fee.

Nearest-integer fee models match 56/100, floor-like models match 4/100, and the defensive `price_is_total` / per-share-first alternatives match essentially none of the sample.

## Evidence classification

`OBSERVATION`:

- current official Stock sell history strongly supports ceiling-like behavior;
- the only discrepancy from a simple logged-price total-value ceiling rule is +$1 and is compatible with hidden sub-cent price precision;
- the existing natural sample cannot determine gross-rounding order.

Not yet a `VALIDATED_FINDING`:

- exact fee calculation order;
- exact internal execution-price precision;
- whether the +$1 anomaly is precision-related, a historical implementation difference, or another receipt/log behavior.

## Consequence

P0-E5 now requires a deliberately discriminating **future/manual confirmation**, not more retrospective mining of the same 100 logs.

The next test should use small human-executed sales whose gross value is deliberately positioned just above an exact $1,000 boundary and below the $0.50 gross-rounding threshold, with enough safety margin that any true execution price inside the conservative hidden-cent interval leaves the competing model predictions unchanged.

This can distinguish:

- ceiling of the unrounded total sale value; from
- floor/nearest integer fee rules; and
- ceiling applied only after gross-value floor/nearest rounding.

P0-E4 minute-boundary execution semantics remain independent and open.
