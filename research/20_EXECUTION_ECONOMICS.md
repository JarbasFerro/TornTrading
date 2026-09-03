# TornTrading — Stock Execution Economics Gate

Status: **Stage 0 / P0 execution research**  
Research date: 2026-09-03  
Questions advanced: MEC-003, MEC-004, MEC-006, VAL-001, VAL-002  
Claim status: mixed `MECHANIC` / `OBSERVATION` / `HYPOTHESIS`; P0-E4 and P0-E5 remain open until empirical evidence is reviewed.

## Purpose

Resolve the Torn-specific execution details required before a predictive stock effect can be interpreted as executable alpha:

1. Which stock price is actually used when a human submits a sale near a one-minute price change?
2. In what order and with what integer rounding are gross sale value and the 0.1% sale fee calculated?

These are economic implementation details. They must not be guessed from screenshots, unrelated Torn fees, or a profitable-looking backtest.

## Current documented mechanics

### `MECHANIC` — known

Current official Torn Stock Market documentation states:

- stock prices move every minute;
- shares are bought and sold instantaneously;
- buying shares has no tax;
- selling shares charges **0.1% of the total value sold**;
- personal statistics include stock profits, losses and fees paid;
- the official Stock Market wiki states that profits/losses-received statistics are not inclusive of fees paid.

Sources:

- Official Stock Market wiki: `https://wiki.torn.com/wiki/Stock_Market`
- Official API documentation / Swagger: `https://www.torn.com/swagger.php`
- Official OpenAPI contract: `https://www.torn.com/swagger/openapi.json`

OpenAPI contract reviewed: **6.6.1 on 2026-09-03**.

The reviewed API contract establishes that:

- `GET /user/log` is a standalone stable v2 selection requiring a **Full** access key;
- it accepts one or more log IDs through the `log` query parameter and up to 100 returned rows per request;
- current `UserLogsResponse.log` is an array;
- each current `UserLog` identifies its log type at `details.id` and exposes dynamic `data` and `params` objects;
- public `GET /torn/logcategories` and `GET /torn/{logCategoryId}/logtypes` expose category and log-type catalogs as arrays of `{id,title}` objects.

These API-shape statements are `MECHANIC`/schema-contract facts, not evidence about the contents of a specific stock-sale log.

### `HYPOTHESIS` / unresolved

The official documentation reviewed so far does **not** specify:

- whether execution uses the page-displayed quote at click time, the server's current price when the request is processed, or another atomic price snapshot;
- the integer rounding convention for gross stock-sale value;
- the integer rounding convention for the 0.1% stock-sale fee;
- whether any rounding occurs before or after fee calculation in a way that matters for small trades.

General Torn transaction-fee rounding behavior in other markets is not valid evidence for stock fees.

## Why current API capabilities improve the experiment

Two read-only evidence paths exist.

### Preferred path — stock sale log

If current `user -> log` stock-sale records expose generic fields corresponding to shares, execution price, gross/after-fee total or fee, the log can serve as the authoritative post-trade receipt. The API call itself performs no game action.

Before reading or retaining any value-bearing user data, TornTrading runs `probe_stock_log_schema.py`. The probe is intentionally narrower than a generic schema dumper. It persists only:

- public stock-related log-type IDs/titles obtained from Torn's public log catalogs;
- matches against a **preregistered allowlist of generic candidate field names** needed for the execution-economics question;
- primitive JSON type classes for those allowlisted candidate fields;
- a UTC retrieval timestamp and whether Full user-log access was available.

It deliberately discards:

- log event IDs;
- event timestamps and rendered titles;
- every private field value;
- every non-preregistered private field name;
- exact historical occurrence counts;
- prices, fees, shares, holdings, profits, losses, account totals and transaction amounts.

This is the minimum public evidence surface needed to decide whether a later value-bearing manual experiment can use stock logs directly.

### Fallback path — personal-stat deltas

If sale logs do not expose all required receipt values, a tightly bracketed manual sale can be measured with deltas in:

- `stockfees`;
- `stockprofits`;
- `stocklosses`;
- the known purchase transaction price/shares from `user -> stocks`.

No other stock transaction may occur between the before/after snapshots. Because Torn documents profits/losses separately from fees, those deltas can potentially reconstruct the sale economics, subject to validation against at least one visible in-game receipt. This identity is a hypothesis until experimentally checked.

## Stage A — privacy-safe candidate-field probe

Instrument: `research/tools/probe_stock_log_schema.py`

Acceptance requirements:

