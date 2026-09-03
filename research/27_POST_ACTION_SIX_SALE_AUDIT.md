# TornTrading — Post-Action Audit of Six New Stock Sales

Status: **FROZEN POST-ACTION OBSERVATIONAL AUDIT — not confirmatory**  
Audit design date: 2026-09-03  
Trigger: human operator reported having bought and sold six different Torn stocks after the P0-E5 targeted protocol was merged.  
Primary questions: MEC-004, MEC-006, P0-E5 evidence quality  

## 1. Epistemic boundary

The six transactions already exist. This audit is therefore not a preregistration of those actions.

The P0-E5 targeted confirmation in `research/25_FEE_ROUNDING_TARGETED_CONFIRMATION.md` requires, before each human sale, a recorded planner-selected stock/price/share count, boundary multiplier K, competing predictions, and attempt number. That pre-click record does not exist in the project record for these six transactions.

Consequently, **these six sales cannot by themselves satisfy the frozen confirmatory acceptance rule**, even if their receipts happen to match H-FEE-001.

The audit may still provide useful prospective-era observational evidence, determine whether the trades accidentally fall into the frozen discriminating geometry, and identify what remains necessary for a valid confirmation.

## 2. Source and selection — frozen before reading the six receipts

Source: official Torn API v2 `GET /user/log`, log type **5511 — Stock sell**.

Protocol-merge timestamp: `1788415072` (2026-09-03T05:57:52Z), corresponding to merge commit `94370c891cb6decb4eb4c21ebf2705527ddd9e33`.

At audit run time:

1. obtain the current official Torn server timestamp;
2. request Stock sell logs from the protocol-merge timestamp through that server timestamp, limit 100;
3. parse only current v2 Stock sell records with usable timestamp, stock ID, amount, price, and integer fee;
4. sort by event timestamp descending;
5. select the **six most recent** usable Stock sell records.

If fewer than six usable post-protocol sales exist, report `INSUFFICIENT_POST_PROTOCOL_SALES`.

The audit does not search for a favorable subset. Exactly the latest six post-protocol sales are the target.

## 3. Frozen calculations

For each selected sale, transiently compute:

- `p` = logged execution price;
- `n` = sold shares;
- `G = p × n`;
- `K = floor(G / 1000)`;
- conservative true-price interval `[max(0, p - 0.005), p + 0.01]` when `p` has exactly two decimal places;
- `G_low` and `G_high` from that interval;
- frozen targeted-geometry qualification: `K >= 1`, `G_low > 1000K`, and `G_high < 1000K + 0.50`;
- H-FEE-001 prediction `K + 1` for qualifying geometry;
- competing prediction `K` for qualifying geometry;
- simple logged-price ceiling prediction `ceil(p × n × 0.001)` for every sale;
- event second `timestamp mod 60` and whether it falls in the targeted stable-minute range 15–40 inclusive.

No formula is tuned after seeing the receipts.

## 4. Aggregate outputs allowed

The persisted report may include only:

- number of selected sales;
- number of distinct stocks;
- count inside/outside server-second range 15–40;
- count with exactly two logged price decimals;
- count qualifying the frozen targeted geometry;
- number of distinct K values among geometry-qualifying sales;
- among geometry-qualifying sales: count supporting `K+1`, supporting `K`, or another fee;
- count matching the simple logged-price total-value ceiling formula across all six;
- aggregate model-fit counts for the unchanged frozen 25-model family;
- a deterministic audit conclusion label;
- explicit statement that pre-click planning was not recorded and confirmatory eligibility is false.

## 5. Forbidden persisted fields

The artifact must not persist:

- event IDs;
- exact timestamps or dates of individual trades;
- stock IDs/acronyms;
- share counts;
- prices;
- observed fees;
- profits/losses;
- gross values;
- K values per transaction;
- per-trade classifications or predictions;
- raw API payloads.

These may exist transiently in memory only as required for the aggregate audit.

## 6. Conclusion labels

The audit may emit:

- `INSUFFICIENT_POST_PROTOCOL_SALES`
- `SIX_SALES_OBSERVED_NONE_TARGET_GEOMETRY`
- `POST_ACTION_GEOMETRY_SUPPORTS_CEILING`
- `POST_ACTION_GEOMETRY_SUPPORTS_COMPETITOR`
- `POST_ACTION_GEOMETRY_MIXED_OR_UNEXPECTED`

All labels are `OBSERVATION`, not `VALIDATED_FINDING`.

## 7. Confirmatory consequence

`confirmatory_eligible` is frozen to `false` for this six-sale audit because required pre-click planner/prediction records are absent from the project record.

The data may reduce uncertainty, but P0-E5 can close only through a subsequent execution that follows `research/25_FEE_ROUNDING_TARGETED_CONFIRMATION.md` from before each click through receipt capture.

## 8. Compliance

This audit is read-only. It submits no Torn game action and must not encourage automation of transaction execution.