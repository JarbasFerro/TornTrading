# TornTrading — P0-E4 Historical Execution-Timing Result and Modeling Decision

Status: **DECISION-SUFFICIENT FOR HOURLY/DAILY RESEARCH; MINUTE-SCALE PRODUCTION STILL GATED**  
Decision date: 2026-09-04  
Primary mechanic: stock-sale execution-price timing around minute transitions

## Result

The preregistered historical diagnostic compared 100 official Torn `Stock sell` receipts with reconciled Tornsy one-minute prices at the exact previous, current and next minute timestamps around each official sale-log event.

Source quality was complete:

- 100 official sale receipts analyzed;
- 100 usable sales;
- 0 rejected sales;
- 99 Tornsy neighborhood requests after cache reuse;
- 0 Tornsy request errors;
- 0 source-incomplete observations;
- 0 unknown stock mappings.

Across all event-second buckets there were **75 changed-boundary observations** where previous-minute and current-minute prices differed.

Observed changed-boundary behavior:

- `PREVIOUS_ONLY`: **0 / 75**;
- no historical receipt at a changed boundary required a stale previous-minute-only execution price explanation.

The first-three-second bucket (`S00_02`) contained 2 changed-boundary observations:

- 1 `CURRENT_ONLY`;
- 0 `PREVIOUS_ONLY`;
- 1 other/multi-minute pattern.

The preregistered diagnostic label was therefore `NO_INFORMATIVE_EARLY_BOUNDARY_HISTORY`: the history cannot prove the exact human click-time rule because click timestamps and page-visible quotes were not recorded historically.

## Modeling decision

For TornTrading's **hourly and daily research**, P0-E4 is considered decision-sufficient without another manual boundary experiment.

The project will use the following execution contract:

1. Never assume a fill at a stale previous-minute price after the server has transitioned to a new minute.
2. A signal observed in minute `t` may be modeled no earlier than the contemporaneous/current server-minute price.
3. Every execution-aware backtest must include at least a `+1 minute` latency sensitivity case.
4. For conservative profitability claims, the less favorable of current-minute and +1-minute execution assumptions should be reported where both are available.
5. Sale transaction cost uses the separately accepted ceiling-like 0.1% fee rule.

This contract is intentionally conservative relative to the historical observation and is sufficient for research at horizons where a one-minute execution difference is small relative to the holding period.

## Remaining boundary

This decision does **not** establish the exact click-time/server-processing mechanic as a universal `VALIDATED_FINDING`.

Any strategy whose expected edge materially depends on sub-minute or one-minute execution timing remains blocked from production until a dedicated controlled execution experiment is completed.

Therefore:

- hourly/daily execution-aware research: **AUTHORIZED**;
- multi-day HYP-001 research: **AUTHORIZED subject to its prospective validation rules**;
- minute-scale executable alpha/profit claims: **STILL GATED**;
- autonomous Torn trading: **PROHIBITED**.

## Rationale for stopping here

The historical evidence materially constrains the downside risk that mattered for longer-horizon backtests: there were zero stale previous-minute-only receipts across 75 changed boundaries. A further manual boundary experiment would mainly refine a mechanism detail that is not currently decision-relevant for hourly/daily research.

The project should therefore spend its next research cycles on external-driver mapping, predictive validation and portfolio economics rather than further execution-mechanic archaeology.
