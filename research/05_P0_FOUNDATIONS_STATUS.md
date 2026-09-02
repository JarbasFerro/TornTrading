# TornTrading — P0 Foundations Gate Status

Status date: 2026-09-02

This document is the operational gate for Stage 0. Detailed evidence lives in `01_GOVERNANCE_COMPLIANCE.md` through `11_PUBLICATION_BOUNDARY_RESULTS.md`.

## Gate summary

| Domain | Gate | Result |
|---|---|---|
| Governance/compliance | Can we safely build API-driven read-only analysis? | **PASS** |
| Market mechanics for data research | Are market publication/timestamp labels measured? | **PASS AT API LEVEL** |
| API/data surface | Can official API support market + portfolio research? | **PASS** |
| Historical price data | Is history validated enough for research? | **PASS WITH QUALIFICATIONS** |
| External-driver mapping/statistics | May mapping and correlation research begin? | **YES** |
| Minute lead/lag research | May candidate timing relationships be tested? | **YES, WITH EXPLICIT AVAILABILITY MODEL** |
| Execution-aware backtesting | May simulated profit be called executable? | **NO — P0-E4/P0-E5 BLOCKERS** |
| Production signals | May a BUY/SELL engine ship? | **NO** |

## Question status

### GOV P0

- GOV-001: CLOSED
- GOV-002: CLOSED for architecture
- GOV-003: CLOSED
- GOV-004: CLOSED with external-provider ToS condition
- GOV-005: CLOSED at policy level; backend architecture deferred
- GOV-006: CLOSED
- GOV-007: CLOSED

**Governance gate: PASS.**

### MEC P0

- MEC-001: **CLOSED / VALIDATED_FINDING** at 2-second API observation resolution — three boundaries transitioned from all-old changed stocks to all-new changed stocks with no sampled mixed official state
- MEC-002: **CLOSED at API/source-label level** — official chart `HH:MM:00` timestamp maps to the corresponding new uncached API minute state; UI/order-execution timing remains separate
- MEC-003: PARTIAL — buy execution model documented; controlled cross-check pending
- MEC-004: PARTIAL — sell execution model documented; controlled cross-check pending
- MEC-005: PARTIAL — documented friction known; rounding empirical
- MEC-006: OPEN — 0.1% fee rounding
- MEC-007: CLOSED — price-update reconfirmation is documented
- MEC-008: OPEN — merged purchase effect on API transactions
- MEC-009: CLOSED — newest transaction consumed first on generic sale

**Mechanics gate: PASS for market-data/timestamp research; HOLD for execution-aware backtests.**

### API P0

- API-001: CLOSED schema
- API-002: CLOSED for current runtime behavior — specific-stock history observed at 60 rows / m1
- API-003: CLOSED for current endpoint observation — current history is a 60-point rolling minute window; repeat monitoring remains active
- API-004: OPEN — API chart versus native loaded graph equality
- API-005: CLOSED schema; merge semantics linked to MEC-008
- API-006: PARTIAL — no separate sale-history schema; full-sale disappearance needs confirmation
- API-007: CLOSED aggregate realized stock stats
- API-008: PARTIAL — cumulative payouts available; event logs require optional Full key
- API-009: CLOSED — service cache exists; research calls use unique `timestamp` query for fresh official data
- API-010: CLOSED server timestamp availability
- API-011: CLOSED documented request limit; endpoint-specific record limits remain monitored

**API gate: PASS.**

### DAT P0

- DAT-001: CLOSED — official history observed as 60 one-minute rows for all 35 official stocks
- DAT-002: PASS WITH QUALIFICATIONS — Tornsy archive audited at m1/h1/d1; gaps and forming-candle caveats documented
- DAT-003: PASS WITH QUALIFICATIONS — official/Tornsy historical prices match exactly at zero timestamp offset across all common points in credentialed runs
- DAT-004: ADVANCED — bounded Tornsy audit quantified observed gaps; deeper monthly/full-archive missingness remains research work
- DAT-005: ADVANCED — observed major gaps were source-wide, supporting provider/system outage interpretation; broader classification continues
- DAT-006: CLOSED as canonical data policy
- DAT-007: **CLOSED for source-label alignment** — official/Tornsy minute labels align at zero offset; live-source availability must be modeled separately
- DAT-008: PASS FOR SHORT-INTERVAL GUARD — 108 fixed windows reran with zero revisions; weekly guard continues
- DAT-009: DESIGN APPROVED — source precedence updated after official reconciliation
- DAT-010: PARTIAL — known structural events seeded; statistical break detection later

**Historical-price gate: PASS WITH QUALIFICATIONS.**

## Credentialed source evidence

### Official/Tornsy reconciliation

