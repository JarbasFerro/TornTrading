# TornTrading — Stage 0 Research Specification

Status: **Stage 0 — Research contract**  
Created: 2026-09-02  
Project objective: build a Torn stock-market decision-support system that uses evidence, historical data, statistical testing, and portfolio economics to improve in-game capital allocation.

## 1. Purpose

TornTrading must not begin with a preferred indicator, trading strategy, model, or UI. It must first determine:

> **What information is observable, what information is predictive, how reliable that predictability is, and whether it can produce superior risk-adjusted in-game returns after Torn-specific costs and constraints.**

Stage 0 defines the questions, evidence standards, data requirements, validation rules, and decision gates for all later research. It is deliberately stricter than a normal userscript specification because the main risk is not implementation failure; it is building a polished tool around false statistical patterns.

## 2. Core principles

1. **Evidence before features.** No trading signal becomes a product feature merely because it is popular in real-world trading or Torn community scripts.
2. **Prediction, not decoration.** RSI, MACD, Bollinger Bands, moving averages, etc. are candidate features, not strategies by default.
3. **Torn-specific economics.** Fees, benefit blocks, capital lock-up, travel/hospital/jail restrictions, and alternative uses of cash belong inside the model.
4. **No look-ahead.** A model may only use information that would actually have been available at the decision timestamp.
5. **Out-of-sample first.** A strategy that only works on the data used to invent it is considered unvalidated.
6. **Raw data is immutable.** Derived datasets may be rebuilt; raw observations must be preserved.
7. **Timestamp provenance matters.** Source timestamp, retrieval timestamp, aggregation window, market timezone, and publication delay must be tracked explicitly.
8. **Community claims are hypotheses.** Forum posts, guides, scripts, and anecdotal profit reports are research inputs, not evidence of alpha.
9. **Explain uncertainty.** TornTrading should eventually express expected return, downside, confidence, and evidence strength rather than definitive BUY/SELL claims.
10. **Human execution only.** TornTrading is a decision-support tool. It must remain inside Torn's scripting rules and must not autonomously execute game actions.

## 3. Verified starting constraints

These are starting facts, not research conclusions. They should be re-checked when implementation begins because Torn mechanics and APIs can change.

- Torn states that stock prices move every minute and are based on real-world stocks in corresponding industries, without disclosing the exact mapping or formula.
- Torn states that stock prices are expected to appreciate by about 10% per year on average, without guarantees.
- Buying shares has no tax; selling shares incurs a 0.1% fee.
- Stock trading is unavailable while hospitalized, jailed, or traveling.
- Torn API v2 currently exposes stable public `GET /torn/stocks` and `GET /torn/{stockId}/stocks` endpoints. The latter includes chart history and period performance.
- Torn API v2 exposes stable limited-access `GET /user/stocks`, including current holdings, stock transactions, and benefit progress.
- The public API documentation currently states a limit of up to 100 requests per minute per user, subject to change.
- Torn's current scripting policy permits tools using the API or data from a page manually loaded and actively viewed, while prohibiting automatic non-API Torn requests, scraping pages not actively viewed, CAPTCHA bypassing, and automatic game actions.
- Tornsy is an existing third-party source that states it has collected Torn stock data once per minute and exposes historical OHLC data.
- Existing tools such as Smart Stock Vault already use Tornsy history and conventional technical indicators. Their existence gives us useful baselines, not proof that their signal logic is optimal.

## 4. Evidence taxonomy

Every material project claim must have one of four labels.

| Label | Meaning | Example |
|---|---|---|
| `MECHANIC` | Documented or experimentally verified Torn behavior | Selling costs 0.1% |
| `OBSERVATION` | Empirical description of collected data | SYM daily returns show positive skew in sample X |
| `HYPOTHESIS` | Testable proposition not yet validated | 1-hour negative z-score predicts positive 24h return |
| `VALIDATED_FINDING` | Survived predefined statistical and out-of-sample validation | Feature X improves 24h forecast error on held-out data |

A fifth status, `REJECTED`, should be retained for hypotheses that fail. Failed experiments are part of the research record and must not disappear from the repository.

## 5. Evidence hierarchy

Highest weight first:

1. Current Torn rules, Torn API OpenAPI schema, official Torn announcements, official Torn Wiki mechanics.
2. Reproducible measurements from Torn/API data collected by us.
3. Reproducible third-party datasets with clear provenance.
4. Open-source tools whose methodology can be inspected.
5. Torn forum experiments with disclosed methodology and data.
6. Community guides and experienced-player claims.
7. Anecdotes, screenshots, unsupported profit claims, and intuition.

