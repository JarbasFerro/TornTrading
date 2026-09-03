# TornTrading — P0-E5 Stock-Sale Fee-Rounding Preregistration

Status: **PREREGISTERED — no private value-bearing run before merge**  
Preregistration date: 2026-09-03  
Primary questions: MEC-004, MEC-006, VAL-001  
Evidence target: P0-E5 stock-sale gross/fee rounding  
Instrument: `research/tools/analyze_stock_sell_fee_rounding.py`

## 1. Research question

Given Torn's documented rule that selling stock incurs a fee equal to **0.1% of the total value sold**, which integer-valued calculation/rounding behavior best reproduces the `fees` value recorded in current official Torn API v2 `Stock sell` logs?

This study is deliberately limited to **behavioral execution-cost reconstruction**. It does not claim to identify Torn's internal source code or prove an implementation order that is observationally indistinguishable from another formula.

## 2. Evidence available before this preregistration

### `MECHANIC`

Official Torn documentation states that stock sales charge 0.1% of total value sold.

### `OBSERVATION`

The approved Stage A candidate-field probe, run from `main` after PR #24, observed that current official user log type **5511 — Stock sell** exposes these allowlisted `data` fields and primitive types:

- `amount: int`
- `price: string`
- `fees: int`
- `profit: int`
- `stock: int`

The corresponding buy log 5510 exposes `amount`, `price`, and `stock`.

The Stage A artifact did not retain any value from an individual transaction.

This schema observation is sufficient to test fee formulas historically without executing an experimental Torn trade.

## 3. Why historical logs are tested before micro-trades

Existing sell logs are preferable to deliberately creating trades when they can answer the same P0 question because they:

- create no experimental transaction cost;
- require no game action from TornTrading;
- provide repeated independent sale receipts;
- can distinguish rounding behavior if gross values happen to fall on useful fractional boundaries.

Historical evidence is not automatically sufficient. The gate remains open if the available observations do not discriminate the frozen candidate family strongly enough.

## 4. Data window and source — frozen before value-bearing execution

Source: official Torn API v2 `GET /user/log` filtered to log type `5511` only.

Window:

- end: official Torn server timestamp obtained immediately before the log request;
- start: end minus **365 days**;
- API row cap: **100** recent matching records;
- no pagination in this first test.

Reasoning:

- one year is recent enough to reduce exposure to obsolete implementation regimes;
- 100 is the documented per-request maximum and is expected to be more than adequate if observations are discriminating;
- the goal is mechanic identification, not estimating the user's trading behavior.

If the sample is capped at 100, the result applies only to the returned recent sample. The analysis must not infer anything about older omitted trades.

## 5. Private fields used transiently

For each valid `Stock sell` entry, the analyzer may read only:

- `data.amount`
- `data.price`
- `data.fees`

`data.profit`, `data.stock`, event ID, event timestamp, title, parameters, and other fields are not needed for the fee test and are not incorporated into a persisted result.

The decimal `price` string is parsed with Python `Decimal`, never binary floating point.

A row is usable only when:

- log type is 5511;
- `amount` is a positive integer;
- `price` is a positive finite decimal;
- `fees` is a non-negative integer.

## 6. Frozen candidate family

Let:

- `p` = logged price;
- `n` = amount/shares;
- `x = p × n`;
- `r = 0.001`.

Integer rounding operators tested:

- `floor`
- `ceiling`
- `half_up`
- `half_even`

### Family A — documented semantic interpretation

`fee = round(x × r)`

Four candidates, one for each integer rounding operator.

Names:

- `total_value__fee_floor`
- `total_value__fee_ceiling`
- `total_value__fee_half_up`
- `total_value__fee_half_even`

### Family B — gross rounded before fee

`fee = round_fee(round_gross(x) × r)`

All combinations of the four gross and four fee operators are considered except three exact mathematical redundancies listed below.

### Family C — defensive `price` semantic falsification

`fee = round(p × r)`

Four candidates. These test the alternative that logged `price` were already a total sale value rather than a per-share value.

### Family D — per-share fee first

`fee = round(p × r) × n`

