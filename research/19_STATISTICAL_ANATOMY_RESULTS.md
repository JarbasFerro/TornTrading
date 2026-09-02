# TornTrading — Corrected Statistical Anatomy Results

Status: **OBSERVATION / hypothesis-generation evidence**  
Evidence run: GitHub Actions `33688072623`  
Artifact: `torn-statistical-anatomy-33688072623`  
Evidence date: 2026-09-02  
Questions advanced: STA-001 through STA-006

## Evidence integrity

The corrected run completed all 175 required Tornsy requests with zero source failures. It produced 245 stock/horizon distribution rows, 1,225 exact-horizon autocorrelation rows, 245 continuation/reversal rows, 980 chronological-quartile rows and 1,190 cross-stock correlation rows.

The analysis excludes forming periods, does not bridge source gaps, and for serial dependence pairs returns only at exact multiples of the stated horizon. The earlier rolling-window ~0.94 30-day ACF result is rejected and superseded.

## Primary observation: broad 7-day reversal

The strongest market-wide structure in this descriptive pass is negative serial dependence at the 7-day horizon.

| Horizon | Median lag-1 ACF | Stocks negative | Stocks below -0.10 | Negative in all 4 chronological quartiles |
|---|---:|---:|---:|---:|
| 1m | -0.065 | 32/35 | 8/35 | 18/35 |
| 5m | -0.048 | 31/35 | 3/35 | 19/35 |
| 1h | -0.018 | 25/35 | 0/35 | 6/35 |
| 6h | -0.005 | 18/35 | 0/35 | 2/35 |
| 24h | -0.038 | 27/35 | 5/35 | 10/35 |
| **7d** | **-0.200** | **35/35** | **34/35** | **34/35** |
| 30d | -0.193 | 32/35 | 29/35 | 23/35 |

At 7d, 27/35 stocks were below -0.10 in every one of the four chronological quartiles. This is materially more broad and stable than the short-horizon reversal observed in the same dataset.

### Non-overlapping continuation/reversal diagnostic

For 7-day returns, consecutive observations in this diagnostic are adjacent non-overlapping 7-day windows.

- median sign-continuation rate: **0.440**;
- all 35 stocks have continuation rate below 0.50;
- 25/35 are below 0.45;
- mean next-7d return after a bottom-decile 7d move is positive for **35/35** stocks;
- mean next-7d return after a top-decile 7d move is negative for **33/35** stocks;
- median next-7d return after a bottom-decile move is about **+0.91%**;
- median next-7d return after a top-decile move is about **-0.44%**.

These values are discovery statistics, not an out-of-sample trading result. The bottom/top-decile rule was inspected on this dataset and therefore cannot be validated on the same historical observations.

## 30-day reversal is real-looking but less stable

The corrected 30-day lag-1 ACF median is -0.193, not the rejected ~+0.94 rolling-window artifact.

- 32/35 stocks are negative overall;
- 29/35 are below -0.10 overall;
- 23/35 are negative in all four chronological quartiles;
- 10/35 remain below -0.10 in all four quartiles;
- median sign-continuation rate is about 0.467;
- bottom-decile next-30d mean is positive for 34/35 stocks.

This is a secondary reversal hypothesis seed, not the primary one, because stability is weaker and a 30-day decision cycle creates slower prospective validation.

## Short-horizon reversal is weak

The 1m and 5m cross-stock medians are modestly negative (-0.065 and -0.048), but chronological stability is much weaker than at 7d. The 1h and 6h medians are close to zero.

Short-horizon reversal should therefore not be prioritized merely because some individual stocks have larger coefficients.

## Return distributions are non-Gaussian

Median excess kurtosis across stocks is approximately:

- 1m: 1.94;
- 5m: 1.00;
- 1h: 0.92;
- 6h: 0.59;
- 24h: **6.68**;
- 7d: **4.73**;
- 30d: **3.26**.

Daily and multi-day returns therefore have materially heavy tails. Later risk models should not assume normal returns or rely only on mean/standard deviation.

## Positive long-run drift is visible

All 35 stocks have positive mean return over the observed 24h and 7d samples; 34/35 do at 30d. Median mean return is approximately +0.022% per 24h, +0.148% per 7d and +0.589% per 30d.

This is descriptive drift, not an annualized guarantee. Structural breaks and Torn's stated long-run market design must be considered before extrapolation.

## Volatility clustering: whole-sample signal, weak stability

Whole-sample median lag-1 absolute-return ACF is high at longer horizons:

- 24h: 0.314;
- 7d: 0.294;
- 30d: 0.247.

However, within chronological quartiles the median absolute-return ACF falls sharply (roughly 0.079, 0.088 and 0.033 respectively), and only 12/35, 15/35 and 6/35 stocks have positive absolute-return ACF in all four quartiles.

Therefore the safe interpretation is **regime/non-stationarity evidence**, not a stable volatility-clustering law. This should feed STA-009/STA-012 regime and structural-break research.

## Cross-stock structure remains weak

Across all 595 stock pairs:

| Horizon | Mean Pearson | Median Pearson | Min | Max |
|---|---:|---:|---:|---:|
| 1h | -0.0016 | -0.0008 | -0.075 | +0.075 |
| 24h | +0.0013 | -0.0004 | -0.125 | +0.135 |

The strongest 24h pair observed is CNC/THS at only +0.135. This agrees with the separate TCSE-factor result: aggregate-market movement exists, but individual Torn stocks are highly idiosyncratic.

## Research decisions

### Promote to preregistered hypothesis seed

**7-day reversal / bottom-decile recovery** is the highest-priority Torn-internal hypothesis generated by this pass.

Because the pattern was discovered using historical data through 2026-09-01, that historical period is contaminated for confirmatory testing. Clean confirmation must use prospectively collected data after preregistration or another genuinely untouched dataset.

### Secondary research

- 30-day reversal: retain as secondary hypothesis seed.
- Volatility regimes / structural breaks: prioritize before volatility-based position sizing.
- Short-horizon reversal: low priority until external-driver residuals are available.
- Cross-stock pairs: do not prioritize generic correlation/pairs trading from raw returns.

## Explicitly not concluded

This evidence does not establish:

- a profitable 7-day trading strategy;
- an optimal bottom-decile threshold;
- an optimal holding period;
- executable returns after Torn fees/delay;
- a production BUY/SELL rule;
- independence from external real-world price drivers.

Those require the external-driver, prospective-validation and execution gates defined by the Stage 0 contract.
