# TornTrading — P0 Foundations Gate Status

Status date: 2026-09-02

This document is the operational gate for the first Stage 0 research sprint. Detailed evidence lives in `01_GOVERNANCE_COMPLIANCE.md` through `04_HISTORICAL_DATA_AUDIT.md`.

## Gate summary

| Domain | Gate | Result |
|---|---|---|
| Governance/compliance | Can we legally/safely build API-driven read-only analysis? | **PASS** |
| Market mechanics | Do we know enough to collect/model data? | **PASS FOR COLLECTION; HOLD FOR BACKTESTING** |
| API/data surface | Can official API support market + portfolio research? | **PASS** |
| Historical data | Is history validated enough for alpha research? | **FAIL / BLOCKED PENDING AUDIT** |
| External-driver research | May Stage 2 begin? | **NO** |
| Signal/alpha research | May Stage 4 begin? | **NO** |

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

- MEC-001: OPEN — exact cross-stock minute boundary
- MEC-002: OPEN — authoritative/effective timestamp semantics
- MEC-003: PARTIAL — buy execution model documented; controlled cross-check pending
- MEC-004: PARTIAL — sell execution model documented; controlled cross-check pending
- MEC-005: PARTIAL — documented friction known; rounding empirical
- MEC-006: OPEN — 0.1% fee rounding
- MEC-007: CLOSED — price-update reconfirmation is documented
- MEC-008: OPEN — merged purchase effect on API transactions
- MEC-009: CLOSED — newest transaction consumed first on generic sale

**Mechanics gate: PASS for data collector; HOLD for transaction simulator/backtests.**

### API P0

- API-001: CLOSED schema
- API-002: PARTIAL — history schema known, runtime depth/resolution unknown
- API-003: OPEN — history resolution by age
- API-004: OPEN — API chart versus native chart equality
- API-005: CLOSED schema; merge semantics linked to MEC-008
- API-006: PARTIAL — no sale-history schema; full-sale disappearance needs confirmation
- API-007: CLOSED aggregate realized stock stats
- API-008: PARTIAL — cumulative payouts available; event logs require optional Full key
- API-009: CLOSED documented cache behavior
- API-010: CLOSED server timestamp availability
- API-011: CLOSED documented request limit; endpoint-specific record limits remain monitored

**API gate: PASS for collector/data model.**

### DAT P0

- DAT-001: OPEN — official history depth
- DAT-002: PARTIAL — Tornsy interface/depth lead known; full audit pending
- DAT-003: OPEN — official vs Tornsy reconciliation
- DAT-004: OPEN — missing-minute rate
- DAT-005: OPEN — missingness mechanism
- DAT-006: CLOSED as canonical data policy
- DAT-007: PARTIAL — timestamp formats known, semantics unresolved
- DAT-008: OPEN — retroactive revision behavior
- DAT-009: DESIGN APPROVED — canonical schema/source precedence provisional
- DAT-010: PARTIAL — known structural events seeded; statistical breaks later

**Historical-data gate: BLOCKED.**

## Immediate experiment queue

Priority order is intentionally dependency-driven.

### P0-E1 — Official history inventory

Requires: Public Torn API key.

For every stock:

- fetch `GET /torn/{stockId}/stocks`;
- record history count, oldest/newest timestamp and adjacent timestamp deltas;
- repeat after 24 hours;
- determine rolling window/resolution behavior.

Closes/advances: API-002, API-003, DAT-001, DAT-007.

### P0-E2 — Live official/Tornsy reconciliation

Requires: Public Torn API key + Tornsy.

At one-minute cadence:

- persist official `/torn/stocks` snapshot;
- retrieve matching Tornsy data after its documented publication delay;
- compare prices/timestamps across all stocks;
- run for at least 7 days before final source-certification decision.

Closes/advances: MEC-001, MEC-002, API-009, DAT-003, DAT-007.

### P0-E3 — Tornsy archive audit

Does not require Torn key.

For every stock:

- inventory `m1`, `h1`, `d1` coverage;
- discover earliest timestamps;
- calculate gaps, duplicates and longest outages;
- hash retrieved historical windows;
- refetch overlaps to detect revisions.

Closes/advances: DAT-002, DAT-004, DAT-005, DAT-008.

### P0-E4 — Controlled transaction semantics

Requires: user's Torn account and deliberately small transactions.

Capture before/after API state around:

- normal buy;
- boundary/reconfirmation buy or sell if naturally encountered;
- small sale designed to expose fee rounding;
- quantity partial sale to verify LIFO representation;
- merge of two purchases;
- full exit of a test holding.

Closes/advances: MEC-003, MEC-004, MEC-005, MEC-006, MEC-008, API-005, API-006.

### P0-E5 — Native graph/API equivalence

Requires: actively viewed Torn stock page + Public API key.

Compare data already present in the loaded native graph with the API history. Do not issue automatic non-API Torn requests.

Closes/advances: API-004.

## Implementation authorization

The Stage 0 contract now authorizes only the following code classes:

1. Research data collector.
2. Historical downloader/auditor.
3. Source reconciliation and data-integrity tooling.
4. Fixtures/tests for the above.
5. Optional manual experiment logger for transaction evidence.

Not authorized yet:

- BUY/SELL signal engine;
- technical-indicator strategy;
- external-market predictive model;
- backtest claims;
- portfolio optimizer;
- autonomous execution;
- production Torn stock-page UI claiming predictive value.

## Next gate

P0 Foundations becomes fully **PASS** only when:

- official chart-history depth/resolution/timestamp behavior is measured;
- Tornsy overlap accuracy and missingness are quantified;
- retroactive-revision behavior is tested;
- execution fee/lot semantics required by a transaction simulator are measured.

External-driver reverse engineering may begin once the **historical-data subset** passes, even if nonessential UI/portfolio transaction edge cases remain open, provided no backtest requires those unresolved execution assumptions.
