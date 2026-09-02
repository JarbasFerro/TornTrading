# TornTrading — Historical Data Audit

Status: **P0 research pass 1**  
Research date: 2026-09-02  
Questions covered: DAT-001 through DAT-010

Primary/official sources:

- Torn API v2 OpenAPI: https://www.torn.com/swagger/openapi.json
- Torn Stock Market Wiki: https://wiki.torn.com/wiki/Stock_Market

Third-party source under evaluation:

- Tornsy API documentation: https://tornsy.com/api
- Tornsy source repository: https://github.com/bbenejc/tornsy

Secondary reproducibility lead (not canonical evidence):

- Torn Stock Analyzer source, inspected 2026-09-02: https://greasyfork.org/en/scripts/570460-torn-stock-analyzer/code

## Executive conclusion

We have a promising historical-data path, but it is **not yet validated strongly enough to run alpha research**.

What is established:

1. Torn API v2 has a stable specific-stock endpoint containing timestamped chart history, but its schema does not specify depth/resolution.
2. Tornsy documents a public historical archive collected from Torn once per minute, with minute and OHLC resolutions and explicit `from`, `to`, and `limit` parameters.
3. Tornsy explicitly warns that live collection can have missing minutes during connectivity/Torn API outages.
4. A recent independent open-source Torn stock analyzer reports receiving 1,956 daily rows (~5.36 years) from Tornsy with `limit=2000` as of 2026-08-25. This is useful corroboration but is not sufficient on its own to certify the archive.

Therefore the next data step is a reproducible source-reconciliation job, not model development.

## DAT-001 [P0] — Years of usable official Torn stock history

**Resolution: OPEN — authenticated measurement required**

Official v2 `GET /torn/{stockId}/stocks` exposes `chart.history[]` with `price`, `change`, and `timestamp`. OpenAPI does not state oldest point, interval, number of rows, or retention.

### Required measurement

With a Public key:

- fetch every stock detail;
- record row count;
- oldest/newest timestamp;
- timestamp-delta distribution;
- exact total span;
- repeat after 24h and 7d.

Until then, no claim about official-history depth is accepted.

## DAT-002 [P0] — Tornsy/other archive depth and resolution

**Resolution: PARTIAL — interface verified, depth requires direct audit**  
**Evidence class: third-party documentation + reproducibility lead**

Tornsy states it collects Torn stock data once per minute and exposes:

- raw/default `m1` history;
- `m5`, `m15`, `m30`;
- `h1`, `h2`, `h4`, `h6`, `h12`;
- `d1`, `w1`, `n1`, `y1`, `all`;
- `from` inclusive timestamp filter;
- `to` exclusive timestamp filter;
- per-request `limit` from 1 to 2000.

For `m1`, rows are documented as timestamp, price, total shares (and TCSE market cap where applicable). For aggregated intervals rows are timestamp, OHLC, total shares (plus TCSE market cap).

A currently published open-source analyzer comments that on 2026-08-25 `interval=d1&limit=2000` returned 1,956 rows / ~5.36 years for its tested symbol. This aligns approximately with Stocks 3.0's April 2021 age, but must be reproduced by TornTrading.

## DAT-003 [P0] — Official API versus Tornsy overlap

**Resolution: OPEN — critical reconciliation experiment**

This is the highest-priority data-quality test.

### Required comparison

For at least 5 representative stocks plus TCSE, and preferably all stocks:

1. collect official current snapshot once/minute;
2. collect Tornsy corresponding minute later (Tornsy states fresh data normally appears 5–10 seconds after the minute);
3. join on candidate timestamp conventions;
4. compare prices exactly and with tolerance for formatting/rounding;
5. measure share/investor agreement where fields overlap;
6. compare official chart-history points with Tornsy historical points.

Report:

- exact-match rate;
- absolute/relative discrepancy distribution;
- systematic timestamp offset;
- whether discrepancies cluster around price-change boundaries/outages.

Tornsy cannot become canonical until this passes.

## DAT-004 [P0] — Missing minute percentage

**Resolution: OPEN — archive scan required**

Tornsy explicitly states data may be missing when it or Torn API has connection trouble. Missingness must be measured stock-by-stock/year-by-year.

### Metrics

For each stock and UTC calendar month:

- expected minutes in covered range;
- observed unique timestamps;
- missing timestamps;
- duplicate timestamps;
- longest contiguous gap;
- count of gaps >1m, >5m, >30m, >6h;
- missing-rate percentage.

Because Torn prices may remain unchanged for consecutive minutes, a repeated price must **not** be classified as missing.

## DAT-005 [P0] — Is missingness random?

**Resolution: OPEN**

After DAT-004, cluster gaps across all stocks.

Interpretation:

- same timestamp missing for most/all stocks → provider/Torn-wide outage likely;
- isolated stock gaps → symbol/provider/data issue;
- gaps around maintenance/known system changes → structural event;
- price-dependent missingness would be dangerous and requires special treatment.

Alpha research must not forward-fill through long gaps and then pretend those rows were observed.

## DAT-006 [P0] — Unchanged price versus missing/forward-filled observation

**Resolution: CLOSED AS DATA POLICY; source-specific validation still required**

Tornsy documents raw minute observations as explicit rows, meaning identical consecutive prices can legitimately be distinct observed minutes.

### Canonical rule

A row exists only if the source supplied an observation for that timestamp. `price[t] == price[t-1]` is a valid zero return, not evidence of missing data.

Never manufacture a minute row merely because the previous price is known.

