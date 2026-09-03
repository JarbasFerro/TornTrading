# TornTrading — Post-Action Six-Sale Audit Result

Status: **OBSERVATION — not confirmatory**  
Evidence run: GitHub Actions `33783308412`  
Source: official Torn API v2 user log type 5511  
Audit design: `research/27_POST_ACTION_SIX_SALE_AUDIT.md`

## Result

The deterministic audit found exactly six usable Stock sell receipts after the targeted P0-E5 protocol merge and selected all six.

Aggregate findings:

- selected latest sales: **6**;
- distinct stocks: **6**;
- receipt event seconds inside frozen stable-minute range 15–40: **6/6**;
- prices represented with exactly two decimal places: **6/6**;
- receipts matching `ceil(logged_price × shares × 0.001)`: **6/6**;
- receipts satisfying the frozen targeted geometry: **0/6**;
- distinct targeted boundary multipliers among qualifying receipts: **0**.

The six observations therefore do not test the deliberately discriminating `K` versus `K+1` geometry from `research/25_FEE_ROUNDING_TARGETED_CONFIRMATION.md`.

## Frozen 25-model behavior on these six receipts

The six receipts are strongly ceiling-like but are not sufficient to identify where the ceiling is applied.

Perfect 6/6 fits include:

- `total_value__fee_ceiling`;
- `gross_floor__fee_ceiling`;
- `gross_half_up__fee_ceiling`;
- `gross_half_even__fee_ceiling`;
- `per_share_fee_ceiling__then_multiply`;
- `price_is_total__fee_ceiling`.

Simple floor variants fit **0/6**. Half-up / half-even nearest-style variants fit **4/6** in the corresponding families.

This equivalence pattern is consistent with sales that are too small/non-discriminating to establish the order of total-value calculation and rounding. Transaction-level values are intentionally not published.

## Interpretation

The observations add current, post-preregistration evidence that ceiling-like fee behavior remains active across six different stocks. They do **not** resolve the remaining P0-E5 ambiguity because none landed in the geometry designed to make the competing ceiling-order formulas disagree.

Evidence state: `OBSERVATION`.

P0-E5 status: **OPEN**.

## Confirmatory boundary

These six transactions cannot be promoted into the frozen targeted confirmation because the required stock, current price, planner-selected share count, `K`, competing predictions, and attempt number were not recorded before each human click.

The next valid attempt must therefore be generated from a live current price using the already-frozen planner, recorded before execution, manually clicked by the human operator, and verified against the resulting official receipt.