# TornTrading — MEC-X1 Publication Boundary Experiment

Status: **experiment implementation**  
Purpose: resolve MEC-001/MEC-002 far enough to permit minute-level timestamp research.

## Research question

At a Torn stock minute boundary, when does the new price become visible through an explicitly uncached official API request, when does Tornsy expose the same minute, and do all official stocks present one internally consistent boundary state?

This experiment measures API/data publication. It does **not** by itself prove the exact Torn UI execution instant.

## Why this is necessary

The first credentialed official-data run showed an apparent live official/Tornsy discrepancy. Artifact review demonstrated that the bulk official request was service-cached. Torn's API documentation states that all requests can be service-cached for up to 30 seconds unless made unique.

The corrected second gate run bypassed this cache and produced 35/35 live price equality.

That same run crossed the `18:03:00 UTC` boundary and produced a useful observation:

- an official individual-stock history request begun at `18:03:00.319` already included the `18:03` chart point;
- Tornsy's minute-history calls made through `18:03:21.640` did not yet include that point;
- a Tornsy minute-history response received at `18:03:22.682` did include it;
- the price values were identical whenever the same timestamp was available from both sources.

This single boundary is an **OBSERVATION**, not a validated timing rule. MEC-X1 collects repeated boundaries under a controlled design.

## Experimental design

The probe observes three consecutive minute boundaries.

For each boundary it samples from 6 seconds before through 30 seconds after the boundary at a 2-second cadence.

Each sample performs:

1. cache-bypassed `GET /torn/timestamp`;
2. cache-bypassed `GET /torn/stocks`;
3. Tornsy watchlist read.

After all three boundaries, the probe retrieves official specific-stock chart history for every current official stock. Each boundary's official chart row becomes the target state for that minute.

The analysis then asks:

- what is the first sampled official bulk response that exactly matches the boundary chart row for all official stocks?;
- what is the first Tornsy response whose minute timestamp and prices exactly match the same boundary row?;
- how large is the Tornsy-minus-official visibility delay?;
- are any stocks missing from the official boundary target?;
- does the bulk official endpoint present a full consistent market state at the first observed new-minute sample?

## API-rate constraint

The observation loop makes two Torn API calls every 2 seconds, or at most **60 Torn requests/minute** during active windows. This remains below Torn's documented 100-request/minute user limit.

A final one-time stock-history inventory adds 35 specific-stock reads after the observation windows. The timing is designed to keep the rolling request rate below the limit.

No automatic non-API Torn action is performed.

## Cache policy

Every official observation includes a changing `timestamp` query parameter so it does not rely on Torn's service cache.

A result obtained without this cache-bypass provenance must not be used to infer publication lead/lag.

## Evidence retained

The raw artifact stores:

- Torn server timestamp observations;
- official bulk stock payloads;
- Tornsy watchlist payloads;
- request start/end timestamps;
- payload hashes;
- final official per-stock history payloads;
- derived boundary summaries.

Artifacts are retained for 90 days. Research conclusions should be summarized into the repository before artifact expiry.

## Interpretation rules

### May establish

- observed upper bound on uncached official API publication delay at the probe cadence;
- observed Tornsy publication delay;
- exact equality or disagreement at a common source timestamp;
- whether official bulk responses are internally consistent with later chart history;
- repeated evidence about cross-stock publication atomicity at 2-second resolution.

### May not establish alone

- exact sub-second Torn calculation time;
- exact UI price-render time;
- exact order-submit execution time;
- exploitable alpha;
- a real-world market lead into Torn.

## Acceptance criteria

MEC-001 may advance to a validated finding when multiple boundaries show that the first cache-bypassed official bulk state matching the new chart minute is internally consistent across the full official stock universe within the observation resolution.

MEC-002 may advance at the **API timestamp-label level** when boundary chart timestamps repeatedly correspond to the first new-minute official state with a stable relationship. Full market-effective/execution semantics still require the controlled transaction/UI cross-check in P0-E4/P0-E5.

## Next decision

If the probe is stable across multiple boundaries, minute-level external-market research may use official/Tornsy source timestamps with a clearly documented publication-delay model. Profitability backtests remain blocked until transaction execution and fee/lot semantics are measured.
