# TornTrading — P0-E5 Post-Confirmation Fee-Rounding Diagnostic Preregistration

Status: **PREREGISTERED DIAGNOSTIC — not confirmatory**  
Preregistration date: 2026-09-03  
Triggering result: first confirmatory fee-rounding run `33718838875` returned `NO_PERFECT_MODEL`  
Instrument: `research/tools/diagnose_stock_sell_fee_rounding.py`

## 1. Why this diagnostic exists

The first preregistered P0-E5 analysis was executed only after its model family and acceptance rule were frozen. It returned:

- 100 usable recent `Stock sell` observations;
- 0 rejected observations;
- 25 frozen candidate models;
- no perfect model;
- four ceiling-like models at 99/100;
- nearest-integer models around 56/100;
- floor-like models around 4/100;
- falsification models around 0–1/100.

The correct confirmatory decision was therefore **failure to close P0-E5**.

This second instrument was designed *after seeing that result*. It is exploratory/diagnostic by construction. Its purpose is to characterize the one-observation anomaly and determine whether more no-cost historical information can narrow the next experiment.

It cannot retroactively turn the failed first test into a successful confirmation.

## 2. Questions

The diagnostic asks:

1. Is the 99/100 ceiling-like fit stable across the rest of the available recent one-year sell history?
2. Are ceiling-reference mismatches rare or recurrent?
3. Do mismatches cluster toward older or newer portions of the sample?
4. Are mismatch residuals predominantly one dollar, larger, positive, or negative?
5. Does expanded natural history distinguish gross-rounding order among the unchanged 25 candidate models?
6. Are ceiling mismatches *compatible* with the hypothesis that the logged `price` is a rounded or truncated representation of a higher-precision execution value?

Compatibility with a precision interval is not proof that Torn uses hidden precision.

## 3. Frozen source and scope

Source remains official Torn API v2 `GET /user/log` filtered to log type **5511 — Stock sell**.

Window:

- end: official Torn server timestamp obtained at run start;
- start: exactly 365 days earlier;
- sort: descending timestamp;
- page size: 100;
- maximum pages: 10;
- maximum unique usable rows: 1,000.

The instrument follows only Torn-provided `_metadata.links.next` pagination.

It refuses a pagination link if it:

- uses a non-HTTPS absolute URL;
- points to a host other than `api.torn.com`;
- changes the `/user/log` endpoint;
- changes log type away from 5511;
- moves `from` or `to` outside the frozen one-year window;
- requests more than 100 rows;
- changes sort away from `DESC`.

Unknown query parameters are ignored rather than forwarded. In particular, credentials/tokens embedded in a link cannot be propagated by the diagnostic.

Event IDs are used transiently only to deduplicate overlapping pagination boundaries. Event timestamps are used transiently only for chronological rank quartiles. Neither is persisted.

## 4. Unchanged fee-model family

The diagnostic reuses the **same 25 behaviorally non-redundant models** frozen before the first private-value run in `research/21_FEE_ROUNDING_PREREGISTRATION.md`.

No fee formula, rounding operator, or model parameter is added or tuned after viewing the first result.

The expanded-history model table is descriptive only:

- aggregate matches;
- aggregate mismatches;
- aggregate match rate;
- prediction-equivalence classes by model name;
- perfect-model names if any;
- global discrimination count;
- winner nearest-competitor separation if there happens to be a unique perfect model.

Because this expanded sample overlaps the original 100 observations and was chosen after the failed result, even a perfect model in the expanded diagnostic would **not** satisfy the original confirmation gate by itself.

## 5. Frozen reference diagnostic

The reference formula is fixed as:

`total_value__fee_ceiling`

This is chosen because it was one of four prediction-equivalent models with the best first-run fit (99/100) and is the simplest expression consistent with Torn's published wording that the fee is 0.1% of total value sold.

For this reference only, publish aggregate:

- matches and mismatches;
- match rate;
- residual direction counts, where residual = observed fee − predicted fee;
- absolute mismatch buckets: exactly 1, 2–5, and 6+;
- mismatch counts in four chronological rank quartiles;
- compatibility counts for two predeclared logged-price precision intervals.

No per-trade residual is persisted.

## 6. Logged-price precision hypotheses

Let:

- `p` = logged decimal price;
- `q` = quantum of its last displayed/logged decimal place, preserving trailing zeros;
- `n` = share amount;
- reference fee at a hypothetical true price `z` = `ceil(z × n × 0.001)`.