Four candidates. These deliberately test a materially different implementation order even though Torn's published wording says the fee is based on total value sold.

## 7. Exact redundancies removed before evidence

Three Family-B expressions are not included as separate candidates because, for non-negative `x`, they are exact behavioral identities of simpler Family-A formulas and can never be distinguished by any receipt:

1. `floor(floor(x) / 1000) = floor(x / 1000)`
2. `ceiling(ceiling(x) / 1000) = ceiling(x / 1000)`
3. `half_up(floor(x) / 1000) = half_up(x / 1000)` because every half-up decision boundary occurs at an integer gross value of `1000k + 500`.

Canonical representatives retained:

- `total_value__fee_floor`
- `total_value__fee_ceiling`
- `total_value__fee_half_up`

No other sample-dependent equivalence is collapsed in advance.

Frozen candidate count after these removals: **25 models**.

## 8. Metrics

For every candidate model, publish only:

- aggregate match count;
- aggregate mismatch count;
- match rate.

Also publish:

- usable observation count;
- rejected observation count;
- number of observations on which at least two frozen candidate models predict different fees;
- if there is exactly one perfect model, the **minimum pairwise separation**: the smallest number of observations on which that winner's prediction differs from any one competing model;
- prediction-equivalence classes across the sample, identified only by model names;
- perfect-model names;
- decision status.

The minimum pairwise separation prevents a superficially large global discrimination count from hiding a winner that beats its nearest competitor on only one or two trades.

Do **not** publish any transaction's amount, price, fee, stock, timestamp, profit, or prediction vector.

## 9. Acceptance rule — frozen

P0-E5 may be **proposed for closure** from this historical test only if all are true:

1. at least **6 observations are globally discriminating** across the frozen candidate family;
2. exactly **one non-redundant candidate model** matches every usable observation;
3. the winning model has zero mismatches;
4. the winner differs from **every competing model on at least 6 observations** — equivalently, its minimum pairwise separation is at least 6;
5. the parser rejects no systematic subset suggesting a changed/unknown log schema;
6. the result is reviewed in a separate post-evidence PR before becoming a `VALIDATED_FINDING`.

Otherwise P0-E5 remains open.

Decision statuses:

- `UNIQUE_PERFECT_MODEL`
- `MULTIPLE_EQUIVALENT_PERFECT_MODELS`
- `MULTIPLE_NON_EQUIVALENT_PERFECT_MODELS`
- `NO_PERFECT_MODEL`
- `INSUFFICIENT_DISCRIMINATION`
- `INSUFFICIENT_WINNER_SEPARATION`
- `NO_USABLE_OBSERVATIONS`

A sample-dependent tie is not resolved merely because the tied models happen to make identical predictions on this history. Likewise, a unique perfect fit is not accepted if its nearest competitor is separated by fewer than six observations.

## 10. Privacy contract

The persisted JSON report may contain only aggregate research diagnostics.

It must not contain:

- raw Torn log payloads;
- event/transaction IDs;
- event timestamps;
- stock IDs/acronyms;
- share counts;
- observed prices;
- observed fees;
- observed profits/losses;
- monetary totals, averages, minima, maxima, quantiles, or distributions;
- per-trade model predictions.

Aggregate sample and model-fit counts are allowed because they are necessary to evaluate statistical sufficiency and do not reveal transaction values.

## 11. Claim progression

Before run: `HYPOTHESIS` — one frozen model may reproduce Torn's current sale fee exactly.

After aggregate run: `OBSERVATION` — model fit on the recent historical sample.

Only after a separate review PR satisfies the acceptance rule may the result become a `VALIDATED_FINDING` for the tested implementation period.

Any later Torn stock-market implementation change or incompatible API/log behavior reopens the gate.

## 12. What this cannot answer

This analysis cannot resolve P0-E4: which quote is used when a human sale is submitted across a minute boundary.

Historical sell logs contain execution values but not the page-visible quote and precise human click timing needed to distinguish click-time/display-time/server-processing semantics.

Therefore, even if P0-E5 closes from historical data, P0-E4 will still require a tightly controlled **human-executed** boundary experiment. TornTrading will remain read-only around that experiment.
