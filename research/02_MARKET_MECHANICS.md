# TornTrading — Stock Market Mechanics Research

Status: **P0 research pass 1**  
Research date: 2026-09-02  
Questions covered: MEC-001 through MEC-009

## Executive conclusion

The official documentation is strong enough to lock the broad execution model: stock prices move every minute; buying and selling are normally instantaneous; buys have no tax; sells pay 0.1% of gross sale value; there is no share-count limit; trades are unavailable while hospitalized, jailed or traveling; and quantity-based sales remove shares from the newest transaction first (LIFO).

However, several details that matter for a statistically honest backtest are not documented precisely enough: exact minute publication boundary, authoritative price timestamp, fee rounding, whether any sub-cent/rounding behavior exists, and the exact effect of merged purchases on API lot history. These remain explicit controlled experiments and **must not be guessed**.

Primary source: https://wiki.torn.com/wiki/Stock_Market  
Patch history: https://wiki.torn.com/wiki/Stock_Market/Patch_History

## MEC-001 [P0] — Do all stocks update on the same exact minute boundary?

**Resolution: OPEN — controlled observation required**  
**Evidence class: HYPOTHESIS**

Official Torn documentation says price movements occur every minute. It does not state that every stock is calculated/published atomically at the same second.

Tornsy's collector represents stock observations on minute-aligned Unix timestamps, but that only establishes the archive's convention, not Torn's internal calculation boundary.

### Required experiment

Poll `GET /torn/stocks` with service-cache bypass around multiple minute boundaries while also sampling `GET /torn/timestamp`. Record local monotonic clock, Torn server time, response start/end time and every stock price. Test whether first observed changes cluster on one server-second and whether constituents can update on different responses.

Do not exceed a conservative polling rate and run only a short boundary experiment, not continuous high-rate polling.

## MEC-002 [P0] — Authoritative timestamp of a price

**Resolution: OPEN — API history provides timestamps but semantics are undocumented**  
**Evidence class: HYPOTHESIS**

The v2 stock-history schema supplies `price`, `change`, and Unix `timestamp`, but the OpenAPI description does not state whether that timestamp means calculation time, effective/publication time, or chart sample time.

### Required experiment

Compare:

1. first live observation of a new price;
2. Torn server timestamp;
3. timestamp later emitted in the stock's chart history;
4. Tornsy timestamp for the same move.

The canonical research dataset must not treat those fields as equivalent until this is resolved.

## MEC-003 [P0] — Buy execution price

**Resolution: PARTIAL — documented behavior, exact edge semantics require test**  
**Evidence class: MECHANIC**

Official stock documentation states buying/selling is instantaneous, except that if a transaction is attempted while prices are updating Torn may take roughly several seconds and ask the user to confirm again with the new share price.

This establishes that Torn does not guarantee a stale displayed quote through a price update: a changed price can force reconfirmation.

### Backtest rule now

Until measured otherwise, simulated buys must execute at the price observable **after** the assumed human decision delay, never at the signal-generation price if a later price would have become active.

### Still required

A controlled small buy should record displayed quote, submission time, any reconfirmation, transaction API price and timestamp.

## MEC-004 [P0] — Sale gross execution price

**Resolution: PARTIAL — same execution/reconfirmation model as buys**  
**Evidence class: MECHANIC**

Official documentation applies the instantaneous/reconfirmation behavior to both buying and selling and separately defines the 0.1% fee on total value sold.

For research, gross sale value should be modeled from the post-delay Torn execution price, with the fee applied separately.

A controlled sale remains necessary to verify API/UI price identity and rounding.

## MEC-005 [P0] — Spread, limits and other execution friction

**Resolution: PARTIAL**  
**Evidence class: MECHANIC + unresolved rounding detail**

Official documentation states:

- no limit on shares purchased, sold or owned;
- buys have no tax;
- sells have a 0.1% fee;
- trades execute directly through the stock market rather than player-to-player matching.

No official bid/ask spread is documented. There is one displayed market price in the API schema.

### Research policy