No level 5–7 source can independently promote a claim to `VALIDATED_FINDING`.

## 6. Required research record

Every research result must record:

- Research question ID.
- Claim/hypothesis.
- Status: mechanic / observation / hypothesis / validated / rejected.
- Source(s).
- Retrieval date.
- Data period.
- Dataset version/hash.
- Feature definitions.
- Exact timestamps and timezones used.
- Method.
- Statistical test or model.
- Baseline/benchmark.
- Transaction-cost assumptions.
- Train/validation/test boundaries.
- Result and effect size.
- Confidence interval or uncertainty estimate where applicable.
- Known limitations.
- Reproduction command/notebook.
- Decision: adopt, investigate further, or reject.

## 7. Research priority definitions

- **P0 — Blocking:** must be answered before we can trust later research or safely design the product.
- **P1 — Core alpha/economics:** expected to materially affect profitability or risk.
- **P2 — Optimization:** valuable after the P0/P1 foundations are established.

## 8. Master research question backlog

### A. Governance, compliance, and operating boundaries — 10 questions

- **GOV-001 [P0]** What exact Torn scripting rules apply to an API-driven stock-analysis userscript as of implementation date?
- **GOV-002 [P0]** Which actions on the stock page count as prohibited automation versus permitted UI assistance or form filling?
- **GOV-003 [P0]** Can TornTrading automatically refresh Torn API data while the user is on other Torn pages, and under what constraints?
- **GOV-004 [P0]** Can externally sourced market data be fetched automatically by the userscript without violating Torn rules?
- **GOV-005 [P0]** What restrictions apply to sending Torn API-derived data to an external backend, if we later need server-side analytics?
- **GOV-006 [P0]** What is the minimum Torn API key access level required for each proposed feature?
- **GOV-007 [P0]** What security controls are required so TornTrading never logs, transmits, or exposes a user's API key unintentionally?
- **GOV-008 [P1]** What disclosures should the script provide about external requests, stored data, models, and limitations?
- **GOV-009 [P1]** Which architectural designs minimize API permissions while preserving useful portfolio analytics?
- **GOV-010 [P1]** What automated compliance tests can prevent future code changes from introducing prohibited Torn requests/actions?

### B. Torn stock-market mechanics — 14 questions

- **MEC-001 [P0]** Do all Torn stocks update on the same exact minute boundary?
- **MEC-002 [P0]** What is the authoritative timestamp of a price: calculation time, publication time, or API response time?
- **MEC-003 [P0]** Is the displayed/API price exactly the execution price for a manual buy at that moment?
- **MEC-004 [P0]** Is the displayed/API price exactly the gross execution price for a manual sale before the 0.1% fee?
- **MEC-005 [P0]** Are there any hidden spreads, rounding effects, minimum share quantities, or other execution friction?
- **MEC-006 [P0]** How is sale fee rounding performed at small and large transaction values?
- **MEC-007 [P0]** Can stock prices change between form submission and transaction execution, and if so which price wins?
- **MEC-008 [P0]** How are merged purchases represented, and can original transaction lots always be reconstructed through the API?
- **MEC-009 [P0]** When partially selling a position, how does Torn attribute cost basis and profit/loss internally?
- **MEC-010 [P1]** Are market cap, outstanding shares, and investor counts merely descriptive, or can player activity affect price generation?
- **MEC-011 [P1]** What precisely happens to benefit eligibility when shares are added, removed, merged, or partially sold?
- **MEC-012 [P1]** How are passive versus periodic stock benefits triggered and timestamped?
- **MEC-013 [P1]** What are the exact scaling rules for second and later benefit increments for every stock?
- **MEC-014 [P1]** Are there documented or measurable structural breaks in the stock algorithm since Stocks 3.0 that require separate research regimes?

### C. Torn API and observable data surface — 16 questions

