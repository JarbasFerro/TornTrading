# TornTrading — P0-E5 Historical Fee-Rounding Result

Status: **OBSERVATION — P0-E5 remains open**  
Evidence run: GitHub Actions `Stock sell fee-rounding evidence` run **33718838875**  
Evidence artifact: `stock-sell-fee-rounding-33718838875`  
Artifact digest: `sha256:27578122143ab45db2f1fa40c7a70b92762ac16e081a12e78b2bf5ad8ff0f117`  
Source commit: `028b6600190c54653f488369e4559fa619f5636c`  
Retrieved: 2026-09-03T05:26:20.514Z

## Decision

The preregistered closure rule **did not pass**.

Decision status emitted by the frozen analyzer:

`NO_PERFECT_MODEL`

Therefore this run does **not** establish a `VALIDATED_FINDING` for P0-E5 and does not authorize a final after-cost execution model.

## Aggregate evidence

The artifact contained:

- **100** usable Stock sell observations;
- **0** rejected observations;
- **100** globally discriminating observations;
- **25** frozen non-redundant candidate models;
- **0** perfect models.

The major behavioral pattern was:

| Candidate behavior | Aggregate fit |
|---|---:|
| Ceiling-like total-value/gross-first family | 99 / 100 |
| Half-up / half-even total-value family | 56 / 100 |
| Floor-like total-value family | 4 / 100 |
| `price` interpreted as already-total sale value | 0–1 / 100 |
| Per-share fee rounded before multiplication | 0–1 / 100 |

The four strongest ceiling-like formulas were prediction-equivalent on this 100-row sample:

- `total_value__fee_ceiling`
- `gross_floor__fee_ceiling`
- `gross_half_up__fee_ceiling`
- `gross_half_even__fee_ceiling`

Each matched 99 of 100 observations and missed the same one observation.

## Interpretation

### `OBSERVATION`

The recent sample strongly favors a **ceiling-like 0.1%-of-total-value behavior** over floor, conventional nearest-integer rounding, interpreting logged price as a total value, or rounding the fee per share first.

### Not established

The result does **not** establish that Torn's implementation is exactly:

`ceil(logged_price × amount × 0.001)`

because:

1. one of 100 observed fees is inconsistent with every frozen candidate;
2. the sample does not distinguish four ceiling-like gross-rounding orders;
3. the API log's `price` field may itself be a rounded representation of a more precise execution value;
4. a historical implementation/logging anomaly or structural change has not been excluded.

The single mismatch must not be discarded post hoc.

## Evidence-quality notes

The official API schema exposes pagination metadata with `next`/`prev` links for UserLogsResponse. The first preregistration intentionally used one page only. More same-period historical observations can therefore be collected without changing the 25-model family or executing a Torn trade.

The official Torn documentation continues to state that the stock sale fee is 0.1% of **total value sold**. No current official source reviewed specifies the integer rounding rule or the precision of the execution value used internally for fee calculation.

## Next research action

Before any manual micro-trade, run a second preregistered **diagnostic** that:

1. follows official pagination across the same 365-day window, subject to a fixed page/row cap;
2. reruns the unchanged 25-model tournament over the expanded history;
3. publishes only aggregate ceiling-model residual direction/magnitude buckets;
4. checks whether mismatches cluster by chronological quartile;
5. records only aggregate logged-price decimal-place counts;
6. tests whether ceiling mismatches are compatible with an unlogged sub-last-decimal price interval under explicitly stated nearest-rounding and truncation hypotheses.

This follow-up is diagnostic because the first preregistered confirmation failed. It must not silently redefine P0-E5 as closed.

## Effect on downstream work

P0-E5 remains open for exact mechanics.

However, if the follow-up establishes a narrow, stable conservative fee envelope, that envelope may be used for **research screening** to avoid overstating alpha. It must not be treated as exact execution economics or used to promote a production recommendation while P0-E4/P0-E5 remain unresolved.
