# TornTrading — Common-Factor Decision

Status: **Stage 0 / reviewed descriptive decision**  
Research date: 2026-09-03  
Questions advanced: STA-006, STA-008, STA-013  
Claim status: `OBSERVATION` plus a `REJECTED` candidate design; no alpha claim.

## Decision

Do **not** adopt an equal-weight Torn peer-market factor as a canonical residualization layer for individual stocks.

Keep TCSE as an explicit market-level benchmark / sensitivity control where relevant, but do not residualize every stock against TCSE by default. Individual-stock analyses remain primary unless a later independently designed factor demonstrates materially stronger and stable explanatory power.

PCA is deferred rather than promoted. Given the near-zero raw cross-stock dependence and weak transparent factors, PCA is not a priority until there is a specific research question and an out-of-sample loading protocol that prevents full-sample factor mining.

## Evidence reviewed

### TCSE experiment

Reviewed GitHub Actions evidence established:

- TCSE vs equal-weight aggregate Torn market R²: approximately **0.73 at 1h** and **0.75 at 24h**;
- median individual-stock TCSE R²: approximately **1.8% at 1h** and **2.6% at 24h**;
- strongest observed individual TCSE relationship: approximately **15% R²**;
- conclusion: TCSE is meaningful as an aggregate benchmark but weak as a universal individual-stock factor.

### Self-exclusion-safe peer-factor experiment

Evidence run: GitHub Actions `33714639426`  
Artifact: `leave-one-out-factor-33714639426`  
Artifact SHA-256 digest: `291688d40b6419a1ab6c350ca3294919d0440d77c1ef5b4b1eb012a190118c2b`  
Source errors: **0**  
Universe: **35 tradable stocks**, TCSE excluded.

The experiment used:

- per-stock factor = equal-weight returns of the other available Torn stocks (`leave-one-out`);
- at least 30 peers at a timestamp;
- exact adjacent timestamps only; source gaps are not bridged;
- horizons 1h and 24h;
- pairwise residual dependence measured with a shared factor excluding **both** members of each pair (`leave-two-out`), after review rejected the mechanically contaminated mutually included construction.

## Results

### Individual explanatory power

| Metric | 1h | 24h |
| --- | ---: | ---: |
| Median R² | 0.047% | 0.049% |
| Mean R² | 0.064% | 0.111% |
| Maximum R² | 0.237% | 0.703% |
| Stocks with R² > 5% | 0 / 35 | 0 / 35 |
| Median residual/raw variance ratio | ~99.95% | ~99.95% |

The peer factor therefore explains essentially none of the typical individual-stock return variance and removes essentially none of its variance.

### Cross-stock dependence

| Horizon | Raw mean pairwise Pearson | Leave-two-out residual mean Pearson | Raw median Pearson | Residual median Pearson |
| --- | ---: | ---: | ---: | ---: |
| 1h | -0.00150 | -0.00153 | -0.00159 | -0.00161 |
| 24h | +0.00132 | +0.00188 | -0.00045 | +0.00166 |

The corrected residualization does not produce a meaningful reduction in common pairwise dependence because there is almost no raw common dependence to remove.

### Chronological stability

The already tiny loadings are not stable:

- at 1h, **26/35** stocks change beta sign across the four chronological quartiles;
- at 24h, **31/35** change beta sign across quartiles;
- quartile median R² remains near zero throughout the sample.

This is inconsistent with treating the equal-weight peer series as a stable individual-stock common factor.

## Interpretation

`OBSERVATION`: Torn stock returns are predominantly idiosyncratic at the tested 1h and 24h horizons. Aggregate-market movement exists, as TCSE demonstrates, but transparent market factors explain little of typical individual-stock variance.

`REJECTED`: the candidate design “equal-weight peer-market factor as a canonical residualization layer for every Torn stock” is rejected at Stage 0. It fails both materiality and stability criteria.

This rejection does **not** imply that external real-world drivers are unimportant. Torn documents that prices are based on real-world stocks/industries; a stock can have a strong external driver while remaining weakly correlated with other Torn stocks. External-driver reverse engineering therefore remains a separate high-priority gate.

## Consequences for subsequent research

1. Analyze individual Torn stocks primarily in raw-return space unless a specific control is independently justified.
2. Keep TCSE as a reported market sensitivity/control, not a mandatory transformation.
3. Do not spend current research budget optimizing generic Torn-market beta models.
4. Prioritize the observed stock-specific **7-day reversal** hypothesis and its prospective evidence program.
5. Prioritize external real-world driver mapping and lead/lag testing as soon as the external-data gate is available.
6. Do not use PCA merely because transparent factors were weak; any PCA experiment requires preregistered dimensionality, chronological fitting and genuinely out-of-sample loadings.

## Not authorized

This finding does not authorize:

- BUY/SELL signals;
- residual trading strategies;
- factor timing;
- executable-profit claims;
- skipping external-driver research;
- treating HYP-001 as validated before its prospective and execution gates are satisfied.