- **API-001 [P0]** What fields are returned by `GET /torn/stocks`, with types, precision, cache behavior, and stability status?
- **API-002 [P0]** What exact history is returned by `GET /torn/{stockId}/stocks` today: sampling interval, count, age, gaps, and aggregation method?
- **API-003 [P0]** Does the specific-stock history change its sampling resolution with age?
- **API-004 [P0]** Is chart history identical to the graph data visible on the manually loaded stock page?
- **API-005 [P0]** What fields are returned by `GET /user/stocks`, and can every acquisition lot be reconstructed reliably?
- **API-006 [P0]** Does `/user/stocks` include sold history, or only transactions belonging to currently held positions?
- **API-007 [P0]** Which API endpoint/personal stats expose realized stock profits, losses, and fees, and at what granularity?
- **API-008 [P0]** Can dividend/benefit payouts be identified with timestamps and values through official API data?
- **API-009 [P0]** What are the effective cache TTLs for stock endpoints in real use?
- **API-010 [P0]** Do API responses include a server timestamp sufficient to measure freshness and clock skew?
- **API-011 [P0]** What are the current per-key, per-user, per-IP, and daily record limits relevant to our collection plan?
- **API-012 [P1]** Which V1 endpoints still contain useful information not yet available in V2?
- **API-013 [P1]** How often does the OpenAPI schema change, and can CI detect breaking Torn API changes automatically?
- **API-014 [P1]** Can a public-only key provide enough market research functionality while a limited key is requested only for portfolio features?
- **API-015 [P1]** Which stock-related data is available only from the actively viewed DOM and not via API?
- **API-016 [P2]** What API polling schedule gives maximum information with minimal redundant calls and safety margin below limits?

### D. Historical dataset quality and reconstruction — 14 questions

- **DAT-001 [P0]** How many years of usable Torn stock history can be obtained from official API endpoints today?
- **DAT-002 [P0]** How many years and what resolutions are available from Tornsy or other reputable public archives?
- **DAT-003 [P0]** Do official API and Tornsy prices match for overlapping timestamps, within expected rounding?
- **DAT-004 [P0]** What percentage of minute observations are missing per stock and per year?
- **DAT-005 [P0]** Are missing observations random, or concentrated around API outages, Torn maintenance, or market events?
- **DAT-006 [P0]** How should unchanged consecutive prices be distinguished from missing/forward-filled data?
- **DAT-007 [P0]** What timestamp convention does every source use, and are timestamps start-of-window or end-of-window?
- **DAT-008 [P0]** Has historical data ever been retroactively revised by Torn or third-party providers?
- **DAT-009 [P0]** Can we reconstruct an immutable canonical minute-level series with explicit source precedence and quality flags?
- **DAT-010 [P0]** What structural breaks correspond to stock-system updates, algorithm changes, stock additions, renames, or benefit changes?
- **DAT-011 [P1]** Can market cap, outstanding shares, and investor counts be reconstructed historically as potential predictors?
- **DAT-012 [P1]** What compression/storage format preserves minute data efficiently without sacrificing exact reconstruction?
- **DAT-013 [P1]** What daily integrity checks should detect duplicates, gaps, impossible jumps, and stale collectors?
- **DAT-014 [P1]** At what point should TornTrading run its own continuous collector rather than relying on third-party history?

### E. Real-world driver and price-generation reverse engineering — 18 questions

- **EXT-001 [P0]** Which real-world industry classification best corresponds to each Torn stock?
- **EXT-002 [P0]** Which individual listed companies are plausible underlying references for each Torn stock?
- **EXT-003 [P0]** Which sector/industry ETFs or indices are plausible underlying references for each Torn stock?
- **EXT-004 [P0]** Are Torn returns more strongly related to individual equities, sector baskets, broad indices, or combinations?
- **EXT-005 [P0]** What lag maximizes relationship strength between real-world returns and Torn returns at 1m/5m/15m/1h horizons?
- **EXT-006 [P0]** Does Torn react only during the relevant real-world exchange's open session, or also to overnight/pre-market/after-hours moves?
- **EXT-007 [P0]** How does Torn behave on weekends and real-world market holidays?
- **EXT-008 [P0]** Are previous trading-session returns incorporated into Torn prices gradually after market reopening?
- **EXT-009 [P0]** Does each Torn stock use a fixed real-world mapping or does the mapping/regression relationship change over time?
- **EXT-010 [P0]** Is the Torn transformation primarily linear in external percentage returns?
- **EXT-011 [P1]** Is there evidence of nonlinear clipping, volatility scaling, mean reversion, smoothing, or random noise added after external returns?
- **EXT-012 [P1]** Does Torn normalize or rescale different real-world stocks toward a common long-term drift target?
- **EXT-013 [P1]** Do exchange rates (USD/GBP/EUR/etc.) improve mapping for candidate international instruments?
- **EXT-014 [P1]** Do commodities such as oil, gold, or other sector inputs explain some Torn stocks better than equities alone?
- **EXT-015 [P1]** Can futures/index futures provide predictive information before the corresponding cash market opens?
- **EXT-016 [P1]** Can changes in candidate real-world volatility measures predict Torn volatility even when direction is weak?
- **EXT-017 [P1]** Are TCSE/index movements mechanically derived from constituent Torn stocks or generated independently?
- **EXT-018 [P1]** After controlling for contemporaneous external returns, is there residual Torn-specific structure that remains predictably exploitable?

