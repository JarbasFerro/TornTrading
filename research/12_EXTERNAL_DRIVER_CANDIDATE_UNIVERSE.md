# TornTrading — External Driver Candidate Universe

Status: **Stage 0 / EXT candidate-design pass**  
Research date: 2026-09-02  
Questions advanced: EXT-001, EXT-002, EXT-003; prepares EXT-004 through EXT-010

## Executive conclusion

Torn's only official statement is that stock prices move every minute and are based on real-world stocks in the same industries as Torn's. Torn deliberately does not disclose the mappings. Therefore this document does **not** assert that any Torn stock follows any specific real-world ticker.

The correct research object is a **candidate universe**. For each of the 35 current tradable Torn stocks we define:

1. a real-world industry hypothesis;
2. one or more sector/industry proxies;
3. several plausible listed-company candidates;
4. broad-market controls shared by every stock;
5. a classification-confidence level that is separate from mapping confidence.

Machine-readable source: `external_driver_candidates.json`.

## Source hierarchy

### Official Torn evidence

- Stocks 3.0 announcement: https://www.torn.com/forums.php#/p=threads&f=1&t=16220039
- Official stock-market wiki: https://wiki.torn.com/wiki/Stock_Market

Officially established mechanic: Torn stock prices are based on real-world stocks in corresponding industries. No company-level mapping is official.

### Community classification lead

A 2021 community thread grouped the original Stocks 3.0 names into sectors such as banks, insurance, communications, entertainment, consumer goods, technology, healthcare, energy, airlines, defense, autos, agriculture and real estate:

https://www.torn.com/forums.php?a=0&b=0&f=61&p=threads&t=16221088

This is useful only as a hypothesis seed. The author did not demonstrate correlations, and subsequent replies explicitly asked how strongly the suggested groupings were correlated. We therefore never promote a community category directly to a `VALIDATED_FINDING`.

### Benchmark/proxy evidence

For broad sector controls, preference is given to long-lived, liquid index ETFs where possible. Examples include State Street Select Sector SPDRs (XLF, XLC, XLK, XLV, XLE, XLI, XLY, XLP), plus more targeted products where a general sector is too broad.

Representative current sources:

- Technology Select Sector SPDR (XLK): https://www.ssga.com/mainfund/XLK
- Health Care Select Sector SPDR (XLV): https://www.ssga.com/us/en/intermediary/etfs/state-street-health-care-select-sector-spdr-etf-xlv
- First Trust Nasdaq Cybersecurity ETF (CIBR): https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker=CIBR
- VanEck Agribusiness ETF (MOO): https://www.vaneck.com/us/en/investments/agribusiness-etf-moo
- U.S. Global Jets ETF (JETS): https://usglobaletfs.com/JETS/
- iShares U.S. Aerospace & Defense ETF (ITA): https://www.ishares.com/us/products/239502/ishares-us-aerospace-defense-etf

The benchmark is a candidate explanatory series, not an assumption about Torn's code.

## Shared controls

Every Torn stock must be tested against the same broad controls before a sector or company candidate is considered explanatory:

| Symbol | Role |
|---|---|
| SPY | US broad-market control |
| ACWI | Global broad-market control |
| QQQ | US growth/technology-heavy control |
| IWM | US small-cap control |

These controls matter because a stock can appear related to an industry candidate simply because both respond to the overall equity market.

## Candidate map

The full machine-readable list is in `external_driver_candidates.json`. The table below summarizes the first-level design.

