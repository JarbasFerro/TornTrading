# TornTrading — HYP-001 Historical Economic Feasibility Results

Status: **ECONOMICALLY_PLAUSIBLE — DISCOVERY SAMPLE ONLY, NOT CONFIRMATORY**  
Evidence run: GitHub Actions `33838657011`  
Artifact: `hyp001-economic-feasibility-33838657011`  
Artifact digest: `sha256:851006fb80e93f126ddc9a0639de4e67282efe07b3c725846a5c4bf5a78888aa`  
Historical outcome cutoff: **2026-09-03 00:00 UTC**

## Decision

HYP-001 remains a high-priority prospective research path. The frozen 7-day reversal rule is economically large enough in its historical discovery sample to justify continued prospective validation after applying the accepted Torn stock-sale fee and a preregistered adverse execution stress.

This is **not** an out-of-sample validation and does not establish executable profit.

## Sample

- 35 tradable Torn stocks;
- 237 Thursday cohorts with eligible observations;
- 8,023 eligible stock/cohort observations;
- 711 signaled observations;
- 7,312 non-signaled observations;
- 209 Thursday cohorts contained both signaled and non-signaled stocks and therefore contributed a cross-sectional spread.

## Gross discovery effect

Across stock/cohort observations:

- signaled mean forward 7-day return: **+0.6485%**;
- signaled median: **+0.4950%**;
- non-signaled mean: **+0.0703%**;
- pooled difference: **+0.5782 percentage points**;
- signaled positive-return rate: **67.1%**.

Using the preregistered equal-weight Thursday-cohort statistic:

- mean weekly signaled-minus-non-signaled spread: **+0.5372 percentage points**;
- median weekly spread: **+0.5228 percentage points**;
- positive weekly spread rate: **73.7%**.

## Primary economic stress case

Primary preregistered scenario:

- position notional ceiling: `$100,000`;
- adverse execution stress: **25 bps on entry + 25 bps on exit**;
- sale fee: `ceil(0.001 × stressed sale gross)`;
- whole-share quantities.

Result:

- signaled mean net 7-day return: **+0.0459%**;
- signaled median net return: **−0.1065%**;
- signaled positive-net-return rate: **46.1%**;
- mean equal-weight weekly net spread versus non-signaled stocks: **+0.5340 percentage points**;
- median weekly net spread: **+0.5197 percentage points**;
- positive weekly net spread rate: **73.7%**.

The primary classification therefore passes the frozen `ECONOMICALLY_PLAUSIBLE` gate:

- 711 signaled observations versus minimum 60;
- mean signaled net return > 0;
- mean weekly net spread +0.5340pp versus required +0.20pp;
- positive primary-scenario net spread in **4/4 chronological quartiles**.

## Execution sensitivity

The result is economically promising but **execution-fragile in absolute-return terms**.

At `$100,000` notional:

| Adverse stress per leg | Signaled mean net 7d return | Mean weekly net spread |
|---:|---:|---:|
| 0 bps | +0.5474% | +0.5367pp |
| 10 bps | +0.3465% | +0.5356pp |
| 25 bps | +0.0459% | +0.5340pp |
| 50 bps | −0.4531% | +0.5313pp |

The cross-sectional reversal spread survives because the same adverse execution assumptions affect both groups similarly. The absolute long-only return does not: at 50 bps adverse execution on each leg, the mean signaled position becomes negative.

Therefore later claims of executable profitability must measure actual execution latency/slippage rather than assuming the discovery spread converts directly into profit.

Integer fee-ceiling effects are negligible at research-relevant notionals: the `$10,000`, `$100,000`, and `$1,000,000` scenarios produced nearly identical weekly spreads under the same stress assumptions.

## Chronological stability

Primary-scenario weekly net spread was positive in every chronological quartile:

- Q1: **+0.9912pp**;
- Q2: **+0.3957pp**;
- Q3: **+0.3067pp**;
- Q4: **+0.4037pp**.

Annual gross weekly spread was also positive in every observed year:

- 2022: +0.9020pp;
- 2023: +0.8528pp;
- 2024: +0.2431pp;
- 2025: +0.3203pp;
- 2026 through the fixed discovery cutoff: +0.4660pp.

The effect weakened materially after 2023 but remained positive. This reinforces the need for the already-active prospective validation rather than treating the historical average as stationary.

## Interpretation

The strongest Torn-only discovery so far is not being killed by the known 0.1% stock-sale fee. Its economic relevance depends much more on execution quality than on Torn's fee rounding or position size.

Accordingly:

- continue HYP-001 prospective collection: **YES**;
- keep HYP-001 as a primary strategy-research candidate: **YES**;
- claim historical discovery return as validated alpha: **NO**;
- claim executable profit: **NO**;
- optimize threshold/horizon using this sample: **NO**;
- prioritize future current/+1-minute execution measurement on actual prospective signals: **YES**.

## Next research priority

The project should now move to external-driver mapping and independent predictive evidence rather than further Torn mechanic work. If the external sector screen remains blocked by credential setup, parallel work should focus on prospective data capture and additional independently preregistered hypotheses rather than retuning HYP-001 on its discovery sample.