### F. Statistical anatomy of the Torn market — 14 questions

- **STA-001 [P0]** What are the return distributions of every stock at 1m, 5m, 1h, 6h, 24h, 7d, and 30d horizons?
- **STA-002 [P0]** How stable are mean, volatility, skewness, kurtosis, and tail risk across time?
- **STA-003 [P0]** What autocorrelation exists in returns and absolute returns at relevant lags?
- **STA-004 [P0]** Which stocks exhibit statistically meaningful short-horizon mean reversion?
- **STA-005 [P0]** Which stocks exhibit statistically meaningful momentum/trend persistence?
- **STA-006 [P0]** What are the pairwise and rolling correlations among Torn stocks?
- **STA-007 [P1]** Do stable stock clusters/factors explain most common movement?
- **STA-008 [P1]** What share of each stock's variance is common-market versus stock-specific?
- **STA-009 [P1]** Are volatility regimes identifiable and persistent enough to affect strategy selection?
- **STA-010 [P1]** Are extreme negative and positive moves followed by asymmetric recovery/reversal behavior?
- **STA-011 [P1]** Are there robust hour-of-day, day-of-week, weekend, month-end, or holiday effects?
- **STA-012 [P1]** How often do apparent statistical properties change after Torn algorithm/mechanics updates?
- **STA-013 [P1]** What is a suitable Torn market factor/index benchmark for abnormal-return calculations?
- **STA-014 [P2]** Can latent-state/regime models improve forecasts enough to justify their complexity over simple rolling statistics?

### G. Signal and alpha hypotheses — 18 questions

- **ALP-001 [P0]** Does price distance from a rolling mean predict future returns after costs?
- **ALP-002 [P0]** Does rolling z-score predict future returns, and at which lookback/holding horizons?
- **ALP-003 [P0]** Does short-term momentum predict continuation after costs?
- **ALP-004 [P0]** Does medium-term momentum predict continuation after costs?
- **ALP-005 [P0]** Do extreme drawdowns predict recovery, and how does recovery probability vary with drawdown depth?
- **ALP-006 [P0]** Do external-market residuals (actual Torn move minus externally implied move) mean-revert?
- **ALP-007 [P0]** Can lagged real-world returns predict Torn returns with enough lead time to trade manually?
- **ALP-008 [P0]** Does cross-sectional ranking of Torn stocks predict relative future performance?
- **ALP-009 [P1]** Does RSI contain predictive information after controlling for simpler return/z-score features?
- **ALP-010 [P1]** Do Bollinger-band features add predictive information beyond rolling volatility and z-score?
- **ALP-011 [P1]** Does MACD add incremental predictive value beyond raw multi-horizon momentum?
- **ALP-012 [P1]** Does ADX/trend-strength filtering improve momentum or mean-reversion signals?
- **ALP-013 [P1]** Do changes in investor counts or outstanding shares predict subsequent price movement?
- **ALP-014 [P1]** Do TCSE/index moves lead individual Torn stocks or vice versa?
- **ALP-015 [P1]** Are pairs/spread relationships stable enough for relative-value signals?
- **ALP-016 [P1]** Does ensemble combination of weak signals outperform the strongest standalone signal out of sample?
- **ALP-017 [P1]** Do probabilistic models estimating `P(return > fee + hurdle)` outperform directional classification?
- **ALP-018 [P2]** Do nonlinear ML models materially outperform regularized linear/tree baselines after strict walk-forward validation?

### H. Benefit blocks, capital allocation, and opportunity cost — 12 questions

