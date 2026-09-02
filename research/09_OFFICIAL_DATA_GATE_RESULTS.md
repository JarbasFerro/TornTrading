# TornTrading — Official Data Gate Results

Status: **P0 credentialed run 1 reviewed**  
Run date: 2026-09-02  
GitHub Actions run: `33663657891`  
Artifact: `official-torn-data-gate-33663657891`  
Artifact SHA-256: `91e2a31c20462ec2e7d01d93e35f7b670bb6447f278aa6974686a8705abff100`

## Executive decision

The first credentialed official/Tornsy reconciliation materially advances P0.

**P0-E1 — Official history inventory: PASS.**

For every stock returned by the official Torn API on this run:

- official stock count: **35 tradable stocks**;
- chart history rows per stock: **60**;
- history cadence: **60 seconds** for every stock;
- history span: approximately **59 minutes** from oldest to newest observation;
- duplicate official timestamps: none observed;
- observed official historical interval: **m1 only**.

This establishes that the current official specific-stock endpoint is a short rolling verification window, not a multi-year research archive.

**P0-E2 — Official/Tornsy historical reconciliation: PASS WITH QUALIFICATIONS.**

The first run compared all 35 official stocks against Tornsy minute history. For every stock:

- best timestamp offset: **0 seconds**;
- comparable observations: **59**;
- exact numeric price match rate: **100.0%**;
- mean absolute price difference: **0.0**.

Total exact historical matches in this run: **2,065 / 2,065** compared stock-minutes.

The intended overlap was 60 minutes, but Tornsy documents its `to` parameter as exclusive. Run 1 requested `to = newest_official_timestamp`, so the newest official minute was intentionally excluded by Tornsy and only 59 points overlapped. This is a tooling-boundary defect, not a source discrepancy. The gate has been corrected to request `to = newest + interval`.

The historical evidence is strong enough to treat Tornsy as a validated bootstrap archive for prices, subject to the already-established gap/revision quality flags and continued repeated reconciliation.

It does **not** yet prove the economic meaning of the timestamp (calculation time versus publication/effective time). Minute-level lead/lag alpha claims remain blocked on the execution-boundary experiment.

## Market universe finding

The official Torn API returned 35 stocks. Tornsy returned 36 symbols because it also exposes:

- `TCSE` — Torn City Stock Exchange index.

TCSE is an index/market measure, not a current tradable stock. Stocks 3.0 removed the old TCSE 30 player-tradable listing.

### Canonical universe rule

Research datasets must distinguish:

```text
asset_type = tradable_stock | market_index
tradable_stock universe = official /torn/stocks symbols
market_index = TCSE when supplied by Tornsy
```

TCSE may be used as a market factor/benchmark but must not enter portfolio allocation or cross-sectional tradable rankings as if it were a purchasable stock.

## Live snapshot finding — service cache

Run 1 initially appeared to show a live disagreement:

- official `/torn/stocks`: 35 stocks;
- Tornsy watchlist: 36 symbols including TCSE;
- only 9/35 official stocks exactly matched Tornsy's live prices at the final snapshot.

Raw evidence resolves this discrepancy.

The run crossed the `17:52:00 UTC` stock boundary while sequentially fetching official individual-stock histories. Individual official history requests made after that boundary already contained the `17:52` price. For all 15 stocks whose official history had advanced to `17:52`, the official history price exactly matched Tornsy's `17:52` watchlist price.

Several values in the later bulk `/torn/stocks` response still reflected the prior minute. Torn's API documentation states that **all API requests are subject to service cache for up to 30 seconds** and that fresh data should be requested using a unique `timestamp` query parameter. Run 1 did not explicitly bypass this service cache.

Therefore:

- the bulk-live mismatch is classified as **SERVICE_CACHE_CONTAMINATION**, not a source disagreement;
- it is **not evidence that Tornsy predicts a future price**;
- the gate now adds a unique `timestamp` query parameter to official requests before comparing live values.

This distinction is critical: ordinary cached API data must never be used to infer a Tornsy lead.

## Timestamp evidence

What run 1 validates:

1. Official chart timestamps and Tornsy minute timestamps join at **zero offset**.
2. At those joined timestamps, prices were exactly equal across 2,065 comparisons.
3. When the run crossed a minute boundary, newly available individual official history points at `17:52` matched Tornsy's `17:52` values.

What run 1 does **not** validate:

1. the exact second at which a new minute price becomes executable in the Torn UI;
2. whether all stocks become executable atomically;
3. whether a chart timestamp denotes calculation, publication, or effective execution time;
4. the lag between Torn UI, uncached Torn API, cached Torn API, and Tornsy publication.

These remain MEC-001/MEC-002 execution-boundary questions.

## Official history depth decision

Observed for all 35 official stocks:

```text
history_rows = 60
median_delta_s = 60
oldest = newest - 59 minutes
```

Accordingly:

- official history is excellent for recent-source reconciliation;
- official history is insufficient for long-horizon statistics or backtesting;
- Tornsy remains the primary bootstrap archive, with provenance and revision checks;
- TornTrading should continuously collect its own observations so reliance on third-party historical retention decreases over time.

## Data precedence after run 1

Approved price-source precedence:

1. directly captured **uncached** official Torn observations for live/recent verification;
2. official Torn chart history for the short rolling verification window;
3. Tornsy historical archive for older research history, with quality/revision flags;
4. other archives only after independent audit.

A cached official response is not automatically superior to a contemporaneous Tornsy observation. Cache state is part of provenance.

## Corrections implemented after run 1

The official gate is corrected to:

1. pass a unique `timestamp` parameter on official requests to bypass service cache;
2. account for Tornsy's exclusive `to` bound and include the newest official history minute;
3. identify Tornsy-only symbols explicitly, expected currently to include TCSE;
4. run automatically after gate-code changes on `main` and daily thereafter to accumulate repeated reconciliation evidence.

## P0 decision after run 1

- **DAT-001: CLOSED / VALIDATED FINDING** — official history is a 60-point, one-minute rolling window in this observation.
- **DAT-002: PASS WITH QUALIFICATIONS** — Tornsy archive structure/depth already audited separately.
- **DAT-003: PASS WITH QUALIFICATIONS** — 2,065/2,065 historical prices exact at zero offset; repeated cache-bypassed runs continue.
- **DAT-007: ADVANCED** — source timestamp labels align at zero offset; economic/effective timestamp semantics remain open.
- **DAT-008: ADVANCED** — short-window Tornsy revision guard passed; weekly guard continues.

The historical price source is now sufficiently validated to begin **non-causal descriptive market statistics and external-driver candidate mapping**. Minute-level predictive/lead-lag claims remain blocked until effective publication/execution timing is measured.

## Next experiment

Run **MEC-X1 / Publication Boundary Experiment** using cache-bypassed official API reads around multiple minute boundaries. The experiment should determine:

- first uncached server second at which each stock changes;
- whether all changed stocks publish atomically;
- how the new price relates to chart-history timestamp;
- delay until Tornsy publishes the same minute;
- whether any apparent cross-source lead survives service-cache bypass.
