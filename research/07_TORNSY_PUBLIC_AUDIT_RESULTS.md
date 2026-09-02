# Tornsy public historical-data audit — P0-E3

Status: **PASS WITH QUALIFICATIONS**  
Audit date: 2026-09-02  
Research question cluster: DAT-002, DAT-004, DAT-005, DAT-007, DAT-008 (partial), P0-E3  
Workflow run: `33658127600`  
Head commit: `66383b1ce2373551768fb809308e5bf444614131`  
GitHub artifact: `9857670269`  
GitHub artifact digest: `sha256:eb114dc30c7cb0718081cae6b36ceaff7f6e9985f034927ca19773c427aee62a`

## Decision

Tornsy is **approved as a bootstrap / candidate historical source for further research**, subject to official Torn reconciliation before any series is promoted to canonical data.

This result does **not** authorize alpha research yet. P0-E2 (official Torn vs Tornsy reconciliation), P0-E1 (official chart-history inventory), and timestamp/execution semantics remain blocking gates.

## Scope

The audit dynamically discovered all 36 symbols exposed by Tornsy and queried each at:

- `m1`, limit 2,000;
- `h1`, limit 2,000;
- `d1`, limit 2,000.

Total expected requests: **108**.  
Successful requests: **108**.  
Failed requests after retries: **0**.

Every response was preserved with retrieval timestamps and SHA-256 provenance.

## Main findings

### 1. Minute history (`m1`)

All 36 symbols returned exactly **2,000 rows** with **zero duplicate timestamps**.

The window spans **1.388889 days** (2,000 minute observations plus one known missing slot).

Every symbol shows the same single 120-second timestamp jump:

- last observation before gap: **2026-09-02 00:10:00 UTC**
- next observation: **2026-09-02 00:12:00 UTC**
- missing observation: **2026-09-02 00:11:00 UTC**

Because the same gap occurs across all 36 symbols at the same timestamp, this is strongly consistent with a source-wide Torn/Tornsy collection interruption rather than stock-specific behavior.

Aggregate missing minute slots: **36** (one per symbol).

### 2. Hourly history (`h1`)

All 36 symbols returned exactly **2,000 rows**, covering **83.291667 days**.

Results:

- duplicate timestamps: **0**
- timestamp gaps larger than one hour: **0**
- inferred missing hourly slots: **0**

This is structurally clean for the audited recent window.

### 3. Daily history (`d1`)

Thirty-one symbols return **1,964 daily observations** from **2021-04-15** through **2026-09-02**, covering essentially the full post-Stocks-3.0 period represented by Tornsy.

Five symbols have shorter histories that begin on their apparent release dates:

| Symbol | First Tornsy daily timestamp | Rows | Corroboration |
|---|---:|---:|---|
| ASS | 2021-06-29 | 1,889 | Torn Wiki patch history: released 29/06/21 |
| MUN | 2021-07-06 | 1,882 | Torn Wiki patch history: released 06/07/21 |
| CBD | 2022-11-01 | 1,399 | contemporaneous Torn forum release discussion |
| LOS | 2022-11-15 | 1,385 | contemporaneous Torn forum release discussion |
| PTS | 2022-11-29 | 1,371 | contemporaneous Torn forum release discussion |

For each of these five, the row count exactly equals the number of calendar days from the observed release date through 2026-09-02 minus the same three-day source-wide gap described below. This is strong evidence that Tornsy's daily archive does not simply truncate all symbols to a common recent window.

Every daily series has the same four-day jump:

- last observation before gap: **2025-06-28 00:00:00 UTC**
- next observation: **2025-07-02 00:00:00 UTC**
- missing dates: **2025-06-29, 2025-06-30, 2025-07-01**

Aggregate inferred missing daily slots: **108** (three per symbol).

Again, synchronization across every stock indicates a source-wide collection outage/gap, not independent missingness.

### 4. No evidence of duplicate timestamps

Across the audited matrix:

- `m1`: 0 duplicates
- `h1`: 0 duplicates
- `d1`: 0 duplicates

This is important because duplicate timestamps would complicate canonicalization and return calculations.

### 5. Current aggregate candles are not necessarily closed bars

The audit crossed the 17:00 UTC hour boundary.

Before the boundary, `h1` responses had newest timestamp `16:00`. Beginning roughly 14 seconds after 17:00, later requests returned a new `17:00` hourly row.

