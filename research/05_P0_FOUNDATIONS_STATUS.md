# TornTrading — P0 Foundations Gate Status

Status date: 2026-09-02

This document is the operational gate for Stage 0. Detailed evidence lives in `01_GOVERNANCE_COMPLIANCE.md` through `09_OFFICIAL_DATA_GATE_RESULTS.md`.

## Gate summary

| Domain | Gate | Result |
|---|---|---|
| Governance/compliance | Can we safely build API-driven read-only analysis? | **PASS** |
| Market mechanics | Do we know enough to collect/model data? | **PASS FOR COLLECTION; HOLD FOR EXECUTION BACKTESTS** |
| API/data surface | Can official API support market + portfolio research? | **PASS** |
| Historical price data | Is price history validated enough for descriptive research? | **PASS WITH QUALIFICATIONS** |
| External-driver candidate mapping | May non-causal mapping/statistics begin? | **YES** |
| Minute lead/lag alpha | May causal timing claims begin? | **NO — EFFECTIVE TIMESTAMP BLOCKER** |
| Execution-aware backtesting | May profitability claims begin? | **NO — MEC-X1/P0-E4 BLOCKERS** |
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

- MEC-001: OPEN — exact cross-stock publication boundary/atomicity
- MEC-002: OPEN — economic/effective timestamp semantics
- MEC-003: PARTIAL — buy execution model documented; controlled cross-check pending
- MEC-004: PARTIAL — sell execution model documented; controlled cross-check pending
- MEC-005: PARTIAL — documented friction known; rounding empirical
- MEC-006: OPEN — 0.1% fee rounding
- MEC-007: CLOSED — price-update reconfirmation is documented
- MEC-008: OPEN — merged purchase effect on API transactions
- MEC-009: CLOSED — newest transaction consumed first on generic sale

**Mechanics gate: PASS for data research; HOLD for execution-aware backtests.**

### API P0

- API-001: CLOSED schema
- API-002: CLOSED for current runtime behavior — specific-stock history observed at 60 rows / m1
- API-003: CLOSED for current endpoint observation — current history is a 60-point rolling minute window; repeat monitoring remains prudent
- API-004: OPEN — API chart versus native loaded graph equality
- API-005: CLOSED schema; merge semantics linked to MEC-008
- API-006: PARTIAL — no separate sale-history schema; full-sale disappearance needs confirmation
- API-007: CLOSED aggregate realized stock stats
- API-008: PARTIAL — cumulative payouts available; event logs require optional Full key
- API-009: CLOSED — all requests have service cache up to 30s; unique `timestamp` query bypasses it
- API-010: CLOSED server timestamp availability
- API-011: CLOSED documented request limit; endpoint-specific record limits remain monitored

**API gate: PASS.**

### DAT P0

- DAT-001: CLOSED — official history observed as 60 one-minute rows for all 35 official stocks
- DAT-002: PASS WITH QUALIFICATIONS — Tornsy archive audited at m1/h1/d1; gaps and forming-candle caveats documented
- DAT-003: PASS WITH QUALIFICATIONS — first credentialed run produced 2,065/2,065 exact historical price matches at zero timestamp offset across all 35 official stocks
- DAT-004: ADVANCED — bounded Tornsy audit quantified observed gaps; deeper monthly/full-archive missingness remains research work
- DAT-005: ADVANCED — observed major gaps were source-wide, supporting provider/system outage interpretation; broader classification continues
- DAT-006: CLOSED as canonical data policy
- DAT-007: PARTIAL — official/Tornsy timestamp labels align at zero offset; executable/publication semantics remain MEC-002
- DAT-008: PASS FOR SHORT-INTERVAL GUARD — 108 fixed windows reran with zero revisions; weekly guard continues
- DAT-009: DESIGN APPROVED — source precedence updated after official reconciliation
- DAT-010: PARTIAL — known structural events seeded; statistical break detection later

