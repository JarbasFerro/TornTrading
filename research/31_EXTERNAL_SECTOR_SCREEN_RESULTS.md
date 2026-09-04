# TornTrading — External Sector Screen Results and Named-Equity Promotion

Status: **Stage 0 sector evidence reviewed / TSB named-equity follow-up authorized**  
Review date: 2026-09-04  
Source workflow: `External EOD sector screen`, run `33839002109`  
Source artifact: `external-eod-sector-screen-33839002109`  
Artifact digest: `sha256:d529821406b15cac37c223e62f27f19801c4c1558e9ad21a9cb9110d64c08745`  
Questions advanced: EXT-004, EXT-009, EXT-010

## Executive decision

The first credentialed sector-first external-driver screen completed successfully:

- 34/34 external symbols were retrieved;
- 35 Torn stocks were evaluated;
- coverage spans the Stocks 3.0 period from 2021-04-06 through 2026-09-03;
- no provider errors were recorded;
- raw external price series were not persisted;
- 1,230 aggregate candidate-statistic rows were produced across raw/adjusted variants and -1/0/+1 civil-date alignments.

The dominant result is **weak sector-level explanatory power**. At the primary adjusted / same-date alignment, the largest absolute Pearson correlation among sector candidates is only about 0.069 and the largest univariate R² is about 0.47%.

This is useful negative evidence. It does not support broad promotion of sector hypotheses to company-level testing.

Exactly one Torn stock is promoted to the already-frozen named-equity candidate stage:

**TSB — Torn & Shanghai Banking**

TSB's KBE same-date relationship is modest, but it is the cleanest sector result when the preregistered review dimensions are considered together:

- Pearson: +0.0616;
- Spearman: +0.0644;
- univariate R²: 0.379%;
- incremental R² over SPY: +0.209 percentage points;
- yearly Pearson sign: positive in 6/6 eligible years;
- raw-price sensitivity is effectively unchanged (Pearson +0.0648; incremental R² +0.256 pp);
- the banking classification was HIGH-confidence before the screen.

This is **candidate-reduction evidence only**. It does not validate KBE, XLF, HSBC, or any other real-world series as Torn's actual driver.

All other Torn stocks receive `NO_NAMED_PROMOTION_V1` from this sector-first screen.

## Review method

The sector gate intentionally did not preregister a mechanical numeric cutoff. The post-evidence decision therefore follows the qualitative dimensions frozen in `15_EXTERNAL_SECTOR_FIRST_GATE.md` rather than inventing a new significance threshold after seeing results.

For each Torn stock, the table below reports the sector proxy with the largest primary (`adjusted`, offset `0`) incremental R² over SPY. The decision also considers:

- multi-year overlap;
- comparison with broad controls;
- Pearson/Spearman agreement;
- year-by-year sign stability;
- raw/adjusted agreement;
- behavior across the three descriptive date offsets;
- the prior classification confidence recorded before the live screen.

## Primary sector summary

| Torn | Best primary proxy | Pearson | Spearman | R² | Incremental R² over SPY | Positive years | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| ASS | PBJ | -0.0579 | -0.0540 | 0.335% | 0.246% | 1/6 | NO_PROMOTION |
| BAG | ITA | -0.0372 | -0.0328 | 0.138% | 0.071% | 1/6 | NO_PROMOTION |
| CBD | MJ | -0.0532 | -0.0309 | 0.283% | 0.345% | 1/5 | NO_PROMOTION |
| CNC | XLE | +0.0147 | +0.0079 | 0.022% | 0.019% | 3/6 | NO_PROMOTION |
| ELT | ITB | +0.0582 | +0.0067 | 0.339% | 0.455% | 3/6 | NO_PROMOTION |
| EVL | PBJ | -0.0607 | -0.0472 | 0.368% | 0.341% | 0/6 | NO_PROMOTION |
| EWM | XLI | -0.0167 | -0.0066 | 0.028% | 0.170% | 1/6 | NO_PROMOTION |
| FHG | BJK | -0.0522 | -0.0543 | 0.273% | 0.139% | 2/6 | NO_PROMOTION |
| GRN | MOO | -0.0166 | -0.0034 | 0.027% | 0.048% | 2/6 | NO_PROMOTION |
| HRG | ITB | +0.0349 | +0.0083 | 0.122% | 0.043% | 4/6 | NO_PROMOTION |
| IIL | XLK | -0.0418 | -0.0229 | 0.174% | 0.053% | 1/6 | NO_PROMOTION |
| IOU | XLF | +0.0309 | +0.0190 | 0.096% | 0.003% | 3/6 | NO_PROMOTION |
| IST | XLY | -0.0099 | -0.0181 | 0.010% | 0.037% | 4/6 | NO_PROMOTION |
| LAG | XLI | -0.0201 | -0.0197 | 0.040% | 0.169% | 3/6 | NO_PROMOTION |
| LOS | XLI | +0.0153 | +0.0268 | 0.023% | 0.101% | 3/5 | NO_PROMOTION |
| LSC | XLY | +0.0091 | -0.0150 | 0.008% | 0.055% | 4/6 | NO_PROMOTION |
| MCS | XLP | +0.0341 | +0.0281 | 0.116% | 0.006% | 3/6 | NO_PROMOTION |
| MSG | XLC | +0.0380 | +0.0181 | 0.144% | 0.007% | 5/6 | NO_PROMOTION |
| MUN | XLP | +0.0214 | +0.0121 | 0.046% | 0.017% | 4/6 | NO_PROMOTION |
| PRN | XLC | +0.0305 | -0.0072 | 0.093% | 0.051% | 3/6 | NO_PROMOTION |
| PTS | XLF | +0.0687 | +0.0432 | 0.472% | 0.558% | 3/4 | NO_PROMOTION |
| SYM | XLV | -0.0188 | -0.0093 | 0.035% | 0.015% | 2/6 | NO_PROMOTION |
| SYS | XLK | +0.0007 | +0.0227 | 0.000% | 0.010% | 3/6 | NO_PROMOTION |
| TCC | XRT | -0.0441 | -0.0299 | 0.195% | 0.005% | 0/6 | NO_PROMOTION |
| TCI | KBE | +0.0458 | +0.0387 | 0.210% | 0.067% | 5/6 | NO_PROMOTION |
| TCM | CARZ | +0.0259 | +0.0372 | 0.067% | 0.038% | 6/6 | NO_PROMOTION |
| TCP | XLC | -0.0082 | -0.0025 | 0.007% | 0.023% | 3/6 | NO_PROMOTION |
| TCT | XLC | +0.0430 | -0.0102 | 0.185% | 0.039% | 2/6 | NO_PROMOTION |
| TGP | XLC | +0.0369 | +0.0193 | 0.136% | 0.234% | 4/6 | NO_PROMOTION |
| THS | IHF | -0.0013 | +0.0111 | 0.000% | 0.026% | 3/6 | NO_PROMOTION |
| TMI | XLC | +0.0371 | +0.0323 | 0.138% | 0.064% | 4/6 | NO_PROMOTION |
| TSB | KBE | +0.0616 | +0.0644 | 0.379% | 0.209% | 6/6 | PROMOTE_NAMED |
| WLT | XLI | +0.0127 | +0.0179 | 0.016% | 0.039% | 4/6 | NO_PROMOTION |
| WSU | XLY | -0.0192 | -0.0179 | 0.037% | 0.006% | 2/6 | NO_PROMOTION |
| YAZ | XLC | -0.0096 | -0.0467 | 0.009% | 0.007% | 2/6 | NO_PROMOTION |

