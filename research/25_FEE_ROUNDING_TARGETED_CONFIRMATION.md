# TornTrading — P0-E5 Targeted Future Fee-Rounding Confirmation

Status: **PREREGISTERED — no targeted confirmation trade before merge**  
Preregistration date: 2026-09-03  
Primary questions: MEC-004, MEC-006, VAL-001  
Evidence target: P0-E5 exact stock-sale fee behavior  
Planner: `research/tools/plan_stock_fee_rounding_trial.py`

## 1. Purpose

The first preregistered historical test failed to close P0-E5 because no candidate model matched all 100 recent official `Stock sell` receipts. The subsequent diagnostic showed:

- the entire available one-year history was already those same 100 sales;
- four ceiling-like formulas were prediction-equivalent and matched 99/100;
- the only mismatch was observed fee = reference prediction + $1;
- all logged execution prices had two decimal places;
- the mismatch was compatible with a higher-precision true execution price hidden behind the logged cent representation.

Retrospective mining cannot resolve the remaining ambiguity. This protocol therefore freezes an **independent future/manual confirmation** designed so that the conservative hidden-price interval cannot change the predicted fee.

## 2. Confirmatory hypothesis

`H-FEE-001`

For a valid qualifying sale, Torn's current stock-sale fee behaves as:

`fee = ceil(true_unrounded_execution_price × shares × 0.001)`

where the true execution price may have more precision than the two-decimal `data.price` later recorded in log type 5511.

This is a behavioral hypothesis. Passing the protocol does not claim knowledge of Torn's internal source code.

## 3. Competing behavior to distinguish

For the deliberately selected trial geometry below, all economically relevant alternatives left unresolved by historical data predict one dollar less than `H-FEE-001`:

- floor of 0.1% of total value;
- nearest-integer rounding of 0.1% of total value;
- floor gross value to an integer dollar, then apply 0.1% and ceiling;
- half-up gross value to an integer dollar, then apply 0.1% and ceiling;
- half-even gross value to an integer dollar, then apply 0.1% and ceiling.

The historical defensive alternatives that treated logged `price` as total sale value or rounded fee per share first already failed essentially the entire natural sample and are not the primary target of this future experiment.

## 4. Conservative hidden-price envelope — frozen

The diagnostic established that current official `Stock sell` log prices are represented to exactly two decimal places.

Let `p` be the two-decimal price used to plan a trial. To remain robust to both diagnostic precision hypotheses, the true execution price is conservatively allowed anywhere in the union envelope:

`[max(0, p - $0.005), p + $0.01]`

This envelope is intentionally wider/asymmetric than a single standard cent-rounding rule:

- the lower side covers nearest-cent rounding;
- the upper side covers downward truncation to cents;
- boundaries are treated conservatively.

A trial is valid for fee confirmation only if its model prediction remains invariant over this entire interval.

## 5. Qualifying trial geometry

Let:

- `n` = integer shares to sell;
- `G = p × n` = displayed/logged-price gross;
- `K = floor(G / 1000)`;
- `B = 1000 × K`;
- `G_low = max(0, p - 0.005) × n`;
- `G_high = (p + 0.01) × n`.

A planner candidate qualifies only when:

1. `K >= 1`;
2. `G_low > B`;
3. `G_high < B + $0.50`.

The inequalities are strict. A candidate touching either boundary is rejected.

### Consequence

Across every possible true execution price in the conservative envelope:

- unrounded-total fee ceiling predicts `K + 1` dollars;
- fee floor/nearest predicts `K` dollars;
- gross-floor then fee-ceiling predicts `K` dollars;
- gross half-up/half-even then fee-ceiling predicts `K` dollars.

Therefore every valid trial separates the remaining model families by exactly $1 despite hidden sub-cent price uncertainty.

Example only, not a required live price:

- `p = $50.01`;
- `n = 20`;
- displayed gross = `$1,000.20`;
- conservative gross interval = `$1,000.10` to `$1,000.40`;
- `H-FEE-001` predicts fee `$2`;
- competing rounded-gross/non-ceiling behaviors predict `$1`.

## 6. Planner rules

`research/tools/plan_stock_fee_rounding_trial.py` is a pure calculator. It performs no Torn API request and no game action.

Inputs:

- current two-decimal stock price;
- maximum shares;
- maximum displayed gross;
- candidate-result limit.

The planner returns only candidates satisfying the strict geometry above. Lowest displayed gross is preferred.