**Historical-price gate: PASS WITH QUALIFICATIONS for descriptive statistics and external-driver candidate mapping.**

## Credentialed official-data evidence

GitHub Actions run `33663657891` established:

- 35 current official Torn stocks;
- 60 official history observations per stock;
- one-minute cadence for every stock;
- 59 historical Torn/Tornsy comparable minutes per stock in run 1;
- 100% exact price equality on all 2,065 compared observations;
- zero best timestamp offset for all 35 stocks.

Run 1 compared 59 rather than 60 points because Tornsy's `to` filter is exclusive. The gate is corrected to request one interval beyond the newest official timestamp.

Tornsy also exposes `TCSE`, which is treated as a **market index**, not a tradable stock. The canonical tradable universe is the official `/torn/stocks` set.

The apparent run-1 live disagreement is classified as service-cache contamination: Torn documents service caching of all requests for up to 30 seconds, while individual official history points obtained after the crossed minute boundary matched Tornsy's new-minute prices exactly. All future official-gate requests explicitly bypass service cache with a unique `timestamp` query parameter.

See `09_OFFICIAL_DATA_GATE_RESULTS.md`.

## Immediate experiment queue

### P0-E1 — Official history inventory

**Status: PASS.**

Continue daily monitoring for schema/depth changes, but the current behavior is established well enough for architecture and source precedence.

### P0-E2 — Official/Tornsy reconciliation

**Status: PASS WITH QUALIFICATIONS.**

Daily cache-bypassed reconciliation now accumulates repeated evidence. Historical source equality is strong; causal publication timing is intentionally delegated to MEC-X1.

### P0-E3 — Tornsy archive audit

**Status: PASS WITH QUALIFICATIONS.**

Public m1/h1/d1 audit and the fixed-window revision guard are operational. Continue revision monitoring and deepen missingness statistics as the full research dataset is assembled.

### MEC-X1 — Publication Boundary Experiment

**Status: NEXT CRITICAL EXPERIMENT.**

Use cache-bypassed official API requests around multiple minute boundaries to determine:

- first Torn server second at which new prices become visible;
- whether stock publication is atomic across the market;
- relationship between first visibility and chart-history timestamp;
- Tornsy publication delay for the same minute;
- whether any apparent source lead survives official service-cache bypass.

This experiment is required before minute-level external-market lead/lag claims.

### P0-E4 — Controlled transaction semantics

Requires deliberately small user transactions.

Capture before/after state around:

- normal buy;
- boundary/reconfirmation buy or sell if naturally encountered;
- small sale designed to expose fee rounding;
- quantity partial sale to verify LIFO representation;
- merge of two purchases;
- full exit of a test holding.

Closes/advances: MEC-003, MEC-004, MEC-005, MEC-006, MEC-008, API-005, API-006.

### P0-E5 — Native graph/API equivalence

Compare data already present in an actively loaded Torn stock graph with official API history. Do not issue automatic non-API Torn requests.

Closes/advances: API-004.

## Research authorization after credentialed run 1

Now authorized:

1. Research data collection and source reconciliation.
2. Historical downloader/auditor and revision monitoring.
3. Descriptive market statistics using audited Tornsy history.
4. External-market **candidate mapping** at horizons that do not depend on unresolved sub-minute publication semantics.
5. Non-causal correlation, clustering, volatility/regime and structural-break exploration.
6. Publication-boundary research.

Still not authorized:

- claims that an external market leads Torn by N minutes;
- minute-level causal predictive backtests;
- BUY/SELL signal engine;
- execution-aware profitability claims;
- portfolio optimizer based on unvalidated alpha;
- autonomous execution;
- production Torn stock-page UI claiming predictive value.

## Next gate

The next major transition is from **validated historical prices** to **validated market-effective timestamps**.

MEC-X1 must pass before minute-level lead/lag research can be interpreted causally. P0-E4 must pass before strategy returns can be represented as realistic executable profit. These two blockers can proceed independently while descriptive external-driver mapping starts in parallel.