- **CAP-001 [P0]** What is the exact acquisition cost of every benefit block at current prices and each incremental tier?
- **CAP-002 [P0]** How should each stock benefit be converted into expected in-game monetary value?
- **CAP-003 [P0]** How variable is that benefit value because of item prices, cooldowns, or player-specific usage?
- **CAP-004 [P0]** What is the expected annualized return of each benefit tier before expected stock-price change?
- **CAP-005 [P0]** How does the seven-day activation/eligibility mechanic affect effective yield and switching costs?
- **CAP-006 [P1]** When does holding a benefit block dominate active trading in expected value?
- **CAP-007 [P1]** When is it rational to break a benefit block to fund a statistically attractive trade?
- **CAP-008 [P1]** What alternative risk-free/low-risk Torn return should be used as the opportunity-cost hurdle (e.g. bank where applicable)?
- **CAP-009 [P1]** What cash reserve is optimal given trading opportunities and inability to transact while traveling/hospitalized/jailed?
- **CAP-010 [P1]** How should portfolio optimization treat benefit-block shares as partially locked capital?
- **CAP-011 [P1]** How should expected trading return, benefit yield, fees, and opportunity cost be combined into one comparable score?
- **CAP-012 [P2]** Does player wealth materially change the optimal strategy because benefit tiers and transaction sizes scale nonlinearly?

### I. Backtesting, validation, and research integrity — 14 questions

- **VAL-001 [P0]** What exact transaction-cost model reproduces manual Torn trades, including fee rounding?
- **VAL-002 [P0]** What execution delay should be assumed between a signal becoming observable and a human completing a trade?
- **VAL-003 [P0]** How should a backtest model signals generated near minute boundaries where the displayed price may update during execution?
- **VAL-004 [P0]** What chronological train/validation/test splits prevent leakage while retaining multiple market regimes?
- **VAL-005 [P0]** What walk-forward schedule will be the standard for all strategies?
- **VAL-006 [P0]** Which benchmarks must every strategy beat: buy-and-hold, TCSE, equal-weight stocks, random timing, benefit-block return, and/or cash hurdle?
- **VAL-007 [P0]** Which primary metric decides whether a strategy is useful: net excess return, risk-adjusted return, drawdown, or a composite?
- **VAL-008 [P0]** What minimum number of independent trades/periods is required before a result can be considered stable?
- **VAL-009 [P0]** How will multiple-hypothesis/data-mining bias be controlled when testing many indicators and parameter combinations?
- **VAL-010 [P0]** What minimum out-of-sample effect size must remain after fees before promotion to `VALIDATED_FINDING`?
- **VAL-011 [P1]** How will confidence intervals be estimated for overlapping time-series returns?
- **VAL-012 [P1]** What bootstrap/Monte-Carlo/stress tests will estimate strategy fragility and drawdown risk?
- **VAL-013 [P1]** How will parameter stability be tested so we reject narrow overfit optima?
- **VAL-014 [P1]** What paper-trading/live-shadow period is required before a validated backtest is allowed to influence real manual trades?

### J. Product and decision-system research — 10 questions

- **PRD-001 [P1]** What decision should TornTrading optimize first: individual trade timing, portfolio allocation, benefit-block allocation, or a combined capital decision?
- **PRD-002 [P1]** What forecast horizon is most useful given Torn's fee and realistic human response time?
- **PRD-003 [P1]** What minimum expected edge should suppress a signal and recommend WAIT instead?
- **PRD-004 [P1]** What risk information must accompany every recommendation so a score is not mistaken for certainty?
- **PRD-005 [P1]** How should confidence incorporate both model uncertainty and data-quality uncertainty?
- **PRD-006 [P1]** Should recommendations be expressed as expected return, probability of profit, opportunity score, suggested allocation, or several of these?
- **PRD-007 [P1]** What explanation can be shown without exposing misleading causal stories for statistical models?
- **PRD-008 [P2]** Which competitor features are useful UX conventions versus unsupported trading logic we should avoid copying?
- **PRD-009 [P2]** What information density works on Torn desktop, mobile browser, and Torn PDA without obscuring the native stock page?
- **PRD-010 [P2]** What audit trail should a user see for past recommendations, actual trades, and model performance?

## 9. Required data domains

The research program should plan for the following source families.

### 9.1 Torn official market data

Minimum fields:

- timestamp / retrieval timestamp;
- stock ID and acronym;
- price;
- market cap;
- shares;
- investors;
- benefit type/frequency/requirement;
- official chart history and performance windows;
- API schema version.

### 9.2 User portfolio data

Minimum fields:

- stock ID;
- current shares;
- acquisition transactions (ID, shares, price, timestamp);
- benefit availability/increment/progress/frequency;
- realized stock profit/loss/fees where available;
- manually recorded sale execution if official API cannot reconstruct it precisely.

