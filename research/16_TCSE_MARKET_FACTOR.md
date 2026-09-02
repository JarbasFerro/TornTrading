# TornTrading — TCSE Market-Factor Research

Status: **Stage 0 / descriptive factor analysis**  
Research date: 2026-09-02  
Questions advanced: STA-006, STA-008, STA-013

## Purpose

Determine whether the Torn City Stock Exchange index (TCSE) captures a common market component in the 35 current tradable Torn stocks.

This is a descriptive market-structure experiment. It does not validate alpha, causal predictability, or trading profit.

## Why this matters

If TCSE explains a material and stable share of individual-stock variance, later stock-specific research should operate on residual returns after controlling for the common market factor. Otherwise a strategy may merely rediscover general Torn market direction.

If TCSE explains little, raw stock-specific structure may be more informative and an equal-weight stock factor may be a better benchmark.

## Universe and horizons

- Tradable universe: exactly 35 stocks from `external_driver_candidates.json`.
- TCSE is excluded from the tradable cross-section and used only as a factor candidate.
- Horizons: 1 hour and 24 hours.
- Forming source candles are excluded.
- Returns require exact adjacent source timestamps; gaps are never bridged.

## Measurements

For each stock and horizon:

- common observation count;
- Pearson correlation with TCSE;
- OLS alpha and beta;
- R²;
- raw return standard deviation;
- TCSE-residual standard deviation;
- residual/raw variance ratio;
- chronological quartile beta and R² stability.

At market level:

- TCSE correlation/R² versus an equal-weight 35-stock return series;
- mean and median raw pairwise cross-stock correlation;
- mean and median pairwise correlation after TCSE residualization.

The equal-weight factor requires at least 30 of 35 stock returns at a timestamp so sparse source coverage cannot dominate it.

## Interpretation

A useful TCSE factor should show more than isolated high stock correlations. Evidence should include:

1. material R² for a broad subset of stocks;
2. reasonably stable beta/R² across chronological quartiles;
3. high relationship to the equal-weight market return; and/or
4. a measurable reduction in pairwise cross-stock correlation after residualization.

If those conditions fail, TCSE should not automatically become the canonical market factor. A later factor-design step may instead use equal-weight, PCA, or another transparent common component.

## Research boundary

Permitted output: `OBSERVATION` about common-factor structure.

Not permitted from this experiment:

- calling TCSE predictive;
- treating TCSE beta as a BUY/SELL signal;
- optimizing entries on residuals;
- claiming executable profit;
- choosing a canonical factor solely because it produces the highest in-sample R².

Any residual-alpha hypothesis must be separately preregistered and validated chronologically.
