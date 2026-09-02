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

The descriptive pass covers:

| Research horizon | Tornsy source | Return construction |
|---|---|---|
| 1m | `m1` | exact 60-second price span |
| 5m | `m5` | exact 300-second price span |
| 1h | `h1` | exact 3,600-second price span |
| 6h | `h6` | exact 21,600-second price span |
| 24h | `d1` | exact 86,400-second price span |
| 7d | `d1` | exact seven-calendar-day price span |
| 30d | `d1` | exact thirty-calendar-day price span |

The currently forming source period is excluded before returns are computed.

Source gaps are never bridged. A return is emitted only when the start and end timestamps are separated by exactly the stated horizon.

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

Distribution statistics may use rolling 7d/30d windows because overlap does not invalidate the descriptive distribution itself. Dependence tests are handled differently, as described below.

Chronological quartiles report mean, volatility, exact-horizon lag-1 return autocorrelation, exact-horizon lag-1 absolute-return autocorrelation and positive-return rate. These are stability diagnostics, not formal structural-break tests.

### Autocorrelation — STA-003

For each stock/horizon, raw and absolute-return autocorrelation are calculated at lags 1, 2, 3, 5 and 10 **complete horizons**.

This distinction is critical for 7d and 30d returns. Adjacent rolling 30d windows share 29 underlying days; correlating those adjacent windows creates mechanically high autocorrelation even when there is no genuine 30d momentum. Therefore the instrument compares a 30d return ending at `t` only with returns ending at `t - 30d`, `t - 60d`, etc. The same rule applies to 7d returns and to all shorter horizons.

Serial pairs also require exact timestamps, so source gaps never become false adjacency.

Raw-return autocorrelation is a descriptive seed for momentum/mean-reversion hypotheses. Absolute-return autocorrelation measures volatility clustering.

### Continuation / reversal diagnostics — STA-004 / STA-005

For each stock/horizon, the instrument reports:

- sign continuation rate;
- mean next return following a positive return;
- mean next return following a negative return;
- mean next return following a bottom-decile return;
- mean next return following a top-decile return.

"Next" means the next **non-overlapping complete horizon**, not the next rolling observation. For example, a 30d continuation test compares the return over `[t-30d,t]` with the return over `[t,t+30d]`, where both exact windows exist.

These statistics are deliberately parameter-light. They do not choose entry thresholds, holding periods, or optimize profitability.

A large negative exact-horizon autocorrelation or positive return after bottom-decile moves can seed a later mean-reversion hypothesis. Positive autocorrelation / sign continuation can seed momentum research. Neither is validated alpha at this stage.

### Cross-stock structure — STA-006

Pairwise Pearson correlations are calculated across all 595 stock pairs at:

- 1h;
- 24h.

Only common exact-horizon timestamps are used. The result is a descriptive correlation graph suitable for later factor/clustering work.

## Source limitations

The current Tornsy endpoint limit is 2,000 observations. Consequently, effective history varies by horizon:

- minute-scale statistics cover a relatively short recent window;
- hourly statistics cover materially more history;
- daily/7d/30d distributions cover much of the Stocks 3.0 era;
- exact-horizon 7d/30d serial-dependence tests have fewer independent pairs than their rolling distribution series.

This difference is a central limitation. A strong 1m effect observed over ~2,000 minutes cannot be compared epistemically with a daily effect observed over years.

The output therefore retains observation counts and serial-pair counts.

## Data integrity controls

- uses the already-audited Tornsy source;
- excludes forming periods;
- requires exact timestamp spans for every labeled return;
- does not forward-fill missing data;
- does not convert source gaps into zero returns;
- does not bridge source gaps in serial-dependence tests;
- rejects mechanically overlapping 7d/30d lag-1 dependence;
- retries transient fetch failures and records persistent failures;
- persists aggregates only, not raw history;
- fails the workflow if any required source request remains failed;
- reruns weekly to detect changing market anatomy.

## Interpretation rules

This pass may produce `OBSERVATION` findings such as:

> "Stock X shows negative exact-horizon hourly autocorrelation over the observed window."

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