### 9.3 External financial-market data

Candidate families:

- individual equities;
- sector and industry ETFs;
- broad equity indices;
- index/sector futures where legally/data-source feasible;
- FX rates;
- relevant commodities;
- trading calendars and exchange sessions.

For every external field we need the **time it became observable**, not merely the bar timestamp.

### 9.4 Third-party Torn archives

Potentially useful for bootstrapping history, but every third-party series must be cross-validated against official Torn data before becoming canonical.

### 9.5 Benefit-value inputs

Where a stock benefit yields an item, service, cash flow, or cooldown-dependent value, we need a documented valuation method and historical value series where feasible.

## 10. Canonical timestamp policy

This is a P0 research concern because a one-minute timestamp mistake can manufacture apparent predictive alpha.

Every observation should eventually distinguish:

- `event_time`: when the underlying value applies;
- `source_publish_time`: when the source made it observable, if known;
- `retrieved_at`: when TornTrading obtained it;
- `window_start` / `window_end`: for aggregated bars;
- `source_timezone`;
- `normalized_time_utc`;
- `quality_flag`.

No external-market feature may be aligned to a Torn prediction timestamp until its publication/availability convention is understood.

## 11. Hypothesis preregistration template

Before running a serious alpha test, record:

```yaml
id: HYP-XXX
research_question: ALP-XXX
statement: "..."
rationale: "..."
information_available_at_signal_time: [...]
target: "forward return over ..."
universe: [...]
sample_start: YYYY-MM-DD
sample_end: YYYY-MM-DD
train_period: "..."
validation_period: "..."
test_period: "..."
features: [...]
parameter_search_space: {...}
transaction_cost_model: "..."
execution_delay: "..."
benchmarks: [...]
primary_metric: "..."
secondary_metrics: [...]
acceptance_threshold: "..."
rejection_condition: "..."
```

Changing the hypothesis after seeing the test data creates a new hypothesis ID.

## 12. Minimum validation standard

A trading idea is **not validated** because it has a high win rate, attractive chart, profitable backtest, or favorable forum anecdote.

To become a `VALIDATED_FINDING`, at minimum it must:

1. Use only data available at signal time.
2. Include the Torn sale fee and realistic execution delay.
3. Use chronological hold-out data not used in hypothesis/parameter selection.
4. Beat at least one economically meaningful benchmark and the defined opportunity-cost hurdle.
5. Show positive effect across more than one time period/regime, not a single lucky episode.
6. Have enough independent observations/trades for the result to be interpretable.
7. Survive reasonable parameter perturbation.
8. Have documented uncertainty and maximum drawdown.
9. Be reproducible from repository code/data manifests.
10. Survive a paper-trading/live-shadow phase before influencing real-money recommendations.

## 13. Research anti-patterns to reject

- Optimizing RSI periods until historical profit looks attractive.
- Evaluating thousands of parameter combinations and reporting only the winner.
- Using same-bar external closing values that were not yet observable at Torn signal time.
- Forward-filling missing data without quality flags.
- Treating unchanged Torn prices as missing observations.
- Using future benefit/item prices to value past benefit-block decisions.
- Comparing a strategy only with cash when the whole market was strongly rising.
- Reporting win rate without payoff ratio and drawdown.
- Treating a 0.2% predicted move as profitable without applying the sale fee and execution uncertainty.
- Assuming a popular userscript's indicator is validated because many players use it.
- Allowing ML models to learn stock identity/time period artifacts without appropriate validation.
- Mixing data from materially different Torn stock algorithms without regime labels.

## 14. Stage gates

### Gate 0A — Research contract complete

Stage 0 can close when:

- this research backlog is reviewed;
- P0 questions are accepted as mandatory;
- evidence taxonomy and validation rules are accepted;
- research outputs have stable repository locations.

### Gate 1 — Mechanics/API feasibility

Before alpha research:

- all GOV/API/MEC P0 items are answered;
- compliant data collection design is established;
- exact execution/fee assumptions are known.

### Gate 2 — Dataset readiness

Before serious statistical modeling:

- a canonical historical dataset exists;
- timestamp alignment is validated;
- gaps and structural breaks are documented;
- official and third-party overlap has been reconciled.

### Gate 3 — External-driver feasibility

Before focusing on classical technical indicators:

