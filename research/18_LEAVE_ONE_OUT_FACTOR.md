# TornTrading — Leave-One-Out Equal-Weight Market Factor

Status: **Stage 0 / descriptive factor analysis**  
Research date: 2026-09-02  
Questions advanced: STA-006, STA-008, STA-013

## Purpose

Test whether a transparent common Torn-market factor explains individual stocks better than TCSE when the target stock is excluded from its own factor.

For each target stock, the factor at a timestamp is the equal-weight mean return of the other available tradable stocks. At least 30 peers are required. The target stock is never included.

## Why leave-one-out

TCSE behaves like a broad market index but is related to its constituents. Regressing a constituent on an index containing that same constituent creates mechanical dependence. The leave-one-out construction removes that direct self-inclusion and provides a cleaner descriptive common-factor benchmark.

## Scope

- exactly 35 current tradable stocks;
- TCSE excluded;
- horizons: 1h and 24h;
- currently forming candles excluded;
- exact adjacent source timestamps required; gaps are not bridged;
- public Tornsy data only;
- aggregate outputs only.

## Measurements

For every stock/horizon:

- overlap count;
- alpha, beta, Pearson and R² versus the other-stock factor;
- raw and residual volatility;
- residual/raw variance ratio;
- chronological quartile beta and R².

At market level:

- raw mean/median pairwise stock correlation;
- mean/median pairwise correlation after leave-one-out residualization.

## Decision rule

This experiment may establish only an `OBSERVATION` about common factor structure. It does not choose a predictive signal.

A useful common factor should show broad explanatory power, stability across chronological quartiles, and a coherent reduction of common dependence without relying on self-inclusion.

The results will be compared with the already-reviewed TCSE evidence before any canonical factor is selected. PCA remains a later candidate and must be designed with explicit anti-overfitting controls rather than fitted and judged on the same full sample.

## Not authorized

- BUY/SELL logic;
- residual trading rules;
- profit claims;
- causal claims;
- selecting whichever factor has the best full-sample R² and calling it validated.