Two exploratory hypotheses are frozen:

### H-precision-A — nearest-rounded logged price

Possible true price interval is conservatively treated as:

`[max(0, p − q/2), p + q/2]`

The upper boundary is intentionally included. Real nearest-rounding intervals would normally be half-open depending on tie convention; inclusion makes this only a **conservative compatibility test**, never proof.

### H-precision-B — downward-truncated logged price

Possible true price interval is conservatively treated as:

`[p, p + q]`

Again the upper boundary is intentionally included as a conservative compatibility envelope.

A mismatch is called compatible with an interval only if its observed integer fee lies between the minimum and maximum ceiling fee attainable somewhere in that interval.

This tests whether unlogged sub-last-decimal precision *could* explain the discrepancy. It does not establish that Torn actually uses either rounding mechanism.

## 7. Chronological diagnostic

The diagnostic sorts usable observations by private event timestamp only in memory and assigns them by rank to four bins:

- `Q1_oldest`
- `Q2`
- `Q3`
- `Q4_newest`

Only observation counts and ceiling-reference mismatch counts per quartile may be persisted.

No timestamp, date, month, week, or exact regime boundary may appear in the artifact.

A concentration in one quartile is a structural-break clue, not a validated regime change.

## 8. Logged-price format diagnostic

The artifact may publish aggregate counts by number of decimal places in the logged `price` string/Decimal representation.

It may not publish any actual price, monetary summary, price range, min/max, quantile, or stock-specific breakdown.

The purpose is only to interpret how wide the predeclared precision intervals are.

## 9. Privacy contract

Persisted diagnostic evidence may contain only aggregate counts/rates and model names.

It must not contain:

- raw Torn logs or API payloads;
- event or transaction IDs;
- event timestamps or exact dates;
- stock IDs/acronyms;
- share amounts;
- observed prices;
- observed fees;
- profits/losses;
- monetary totals, averages, ranges, minima, maxima, quantiles, or distributions of transaction values;
- per-trade predictions/residuals;
- per-stock or per-event diagnostics.

The workflow must validate the safe-report schema before uploading the artifact.

## 10. Diagnostic conclusion labels

The tool may emit one of the following descriptive conclusions:

- `NO_USABLE_OBSERVATIONS`
- `EXPANDED_HISTORY_HAS_UNIQUE_PERFECT_MODEL`
- `CEILING_REFERENCE_PERFECT_BUT_MODEL_ORDER_UNRESOLVED`
- `ALL_CEILING_MISMATCHES_COMPATIBLE_WITH_LOGGED_PRICE_PRECISION_HYPOTHESES`
- `CEILING_MISMATCHES_NOT_FULLY_EXPLAINED_BY_TESTED_PRICE_PRECISION_HYPOTHESES`

These labels are **diagnostic descriptions only**. None closes P0-E5 automatically.

## 11. Decision rules after the diagnostic

P0-E5 remains open after this diagnostic unless a later, separately preregistered confirmatory design validates the relevant mechanic.

The diagnostic determines the next path:

### Path A — ceiling behavior nearly exact and every mismatch precision-compatible

Interpretation: hidden execution-price precision becomes a plausible explanation.

Next action: design a confirmatory protocol that can observe enough execution-price precision or deliberately choose sales where plausible hidden precision cannot change the predicted fee.

### Path B — ceiling mismatches recurrent but very small and not fully precision-compatible

Interpretation: there is an additional execution/logging mechanic or regime effect.

Next action: design targeted manual human-executed micro-trades plus bracketed read-only observations.

### Path C — mismatches cluster chronologically

Interpretation: possible structural break.

Next action: preregister a change-point/regime comparison using only coarse/approved aggregate evidence or a private reproducible analysis whose public output does not disclose user trades.

### Path D — expanded history naturally distinguishes ceiling gross-rounding order

Interpretation: useful diagnostic narrowing, but still post-hoc.

Next action: freeze the narrowed formula in a new confirmatory test on future/manual observations rather than declaring it validated from overlapping history.

## 12. P0-E4 remains independent

This diagnostic cannot answer which quote is selected when a human clicks near a minute transition.

P0-E4 still requires a human-executed boundary experiment with:

- visible pre-click quote;
- precise human click timing;
- official read-only price observations before/after the boundary;
- authoritative sale-log receipt after the click.

TornTrading must never submit the game transaction itself.
