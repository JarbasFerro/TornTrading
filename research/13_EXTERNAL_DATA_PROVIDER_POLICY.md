# TornTrading — External Market Data Provider Policy

Status: **Stage 0 provider-policy pass**  
Research date: 2026-09-02

## Decision

For the first external-driver screen, **Tiingo is the preferred EOD provider candidate**, subject to the usage rules below. This decision is based on current documentation and terms, not on assumed historical behavior.

Tiingo currently advertises a free Starter tier with 30+ years of historical coverage, up to 500 unique API symbols per month, 50 requests/hour, and 1,000 requests/day. Its EOD API supports dated historical requests and raw/adjusted OHLCV fields.

Sources:

- Pricing: https://www.tiingo.com/pricing
- EOD API: https://www.tiingo.com/documentation/end-of-day
- General API/licensing notes: https://www.tiingo.com/documentation/general
- Terms of Use: https://api.tiingo.com/tos/
- Developer program: https://www.tiingo.com/documentation/appendix/developers

## Critical Starter-plan retention rule

Current Tiingo Terms section 1.6 states that Starter/trial users may not write, save, archive, back up, or otherwise retain Tiingo Data in persistent storage. Data may only be processed transiently in memory or a temporary non-persistent cache and must be removed after the calculation/session.

Therefore TornTrading must **never** on a Starter plan:

- commit raw Tiingo responses;
- write raw Tiingo price files into the repository;
- upload raw Tiingo prices as GitHub Actions artifacts;
- print raw price series into Actions logs;
- preserve recoverable raw-price hashes or encodings that could reconstruct the data;
- place raw prices in a durable database, cache, backup, or queue.

## Derived-product rule

Tiingo's current Terms allow creation/retention/distribution of a Derived Product without separate approval only when the derived result:

1. is not a substitute for Tiingo Data or the Tiingo service; and
2. cannot reasonably be reverse engineered or otherwise used to recover the underlying Tiingo Data.

This gives TornTrading a compliant research pattern:

```text
Tiingo API response
      ↓
volatile memory only
      ↓
returns / joins / statistical calculations
      ↓
non-reconstructable aggregate statistics
      ↓
raw Tiingo values deleted before process exit
```

Potentially retainable research outputs include aggregate correlation/regression/ranking statistics only if they satisfy the non-substitution/non-reconstruction criteria. We must not assume that every derived table is automatically permitted.

## Public-repository architecture

Because TornTrading is a public repository:

### Repository may contain

- provider client code;
- query definitions;
- ticker manifests;
- data schemas;
- statistical algorithms;
- synthetic fixtures;
- tests;
- provider metadata that Tiingo itself publicly documents;
- non-reconstructable derived research results permitted under the provider terms.

### Repository / public Actions artifacts must not contain

- Tiingo EOD/intraday raw rows;
- downloadable transformed series that are equivalent to the raw series;
- recoverable per-date Tiingo values;
- API tokens;
- request logs containing the token.

## Credential model

The implementation will use an Actions secret named:

`TIINGO_TOKEN`

The token must never be passed as a command-line argument or printed. It should be sent only through the provider-supported authorization mechanism.

The software may also support a user's own Tiingo token outside GitHub Actions; Tiingo's developer-program documentation explicitly describes software where each user supplies their own token as a supported integration model, provided the software itself is not redistributing Tiingo data.

## First-screen data policy

For each external candidate:

1. request metadata first to establish provider ticker, exchange, first/last available date;
2. fetch EOD data from 2021-04-01 onward into volatile memory;
3. choose raw versus adjusted price according to a preregistered rule;
4. calculate returns in memory;
5. align with Torn daily returns;
6. calculate only aggregate pair statistics;
7. discard external raw observations before process termination;
8. output a result matrix that cannot reconstruct the underlying provider series.

## Raw versus adjusted external prices

The first screening engine must calculate both concepts where provider fields permit, but **the research question must specify which one is primary before viewing results**.

Initial policy:

- primary: adjusted close-to-close returns for equity-company relationship screening, because corporate actions should not appear as economic stock moves;
- secondary sensitivity: raw close-to-close returns, to detect whether Torn itself may be using an unadjusted market-price feed;
- dividends/splits must never silently create fake predictive relationships.

If raw and adjusted results materially disagree, the mapping remains unresolved until the difference is explained.

## Alternative providers

### Alpha Vantage

Current documentation advertises 20+ years of global equity history. Historical intraday is premium. The free standard rate is currently 25 requests/day, making it less attractive for broad candidate screening but potentially useful for a reduced minute candidate set after paid access.

Sources:

- https://www.alphavantage.co/documentation/
- https://www.alphavantage.co/premium/

### Twelve Data

Current Basic pricing advertises 8 API credits/minute and 800/day with internal non-display usage, while paid tiers increase market coverage and throughput. It remains a viable alternative/provider cross-check after separate terms review.

Source: https://twelvedata.com/pricing

## Approval

**APPROVED for implementation of a Tiingo-compatible transient EOD screening adapter.**

This approval does not authorize persistence or redistribution of raw Tiingo market data. Any implementation that writes provider price rows to durable storage fails the Stage 0 governance gate.
