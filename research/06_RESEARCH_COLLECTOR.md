# Research collector and audit tooling

Status: **research-only implementation**  
Created: 2026-09-02  
Authorized by: `research/05_P0_FOUNDATIONS_STATUS.md`

## Purpose

`research/tools/torn_research.py` exists only to collect evidence needed to close the P0 data and API gates. It contains no BUY/SELL logic, technical indicators, prediction model, portfolio optimizer, or Torn game-action automation.

The tool is dependency-free Python 3 and uses:

- official Torn API v2 for automated Torn requests;
- Tornsy's public API for third-party historical/archive observations;
- immutable JSON evidence files plus compact audit summaries.

Tornsy's published API documentation states that it collects Torn stock data once per minute, normally exposes fresh data 5–10 seconds after each minute, supports minute/OHLC historical intervals, and may contain missing minutes during connection/API outages: https://tornsy.com/api

## Security boundary

Official API commands read the key only from the `TORN_API_KEY` environment variable.

The key is deliberately **not** accepted as a command-line argument because shell history/process listings are unnecessary exposure paths. API v2 authentication is sent in the `Authorization: ApiKey ...` header. The tool never writes request headers to output and redacts common credential-like URL parameters in diagnostics.

Research output under `data/raw/` is gitignored. Do not commit personal portfolio data, API keys, or raw private API responses.

## Commands

Run from repository root.

### 1. Official current snapshot

```bash
export TORN_API_KEY='...'
python3 research/tools/torn_research.py snapshot
```

Captures:

- `GET /torn/timestamp`
- `GET /torn/stocks`
- request start time
- response receipt time
- HTTP status
- SHA-256 of the canonical JSON payload
- complete raw JSON response

This supports P0-E2 and timing work. Retrieval timestamp is explicitly **not** treated as price-effective timestamp.

### 2. Official history inventory

```bash
python3 research/tools/torn_research.py official-history
```

For every stock it captures `GET /torn/{stockId}/stocks`, preserves the raw response, and produces `inventory.csv` / `inventory.json` with:

- row count;
- unique timestamp count;
- oldest/newest timestamp;
- covered span in days;
- minimum/median/maximum adjacent timestamp delta;
- percentage of 60-second deltas;
- duplicate timestamp count;
- payload hash.

Run this on multiple dates to determine whether the official chart-history window rolls or changes resolution. This directly advances P0-E1 / API-002 / API-003 / DAT-001.

### 3. Tornsy single-window audit

```bash
python3 research/tools/torn_research.py tornsy-audit LSC --interval m1 --limit 2000
python3 research/tools/torn_research.py tornsy-audit LSC --interval d1 --limit 2000
```

Optional `--from-ts` is inclusive and `--to-ts` exclusive, matching Tornsy's documented API semantics.

The audit preserves raw data and reports timestamps, duplicates, adjacent deltas, regular-grid gaps and estimated missing slots for fixed-width intervals.

Important: repeated consecutive prices are retained as real observations. A zero price change is not treated as missing data.

### 4. Tornsy watchlist snapshot

```bash
python3 research/tools/torn_research.py tornsy-watchlist
```

Preserves Tornsy's current watchlist response for provenance/revision tests.

### 5. Live official/Tornsy reconciliation observation

```bash
python3 research/tools/torn_research.py reconcile-live
```

Optionally:

```bash
python3 research/tools/torn_research.py reconcile-live --wait-seconds 8
```

This captures:

- Torn server-time response;
- official current stock response;
- Tornsy watchlist response;
- exact numeric price difference per matching acronym;
- current share-count difference;
- source retrieval timestamps and hashes.

The report intentionally does **not** declare which source is right or assume the timestamps are equivalent. Repeated observations across minute boundaries are required before interpreting offsets.

## Output layout

Default root is `data/raw/`. Each command creates a unique UTC microsecond run directory and refuses to overwrite an existing raw file.

```text
data/raw/
  torn_api_v2/
    snapshots/<run-id>/
    official_history/<run-id>/
  tornsy/
    watchlist/<run-id>/
    audit/<SYMBOL>/<interval>/<run-id>/
  reconciliation/
    live/<run-id>/
```

Raw files contain both the payload and retrieval metadata. SHA-256 hashes allow us to detect changed/revised historical responses in later repeated runs.

## Reproducibility and source policy

- Preserve raw responses before deriving metrics.
- Never silently forward-fill missing timestamps in raw data.
- Never replace a prior observation with a later response.
- Treat a source mismatch as an observation requiring investigation.
- Do not infer price-effective time from response-retrieval time.
- Do not promote Tornsy to canonical source until official overlap is quantified.
- Do not begin alpha/correlation research merely because the tooling can download history.

## Tests

Run:

```bash
python3 -m unittest discover -s tests -v
```

The initial suite covers credential redaction, immutable writes, timestamp inventory, repeated-price preservation, Tornsy minute/OHLC parsing, gap detection, live source reconciliation, and symbol validation.

## What this version does not do

Deliberately excluded:

- scheduling/continuous collection;
- external financial-market data;
- automatic native Torn page requests;
- trade execution;
- user portfolio access;
- technical indicators;
- strategy/backtest logic;
- automatic interpretation of source differences.

Scheduling and a full archive paginator should be added only after this minimal evidence format passes review. Continuous collection belongs in a controlled runtime environment where raw evidence can be retained reliably; it should not be hidden inside the eventual userscript by default.

## Gate impact

If the tool behaves as designed on live data, it gives us the machinery to execute:

- **P0-E1** — official history inventory;
- **P0-E2** — live official/Tornsy reconciliation observations;
- **P0-E3** — Tornsy archive-window audits and repeated-hash revision checks.

P0-E4 (controlled buy/sell/merge semantics) and P0-E5 (native graph/API equivalence) still require explicit user-account/browser experiments and are outside this CLI.
