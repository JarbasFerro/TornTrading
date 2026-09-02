# TornTrading — TCSE Factor Results

Status: **OBSERVATION / descriptive factor evidence**  
Evidence run: GitHub Actions `33687543137`  
Artifact: `tcse-factor-33687543137`  
Questions advanced: STA-006, STA-008, STA-013

## Decision

**TCSE is useful as a market-level benchmark, but current evidence does not justify using it as a universal residualization factor for all Torn stocks.**

The strongest evidence is at aggregate-market level. Individual-stock explanatory power is generally weak.

## Aggregate market relationship

TCSE versus the equal-weight return of the 35 tradable stocks:

| Horizon | Overlap | Pearson | R² | Beta |
|---|---:|---:|---:|---:|
| 1h | 1,998 | 0.8548 | 0.7306 | 0.7039 |
| 24h | 1,961 | 0.8664 | 0.7506 | 0.7638 |

This is strong descriptive evidence that TCSE captures broad aggregate Torn-market direction.

## Individual-stock explanatory power

Across the 35 tradable stocks:

| Metric | 1h | 24h |
|---|---:|---:|
| Median individual R² | 0.0178 | 0.0260 |
| Mean individual R² | 0.0286 | 0.0338 |
| Median Pearson | 0.1334 | 0.1612 |
| Median residual/raw variance ratio | 0.9822 | 0.9740 |
| Maximum individual R² | 0.1509 | 0.1407 |

Therefore TCSE explains only about 1.8% of the typical stock's hourly variance and 2.6% of the typical stock's daily variance in this sample.

### Highest observed TCSE relationships

1h:

| Stock | R² | Pearson | Beta |
|---|---:|---:|---:|
| TCI | 0.1509 | 0.3885 | 2.0872 |
| TSB | 0.1243 | 0.3526 | 1.7321 |
| MCS | 0.0882 | 0.2970 | 1.5684 |
| FHG | 0.0740 | 0.2720 | 1.3785 |
| SYM | 0.0579 | 0.2407 | 1.1583 |

24h:

| Stock | R² | Pearson | Beta |
|---|---:|---:|---:|
| TCI | 0.1407 | 0.3751 | 1.7338 |
| TSB | 0.1107 | 0.3327 | 1.4975 |
| FHG | 0.0979 | 0.3129 | 1.6977 |
| CNC | 0.0947 | 0.3077 | 1.5004 |
| MCS | 0.0729 | 0.2701 | 1.3009 |

TCI and TSB are the clearest candidates for later stock-specific TCSE-control sensitivity analysis. Even there, most variance remains unexplained.

## Stability observation

TCSE beta was positive in all four chronological quartiles for:

- 28 of 35 stocks at 1h;
- 26 of 35 stocks at 24h.

For the strongest relationships, TCI, TSB, MCS and FHG retained positive beta in every quartile. However, quartile R² remains modest and varies materially. This supports a broad directional relationship for some stocks, not a stable high-explanatory-power factor model.

## Cross-stock correlation

Raw cross-stock pairwise correlation is essentially zero on average:

| Horizon | Raw mean | Raw median | After TCSE residualization mean | After residualization median |
|---|---:|---:|---:|---:|
| 1h | -0.0016 | -0.0010 | -0.0217 | -0.0196 |
| 24h | 0.0013 | -0.0004 | -0.0222 | -0.0203 |

TCSE residualization does not reveal a large hidden positive common-correlation structure; instead the average pairwise correlation becomes slightly negative.

This is consistent with a market index that captures the aggregate mean while individual Torn stocks remain highly idiosyncratic. It is also a warning against treating TCSE as an exogenous common driver: because an index is related to its constituents, residualizing every constituent against that index can mechanically induce negative residual dependence.

## Research interpretation

### Accepted observations

- `OBSERVATION`: TCSE has a strong relationship with the equal-weight aggregate Torn market at 1h and 24h.
- `OBSERVATION`: typical individual-stock TCSE R² is low.
- `OBSERVATION`: TCI, TSB, MCS, FHG and several others show stronger-than-median TCSE exposure, but no individual R² exceeds ~0.16 in this run.
- `OBSERVATION`: raw pairwise stock correlation is near zero on average at 1h and 24h.

### Rejected conclusions

This evidence does **not** establish:

- TCSE as a predictive signal;
- TCSE as the canonical residualization factor for all stocks;
- a profitable market-neutral strategy;
- causal direction from TCSE to constituent prices;
- executable alpha.

## Decision for later research

1. Keep TCSE as an explicit market benchmark/control.
2. For stocks with stronger TCSE exposure, report both raw and TCSE-controlled results in later research.
3. Do not force TCSE residualization on every stock.
4. Compare TCSE against a transparent equal-weight market factor and a first-principal-component factor before selecting a canonical common factor.
5. Preserve raw-stock analysis because the majority of individual variance is idiosyncratic under this model.

## Evidence integrity

- 70 stock/horizon factor rows completed.
- 280 chronological quartile rows completed.
- Zero source errors were reported.
- Raw source history was not persisted in the artifact.
