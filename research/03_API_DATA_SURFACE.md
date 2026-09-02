# TornTrading — Torn API & Observable Data Surface

Status: **P0 research pass 1**  
Research date: 2026-09-02  
OpenAPI observed version: **6.13.1**  
Questions covered: API-001 through API-011

Primary sources:

- Torn API v2 OpenAPI: https://www.torn.com/swagger/openapi.json
- Torn API documentation / ToS: https://www.torn.com/api.html
- Torn API Wiki: https://wiki.torn.com/wiki/API

## Executive conclusion

The official API is sufficient for the core market and portfolio data model without DOM scraping.

Stable v2 endpoints currently include:

- `GET /torn/stocks` — Public key — all stocks/current market metadata.
- `GET /torn/{stockId}/stocks` — Public key — a specific stock plus chart performance/history.
- `GET /torn/timestamp` — Public key — current Torn server time.
- `GET /user/stocks` — Limited key — current holdings, acquisition transactions and benefit progress.
- `GET /user/personalstats` — stable, with investment statistics including stock profits/losses/fees/net profits/payouts when available to the key owner.
- `GET /user/log` — Full key — detailed timestamped logs; should be optional because of its privilege level.

This means TornTrading does **not** need a Full key for its core trading/portfolio model. Public + Limited/custom access should be the default design.

The biggest unresolved API issue is not field availability but **historical behavior**: the OpenAPI schema does not specify chart-history depth, sampling resolution or timestamp-window semantics. Those require authenticated empirical sampling.

## API-001 [P0] — `GET /torn/stocks` fields, types, precision, cache, stability

**Resolution: CLOSED for schema; runtime precision/freshness still measured under API-009**  
**Evidence class: MECHANIC**

Endpoint: `GET /torn/stocks`  
Access: Public  
Stability: Stable

Each `TornStock` contains:

- `id`
- `name`
- `acronym`
- `images.logo`
- `images.full`
- `market.price` — number/float
- `market.cap` — int64
- `market.shares` — int64
- `market.investors` — int64
- `bonus.passive` — boolean
- `bonus.frequency` — int32
- `bonus.requirement` — int64
- `bonus.description` — string

### Collector consequence

Persist all market fields even if the first predictive model uses only price. Shares/investors/cap are potential later predictors and historical reconstruction may be difficult.

Persist the raw API response alongside normalized values because OpenAPI types do not define decimal display precision or future field additions.

## API-002 [P0] — Exact history returned by `GET /torn/{stockId}/stocks`

**Resolution: PARTIAL — schema closed, depth/resolution open**  
**Evidence class: MECHANIC + OPEN OBSERVATION**

Endpoint: `GET /torn/{stockId}/stocks`  
Access: Public  
Stability: Stable

It returns the normal `TornStock` fields plus `chart`:

### `chart.performance`

For each of:

- `last_hour`
- `last_day`
- `last_week`
- `last_month`
- `last_year`
- `all_time`

fields are:

- `change`
- `change_percentage`
- `start`
- `end`
- `high`
- `low`

### `chart.history[]`

Each history point contains:

- `price`
- `change`
- `timestamp`

### Unknown from specification

The schema does **not** document:

- number of rows;
- oldest timestamp;
- sampling interval;
- whether interval changes with age;
- whether unchanged minutes are omitted;
- exact timestamp semantics;
- aggregation method, if any.

These must be measured using a Public key before official history is treated as a research dataset.

## API-003 [P0] — Does official history change resolution with age?

**Resolution: OPEN — authenticated observation required**

OpenAPI defines one history array and no resolution metadata. No conclusion is permitted from schema alone.

### Test

For every stock, retrieve history once and calculate adjacent timestamp deltas. Report frequency distribution of 60s/300s/hourly/daily/irregular gaps and whether resolution changes as points get older.

Repeat on multiple days to determine if the window rolls or is recomputed.

## API-004 [P0] — API chart history versus manually loaded stock graph

**Resolution: OPEN — browser observation required**

The endpoint description calls the data "chart history", which strongly suggests shared use, but identity with the stock-page graph is not stated.

### Test

On an actively viewed stock page:

- capture the visible graph's exact points/data source without issuing additional native Torn requests;
- fetch v2 specific-stock history through the API;
- compare timestamp, price and point count.

This is a diagnostic test only; the production collector should prefer the API regardless.

## API-005 [P0] — `/user/stocks` fields and acquisition-lot reconstruction

**Resolution: CLOSED for schema; merge semantics open under MEC-008**  
**Evidence class: MECHANIC**

Endpoint: `GET /user/stocks`  
Access: Limited  
Stability: Stable

Each `UserStock` contains:

- `id` — stock ID
- `shares` — int64
- `transactions[]`
- `bonus`

Each `UserStockTransaction` contains:

- `id` — int64 transaction ID
- `shares` — int64
- `price` — float
- `timestamp` — int32 Unix timestamp

Bonus state contains:

- `available`
- `increment`
- `progress`
- `frequency`

This is sufficient to reconstruct visible acquisition lots **provided Torn preserves their semantics after merges/partial sales**. That proviso is being tested separately.

## API-006 [P0] — Does `/user/stocks` contain sold history?

**Resolution: LIKELY NO; empirical confirmation required**  
**Evidence class: SCHEMA OBSERVATION**

The schema models current `stocks`, their current `shares`, current bonus state and their acquisition `transactions`. It provides no sale object and no explicit historical-position collection.

Therefore TornTrading must not rely on `/user/stocks` as a complete realized-trade ledger.

### Data-design consequence

