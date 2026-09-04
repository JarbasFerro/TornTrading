# TornTrading — TSB Named-Equity Follow-up Results

Status: **Stage 0 named-equity follow-up complete / no stable named mapping**  
Review date: 2026-09-04  
Source workflow: `External EOD TSB named follow-up`, run `33864298709`  
Source artifact: `external-eod-tsb-named-followup-33864298709`  
Artifact digest: `sha256:cf121ca9399e2aaab5be24edc20bc07366416530dd42d1f0ce1360612b6d7f60`  
Questions advanced: EXT-002, EXT-004, EXT-009, EXT-010

## Executive decision

The frozen TSB named-equity follow-up completed successfully:

- 10/10 requested external symbols succeeded;
- no provider errors were recorded;
- the requested universe was exactly `SPY`, `ACWI`, `QQQ`, `IWM`, `XLF`, `KBE`, `HSBC`, `JPM`, `BAC`, `C`;
- raw external price series were not persisted;
- 876 aggregate statistic rows were produced across raw/adjusted prices and -1/0/+1 civil-date alignments.

**Decision: `NO_STABLE_NAMED_MAPPING_V1`.**

None of the four preregistered bank equities provides a relationship that is materially stronger and more stable than the broad controls or the retained KBE sector proxy.

The candidate universe will **not** be expanded after seeing these results.

## Primary adjusted / same-date comparison

| External series | Role | Pearson | Spearman | R² | Incremental R² over SPY | Positive years |
|---|---|---:|---:|---:|---:|---:|
| IWM | broad control | +0.0621 | +0.0641 | 0.386% | +0.260% | 5/6 |
| QQQ | broad control | +0.0617 | +0.0602 | 0.381% | +0.500% | 5/6 |
| KBE | sector proxy | +0.0616 | +0.0644 | 0.379% | +0.209% | 6/6 |
| BAC | named equity | +0.0554 | +0.0579 | 0.307% | +0.145% | 5/6 |
| ACWI | broad control | +0.0487 | +0.0470 | 0.238% | +0.130% | 5/6 |
| C | named equity | +0.0372 | +0.0468 | 0.138% | +0.020% | 5/6 |
| XLF | sector proxy | +0.0334 | +0.0474 | 0.111% | ~0.000% | 4/6 |
| JPM | named equity | +0.0302 | +0.0391 | 0.091% | +0.004% | 4/6 |
| HSBC | named equity | +0.0206 | +0.0347 | 0.042% | ~0.000% | 3/6 |
| SPY | broad control | +0.0413 | +0.0461 | 0.170% | baseline | 5/6 |

Two broad controls, QQQ and IWM, have slightly higher primary full-period correlation/R² than KBE and all four named banks. BAC is the strongest named bank but remains weaker than QQQ/IWM and KBE.

## Stability and alignment review

No named candidate clears the qualitative promotion standard frozen before the run.

### BAC

BAC is the strongest named candidate at the primary alignment:

- adjusted offset 0 Pearson +0.0554 / Spearman +0.0579;
- 5/6 yearly Pearson signs positive;
- raw results are essentially unchanged.

However:

- its primary R² is only 0.307%;
- its incremental R² over SPY is only +0.145 pp;
- it is still weaker than QQQ/IWM and KBE;
- yearly Pearson includes a negative year;
- adjacent-date results do not establish a unique alignment.

This is insufficient to call BAC a stable TSB mapping.

### JPM and C

JPM and C show somewhat larger Pearson correlations at external date offset -1, but Pearson/Spearman agreement weakens and the incremental explanatory contribution over SPY remains very small. The apparent improvement at one descriptive civil-date alignment is not evidence of a causal lead.

### HSBC

The name resemblance between Torn & Shanghai Banking and HSBC was a legitimate pre-data candidate, but the empirical result is weak. HSBC adds essentially zero incremental R² over SPY at the primary alignment and has only 3/6 positive yearly correlations there.

The naming resemblance is therefore not promoted into a market-mechanics claim.

## EXT interpretation

The v1 sector-first EOD funnel has now produced a legitimate null result:

1. the 35-stock sector screen found generally tiny sector relationships and promoted only TSB;
2. the frozen TSB named follow-up found no named bank stronger or more stable than broad controls;
3. no new ticker will be added post hoc.

For the frozen v1 daily EOD universe, there is **no validated stock-specific external mapping** suitable for residualizing Torn returns or for building a trading signal.

This does not contradict Torn's statement that prices are based on real-world stocks in corresponding industries. The relationship may be transformed, noisy, intraday/session-dependent, based on a basket not represented by our candidates, or otherwise not recoverable from simple civil-date EOD return correlation.

## HYP-001 consequence

HYP-001 should **not** be residualized against an arbitrarily selected external company merely to satisfy the external-driver sensitivity note.

The correct v1 conclusion is that no stock-specific external control has earned inclusion. Prospective HYP-001 evidence collection may continue under its frozen rule without inserting a post-hoc external ticker.

This result does **not** itself validate HYP-001, does not close the prospective 26-cohort/70-signal requirement, and does not establish executable alpha.

## Next EXT boundary

The next external-driver question, if pursued, must be a separately preregistered intraday/session experiment addressing EXT-005 through EXT-008. It must not reuse the failed EOD candidate screen as permission to search an unlimited new ticker universe.

Given the weak EOD effect sizes, purchasing broad minute-level historical coverage is not justified yet. Any intraday work should begin with the smallest defensible universe and an explicit information-availability model.

## Gate status

- EXT-004 v1 daily candidate comparison: **COMPLETE — weak/null mapping result**.
- TSB named-equity follow-up: **COMPLETE — `NO_STABLE_NAMED_MAPPING_V1`**.
- Stock-specific external residual control for HYP-001: **NONE JUSTIFIED BY V1 EOD EVIDENCE**.
- EXT-005 through EXT-008 intraday/session mechanics: **OPEN / separate future experiment**.
