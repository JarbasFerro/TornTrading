# TornTrading — P0-E5 Fee-Rounding Project Decision

Status: **VALIDATED_FINDING — PROJECT-DECISION CLOSURE**  
Decision date: 2026-09-04  
Decision owner: project owner / research governance  
Primary mechanic: stock-sale transaction fee rounding

## Decision

For TornTrading research and downstream transaction-cost modeling, current Torn stock-sale fees are treated as **ceiling-like at 0.1% of sale value**.

The operational fee model is:

`fee = ceil(0.001 × gross_sale_value)`

This rule is accepted as decision-sufficient and P0-E5 is closed. No further manual fee-rounding trials are required unless later evidence directly contradicts this model or the exact internal preprocessing order becomes material to a downstream decision.

## Evidence basis

The project reached this decision after:

- official Torn documentation established the 0.1% stock-sale fee;
- the official Stock sell log schema exposed receipt fields including amount, price and fees;
- a preregistered historical model screen found ceiling-like total-value formulas matched 99 of 100 recent official sale receipts, while floor-like and conventional-nearest alternatives fit materially worse;
- a follow-up diagnostic found the single historical mismatch was +$1 and compatible with hidden execution-price precision relative to the two-decimal logged price;
- six additional contemporary post-action sales all matched simple ceiling-like fee calculation;
- a prospective HRG example was planned at $272.67 for 4 shares, where the ceiling-family predicted $2 and the competing floor/nearest family predicted $1; the official receipt charged $2.

The final closure is a governance decision about **decision sufficiency**, not a claim that every internal Torn calculation step has been reverse-engineered.

## Remaining non-material uncertainty

The project does **not** claim to distinguish whether Torn applies an intermediate floor/nearest/other preprocessing step to gross sale value before the final ceiling operation. The strongest surviving ceiling-like formulations were observationally equivalent over the available history.

That distinction is currently immaterial for TornTrading's intended transaction-cost treatment. It is therefore intentionally left unresolved rather than consuming additional research cycles.

## Downstream rule

Research backtests and execution-cost calculations may now use the ceiling-like 0.1% sale-fee model.

Where internal price precision is not observable, calculations should remain conservative and should not assume more precision than the source provides.

This finding does not authorize production BUY/SELL signals or automated game actions.

## Superseded manual gates

The following manual fee-confirmation gates are closed as completed by project decision:

- Issue #28 — targeted exact-order fee trials;
- Issue #34 — broad ceiling-family confirmation trials.

Future work should proceed to the next unresolved execution and validation gates rather than reopening fee rounding without new contradictory evidence.