TornTrading should maintain its own append-only portfolio snapshots/trade journal once activated. Realized totals can be reconciled to personal stats.

### Test

Sell an entire controlled position and verify whether the stock/transactions disappear from `/user/stocks`.

## API-007 [P0] — Realized stock profits/losses/fees through API

**Resolution: CLOSED for aggregate values; transaction-level attribution not available here**  
**Evidence class: MECHANIC**

`GET /user/personalstats` supports investment statistics whose stock section contains:

- `profits`
- `losses`
- `fees`
- `net_profits`
- `payouts`

OpenAPI also exposes legacy/stat names such as `stockprofits`, `stocklosses`, `stockfees`, `stocknetprofits`, and `stockpayouts` for historical-stat querying.

The endpoint supports specific historical personal stats with a `timestamp` parameter (converted to nearest date), which can help reconcile daily cumulative changes.

### Limitation

These are cumulative/account statistics, not individual trade records. TornTrading needs its own transaction journal for precise per-trade attribution.

## API-008 [P0] — Timestamped benefit/dividend payouts

**Resolution: PARTIAL; optional Full-key path exists**  
**Evidence class: MECHANIC + implementation unknown**

Two official routes exist at different granularities:

1. `/user/personalstats` exposes cumulative stock `payouts` but not event-level timestamp/value detail.
2. `/user/log` exposes timestamped dynamic logs and can filter by log ID/category, but requires **Full Access**.

The exact stock-payout log IDs and event payload fields still require authenticated `logtypes`/log inspection.

### Product decision

Core TornTrading will not require Full Access merely to obtain payout timestamps. Benefit economics can start from current benefit definitions + cumulative reconciliation/manual/account-local records. Full-key payout-history enrichment is optional and requires a separate value/security review.

## API-009 [P0] — Effective cache TTLs

**Resolution: CLOSED for documented service cache; stock-specific runtime behavior should still be measured**  
**Evidence class: MECHANIC**

Official API documentation states:

- API requests use a service cache that can last **up to 30 seconds**;
- identical requests can return the same cached data;
- the service cache may be bypassed by making the request unique using a `timestamp` query parameter;
- `comment` is ignored for cache uniqueness;
- requests served from service cache do not consume API-key quota;
- some selections also use non-bypassable global cache, and the official listed global-cache selections currently do not include Torn stocks.

### Collector policy

Normal collector mode should not bypass cache unnecessarily. If Torn prices genuinely update once/minute, one market snapshot per minute is sufficient. Cache bypass belongs only in short controlled timing experiments.

## API-010 [P0] — Server timestamp / freshness / clock skew

**Resolution: CLOSED for availability**  
**Evidence class: MECHANIC**

Stable `GET /torn/timestamp` returns current Torn server time and requires a Public key.

Stock responses themselves do not define a response-level server timestamp in their schema. Therefore collection records must contain:

- `request_started_at_utc`
- `response_received_at_utc`
- optional Torn server timestamp sampled for synchronization
- any source/history timestamp supplied by the stock endpoint
- local monotonic duration

Do not use retrieval time as a substitute for market-effective timestamp.

## API-011 [P0] — Request and daily limits

**Resolution: CLOSED for documented global request limit; record-volume limits are endpoint-dependent**  
**Evidence class: MECHANIC**

Current Torn docs state:

- maximum **100 individual requests per minute per user across all keys**;
- the limit may change without notice;
- invalid keys can lead to temporary IP blocks;
- error code 5 = too many requests;
- error code 14 = daily read limit reached for cloud-service record pulls.

The stock endpoints in the OpenAPI do not expose a pagination limit because their responses are fixed stock/history structures. The exact record-based daily limit relevant to any cloud-backed historical personal-stat use is not numerically documented here.

### TornTrading policy

Target collection load:

- one `GET /torn/stocks` per minute for market snapshots;
- optional infrequent per-stock detail/history refreshes;
- `/user/stocks` at a low cadence or on user-open/refresh, not every few seconds;
- no design that approaches the 100/min limit.

A healthy system should remain useful at <5 Torn API requests/minute in normal interactive use, excluding one-time research/history work.

## Authentication design

API v2 OpenAPI defines header authentication:

`Authorization: ApiKey <key>`

This must be the preferred implementation. It avoids putting the key into URLs, browser history, copied links or external error traces.

## Approved normalized market schema

The collector may now standardize the following minimum record:

```text
source = "torn_api_v2"
source_schema_version
request_started_at_utc
response_received_at_utc
torn_server_timestamp?   # synchronization sample, not assumed effective price time
stock_id
acronym
name
price
market_cap
shares
investors
bonus_passive
bonus_frequency
bonus_requirement
bonus_description
raw_payload_hash
```

Raw response payloads must be preserved for reproducibility/schema-change audits.

## Remaining P0 API experiments

Before moving official chart history into the canonical research dataset:

- API-X1: measure `chart.history` count/oldest point/delta distribution for every stock.
- API-X2: repeat API-X1 after 24h to determine rolling/reaggregation behavior.
- API-X3: compare one stock's API chart history to actively viewed Torn graph data.
- API-X4: capture `/user/stocks` before/after partial sale, full sale and merge.
- API-X5: inspect exact personal-stats investment output with a Limited/custom key.
- API-X6 (optional): identify stock payout log IDs/payload using Full-key logs only if benefit-event history is worth the privilege.

## Decision

**APPROVED for collector/data-model implementation.** The official API surface and permission model are sufficient. `chart.history` is **not yet approved as canonical historical research data** until API-X1/X2 establish its real resolution, depth and timestamp behavior.