1. Discover stock-related log categories from official `torn -> logcategories`.
2. Enumerate their log types from official category-specific `torn -> logtypes` selections.
3. Parse the **current v2 array response shapes** documented in OpenAPI 6.6.1.
4. Query each public stock log type separately through official `user -> log`, using up to 100 rows for that type so a busy log type cannot crowd out another type's schema observation.
5. Pace requests conservatively. The current implementation uses a 0.7-second inter-request delay as an operational choice; this is **not** represented as a Torn-documented per-filter limit.
6. Persist no private user-log values.
7. Persist no unknown private field names or exact per-type historical occurrence counts.
8. Persist only preregistered generic candidate field names and primitive type classes.
9. If user-log access is unavailable or the probe fails mid-run, discard partial private-log observations, record only the failed/unavailable state, upload the safe report, and fail the evidence job.
10. Review the resulting candidate-field evidence before designing any value-bearing manual experiment.

Stage A cannot resolve P0-E4/P0-E5 by itself.

## Stage B — manual micro-trade experiment

Only a human may execute the Torn transaction. TornTrading may collect read-only API observations around it and calculate the result afterward.

### Trial isolation

For every trial:

- use one explicitly identified stock purchase/transaction;
- perform no other stock buy, sale, merge or split between the bracket observations;
- record the intended number of shares and the page-displayed sale quote before clicking;
- record the human click time as accurately as practical;
- preserve the resulting Torn stock-sale receipt/log through the read-only API where available;
- use small positions sufficient to distinguish integer rounding while keeping experimental cost low.

### Fee-rounding trials

Choose several gross-value candidates whose exact 0.1% fee has different fractional-dollar parts. The candidate rounding models are frozen before inspecting results:

- exact integer already implied by a prior gross-value rounding step;
- floor;
- ceiling;
- nearest integer, half-up;
- nearest integer, ties-to-even.

A model is not accepted because it matches one trade. Require multiple independent gross values that discriminate among the candidate rules. At least six discriminating trials are preferred; more are required if two rules remain observationally equivalent.

### Execution-price trials

Use two groups:

1. **Control trials** comfortably inside a price minute, where page quote and server minute should be identical.
2. **Boundary trials** deliberately submitted close to a minute transition, with the page visibly loaded/active and the human recording the displayed quote and click timing.

For each trial compare the authoritative receipt-derived execution price against:

- the quote visibly presented to the human;
- the Torn stock price immediately before the minute boundary;
- the Torn stock price immediately after the boundary;
- the receipt/log timestamp and any available server timestamp.

A boundary rule requires repeated observations. One ambiguous boundary trade is insufficient.

## Analysis formulas

Let:

- `n` = shares sold;
- `C` = matched purchase cost basis under Torn's sale-removal rule;
- `P+` = increase in `stockprofits`;
- `P-` = increase in `stocklosses`;
- `F` = increase in `stockfees`;
- `G` = gross sale value before fee;
- `N` = net proceeds after fee.

Candidate fallback identity to test experimentally:

`G = C + P+ - P-`

If that identity is validated for isolated sales, then:

`execution_price = G / n`

The independently observed fee delta gives:

`observed_fee_rate = F / G`

and, where the receipt/net value is available:

`N = G - F`.

The experiment must verify Torn's current personal-stat semantics against visible/read-only receipt evidence before this fallback identity is adopted.

## Evidence classification

The following progression is required:

1. Documentation/OpenAPI → `MECHANIC` only for explicitly documented behavior and schema shapes.
2. Candidate-field probe → `OBSERVATION` only about which preregistered generic fields appear to be available in current read-only stock logs.
3. Manual micro-trades → `OBSERVATION` about current execution/rounding behavior.
4. Repeated discriminating trials with internally consistent results → candidate `VALIDATED_FINDING` for the tested Torn implementation period.
5. Any later Torn stock-market implementation change reopens P0-E4/P0-E5.

## Gate effect on HYP-001

HYP-001 can continue accumulating prospective predictive evidence while this experiment is pending.

HYP-001 may **not** be promoted to executable alpha, and no after-cost backtest may be considered final, until:

- sale execution-price semantics are sufficiently characterized;
- stock-sale fee/gross rounding is sufficiently characterized;
- the resulting execution model is incorporated into chronological validation;
- realistic human execution delay is included.

## Compliance boundary

Permitted:

- official read-only API calls;
- calculations and evidence capture;
- instructions to the human operator;
- human clicking the Torn buy/sell controls.

Not permitted:

- automated Torn buy/sell submission;
- automatic game-page requests outside Torn API rules;
- hidden interaction with Torn controls;
- treating an API observation tool as authorization to execute a transaction.
