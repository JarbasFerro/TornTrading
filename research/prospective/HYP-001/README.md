# HYP-001 Prospective Evidence

This directory is the durable, append-only confirmatory evidence store for preregistered HYP-001.

- `cohorts/YYYY-MM-DD.json` is created on an eligible Thursday between 00:00 and 03:00 UTC, after the anchor boundary and before the corresponding 7-day outcome exists.
- `outcomes/YYYY-MM-DD.json` is created one week later for that cohort.
- Existing cohort and outcome files are never overwritten; staged evidence must be new files only.
- The originally nominated 2026-09-03 anchor was missed before collector activation and must never be backfilled. The first eligible confirmatory anchor is 2026-09-10.
- `condition_met` is a research condition used to test HYP-001; it is **not** a production BUY recommendation.
- Every cohort stores hashes of the hypothesis registry, stock-universe manifest and collector source code used for the decision, plus per-source retrieval timestamps and payload hashes.
- A missing exact anchor endpoint invalidates the cohort capture rather than being converted to a non-signal.
- A stock with insufficient trailing history is explicitly ineligible for that cohort and excluded from both comparison groups.
- If the public source or workflow remains unavailable after 03:00 UTC, that Thursday is a missed cohort rather than a later reconstruction.

The workflow makes several early-Thursday attempts to tolerate short source outages. Once a cohort file exists, later scheduled attempts do not modify it.