This shows that Tornsy's aggregated endpoints can expose a candle identified by the **start of the currently forming interval**, rather than only fully closed candles.

The `d1` responses likewise contain a row timestamped `2026-09-02 00:00:00 UTC` while the day is still in progress.

**Backtesting rule:** a current/open aggregate candle must never be treated as a fully known historical bar. For model training/backtesting, either:

1. exclude the last aggregate candle unless its interval has definitely closed; or
2. model it explicitly as an in-progress observation with an `observable_at` timestamp.

Failing to do this would introduce look-ahead leakage.

### 6. Minute freshness is consistent with Tornsy documentation

The sequential audit observed newest `m1` points appearing shortly after minute boundaries. Because requests were deliberately spread over several minutes, retrieval-to-bar-start lag ranged roughly 13–79 seconds.

This is consistent with Tornsy's published statement that it collects once per minute and normally exposes fresh data about 5–10 seconds after each minute, but this audit was not designed to measure exact publication latency. P0-E2 must measure that against official Torn timestamps.

## Interpretation

The bounded audit supports the following observations:

- Tornsy provides usable historical coverage at multiple resolutions.
- Its `d1` archive reaches the Stocks 3.0 era for stocks that existed then.
- Later stock histories begin on dates matching observed/documented releases.
- Missingness in the audited data is sparse and highly synchronized across stocks.
- The source has known gaps that must remain explicit; they must never be silently forward-filled.
- Aggregate interval rows require open/closed-candle handling to prevent leakage.

The audit does **not** establish:

- that Tornsy prices equal official Torn prices;
- whether its timestamps are exactly Torn publication/calculation timestamps;
- whether old records have ever been revised;
- whether every historical minute can be reconstructed through pagination;
- whether the source is suitable as canonical truth;
- whether any price pattern is predictive.

## P0-E3 gate

**Decision: PASS WITH QUALIFICATIONS.**

Approved:

- Tornsy as a candidate bootstrap source.
- Using Tornsy data to design/validate ingestion, canonicalization, missingness handling, and external-market alignment tooling.
- Proceeding with deeper fixed-window archive/revision checks.

Not approved:

- promoting Tornsy to canonical history;
- starting final alpha/backtest research solely from Tornsy;
- assuming aggregate candles are completed at their timestamp;
- interpolating or forward-filling source-wide gaps without an explicit research treatment.

## Remaining blockers before alpha research

1. **P0-E1** — inventory official Torn detailed-stock chart history.
2. **P0-E2** — reconcile official Torn and Tornsy prices/timestamps across repeated minute boundaries.
3. **P0-E3b** — repeat fixed, closed historical windows over time to detect retroactive revision.
4. **P0-E4** — controlled manual transaction semantics: fee rounding, price update/confirmation behavior, lot/merge handling.
5. **P0-E5** — compare actively viewed Torn stock graph data with official API chart history.

## Source register

Primary public source:

- Tornsy API documentation: https://tornsy.com/api
  - states once-per-minute collection;
  - notes occasional missing minutes due to connection/Torn API outages;
  - documents `m1`, `h1`, `d1` and other OHLC intervals;
  - documents `from` inclusive, `to` exclusive, max 2,000 rows.

Torn mechanics / historical corroboration:

- Torn Wiki Stock Market: https://wiki.torn.com/wiki/Stock_Market
  - Stocks 3.0 released 06/04/21;
  - ASS released 29/06/21;
  - MUN released 06/07/21.
- CBD contemporaneous release thread: https://www.torn.com/forums.php?a=0rh%3D76&b=0&f=2&p=threads&start=140&t=16298327
- LOS contemporaneous release thread: https://www.torn.com/forums.php?a=0rh%3D94&b=0&f=2&p=threads&t=16305616
- PTS contemporaneous release thread: https://www.torn.com/forums.php?a=0rh%3D43&b=0&f=2&p=threads&t=16307611

## Evidence retention

The first reviewed GitHub Actions ZIP artifact was generated with a 7-day retention period. The workflow is updated in this PR to retain subsequent raw audit artifacts for **90 days**.

The compact per-request audit matrix is committed under `research/evidence/` so row counts, timestamp spans, gap metrics, retrieval times, and source payload hashes remain part of the permanent research record.

GitHub Actions artifacts are still considered transport/review evidence rather than the eventual long-term store for continuous raw market collection. A durable raw-data store is required before TornTrading begins continuous collection.
