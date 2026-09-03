# TornTrading — Leave-One-Out Equal-Weight Market Factor

Status: **Stage 0 / descriptive factor analysis**  
Research date: 2026-09-03  
Questions advanced: STA-006, STA-008, STA-013

## Purpose

Test whether a transparent common Torn-market factor explains individual stocks better than TCSE when the target stock is excluded from its own factor.

For each target stock, the factor at a timestamp is the equal-weight mean return of the other available tradable stocks. At least 30 peers are required. The target stock is never included.

## Why leave-one-out

TCSE behaves like a broad market index but is related to its constituents. Regressing a constituent on an index containing that same constituent creates mechanical dependence. The leave-one-out construction removes that direct self-inclusion and provides a cleaner descriptive common-factor benchmark.

A second exclusion rule is required for the market-level residual-correlation diagnostic. If residual(A) were computed against a factor containing B while residual(B) were computed against a factor containing A, the diagnostic itself could manufacture negative dependence. Therefore every pairwise residual correlation uses one common equal-weight factor that excludes **both** members of that pair (leave-two-out).

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
- alpha, beta, Pearson and R² versus the other-stock leave-one-out factor;
- raw and residual volatility;
- residual/raw variance ratio;
- chronological quartile beta and R².

At market level:

- raw mean/median pairwise stock correlation;
- mean/median pairwise residual correlation using a pair-specific leave-two-out factor that excludes both stocks from the factor.

## Decision rule

This experiment may establish only an `OBSERVATION` about common factor structure. It does not choose a predictive signal.

A useful common factor should show broad explanatory power and stability across chronological quartiles. Any apparent reduction of common dependence is considered interpretable only with the pairwise leave-two-out diagnostic; the earlier mutually included residual construction is explicitly rejected as mechanically contaminated.

The results will be compared with the already-reviewed TCSE evidence before any canonical factor is selected. PCA remains a later candidate and must be designed with explicit anti-overfitting controls rather than fitted and judged on the same full sample.

## Not authorized

- BUY/SELL logic;
- residual trading rules;
- profit claims;
- causal claims;
- selecting whichever factor has the best full-sample R² and calling it validated.
