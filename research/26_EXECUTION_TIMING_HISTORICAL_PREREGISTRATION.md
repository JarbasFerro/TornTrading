# TornTrading — P0-E4 Historical Execution-Timing Diagnostic Preregistration

Status: **PREREGISTERED DIAGNOSTIC — not confirmatory**  
Preregistration date: 2026-09-03  
Primary questions: MEC-003, MEC-007, VAL-002  
Evidence target: P0-E4 sale execution-price timing  
Instrument: `research/tools/diagnose_stock_sell_execution_timing.py`

## 1. Purpose

P0-E4 asks which stock quote actually wins when a human-submitted Torn stock sale occurs near a one-minute price transition.

A definitive answer requires the visible quote at human click time plus precise click timing. Historical official sale logs do not contain those two facts, so this study **cannot close P0-E4**.

However, the existing official `Stock sell` history contains:

- official event timestamp;
- stock ID;
- logged execution price.

Tornsy minute history has already been independently reconciled against official Torn minute history with exact timestamp/price agreement over the tested official overlap. Therefore a privacy-safe historical diagnostic can ask whether any official sale receipt timestamped just after a changed minute boundary still carries the previous minute's market price.

That observation would materially narrow the future manual experiment.

## 2. Frozen source scope

Private source:

- official Torn API v2 `GET /user/log`;
- log type **5511 — Stock sell** only;
- fixed 365-day lookback ending at current official Torn server timestamp;
- maximum 100 returned sale logs, matching the already observed available one-year history.

Public market source:

- Tornsy `m1` endpoint;
- for each usable sale, request only the previous/current/next minute neighborhood around the official event timestamp;
- Tornsy is treated as a reconciled secondary historical source, not canonical truth.

Public official stock metadata is used only to map Torn stock ID to current acronym for the Tornsy request.

## 3. Private fields used transiently

From each official sell log the diagnostic may use only:

- event timestamp;
- `data.stock`;
- `data.price`.

It does not need amount, fee, profit, account totals, holdings, or transaction economics.

No event timestamp, stock ID/acronym, or price may appear in the persisted artifact.

## 4. Minute alignment — frozen

For official event timestamp `t`:

- `minute = floor(t / 60) × 60`;
- `previous = minute - 60`;
- `current = minute`;
- `next = minute + 60`.

The logged receipt price is compared at cent precision with Tornsy's price at those three exact minute timestamps.

No nearest-timestamp substitution or forward fill is allowed.

If a required Tornsy row is missing, the observation is classified as source-incomplete rather than imputed.

## 5. Event-second buckets — frozen

Only coarse second-of-minute bins may be persisted:

- `S00_02`: event seconds 0–2;
- `S03_09`: 3–9;
- `S10_49`: 10–49;
- `S50_59`: 50–59.

Exact event seconds are private transient data and are not persisted.

The `S00_02` bin is the primary timing clue because an official receipt recorded in the first three seconds after a changed boundary is closest to the execution transition.

## 6. Frozen match classifications

For each source-complete observation, calculate the set of minute prices equal to the logged receipt price:

- `PREVIOUS`
- `CURRENT`
- `NEXT`

Persist only aggregate match-pattern counts, using labels such as:

- `CURRENT_ONLY`
- `PREVIOUS_ONLY`
- `NEXT_ONLY`
- `PREVIOUS_CURRENT`
- `CURRENT_NEXT`
- `PREVIOUS_CURRENT_NEXT`
- `NONE`

A flat market minute can naturally produce multi-label matches and is not evidence about execution timing.

## 7. Changed-boundary diagnostic

A sale is a **changed-boundary observation** when both previous and current Tornsy rows exist and their prices differ.

For changed-boundary observations, previous/current receipt matches are unambiguous at minute resolution.

Publish, per coarse second bin, aggregate counts of:

- observations;
- source-complete observations;
- changed-boundary observations;
- `CURRENT_ONLY` matches among changed boundaries;
- `PREVIOUS_ONLY` matches among changed boundaries;
- other/none matches among changed boundaries.

## 8. Primary diagnostic clue — frozen

For `S00_02` changed-boundary observations:

### If at least one `PREVIOUS_ONLY` receipt exists

Diagnostic label:

`PREVIOUS_MINUTE_RECEIPT_OBSERVED_IN_EARLY_POST_BOUNDARY_LOG_TIME`

Interpretation:

An official sale event timestamped in the first three seconds of a new changed minute can carry the previous minute's price. This would be consistent with click/request-time price capture or with event/log timestamping after an earlier execution decision.

It would **not** by itself prove the page-visible quote won, because historical click time/display data are absent.

### If changed-boundary early observations exist but all are `CURRENT_ONLY`

Diagnostic label:

`EARLY_CHANGED_BOUNDARY_RECEIPTS_ALL_MATCH_CURRENT_MINUTE`

Interpretation:

Historical early-minute receipts are consistent with current-minute/server-state execution, but remain non-confirmatory because the human may simply have clicked after the boundary.

### If no usable changed-boundary observations exist in S00_02

Diagnostic label:

`NO_INFORMATIVE_EARLY_BOUNDARY_HISTORY`

Interpretation:

Historical logs cannot narrow P0-E4; proceed directly to the controlled human experiment.

## 9. Privacy contract

Persisted output may contain only:

- retrieval date/time;
- source names;
- aggregate sample/error counts;
- coarse second-bin labels;
- aggregate match-pattern counts;
- aggregate changed-boundary counts;
- the diagnostic label and interpretation.

It must not contain:

- raw Torn logs;
- event IDs;
- exact event timestamps/dates;
- exact second-of-minute values;
- stock IDs/acronyms;
- prices;
- share amounts;
- fees/profits/losses;
- per-event classifications or predictions.

## 10. Claim boundary

This study is `OBSERVATION` / diagnostic only.

It cannot promote any click-time or server-processing-time rule to `VALIDATED_FINDING` because it lacks the historical human click timestamp and page-visible quote.

Any historical clue must be used only to improve the later preregistered human boundary protocol.

## 11. Compliance

The diagnostic uses read-only Torn API calls and public Tornsy data. It performs no Torn game action and makes no non-API Torn request.