A planner result is not an instruction to trade. It is an experimental design candidate.

## 7. Human execution only

Every Torn buy or sale must be manually submitted by the human operator on the normal Torn interface.

TornTrading may:

- calculate candidate share counts;
- make read-only official API observations;
- display the planned fee predictions;
- analyze the resulting official log receipt.

TornTrading must never:

- submit a buy or sell;
- click Torn controls;
- synthesize a hidden game request;
- automate transaction timing.

## 8. Required trial controls

A trial becomes a **valid confirmation observation** only if every condition below is satisfied.

### A. Planned before click

Before the human sale:

- the stock is identified;
- `p` is recorded from current Torn price data;
- `n` is selected by the frozen planner;
- boundary multiplier `K` and the two competing fee predictions are recorded;
- the trial is assigned an attempt number before the result is known.

### B. Stable-minute timing

Fee trials deliberately avoid P0-E4 minute-boundary execution ambiguity.

The human should submit the sale comfortably inside a Torn price minute, targeting server second **15 through 40 inclusive**.

Read-only observations must establish that the official stock price immediately before and after the manual sale remained the same two-decimal value `p`.

A trial crossing a price change is invalid for P0-E5 and may instead become evidence for the separate P0-E4 execution-timing study.

### C. Receipt integrity

The resulting official `Stock sell` log 5511 must show:

- sold `amount = n`;
- logged `price = p` exactly at two decimals;
- an integer `fees` value.

If amount or logged price differs, the attempt is invalid for this confirmation.

### D. Isolation

No other stock action may occur between the bracketed pre-trial observation and identification of the corresponding sale log.

If the operator needs to acquire test shares first, that purchase must finish before the trial bracket begins. Buying carries no documented stock tax, but any price movement risk remains the operator's economic cost.

## 9. Sample size and diversification — frozen

Confirmation requires **6 valid trials**.

They must span:

- at least **2 distinct Torn stocks**;
- at least **3 distinct boundary multipliers `K`**;
- no more than **3 valid trials from one stock**.

Maximum attempted manual sales: **10**.

Attempts are classified using only the predeclared validity rules above. Invalid attempts remain in the experiment log with an objective exclusion reason; they are not silently deleted.

If fewer than six valid observations are obtained after ten attempts, the result is `INSUFFICIENT_VALID_TRIALS`, not a pass or rejection.

## 10. Acceptance and rejection rules — frozen

For every valid trial:

- reference prediction = `K + 1`;
- competing prediction = `K`.

### `VALIDATED_FINDING` candidate for P0-E5

P0-E5 may be proposed for closure only if:

1. six valid trials are obtained within ten attempts;
2. diversification requirements are met;
3. all **6/6** valid receipt fees equal `K + 1`;
4. **0/6** valid receipt fees equal `K`;
5. no valid trial has any other unexpected fee;
6. the complete experiment record passes a separate post-evidence project review.

### Reject `H-FEE-001`

If any valid trial records fee `K`, the unrounded-total ceiling hypothesis fails the targeted confirmation and must not be rescued by post-hoc parameter changes.

If any valid trial records neither `K` nor `K + 1`, the frozen candidate family is incomplete for current Torn behavior; P0-E5 remains open and the mechanism must be reinvestigated.

## 11. Attempt record

The private/research attempt record should contain only what is necessary to audit the experiment:

- attempt number;
- stock ID/acronym;
- planned price `p`;
- shares `n`;
- `K`;
- conservative gross interval;
- reference/competing fee predictions;
- pre/post read-only price observations and timestamps;
- human click-time estimate;
- resulting log ID/timestamp/amount/price/fee;
- validity state and exclusion reason if invalid.

Public repository evidence should contain aggregate results only unless the human explicitly approves publishing transaction-level details.

## 12. Relationship to P0-E4

This protocol intentionally avoids minute boundaries and therefore cannot close P0-E4.

After P0-E5 is resolved, P0-E4 still requires repeated human-executed boundary trials comparing:

- visible quote at click;
- pre-boundary official price;
- post-boundary official price;
- resulting official sale receipt.

The two mechanics must not be conflated.

## 13. Gate effect

Until a future targeted experiment satisfies the acceptance rule:

- P0-E5 remains open;
- the 0.1% documented rate may be modeled descriptively, but exact fee rounding cannot be treated as a validated mechanic;
- HYP-001 remains a predictive research hypothesis, not executable alpha;
- production BUY/SELL recommendations remain unauthorized.