Do **not** add an invented spread to the base simulator. Model the documented 0.1% exit fee plus execution delay. Add further friction only if empirical execution tests demonstrate it.

Unknown: currency/share-value rounding at transaction boundaries.

## MEC-006 [P0] — Sale-fee rounding

**Resolution: OPEN — controlled transaction experiment required**  
**Evidence class: HYPOTHESIS**

Official documentation defines the fee as 0.1% of total value sold and gives an exact $1,000 fee on a $1,000,000 sale, but does not specify rounding for values where 0.1% is fractional dollars.

### Required experiment

Execute deliberately small sales (when economically acceptable) that create fractional theoretical fees and compare:

- shares × recorded execution price;
- UI gross proceeds;
- cash received;
- personal-stat `fees` delta;
- theoretical floor/round/ceil outcomes.

Never infer the rule from large transactions where all methods coincide.

## MEC-007 [P0] — Price changes during submission

**Resolution: CLOSED at mechanic level**  
**Evidence class: MECHANIC**

Official Torn documentation explicitly states that when prices are updating, a transaction may pause and ask the user to confirm again with the new share price.

Therefore signal and execution prices can differ. This is a mandatory property of the backtest model.

### Consequence

Every strategy must be evaluated under multiple human-delay assumptions rather than assuming zero-latency execution.

## MEC-008 [P0] — Merged purchases and reconstructing original lots

**Resolution: OPEN/PARTIAL**  
**Evidence class: MECHANIC + schema observation**

Official documentation says purchases can be merged into one position and that displayed bought price, bought date, profit and change are averaged.

API v2 `/user/stocks` returns, for each currently represented stock, a `transactions` array whose records contain:

- transaction ID;
- shares;
- price;
- timestamp.

The schema alone does not prove whether merging preserves all original acquisition transactions, creates/replaces an aggregate transaction, or changes IDs.

### Required experiment

Capture `/user/stocks` before and after merging two controlled purchases and diff the transaction array exactly. Until this is tested, TornTrading must not promise tax-lot/lot-level historical reconstruction after merges.

## MEC-009 [P0] — Partial-sale lot attribution / cost basis

**Resolution: CLOSED for quantity sales**  
**Evidence class: MECHANIC**

Torn's official patch history states that on 2021-06-22 stock-market sells were changed to remove shares from the **newest transaction rather than the oldest**.

That is LIFO attribution for quantity-based position reductions.

The stock page also permits selling an individual purchase directly, which is a separate explicit-lot action.

### Simulator requirement

- Generic sale of N shares: consume acquisition lots newest-first.
- Explicit sale of a selected purchase: consume that selected lot.
- Merged-position behavior must follow the result of MEC-008 rather than an assumption.

## Locked mechanics for later research

The following may now be treated as `MECHANIC` unless Torn changes them:

- price movements occur every minute;
- trades are generally instantaneous;
- updating prices can trigger reconfirmation at a new price;
- no share quantity/ownership limit;
- buy tax = 0;
- sell fee = 0.1% of gross sold value;
- trading unavailable while hospital/jail/travel;
- generic partial sales consume newest acquisition transaction first;
- stock prices are stated by Torn to be based on real-world stocks in corresponding industries.

## Blocking experiment pack

Before the backtesting engine is approved, run **MEC-X1 Execution Boundary Experiment**:

1. Observe 20+ price-change boundaries with synchronized Torn server timestamps.
2. Determine whether all stocks change atomically.
3. Map chart-history timestamp to first observable live price.
4. Execute at least one controlled buy away from boundary and one near boundary.
5. Execute controlled small sales sufficient to identify fee rounding.
6. Capture `/user/stocks` before/after a partial LIFO sale.
7. Capture `/user/stocks` before/after merging purchases.

Raw responses/screenshots and exact timestamps must be retained as research evidence.

## Decision

**PARTIALLY APPROVED.** Enough mechanics are known to design the collector and data model. The execution/backtesting engine is **not yet approved** until MEC-001, MEC-002, MEC-006 and MEC-008 are experimentally resolved, and MEC-003/004 are cross-checked with at least one controlled transaction.