## Important non-promotions

### PTS

PTS has the numerically largest primary sector statistic (XLF Pearson +0.0687; incremental R² +0.558 pp), but the underlying sector hypothesis was explicitly `VERY_LOW` confidence before screening, only four years are eligible for the yearly summary, and the generic payments/financial interpretation is weak. Promoting named payment companies from this result would convert a weak prior into a story fitted after the data. PTS is therefore not promoted.

### ELT

ITB has Pearson +0.0582 and incremental R² +0.455 pp, but Spearman is only +0.0067 and the primary yearly sign is split 3/3. Other real-estate/homebuilding proxies are also weak. This does not meet the stability/agreement standard for named-company promotion.

### EVL and ASS

Consumer-sector proxies show relatively stable **negative** same-date relationships (for example EVL/PBJ Pearson -0.0607 and ASS/PBJ -0.0579), but the relationships largely disappear under adjacent-date alignments and do not support the preregistered positive same-industry mapping interpretation. They are retained as descriptive observations, not promoted.

### TCM

CARZ has positive yearly Pearson signs in 6/6 eligible years at the primary alignment, but the effect is extremely small (Pearson +0.0259; R² 0.067%; incremental R² +0.038 pp) and changes sign at adjacent date offsets. This is insufficient for named-company promotion.

### TCI

KBE is positive in 5/6 years at offset 0, but the relationship changes sign at both adjacent offsets and adds only +0.067 pp incremental R² over SPY at the primary alignment. No promotion.

## Frozen named-equity follow-up

Only TSB advances.

The follow-up may test only the candidates that were frozen **before** the sector evidence was observed:

- sector controls retained for context: `XLF`, `KBE`;
- named candidates: `HSBC`, `JPM`, `BAC`, `C`;
- broad controls: `SPY`, `ACWI`, `QQQ`, `IWM`.

No new bank, ETF, date offset, or price variant is introduced by this decision.

The machine-readable follow-up plan is `external_named_followup_v1.json`. The wrapper `run_external_named_followup.py` enforces the frozen TSB candidate set and removes sector/named candidates for every non-promoted Torn stock before delegating to the existing reviewed EOD screening engine.

## Interpretation boundary

This review does **not** establish:

- a causal mapping from any real-world security to a Torn stock;
- a lead/lag relationship;
- information availability at an intraday signal timestamp;
- executable alpha;
- a profitable strategy.

The named-equity follow-up is the next candidate-reduction stage. If none of the four frozen TSB named candidates materially improves on KBE/XLF and broad controls with stable behavior, TSB should resolve to `NO_STABLE_NAMED_MAPPING_V1` rather than expanding the candidate universe post hoc.

## Gate status

- EXT-004 sector screen: **COMPLETE — evidence reviewed**.
- Sector-first named promotion: **TSB only**.
- All other v1 sector hypotheses: **no named-equity promotion from this screen**.
- TSB named-equity mapping: **OPEN — next evidence run**.
