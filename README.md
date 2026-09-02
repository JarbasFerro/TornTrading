# TornTrading

TornTrading is a research-driven decision-support tool for the Torn City stock market.

The objective is not to reproduce conventional trading indicators. The project will determine what information is observable, identify whether it has predictive value in Torn, validate strategies against historical and live-shadow data, and use the resulting evidence to improve capital allocation across active trades, stock benefit blocks, and cash/opportunity-cost alternatives.

## Current status

**Stage 0 — Research specification**

The project is intentionally not implementing production trading signals yet. Stage 0 defines the research questions, evidence hierarchy, data standards, anti-overfitting rules, validation gates, and priorities that later work must satisfy.

See: [`research/00_RESEARCH_SPECIFICATION.md`](research/00_RESEARCH_SPECIFICATION.md)

## Project principles

- Evidence before features.
- Torn-specific validation before importing real-world trading assumptions.
- Raw data preserved; derived data reproducible.
- Strict chronological/out-of-sample testing.
- Transaction costs and realistic manual execution included.
- Benefit-block economics and opportunity cost included in capital decisions.
- Community claims treated as hypotheses until independently validated.
- Human execution only; TornTrading remains a Torn-rules-compliant decision-support system.

## Research roadmap

0. Research specification and validation contract
1. Torn mechanics and API surface
2. Price-generation / real-world mapping research
3. Historical dataset construction and validation
4. Statistical market anatomy
5. Alpha / market-inefficiency research
6. Portfolio and benefit-block economics
7. Backtesting and live-shadow validation
8. Product requirements
9. Architecture
10. Implementation
