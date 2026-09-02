# Stage 0 — Official Torn data gate

Status: **BLOCKED ON FIRST CREDENTIALED RUN**

This gate closes the remaining official-data questions that cannot be answered from public third-party archives alone. It is an evidence-collection step, not alpha research.

## Objectives

1. Inventory the official Torn V2 chart history returned for every current stock.
2. Measure official history depth, cadence, duplicates, and timestamp coverage.
3. Compare the overlapping official history with Tornsy using only an observed compatible cadence.
4. Test small timestamp offsets around zero instead of assuming both systems assign timestamps identically.
5. Capture a fresh official stock snapshot immediately before a Tornsy watchlist snapshot for a live comparison.
6. Preserve raw responses, retrieval timestamps, payload hashes, and comparison outputs for review.

## Credential rule

The workflow reads `TORN_API_KEY` only from a GitHub Actions repository secret.

- Never commit an API key.
- Never paste the key into source code, a workflow input, an issue, a PR, or a research artifact.
- Never pass the key on the command line.
- Use the least-privileged Torn API key that can access the public `/torn` endpoints required by this gate. Do not grant Limited or Full Access merely for this research step.
- The existing HTTP client sends the key only in the `Authorization: ApiKey …` request header. Stored observations do not contain request headers.

## One manual setup step

In GitHub, open the TornTrading repository and add an Actions repository secret named exactly:

`TORN_API_KEY`

Then run the `Official Torn data gate` workflow manually from the Actions tab on `main`.

The workflow is intentionally not scheduled. We will decide cadence only after the first run establishes official history depth, cache behavior, and useful reconciliation timing.

## Evidence produced

The workflow writes an immutable run directory under:

`data/raw/official_data_gate/<run-id>/`

It contains:

- Torn server timestamp response.
- Initial official all-stocks response.
- Detailed official history response for every stock.
- Tornsy overlap response for each stock when the official cadence maps to a supported Tornsy interval.
- A fresh official all-stocks response for the live comparison.
- Tornsy live watchlist response.
- `history_inventory.csv`.
- `history_comparison.json` with every tested timestamp offset.
- `live_comparison.json`.
- `summary.json`.

Raw workflow evidence is retained by GitHub Actions for 90 days.

## Offset methodology

For an official cadence `d`, the first comparison tests:

`-2d, -d, 0, +d, +2d`

This is diagnostic only. A best-fitting offset is an **observation**, not a validated timing rule. It must be repeated across independent runs before being used to align datasets for statistical research.

The comparison ranking uses, in order:

1. percentage of numerically identical overlapping prices;
2. number of comparable timestamp pairs;
3. lower mean absolute price difference;
4. smaller absolute timestamp offset.

## Review criteria for P0-E1

Official-history inventory can pass when:

- every current stock is queried successfully;
- response envelopes parse without silent row loss;
- history row count and timestamp cadence are known;
- duplicates and gaps are explicitly quantified;
- the available depth is documented by stock.

## Review criteria for P0-E2

Official-vs-Tornsy reconciliation can pass only when evidence establishes enough agreement to define a safe canonicalization rule. At minimum we need:

- explicit overlap counts for every comparable stock;
- price agreement statistics;
- timestamp-offset evidence;
- treatment of unmatched timestamps;
- a decision about currently forming observations/candles;
- repeated captures if one run cannot distinguish source latency from timestamp convention.

A single successful workflow run does **not** automatically pass P0-E2.

## Stage boundary

Until P0-E1/P0-E2 and the remaining Torn execution/timestamp semantics are approved, TornTrading remains blocked from alpha claims, profitability backtests, and production BUY/SELL/HOLD logic.
