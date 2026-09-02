# TornTrading — Stock Market Mechanics Research

Status: **P0 research pass 2**  
Research date: 2026-09-02  
Questions covered: MEC-001 through MEC-009

## Executive conclusion

The broad Torn stock execution model is documented, and the market-data publication boundary has now also been measured experimentally.

Locked mechanics/findings include: prices move every minute; cache-bypassed official bulk stock data presented a coherent full-market transition across three observed boundaries; official chart minute timestamps map directly to the corresponding new API market state; buying/selling is normally instantaneous; buys have no tax; sells pay 0.1% of gross sale value; generic quantity sales consume newest transactions first; and trading is unavailable while hospitalised, jailed or travelling.

The remaining blockers for an **execution-aware profitability backtest** are transaction semantics rather than historical price alignment: UI/order execution timing, fee rounding, and merged-purchase representation still require controlled user transactions/native-page evidence.

Primary source: https://wiki.torn.com/wiki/Stock_Market  
Patch history: https://wiki.torn.com/wiki/Stock_Market/Patch_History  
Experimental result: `11_PUBLICATION_BOUNDARY_RESULTS.md`

## MEC-001 [P0] — Do all stocks update on the same exact minute boundary?

**Resolution: CLOSED at 2-second API observation resolution**  
**Evidence class: VALIDATED_FINDING**

MEC-X1 observed three consecutive minute boundaries using cache-bypassed `GET /torn/stocks` snapshots, Torn server timestamps, and later official per-stock chart history as the target state.

At the three boundaries, 25, 27 and 24 stocks respectively changed price. For each boundary:

- the final sampled server-second before the boundary showed every changed stock at its previous-minute price;
- the first sampled server-second after the boundary showed every changed stock at its new chart-history price;
- no sampled official response contained a mixed state with some changed stocks old and others new.

First full new-state responses were received at +1.426s, +1.354s and +1.345s relative to the minute boundary. The last pre-boundary responses were around -0.55 to -0.62s.

### Research rule

At the measured 2-second resolution, cache-bypassed bulk `/torn/stocks` may be treated as a coherent market snapshot. Do not claim a sub-second atomic switch; the actual transition occurs somewhere between the last old and first new observations.

The weekly boundary probe remains active and any future mixed response reopens this question.

## MEC-002 [P0] — Authoritative timestamp of a price

**Resolution: CLOSED at API/source-label level; UI/order-execution semantics remain open**  
**Evidence class: VALIDATED_FINDING with scope limitation**

The official v2 stock-history schema provides `price`, `change`, and Unix `timestamp`. MEC-X1 established that the chart row timestamped exactly at `HH:MM:00` corresponds to the complete new minute state seen through the uncached official bulk API on the first observed post-boundary sample.

Independent official/Tornsy reconciliation also found historical rows joining at zero timestamp offset with exact numeric price equality.

### Canonical data rule

For historical/source alignment:

```text
source_timestamp = official chart minute timestamp
source_timestamp_semantics = minute_state_label_verified
```

Tornsy `m1` rows carrying the same timestamp may be joined directly to that Torn minute **as a data label**.

Do not interpret the field as `order_executable_at`. MEC-X1 did not observe the native Torn page or an actual trade submission. UI render/execution timing remains part of P0-E4/P0-E5.

### Tornsy live availability caveat

In the first three-boundary experiment, Tornsy exposed the matching minute later than the first uncached official state: +23.746s, +23.762s and +11.765s after the boundary. Historical Tornsy rows therefore must not be treated as if they were available to a live consumer at `HH:MM:00` merely because their source timestamp has that value.

## MEC-003 [P0] — Buy execution price

**Resolution: PARTIAL — documented behavior, exact edge semantics require test**  
**Evidence class: MECHANIC**

Official stock documentation states buying/selling is instantaneous, except that if a transaction is attempted while prices are updating Torn may take several seconds and ask the user to confirm again with the new share price.

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

API v2 `/user/stocks` returns, for each currently represented stock, a `transactions` array whose records contain transaction ID, shares, price and timestamp.

The schema alone does not prove whether merging preserves all original acquisition transactions, creates/replaces an aggregate transaction, or changes IDs.

### Required experiment

Capture `/user/stocks` before and after merging two controlled purchases and diff the transaction array exactly. Until this is tested, TornTrading must not promise lot-level historical reconstruction after merges.

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

## Locked mechanics/findings for later research

The following may now be treated as `MECHANIC` or scoped `VALIDATED_FINDING` unless new evidence contradicts them:

- price movements occur every minute;
- at 2-second observation resolution, cache-bypassed bulk official publication transitioned coherently across the full market in three tested boundaries;
- official chart minute timestamps label the corresponding new official API minute state;
- Tornsy historical minute timestamps use the same price-state label, but Tornsy live publication may lag the official state materially;
- trades are generally instantaneous;
- updating prices can trigger reconfirmation at a new price;
- no share quantity/ownership limit;
- buy tax = 0;
- sell fee = 0.1% of gross sold value;
- trading unavailable while hospital/jail/travel;
- generic partial sales consume newest acquisition transaction first;
- stock prices are stated by Torn to be based on real-world stocks in corresponding industries.

## Remaining execution experiment pack

Before an execution-aware backtesting engine is approved, complete P0-E4/P0-E5:

1. Compare the actively loaded native stock graph/quote with cache-bypassed API data.
2. Execute at least one controlled buy away from a minute boundary and record quote/submission/API transaction evidence.
3. Observe a boundary/reconfirmation trade if it can be done safely and economically.
4. Execute controlled small sales sufficient to identify fee rounding.
5. Capture `/user/stocks` before/after a quantity partial sale and verify API representation.
6. Capture `/user/stocks` before/after merging purchases.
7. Capture a full exit to determine how the holding disappears from `/user/stocks`.

Raw API responses, screenshots/native-page observations and exact timestamps must be retained as research evidence.

## Decision

**APPROVED for historical market research and minute-level source timestamp alignment.** MEC-001 is validated at 2-second API observation resolution and MEC-002 is validated at the API/source-label level.

**NOT YET APPROVED for execution-aware profitability backtesting.** MEC-003, MEC-004, MEC-006 and MEC-008 still require controlled transaction/native-page evidence, and the validated API timestamp must not be presented as an exact order-execution timestamp.