- candidate real-world mappings are tested systematically;
- lead/lag relationships are measured out of sample;
- residual Torn-specific behavior is quantified.

### Gate 4 — Alpha validation

Before productizing any recommendation:

- at least one strategy survives the minimum validation standard;
- its edge remains after costs and realistic delay;
- its failure modes and applicable regimes are documented.

### Gate 5 — Portfolio economics

Before suggested allocation sizing:

- benefit-block economics and opportunity cost are included;
- position sizing and drawdown limits are validated.

### Gate 6 — Product requirements

Only after the previous gates should the final userscript architecture and UI be fixed.

## 15. Planned Stage 0 outputs

This specification should become the parent document for the following research artifacts:

1. `research/01_MARKET_MECHANICS.md`
2. `research/02_PRICE_GENERATION.md`
3. `research/03_DATA_SOURCES.md`
4. `research/04_DATASET_DESIGN.md`
5. `research/05_MARKET_STATISTICS.md`
6. `research/06_MARKET_INEFFICIENCIES.md`
7. `research/07_SIGNAL_RESEARCH.md`
8. `research/08_EXISTING_TOOLS.md`
9. `research/09_CAPITAL_ALLOCATION.md`
10. `research/10_PORTFOLIO_OPTIMIZATION.md`
11. `research/11_BACKTESTING_STANDARD.md`
12. `research/12_PRODUCT_REQUIREMENTS.md`

Supporting machine-readable research files should later include:

- `research/registry/questions.yaml`
- `research/registry/hypotheses.yaml`
- `research/registry/sources.yaml`
- `research/registry/findings.yaml`
- `research/registry/structural_breaks.yaml`

## 16. Initial research order

The first research sprint should not follow the numeric document order blindly. The recommended sequence is:

1. **GOV + MEC + API P0:** establish legal/technical boundaries and exact market mechanics.
2. **DAT P0:** determine whether current official history is sufficient and reconcile it with Tornsy.
3. **EXT P0:** attack the real-world mapping/lead-lag problem early because it may dominate every conventional technical signal.
4. **STA P0:** characterize the market and identify regimes.
5. **ALP P0:** test simple, interpretable hypotheses first.
6. **VAL P0:** apply one common backtesting standard to every candidate strategy.
7. **CAP P0/P1:** compare trading alpha with benefit blocks and alternative capital uses.
8. **PRD:** only then decide what TornTrading should show and how it should recommend actions.

## 17. Current high-value unknowns

If only a small number of questions could be answered, these would have the largest information value:

1. What exactly is contained in the official stock chart history endpoint, and how far back does it go at each resolution?
2. Can we reconcile official minute prices with Tornsy sufficiently to trust Tornsy's longer archive?
3. Which real-world instruments best explain each Torn stock?
4. Is there a reproducible lead between observable real-world moves and subsequent Torn price updates?
5. Does any such lead survive manual execution delay and the 0.1% sale fee?
6. After removing external-market effects, does Torn-specific mean reversion/momentum remain?
7. Can benefit-block yield beat active trading for realistic capital levels?
8. Which benchmark represents the true opportunity cost of a trade?

These questions determine whether TornTrading ultimately becomes primarily an **external-market predictor**, a **Torn statistical arbitrage/mean-reversion tool**, a **capital-allocation optimizer**, or some combination.

## 18. Source register — Stage 0 seed sources

Primary/official:

- Torn Stock Market Wiki: https://wiki.torn.com/wiki/The_Empty_Lunchbox_Building_Traders
- Torn API Wiki: https://wiki.torn.com/wiki/API
- Torn API v2 OpenAPI schema: https://www.torn.com/swagger/openapi.json
- Torn scripting rules / Tools & Userscripts announcement: https://www.torn.com/forums.php?p=threads&t=16037108

Secondary/research inputs:

- Tornsy API documentation: https://tornsy.com/api
- Smart Stock Vault forum thread: https://www.torn.com/forums.php?p=threads&t=16535978
- Smart Stock Vault source: https://greasyfork.org/en/scripts/564798-smart-stock-vault/code
- Torn Stock Analyzer source: https://greasyfork.org/en/scripts/570460-torn-stock-analyzer/code

## 19. Stage 0 decision

**Do not implement production trading signals yet.**

The next executable research work is to answer the blocking governance/mechanics/API/data-history questions and build a reproducible source/dataset inventory. In parallel, we should begin the real-world mapping research as soon as timestamps and historical price integrity are understood.