| Torn | Industry hypothesis | Sector/industry proxies | Named candidates | Classification confidence |
|---|---|---|---|---|
| TSB | Diversified banks | XLF, KBE | HSBC, JPM, BAC, C | HIGH |
| TCI | Banks / diversified financials / investment services | XLF, KBE | JPM, C, GS, MS | MEDIUM |
| SYS | Cybersecurity / software / communications equipment | CIBR, XLK | PANW, FTNT, CSCO, CRWD | HIGH |
| LAG | Legal / professional information & services | XLI | TRI, RELX, VRSK | LOW |
| IOU | Insurance | KIE, XLF | CB, PGR, AIG, ALL | HIGH |
| GRN | Agribusiness / agricultural trading | MOO, XLB | ADM, BG, MOS | HIGH |
| THS | Healthcare providers / facilities | IHF, XLV | HCA, UHS, UNH, CVS | HIGH |
| YAZ | Internet content / advertising / portals | XLC | GOOGL, META, SNAP, VZ | MEDIUM |
| TCT | News media / advertising | XLC | NYT, NWSA, OMC, WPP | HIGH |
| CNC | Oil & gas | XLE, XOP | XOM, CVX, SHEL, BP | HIGH |
| MSG | Messaging / social media | XLC | META, SNAP; TWTR historical | HIGH |
| TMI | Music / entertainment | XLC | SPOT, WMG, SONY, LYV | HIGH |
| TCP | Media / entertainment production | XLC | DIS, CMCSA, NFLX, WBD, PARA | HIGH |
| IIL | Technology hardware / IT services | XLK | IBM, DELL, CSCO, AAPL | MEDIUM |
| FHG | Hotels / resorts / leisure | XLY, BJK | MAR, HLT, H, RCL | HIGH |
| SYM | Pharmaceuticals / biotechnology | XLV, IHE, XBI | PFE, MRK, LLY, BMY | HIGH |
| LSC | Casinos / gaming | BJK, XLY | MGM, LVS, WYNN, CZR | HIGH |
| PRN | Adult entertainment / media | XLC | RICK, PLBY | LOW |
| EWM | Defense / military services | ITA, XAR, XLI | LMT, NOC, RTX, GD | HIGH |
| TCM | Automobiles / mobility | CARZ, XLY | F, GM, TSLA, TM | HIGH |
| ELT | Residential real estate / homebuilding | XLRE, VNQ, ITB, XHB | DHI, LEN, PHM | MEDIUM |
| HRG | Real estate **or** home-improvement retail | XLRE, VNQ, ITB, XHB, XRT | HD, LOW, DHI, LEN | LOW |
| TGP | Advertising / marketing services | XLC | OMC, WPP, TTD | HIGH |
| MUN | Beverages / energy drinks | XLP, PBJ | MNST, KO, PEP, CELH | HIGH |
| WSU | Education services | XLY | LOPE, STRA, ATGE, LAUR | HIGH |
| IST | Education services | XLY | LOPE, STRA, ATGE, LAUR, EDU, TAL | HIGH |
| BAG | Firearms / ammunition / defense-related manufacturing | ITA, XAR, XLI | SWBI, RGR | HIGH |
| EVL | Confectionery / packaged food | XLP, PBJ | HSY, MDLZ | HIGH |
| MCS | Packaged consumer goods | XLP, PBJ | PG, CL, KMB, MDLZ | MEDIUM |
| WLT | Airlines / travel | JETS, XLI | DAL, UAL, AAL, LUV | HIGH |
| TCC | Apparel retail | XRT, XLY | NKE, LULU, ANF | HIGH |
| ASS | Alcoholic beverages | XLP, PBJ | STZ, TAP, DEO, BUD | HIGH |
| CBD | Cannabis | MSOS, MJ | TLRY, CGC, CRON | HIGH |
| LOS | Waste management / environmental services | XLI | WM, RSG, WCN, CLH | HIGH |
| PTS | Unknown; loyalty/rewards/payments hypothesis | XLF | AXP, V, MA | VERY LOW |

## Important ambiguous cases

### TSB

`Torn & Shanghai Banking` strongly resembles the naming of the Hongkong and Shanghai Banking Corporation. HSBC is therefore a high-priority named candidate, but that resemblance is not evidence that Torn uses HSBC directly. KBE/XLF remain mandatory competing explanations.

### SYS

The Advanced Firewall benefit makes cybersecurity a stronger hypothesis than generic technology. CIBR and named firewall/security vendors should therefore be tested before generic XLK-only explanations.

### HRG

The 2021 community guide placed Home Retail Group in real estate, but the name itself points toward home retail. The benefit produces property. We explicitly preserve both hypotheses rather than choosing one before seeing data.

### PRN

There are few public pure-play adult-entertainment securities with clean multi-year histories. A weak or absent real-world mapping is a legitimate possible outcome.

### PTS

PointLess is the least interpretable Torn company name. Its benefit is Torn-specific points and gives no trustworthy sector clue. A payments/loyalty hypothesis (AXP/V/MA) is exploratory only. PTS should receive especially aggressive broad-control and null-model testing.