If a downstream model requires a regular grid, create a derived grid with explicit flags:

```text
observed = true/false
imputed = true/false
imputation_method = null/...
source_gap_seconds
```

Raw canonical data remains sparse/observed-only.

## DAT-007 [P0] — Timestamp conventions

**Resolution: PARTIAL**

Established:

- Torn API history uses Unix-second integer timestamps.
- Tornsy uses Unix-second timestamps.
- Tornsy states absolute interval parameters are rounded down to the closest minute.
- Aggregated OHLC example timestamps are aligned to interval boundaries.

Not established:

- whether Torn API history timestamp is price effective/start/end time;
- whether Tornsy minute timestamp denotes retrieval minute or Torn effective minute;
- whether Tornsy aggregated timestamp is formally candle-open time (examples strongly imply this but audit it).

### Canonical timestamp model

Store distinct fields rather than one overloaded `timestamp`:

```text
source_timestamp
source_timestamp_semantics   # unknown/effective/window_start/window_end/retrieval
retrieved_at_utc
request_started_at_utc
response_received_at_utc
market_effective_at_utc      # nullable until proven
```

All external-market alignment must use `market_effective_at_utc`, never a guessed source label.

## DAT-008 [P0] — Retroactive revisions

**Resolution: OPEN — snapshot/hash experiment required**

Neither official stock schema nor Tornsy docs provide a revision/version guarantee.

### Test

Fetch overlapping historical windows on multiple dates. Hash rows keyed by source + stock + timestamp and flag changed values. Preserve both first-seen and latest-seen versions if revisions occur.

A revision is analytically important because using today's corrected history in a past backtest can create hidden look-ahead.

## DAT-009 [P0] — Canonical minute-level reconstruction

**Resolution: DESIGN APPROVED; data-source precedence pending DAT-003/008**

Approved raw event schema:

```text
record_id
source
source_schema_version
stock_id
acronym
source_timestamp
source_timestamp_semantics
retrieved_at_utc
price
shares?
market_cap?
investors?
raw_payload_hash
quality_flags[]
first_seen_at
last_verified_at
```

### Source precedence (provisional)

1. Our directly captured official Torn API observation.
2. Official Torn chart history, once timestamp semantics are validated.
3. Tornsy, once overlap quality passes DAT-003.
4. Other archives only after independent audit.

Do not silently overwrite conflicting observations. Store conflict flags and provenance.

## DAT-010 [P0] — Structural breaks since Stocks 3.0

**Resolution: PARTIAL — known events identified; statistical detection still required**

Known official events include:

- 2021-04-06: Stocks 3.0 released.
- 2021-04-20: 0.1% sale fee introduced after temporary free period.
- 2021-06-22: sales changed to remove shares from newest transaction rather than oldest.
- 2021-06-29: ASS stock released.
- 2021-07-06: MUN stock released.
- 2022-10-04: Mc Smoogle dividend increment cap change.

The price-generation algorithm may have changed without a clearly documented public patch. Statistical research must therefore independently run change-point/regime diagnostics instead of assuming 2021–2026 is stationary.

### Dataset requirement

Maintain a `market_events` table containing documented mechanics/stock additions/benefit changes. Models should be able to exclude or stratify periods around known structural changes.

## Canonical data quality flags

Initial controlled vocabulary:

- `SOURCE_OFFICIAL_LIVE`
- `SOURCE_OFFICIAL_HISTORY`
- `SOURCE_TORNSY`
- `TIMESTAMP_SEMANTICS_UNVERIFIED`
- `SOURCE_CONFLICT`
- `DUPLICATE_TIMESTAMP`
- `MISSING_PREVIOUS_MINUTE`
- `GAP_GT_5M`
- `GAP_GT_30M`
- `REVISED_AFTER_FIRST_SEEN`
- `OUTLIER_UNVERIFIED`
- `SCHEMA_CHANGED`

Quality flags describe evidence; they do not automatically delete rows.

## Required P0 data audit program

### DAT-X1 — Official history inventory

Run against all stocks and output one row per stock containing:

```text
stock
history_rows
oldest_ts
newest_ts
span_days
median_delta_s
min_delta_s
max_delta_s
pct_60s_delta
```

### DAT-X2 — Tornsy full inventory

For every stock and supported research interval (`m1`, `h1`, `d1` initially):

- discover earliest available timestamp by paginated/backward retrieval;
- count rows;
- calculate gaps/duplicates;
- preserve raw response hashes.

### DAT-X3 — Source reconciliation

Run live overlap for at least 7 days, preferably longer, comparing official minute snapshots to Tornsy.

### DAT-X4 — Revision audit

Refetch overlapping windows daily for 7 days and compare hashes/values.

### DAT-X5 — Structural-event registry

Seed known official patch dates and update whenever a relevant Torn announcement/patch occurs.

## Gate to Stage 2/external-market reverse engineering

Do **not** begin mass correlation/lead-lag search until all conditions below are met:

1. Timestamp semantics are known well enough to prevent directionally wrong joins.
2. At least one historical source has quantified missingness.
3. Tornsy/official overlap discrepancy is measured.
4. Canonical source-precedence/conflict rules are operational.
5. Structural breaks are represented as metadata.
6. Historical rows are reproducibly retrievable and hashed/versioned.

## Decision

**NOT YET APPROVED FOR ALPHA RESEARCH.** The available historical sources are promising and likely sufficient, but source reconciliation and timestamp validation are still blocking. **APPROVED to implement the research collector/audit tooling needed to close DAT-X1 through DAT-X4.**
