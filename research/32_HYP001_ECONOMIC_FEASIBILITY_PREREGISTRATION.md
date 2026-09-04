# TornTrading — HYP-001 Historical Economic Feasibility Audit

Status: **PREREGISTERED DISCOVERY-SAMPLE AUDIT — NOT CONFIRMATORY**  
Preregistration date: 2026-09-04  
Hypothesis: `HYP-001`  
Primary question: is the already-discovered 7-day reversal effect economically large enough to justify continued prospective validation?

## 1. Claim boundary

This audit reuses the historical archive that originally generated HYP-001. It therefore **cannot confirm HYP-001**, produce an out-of-sample finding, or authorize a trading recommendation.

Its sole purpose is economic triage: determine whether the frozen reversal rule is large and robust enough, after the now-accepted stock-sale fee and conservative execution stress, to remain worth prospective research effort.

No parameter in HYP-001 may be changed because of this audit.

## 2. Frozen signal rule

The audit must import and reuse the canonical HYP-001 implementation in `research/tools/run_hyp001_prospective.py` rather than reimplementing its signal definition.

For each tradable Torn stock and Thursday 00:00 UTC anchor:

- trailing window: 365 days;
- prior return horizon: exact open-to-open 7 days;
- signal threshold: stock-specific trailing 10th percentile;
- minimum trailing return observations: 300;
- condition: prior exact 7-day return <= trailing 10th percentile;
- forward outcome: exact next Thursday 00:00 UTC open-to-open 7-day return.

Universe remains the frozen 35 tradable stocks; TCSE is excluded.

## 3. Historical discovery cutoff

To prevent later prospective evidence from leaking back into the discovery audit:

- latest allowed forward outcome endpoint: **2026-09-03 00:00 UTC**;
- therefore an anchor is included only when both its signal information and complete next-7-day outcome are at or before that cutoff.

Any data after this fixed endpoint is ignored even if available when the workflow is run.

## 4. Source and candle rule

Source: Tornsy `d1`, using its already-audited historical archive.

- fetch up to 2,000 daily rows per stock;
- use daily `open` only;
- require exact UTC daily timestamps;
- no interpolation, forward fill, nearest-date substitution, or use of forming/future outcome candles;
- missing endpoints make that stock/cohort ineligible rather than imputed.

## 5. Transaction cost

P0-E5 is now closed by project decision. For every modeled sale:

`fee = ceil(0.001 × gross_sale_value)`

Buy fee remains zero.

Share quantities are whole integers. For each fixed capital scenario, shares are:

`floor(position_notional / stressed_entry_price)`

If zero shares can be purchased, that observation is unavailable for that notional scenario and is counted explicitly.

## 6. Frozen capital scenarios

The audit will report exactly three fixed per-position notional ceilings:

- `$10,000`;
- `$100,000`;
- `$1,000,000`.

These scenarios are sensitivity checks for integer-share and fee-ceiling effects; they are not portfolio recommendations.

The **primary feasibility scenario is `$100,000`** per position.

## 7. Frozen execution stress

Exact historical +1-minute fills are unavailable over the full multi-year daily archive. Therefore this audit is an economic stress test, **not a final execution-aware backtest**.

For each notional, report exactly four symmetric adverse execution stresses per leg:

- `0 bps`;
- `10 bps`;
- `25 bps`;
- `50 bps`.

For stress `s`:

- modeled buy price = Thursday open × `(1 + s)`;
- modeled sell price = next-Thursday open × `(1 - s)`;
- whole-share quantity is based on the stressed buy price;
- the accepted ceiling-like 0.1% sale fee is charged on stressed sale proceeds.

The **primary feasibility stress is 25 bps per leg**.

This stress grid is fixed before reading the economic results. It does not replace the separate current-minute/+1-minute execution contract for future datasets where those observations are actually available.

## 8. Frozen metrics

Overall discovery-sample metrics:

- eligible stock/cohort observations;
- signaled observations;
- non-signaled observations;
- mean and median gross forward 7-day return for signaled observations;
- mean and median gross forward 7-day return for non-signaled observations;
- gross signaled-minus-non-signaled spread;
- signaled positive-return rate.

For every notional × execution-stress scenario:

- available signaled/non-signaled observations;
- mean and median net return after modeled execution stress and exact ceiling-like sale fee;
- signaled positive-net-return rate;
- mean net signaled-minus-non-signaled spread.

Stability metrics:

- four chronological quartiles of eligible anchors;
- signaled count, signaled mean gross forward return, non-signaled mean gross forward return and spread in each quartile;
- same net spread under the **primary `$100,000 / 25 bps-per-leg` scenario**;
- annual aggregate counts and gross spreads for descriptive context.

No threshold, horizon, weekday, notional, stress level or subgroup will be optimized after seeing results.

## 9. Frozen feasibility classification

Primary scenario: `$100,000` position notional, 25 bps adverse execution stress on both entry and exit.

`ECONOMICALLY_PLAUSIBLE` requires all of:

1. at least 60 historical signaled observations;
2. primary-scenario mean signaled net 7-day return > 0;
3. primary-scenario mean net signaled-minus-non-signaled spread >= **+0.20 percentage points**;
4. primary-scenario net spread > 0 in at least 3 of 4 chronological quartiles.

`NOT_ECONOMICALLY_PLAUSIBLE` applies if either:

- primary-scenario mean signaled net return <= 0; or
- primary-scenario mean net spread <= 0.

Otherwise classification is `MARGINAL_OR_UNSTABLE`.

This classification is a **research-priority decision only**. Even `ECONOMICALLY_PLAUSIBLE` does not confirm predictability or profit.

## 10. Output/privacy contract

Tornsy prices are public, but the audit will still persist aggregate evidence only. Allowed outputs:

- one aggregate JSON summary;
- one annual aggregate CSV.

Do not persist raw price series, per-stock signal dates, per-trade returns, or reconstructable transaction sequences.

## 11. Decision use

- If `ECONOMICALLY_PLAUSIBLE`: continue HYP-001 prospective validation and prioritize later execution-aware/OOS economics.
- If `MARGINAL_OR_UNSTABLE`: continue prospective collection but lower research priority until more evidence accumulates.
- If `NOT_ECONOMICALLY_PLAUSIBLE`: prospective collector may remain for scientific completeness, but HYP-001 should no longer be a primary strategy-development path unless new independent evidence justifies reopening it.

No result from this discovery-sample audit authorizes production BUY/SELL signals or automated Torn actions.