The first credentialed run established 35 current official Torn stocks, 60 official one-minute history rows per stock, and 2,065/2,065 exact historical price matches against Tornsy at zero offset for the 59 points made comparable by the original exclusive-boundary request.

The corrected cache-bypassed run subsequently showed:

- 35/35 live official prices exactly equal to Tornsy at the final snapshot;
- TCSE as the only Tornsy-only symbol, classified as a market index rather than tradable stock;
- every common historical point exact at zero offset;
- service-cache contamination eliminated from the comparison design.

See `09_OFFICIAL_DATA_GATE_RESULTS.md`.

### MEC-X1 publication boundary evidence

GitHub Actions run `33665395253` observed three consecutive boundaries at 18:09, 18:10 and 18:11 UTC.

At those boundaries:

- 25, 27 and 24 stocks actually changed price;
- the last sampled pre-boundary official state showed all changed stocks at the previous-minute value;
- the first sampled post-boundary official state showed all changed stocks at the new chart-history value;
- no sampled official state mixed old/new values among changed stocks;
- first full official responses arrived at +1.426s, +1.354s and +1.345s;
- Tornsy's first full matching state arrived at +23.746s, +23.762s and +11.765s.

Tornsy's historical timestamp is therefore a valid Torn minute label but is **not** evidence that the historical row was observable live at the boundary instant.

See `11_PUBLICATION_BOUNDARY_RESULTS.md`.

## Immediate experiment / research queue

### P0-E1 — Official history inventory

**Status: PASS.** Daily monitoring remains active for schema/depth changes.

### P0-E2 — Official/Tornsy reconciliation

**Status: PASS WITH QUALIFICATIONS.** Daily cache-bypassed reconciliation accumulates repeated evidence.

### P0-E3 — Tornsy archive audit

**Status: PASS WITH QUALIFICATIONS.** Public audit and weekly fixed-window revision guard are operational.

### MEC-X1 — Publication Boundary Experiment

**Status: PASS for first three-boundary API experiment.** Weekly repetition remains active to detect regime/source changes and accumulate a delay distribution.

This closes the timestamp-label blocker for research. It does not close transaction/UI timing.

### EXT / external-driver candidate mapping

**Status: AUTHORIZED NOW.**

May begin:

- map each Torn stock to candidate real-world equities, sector/industry ETFs, indices and other plausible drivers;
- build minute/hour/day aligned datasets;
- test contemporaneous correlation and candidate lag structures;
- test rolling stability and regime dependence;
- use TCSE as a potential Torn market factor/benchmark, not a tradable asset.

Required discipline:

- source availability timestamps must be distinguished from source labels;
- any live-use hypothesis must use information that would actually have been available before the Torn decision point;
- Tornsy historical rows cannot be assumed available at their minute timestamp because observed Tornsy live publication lagged Torn by roughly 10–22 seconds in MEC-X1;
- discoveries remain HYPOTHESIS until out-of-sample validation.

### P0-E4 — Controlled transaction semantics

**Status: BLOCKING EXECUTION-AWARE PROFITABILITY.**

Requires deliberately small user transactions/native observations around:

- normal buy;
- boundary/reconfirmation trade if naturally encountered;
- small sale designed to expose fee rounding;
- quantity partial sale;
- merge of two purchases;
- full exit.

Closes/advances: MEC-003, MEC-004, MEC-005, MEC-006, MEC-008, API-005, API-006.

### P0-E5 — Native graph/API equivalence

**Status: OPEN.**

Compare data already present in an actively loaded Torn stock page/graph with cache-bypassed API observations. No automatic non-API Torn requests.

Closes/advances: API-004 and helps convert API publication timing into realistic user-visible timing.

## Research authorization after MEC-X1

Now authorized:

1. Research data collection, reconciliation and revision monitoring.
2. Descriptive market statistics using audited Tornsy history.
3. External-market candidate mapping.
4. Minute/hour/day source alignment using verified Torn timestamp labels.
5. Candidate lead/lag discovery with explicit information-availability controls.
6. Non-causal and predictive research experiments that remain clearly labeled as hypotheses until proper validation.
7. Cross-sectional, volatility, regime, structural-break and residual research.

Still not authorized:

- calling a backtest return executable profit;
- zero-latency execution assumptions;
- BUY/SELL production signals;
- portfolio optimizer based on unvalidated alpha;
- autonomous execution;
- production Torn stock-page UI claiming predictive value.

## Next gate

The project can now move from **source validation** into **external-driver and statistical discovery** while P0-E4/P0-E5 proceed independently.

The next major research question is no longer whether our historical Torn prices are trustworthy. It is:

> Which observable real-world market variables explain or predict the next Torn stock state, with information-availability timing enforced and without look-ahead?

Execution-aware profitability remains a later gate and must wait for controlled transaction/native-page evidence.
