# TornTrading — MEC-X1 Publication Boundary Results

Status: **reviewed experimental finding**  
Run date: 2026-09-02  
GitHub Actions run: `33665395253`  
Artifact: `publication-boundary-probe-33665395253`  
Artifact SHA-256: `1aad118e23fb077a86baafe7f5d23ee68f4f25dadc65ef2910c080af29ecf507`

## Executive decision

MEC-X1 passed its first controlled three-boundary experiment.

**MEC-001 — cross-stock API publication boundary: VALIDATED FINDING at 2-second observation resolution.**

Across all three observed minute boundaries, every official stock that changed price moved from the prior chart state to the new chart state without any observed mixed old/new official market response.

**MEC-002 — chart timestamp to uncached API state: VALIDATED FINDING at the API timestamp-label level.**

For all three boundaries, the official chart row timestamped exactly `HH:MM:00` matched the complete uncached `/torn/stocks` state on the first sampled server-second after the boundary. This validates the source-label join used by research datasets.

It does **not** yet prove Torn UI rendering time or order-execution time. Those remain transaction/native-page questions under P0-E4/P0-E5.

## Experiment configuration

Three consecutive boundaries were observed:

- `2026-09-02T18:09:00Z`
- `2026-09-02T18:10:00Z`
- `2026-09-02T18:11:00Z`

Sampling window per boundary:

- start: 6 seconds before boundary;
- end: 30 seconds after boundary;
- cadence: 2 seconds;
- official requests: cache-bypassed using a changing `timestamp` query parameter;
- sources per sample: `/torn/timestamp`, `/torn/stocks`, Tornsy watchlist;
- post-experiment target: official per-stock chart history.

The probe stayed below Torn's documented request-rate ceiling by making at most two Torn API calls every two seconds during observation windows.

## Results by boundary

| Boundary | Stocks that actually changed | Last pre-boundary official changed state | First post-boundary full official state | Tornsy full state first observed | Tornsy minus official |
|---|---:|---|---|---|---:|
| 18:09:00Z | 25 | all 25 old | all 25 new; response +1.426s | all 35 target prices; response +23.746s | +22.320s |
| 18:10:00Z | 27 | all 27 old | all 27 new; response +1.354s | all 35 target prices; response +23.762s | +22.408s |
| 18:11:00Z | 24 | all 24 old | all 24 new; response +1.345s | all 35 target prices; response +11.765s | +10.420s |

For unchanged stocks, the old and new target prices are naturally identical; atomicity analysis therefore uses only stocks whose official chart price actually changed at the boundary.

## Official publication finding

For each boundary, the final pre-boundary sample had Torn server timestamp `boundary - 1 second` and every changed stock still matched the previous chart minute.

The first post-boundary sample had Torn server timestamp `boundary + 1 second` and every changed stock matched the new chart minute.

Observed transition windows were therefore bounded by approximately:

- 18:09: last pre response at -0.615s; full new response at +1.426s;
- 18:10: last pre response at -0.551s; full new response at +1.354s;
- 18:11: last pre response at -0.558s; full new response at +1.345s.

No sampled official response contained a mixture where some changed stocks had the old price and other changed stocks had the new price.

### Interpretation

At the experiment's 2-second sampling resolution, the cache-bypassed bulk Torn stock API behaves as an **atomic market snapshot around the minute boundary**.

The experiment does not distinguish whether the actual internal switch occurs exactly at `HH:MM:00.000`, several hundred milliseconds later, or anywhere between the last pre-boundary and first post-boundary observations. A sub-second claim is not justified.

## Chart timestamp finding

The later official chart histories contained one row for each tested boundary, timestamped exactly at the minute boundary. The complete new bulk API state observed after each boundary matched those chart target prices across all 35 official stocks.

This supports the following research convention:

```text
source_timestamp = official chart minute timestamp
source_timestamp_semantics = minute_state_label_verified
```

For source-to-source historical joins, an official Torn row and Tornsy `m1` row with the same timestamp may be compared directly. The prior reconciliation experiments already found exact price equality at zero timestamp offset across all common observations.

Do not relabel this field as `order_executable_at` until UI/transaction evidence exists.

## Tornsy publication finding

Tornsy's watchlist eventually presented the exact same 35-stock boundary state in all three observations, with the Tornsy timestamp equal to the boundary minute.

The first full Tornsy state was observed:

- +23.746 seconds after the 18:09 boundary;
- +23.762 seconds after the 18:10 boundary;
- +11.765 seconds after the 18:11 boundary.

Thus Tornsy publication lag was **variable**, not a fixed constant, and in this run lagged the first observed uncached official full state by roughly **10.4 to 22.4 seconds**.

### Research consequence

Tornsy is validated as an historical archive, but its live publication time must not be confused with the Torn market's effective minute boundary.

For any future live strategy research:

- official uncached API observation time and Tornsy availability time are separate variables;
- historical Tornsy timestamps represent the Torn minute label, not the moment Tornsy made the row available;
- backtests must not act as though a Tornsy historical row was observable at `HH:MM:00` merely because it carries that timestamp.

This is a major anti-look-ahead requirement.

## What this authorizes

The experiment now permits:

1. minute-aligned Torn historical statistics using the verified source timestamp label;
2. minute-level external-market alignment research at the **data-label** level;
3. candidate lead/lag discovery, provided later interpretation uses an explicit Torn publication/observation model;
4. treating cache-bypassed bulk `/torn/stocks` as a coherent official market snapshot at the observed resolution;
5. modeling Tornsy as a delayed live distributor rather than the authoritative real-time source.

## What remains blocked

This experiment does not authorize executable-profit claims because it did not observe the native Torn stock page or a transaction submission.

Still required before execution-aware backtesting:

- MEC-003: controlled buy price cross-check;
- MEC-004: controlled sale price cross-check;
- MEC-006: sale-fee rounding;
- MEC-008: merge effect on `/user/stocks` transaction representation;
- API-004/P0-E5: native loaded graph versus API equivalence;
- transaction/UI timing sufficient to define realistic human execution latency.

## Evidence classification

- Official full-market transition consistency across 3 boundaries: **VALIDATED_FINDING**, scoped to 2-second API observation resolution.
- Official chart timestamp mapping to the new minute API state: **VALIDATED_FINDING**, API/source-label scope.
- Tornsy live delay of 11.8–23.8 seconds in this run: **OBSERVATION**, not yet a stable distribution.
- Exact Torn UI/order-execution boundary: **HYPOTHESIS / OPEN**.

## Ongoing validation

The publication-boundary workflow is scheduled weekly. Repeated runs should accumulate a distribution for:

- uncached official API transition bound;
- Tornsy live publication delay;
- any future mixed-state observation;
- any market-universe or source behavior change.

Any mixed official response or changed timestamp convention reopens MEC-001/MEC-002 automatically for review.
