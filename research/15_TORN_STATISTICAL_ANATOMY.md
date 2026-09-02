# TornTrading — Torn-only Statistical Anatomy

Status: **Stage 0 / descriptive research instrument**  
Research date: 2026-09-02  
Questions advanced: STA-001 through STA-006

## Purpose

This stage describes the internal statistical structure of Torn's stock market before any trading strategy is optimized.

It is intentionally separate from external-driver mapping. If the Tiingo sector screen is delayed, Torn-only statistical research can continue independently using the already-audited Tornsy historical source.

No result from this instrument is a trading signal or an executable-profit claim.

## Canonical universe

The analysis uses exactly the 35 current tradable Torn stocks from `external_driver_candidates.json` and excludes TCSE from the tradable cross-section.

TCSE may later be evaluated separately as a market factor/benchmark under STA-013.

## Horizons

The first descriptive pass covers:

| Research horizon | Tornsy source | Construction |
|---|---|---|
| 1m | `m1` | one observation lag |
| 5m | `m5` | one observation lag |
| 1h | `h1` | one observation lag |
| 6h | `h6` | one observation lag |
| 24h | `d1` | one observation lag |
| 7d | `d1` | seven daily observations |
| 30d | `d1` | thirty daily observations |

The currently forming source period is excluded before returns are computed.

Because Torn trades continuously, 7d and 30d are constructed from Torn daily candles rather than from equity-market business-day conventions.

## Metrics

### Distribution anatomy — STA-001 / STA-002

For every stock and horizon:

- observation count;
- mean and median return;
- standard deviation;
- skewness;
- excess kurtosis;
- minimum / maximum;
- 1%, 5%, 25%, 75%, 95%, 99% percentiles;
- positive / negative / zero return rates.

Chronological quartiles additionally report mean, volatility, lag-1 return autocorrelation, lag-1 absolute-return autocorrelation and positive-return rate. These are stability diagnostics, not formal structural-break tests.

### Autocorrelation — STA-003

For each stock/horizon, both raw and absolute-return autocorrelation are calculated at lags 1, 2, 3, 5 and 10.

Raw-return autocorrelation is a descriptive seed for momentum/mean-reversion hypotheses. Absolute-return autocorrelation measures volatility clustering.

### Continuation / reversal diagnostics — STA-004 / STA-005

For each stock/horizon, the instrument reports:

- sign continuation rate;
- mean next return following a positive return;
- mean next return following a negative return;
- mean next return following a bottom-decile return;
- mean next return following a top-decile return.

These statistics are deliberately parameter-light. They do not choose entry thresholds, holding periods, or optimize profitability.

A large negative lag-1 autocorrelation or positive return after bottom-decile moves can seed a later mean-reversion hypothesis. Positive autocorrelation / sign continuation can seed momentum research. Neither is validated alpha at this stage.

### Cross-stock structure — STA-006

Pairwise Pearson correlations are calculated across all 595 stock pairs at:

- 1h;
- 24h.

Only common timestamps are used. The result is a descriptive correlation graph suitable for later factor/clustering work.

## Source limitations

The current Tornsy endpoint limit is 2,000 observations. Consequently, effective history varies by horizon:

- minute-scale statistics cover a relatively short recent window;
- hourly statistics cover materially more history;
- daily/7d/30d statistics cover much of the Stocks 3.0 era.

This difference is a central limitation. A strong 1m effect observed over ~2,000 minutes cannot be compared epistemically with a daily effect observed over years.

The output therefore retains observation counts and source interval for every metric.

## Data integrity controls

- uses the already-audited Tornsy source;
- excludes forming periods;
- does not forward-fill missing data;
- does not convert source gaps into zero returns;
- retries transient fetch failures and records persistent failures;
- persists aggregates only, not raw history;
- fails the workflow if any required source request remains failed;
- reruns weekly to detect changing market anatomy.

## Interpretation rules

This pass may produce `OBSERVATION` findings such as:

> "Stock X shows negative lag-1 hourly autocorrelation over the observed window."

It may not produce claims such as:

> "Buy Stock X after a fall because this strategy is profitable."

Before any descriptive pattern becomes a strategy hypothesis, it must receive a preregistered hypothesis ID, chronological validation design, cost/execution model and multiple-testing control.

## Outputs

The workflow produces only aggregate files:

- `horizon_statistics.csv`
- `autocorrelation.csv`
- `continuation_reversal.csv`
- `stability_quartiles.csv`
- `pairwise_correlations.csv`
- `fetch_audit.csv`
- `errors.csv`
- `summary.json`

## Gate decision

Approval of this document/tool authorizes descriptive Torn-market anatomy and hypothesis generation for STA-001 through STA-006.

It does **not** authorize:

- parameter optimization;
- strategy backtesting as executable profit;
- BUY/SELL recommendations;
- portfolio optimization;
- promotion of any observed autocorrelation to `VALIDATED_FINDING` without chronological out-of-sample testing.
