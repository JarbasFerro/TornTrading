# TornTrading — P0-E5b Broad Ceiling-Family Confirmation

Status: **PREREGISTERED FOLLOW-UP — no P0-E5b trial may be interpreted before this protocol is merged to `main`**

## Why this follow-up exists

The original targeted P0-E5 protocol remains frozen and unchanged. It was designed to distinguish the exact order of gross-value rounding versus fee rounding by requiring the entire conservative true-gross interval to fit inside `(1000K, 1000K + 0.50)`. Because the conservative hidden-price interval has width `$0.015 × shares`, that geometry necessarily requires fewer than 34 shares and is rare in the live 35-stock universe.

This follow-up was designed after observing that scarcity. It therefore receives a new identifier and cannot retroactively alter or rescue the original protocol.

The practical downstream question is broader than exact calculation order: can we validate a conservative, current-era transaction-cost family in which Torn rounds the 0.1% stock sale fee upward rather than by floor or conventional nearest-integer rounding?

## Frozen hypothesis

`H-FEE-002`:

> For a valid broad-zone stock sale whose entire conservative true-gross interval lies safely inside the lower half of a `$1,000` fee interval, current Torn stock-sale fees belong to the ceiling-like family and equal `K + 1` dollars.

This hypothesis does **not** distinguish among:

- `total_value__fee_ceiling`;
- `gross_floor__fee_ceiling`;
- `gross_half_up__fee_ceiling`;
- `gross_half_even__fee_ceiling`.

Those four models were the strongest sample-equivalent family in the historical diagnostic. Exact gross-preprocessing order remains a separate question under the original narrow P0-E5 protocol.

## Price uncertainty

For displayed two-decimal stock price `p`, preserve the existing conservative internal execution-price envelope:

- lower true price: `p - $0.005`;
- upper true price: `p + $0.01`.

For `n` shares:

- `G_low = (p - 0.005) × n`;
- `G_high = (p + 0.01) × n`.

No narrower hidden-price assumption is introduced.

## Broad candidate geometry

Let `K = floor((p × n) / 1000)` with `K >= 1`.

A trade is a P0-E5b broad candidate only when the entire conservative gross interval satisfies:

`1000K + 1 < G_low`

and

`G_high < 1000K + 499`.

These margins keep the entire hidden-price interval away from both the exact `$1,000` fee boundary and the `$500` conventional-nearest fee boundary, including integer gross preprocessing.

For every accepted candidate:

- the ceiling-like family predicts `K + 1`;
- final-fee floor predicts `K`;
- final-fee half-up / half-even predicts `K`;
- gross-first variants followed by non-ceiling fee rounding also predict `K` within the frozen band.

The broad protocol therefore tests the **fee-rounding family**, not exact gross preprocessing.

## Capital and planner limits

- maximum displayed gross per trial: `$5,000`;
- current official two-decimal price required;
- human execution only;
- `TCSE` excluded;
- no automated Torn transaction submission.

The `$5,000` cap is unchanged from the live narrow-candidate snapshot, so broader availability comes from scientifically broader geometry rather than increased required capital.

## Prospective trial validity

Before every human click, record:

1. stock;
2. current price;
3. shares;
4. boundary multiplier `K`;
5. ceiling-family prediction `K + 1`;
6. non-ceiling prediction `K`;
7. attempt number.

Target Torn server seconds 15–40. No other stock action may occur in the bracket.

After the sale, the trial is valid only if:

- the official/logged sale price equals the planned two-decimal price;
- the Stock sell 5511 amount equals planned shares;
- an integer fee is present;
- the receipt event second is 15–40;
- the planned broad geometry revalidates using the logged price.

Price changes or other failed controls are retained as invalid attempts and never silently discarded.

## Frozen decision rule

Potential validation of `H-FEE-002` requires:

- **6 valid broad-zone trials**;
- at least **2 different stocks**;
- at least **3 different K values**;
- no more than **3 valid trials from one stock**;
- all **6/6** observed fees equal `K + 1`.

Any valid observed fee equal to `K` rejects `H-FEE-002`.

Any other valid fee means the frozen family is incomplete and the gate remains open.

## Relationship to exact P0-E5

A successful P0-E5b result may validate a **current ceiling-like fee family** and support a conservative research transaction-cost envelope. It does not establish the exact internal gross-rounding order.

The original narrow protocol remains the mechanism-level path for distinguishing the four ceiling-like calculation orders.

Downstream research may only use a conservative cost model after a separate review decision. No production BUY/SELL recommendation is authorized by this protocol.
