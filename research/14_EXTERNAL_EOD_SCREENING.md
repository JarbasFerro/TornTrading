# TornTrading — External EOD Candidate Screening Instrument

Status: **Stage 0 implementation / awaiting live provider evidence**  
Research date: 2026-09-02  
Questions prepared: EXT-004, EXT-009, EXT-010; screening support for EXT-001/002/003

## Purpose

`research/tools/run_external_eod_screen.py` is the first empirical external-driver screening instrument.

It is deliberately **not** a trading model. Its job is to reduce the frozen v1.0 candidate universe from `external_driver_candidates.json` using long-horizon daily evidence before we spend money or multiple-testing budget on intraday data.

## Provider/data boundary

The first adapter uses Tiingo EOD data under the policy in `13_EXTERNAL_DATA_PROVIDER_POLICY.md`.

External price rows:

- exist only in process memory;
- are never written to disk;
- are never printed;
- are never uploaded as GitHub Actions artifacts;
- are reduced to aggregate statistics before process exit.

Generated files are ignored by Git and the GitHub workflow has an explicit four-file artifact allowlist.

## Rate-limit design

The frozen candidate universe contains more external symbols than one conservative Starter-tier run should request.

The screen therefore uses deterministic batches:

- up to **35 non-control external symbols** per batch;
- SPY, ACWI, QQQ and IWM are included in every batch;
- therefore at most **39 Tiingo EOD price requests per batch**;
- `batch_index` is zero-based and the tool reports the total batch count.

The initial screen does not make a separate metadata request for every symbol because that would double the request budget. First/last usable return dates are inferred from the historical response. Symbols with identity/listing-history ambiguity remain research-review items and may receive targeted metadata checks later.

## Torn series construction

Torn daily history comes from the already audited Tornsy `d1` endpoint.

Rules:

1. fetch up to 2,000 daily bars for every current tradable Torn stock;
2. treat each Tornsy `d1` timestamp as the UTC candle-start label;
3. exclude the current UTC-day candle because the Tornsy audit established that aggregated endpoints can expose a still-forming candle;
4. calculate close-to-close Torn returns only after that exclusion;
5. never include TCSE as a tradable stock in this screen.

## External return variants

Each Tiingo EOD response supplies both raw and adjusted close fields, allowing both sensitivity cases from one request.

### Primary: adjusted

`adjClose[t] / adjClose[t-1] - 1`

Adjusted returns are primary for company/industry relationship screening because splits and dividends should not create artificial economic price jumps.

### Sensitivity: raw

`close[t] / close[t-1] - 1`

Raw returns are retained as a preregistered sensitivity because Torn's upstream external feed could conceivably use unadjusted market prices. A material raw/adjusted disagreement prevents confident mapping until explained.

## Daily alignment hypotheses

The daily screen tests three civil-date relationships:

- external date = Torn date − 1;
- external date = Torn date;
- external date = Torn date + 1.

Persisted field: `external_date_offset_days` ∈ `{-1,0,+1}`.

These are **descriptive alignment hypotheses**, not causal lead/lag claims. Differences in exchange close time, UTC Torn day boundaries, weekends and provider publication times make a daily date offset insufficient to prove information flow.

## Statistics persisted per Torn/candidate/variant/offset

Only aggregates are retained:

- Torn symbol;
- external symbol;
- candidate role (`broad_control`, `sector_proxy`, `named_equity`);
- raw vs adjusted variant;
- tested civil-date offset;
- overlap observation count;
- overlap start/end date;
- Pearson return correlation;
- Spearman return correlation;
- univariate alpha and beta;
- univariate R²;
- SPY-only R²;
- candidate + SPY R²;
- incremental R² above SPY;
- number of eligible calendar years;
- median/min/max yearly Pearson correlation;
- number of positive/negative yearly correlations.

No per-date external return or price series is persisted.

## Why incremental R² matters

A Torn stock can correlate with an industry proxy simply because both participate in a broad equity-market move.

For every non-SPY candidate with sufficient overlap, the screen compares:

```text
Model 0: Torn return ~ SPY return
Model 1: Torn return ~ SPY return + candidate return
```

`incremental_r2_over_control = R²(Model 1) - R²(Model 0)`

A candidate that adds essentially nothing beyond SPY is weak evidence for an industry-specific mapping even if its raw correlation looks attractive.

This is still descriptive screening, not a causal model.

## Annual stability

Full-period correlation can hide regime instability. For each alignment with at least 30 observations in a calendar year, the screen also calculates yearly Pearson correlations and persists only aggregate stability measures:

- eligible year count;
- median yearly correlation;
- minimum and maximum yearly correlation;
- number of years with positive/negative correlation.

A strong full-period relationship with alternating yearly signs should normally be rejected or downgraded.

## Error policy

A provider failure for one symbol does not erase the batch. The output records only:

- external symbol;
- generic error class;
- a short diagnostic message.

Missing/delisted/unavailable candidates therefore remain visible rather than silently disappearing from the research set.

## Persistent outputs

The workflow may upload only:

- `candidate_statistics.csv`
- `external_coverage.csv`
- `errors.csv`
- `summary.json`

The workflow rejects unexpected files and scans the output for fields suggestive of reconstructable price/return series before artifact upload.

`summary.json` explicitly records `raw_external_data_persisted: false`.

## Live-run interpretation protocol

After all batches are collected, we will combine only their aggregate outputs and produce a candidate ranking.

A candidate may advance to hourly/intraday research only when all of the following are considered:

1. adequate overlap;
2. relationship materially stronger than broad controls;
3. positive incremental explanatory power over SPY;
4. reasonable Pearson/Spearman agreement;
5. stability across multiple calendar years;
6. no obvious listing/corporate-action explanation;
7. raw/adjusted sensitivity understood;
8. performance not dependent on a single arbitrary date offset.

The ranking must retain all failed candidates and permit `NO_STABLE_MAPPING`.

## What this instrument does not establish

Even a very strong daily result does not prove:

- that Torn directly consumes that ticker;
- that the external market causally leads Torn;
- the transformation Torn applies;
- that a relationship is exploitable intraday;
- that a player can execute a profitable trade after observing the external move.

Those require subsequent EXT and VAL gates.

## Credentials

GitHub Actions expects one repository secret:

`TIINGO_TOKEN`

Never paste this token into source code, issues, workflow inputs, or chat.

Workflow: **External EOD candidate screen**.

## Approval boundary

The implementation can be approved before a live provider run if normal CI passes, because all statistical/security behavior is covered with synthetic tests. EXT-004 remains OPEN until credentialed screening artifacts are reviewed.