## Screening sequence

The purpose of the first screen is **candidate reduction**, not proof of causality.

### Screen A — daily returns

Use Stocks 3.0 history from 2021-04-06 onward and compare Torn daily returns with:

1. broad controls;
2. sector/industry proxies;
3. named candidates.

For every pair calculate at minimum:

- overlapping observations;
- Pearson correlation;
- Spearman correlation;
- univariate beta / R-squared;
- partial/incremental explanatory power after broad-market controls;
- yearly and rolling-window stability;
- sign consistency;
- missing-data and listing-period coverage.

Do not select a mapping solely on full-period correlation.

### Screen B — hourly / session structure

Only the strongest daily candidates advance. Questions include:

- whether relationship exists only during the candidate exchange's session;
- whether overnight/after-hours moves matter;
- whether prior-session returns explain Torn behavior;
- whether international candidates require FX adjustment.

### Screen C — minute research

Minute data is purchased/collected only for the reduced candidate set. MEC-X1 establishes that official Torn chart minute labels correspond to the new uncached Torn API minute state; however every external observation must still use its own actual publication/availability convention.

The first minute-stage outputs remain `OBSERVATION` or `HYPOTHESIS`. A lead of N minutes is not a `VALIDATED_FINDING` until it survives chronological holdout and information-availability checks.

## Multiple-testing protection

Candidate discovery creates an obvious data-mining risk. The following rules apply:

1. The candidate universe in `external_driver_candidates.json` is frozen before the first broad screen.
2. Adding a new candidate after seeing results creates a versioned universe and is tagged as post-hoc.
3. Broad controls are always included.
4. Full-sample ranking is descriptive; promotion decisions use chronological stability and holdout periods.
5. We will report all tested candidates, not only winners.
6. Mapping can resolve to `NO_STABLE_MAPPING`.

## External data provider decision

### Preferred EOD screening candidate: Tiingo

Tiingo's current Starter plan advertises:

- $0/month;
- 30+ years of historical price coverage;
- up to 500 unique API symbols per month;
- 50 requests/hour and 1,000 requests/day;
- EOD composite prices for equities and ETFs.

Documentation: https://www.tiingo.com/documentation/end-of-day  
Pricing: https://www.tiingo.com/pricing

This is operationally sufficient for the daily screening universe without paying for minute data first.

### Licensing constraint

Tiingo's Starter terms shown on its pricing page describe the data as **internal use only** and state that it may not be displayed or shared with another person or organization. TornTrading is currently a public GitHub repository.

Therefore:

- do **not** commit raw Tiingo prices to this repository;
- do **not** upload raw Tiingo datasets as public GitHub artifacts;
- keep provider credentials in GitHub Actions secrets or another secret store;
- complete a provider-license review before deciding what derived outputs may be published;
- preserve reproducibility through code, query manifests, hashes/metadata and legally permissible aggregate results rather than redistributing licensed raw prices.

Tiingo is the leading EOD candidate, not yet an approved raw-data publication source.

### Intraday procurement

Do not buy large intraday coverage before daily/hourly screening has reduced the candidate set.

Current alternatives include Alpha Vantage (20+ years of intraday history, premium for historical intraday) and Tiingo's intraday endpoints. Any provider selected for minute research must be reviewed for historical depth, exchange/session timestamps, after-hours semantics, adjustments, rate limits and license before ingestion.

## Decisions

- **EXT-001: ADVANCED / candidate classifications frozen for screening v1.0.**
- **EXT-002: ADVANCED / named-company candidate universe frozen for screening v1.0.**
- **EXT-003: ADVANCED / sector/industry proxy universe frozen for screening v1.0.**
- **EXT-004 onward: OPEN — empirical tests required.**

No mapping in this document is a `VALIDATED_FINDING`.

## Next implementation

Build a provider-neutral external EOD ingestion interface and a screening engine that consumes this manifest. The implementation must:

1. keep provider credentials out of the repository;
2. avoid committing licensed raw price data;
3. record ticker metadata/listing windows;
4. preserve raw-vs-adjusted price choice explicitly;
5. use Torn daily returns derived only from audited history;
6. output the complete candidate-ranking matrix, including failed candidates and broad controls;
7. prevent minute/lead-lag code from silently using data that was not observable at the signal timestamp.
