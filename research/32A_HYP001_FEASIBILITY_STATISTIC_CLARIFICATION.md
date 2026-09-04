# HYP-001 Economic Feasibility — Preregistration Clarification

Status: **PRE-DATA CLARIFICATION**  
Date: 2026-09-04

Before the first economic-feasibility evidence run, clarify the unit of the spread metric in `32_HYP001_ECONOMIC_FEASIBILITY_PREREGISTRATION.md`.

HYP-001's canonical prospective outcome is a **weekly cross-sectional spread**. Therefore all primary gross/net signaled-minus-non-signaled spread metrics in this feasibility audit must be calculated as follows:

1. within each Thursday cohort, compute the mean return of signaled eligible stocks;
2. within the same cohort, compute the mean return of non-signaled eligible stocks;
3. calculate that cohort's signaled-minus-non-signaled spread;
4. average the available cohort spreads with **equal weight per Thursday cohort**.

The primary +0.20 percentage-point feasibility threshold applies to this equal-weight mean weekly cohort spread, not to a pooled trade-level difference.

Pooled observation-level means and medians may also be reported descriptively, but they do not control the feasibility classification.

The same equal-weight-per-cohort convention applies to chronological-quartile and annual spread summaries.

This clarification was committed before any live economic-feasibility run and does not change the HYP-001 signal, horizon, threshold, notional scenarios, stress scenarios, or decision thresholds.
