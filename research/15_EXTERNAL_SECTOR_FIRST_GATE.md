# TornTrading — External Driver Sector-First Gate

Status: **Stage 0 implementation / awaiting live sector evidence**  
Research date: 2026-09-02

## Decision

The first credentialed external-market screen will test **sector/industry proxies before named companies**.

The frozen v1.0 universe contains:

- 30 unique sector/industry proxy symbols;
- 4 mandatory broad controls: SPY, ACWI, QQQ, IWM;
- 34 total Tiingo EOD requests.

This fits in one conservative Starter-tier run and materially reduces the multiple-testing burden.

## Why this is preferable

Testing every named company immediately would create roughly 148 unique external symbols across the full frozen universe and would require multiple rate-limited batches. More importantly, it would encourage company-story fitting before establishing whether Torn's stated industry relationship is visible at all.

The research funnel is therefore:

```text
Broad market controls
        ↓
Sector / industry proxies
        ↓
Sector evidence review
        ↓
Named-company candidates only for surviving Torn stocks
        ↓
Hourly / session research
        ↓
Minute / information-availability research
```

## Sector-screen implementation

`run_external_sector_screen.py` creates a temporary in-memory/local manifest copy with every `individual_equity_candidates` list removed, then delegates to the already-reviewed transient EOD screening engine.

The temporary manifest contains no licensed market data and is deleted automatically.

The wrapper fails if the frozen sector universe changes from exactly 34 total requested symbols, making an unreviewed candidate-universe expansion visible in CI rather than silently increasing the provider request budget.

Workflow: **External EOD sector screen**.

## Promotion rule to named-company screen

A Torn stock is eligible for named-company follow-up only after review of its sector/proxy results. Promotion is a research decision, not an automatic top-correlation rule.

Evidence considered includes:

- adequate multi-year overlap;
- relationship versus the four broad controls;
- incremental R² over SPY;
- Pearson/Spearman agreement;
- yearly sign/stability;
- raw/adjusted sensitivity;
- behavior across the three descriptive date offsets;
- whether the sector hypothesis itself was high- or low-confidence before screening.

A low or unstable sector relationship may result in:

- `NO_SECTOR_EVIDENCE`;
- a revised industry hypothesis only as a separately versioned post-hoc research branch;
- no named-company screen for that Torn stock.

## Multiple-testing boundary

The 30 proxy set was frozen before any live EOD correlation results were observed.

After the sector artifact exists, adding a new sector proxy is post-hoc and must be labeled/versioned separately. The original proxy results remain reported.

## Credential

The workflow uses the same repository Actions secret as the general EOD screen:

`TIINGO_TOKEN`

No token or raw Tiingo series may be placed in GitHub source, issues, workflow inputs, logs, or chat.

## Approval boundary

Approval authorizes the **one-run sector measurement instrument** only.

EXT-004 remains OPEN until the live aggregate artifact is reviewed. No sector or named-company mapping is validated by this document.
