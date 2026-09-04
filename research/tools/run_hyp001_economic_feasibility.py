#!/usr/bin/env python3
"""Discovery-sample economic feasibility audit for frozen HYP-001.

This tool deliberately reuses historical discovery data. It is research triage,
not confirmatory evidence and not a trading signal.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from typing import Any, Mapping, Sequence

import run_hyp001_prospective as hyp
from torn_research import ResearchToolError, TornsyClient, iso_utc, parse_tornsy_rows

DISCOVERY_OUTCOME_CUTOFF = date(2026, 9, 3)
POSITION_NOTIONALS = (10_000, 100_000, 1_000_000)
STRESS_BPS = (0, 10, 25, 50)
PRIMARY_NOTIONAL = 100_000
PRIMARY_STRESS_BPS = 25
FEE_RATE = Decimal("0.001")
FETCH_LIMIT = 2000
DEFAULT_REQUEST_DELAY = 0.25
MIN_SIGNALLED_FOR_PLAUSIBILITY = 60
MIN_PRIMARY_SPREAD = 0.002

SUMMARY_KEYS = {
    "research_status", "hypothesis_id", "source", "generated_at_utc",
    "discovery_outcome_cutoff_utc", "universe_size", "source_fetches",
    "source_errors", "eligible_observations", "signaled_observations",
    "non_signaled_observations", "cohorts_with_eligible_observations",
    "cohorts_with_cross_sectional_spread", "gross_observation_metrics",
    "gross_weekly_cross_sectional_metrics", "scenario_metrics",
    "chronological_quartiles", "primary_scenario", "feasibility_classification",
    "classification_reasons", "claim_boundary", "execution_note",
}
GROSS_OBS_KEYS = {
    "signaled_mean", "signaled_median", "non_signaled_mean", "non_signaled_median",
    "pooled_spread", "signaled_positive_rate",
}
GROSS_WEEKLY_KEYS = {"mean_weekly_spread", "median_weekly_spread", "positive_spread_rate"}
SCENARIO_KEYS = {
    "notional", "stress_bps_per_leg", "signaled_available", "non_signaled_available",
    "signaled_unavailable", "non_signaled_unavailable", "signaled_mean_net",
    "signaled_median_net", "non_signaled_mean_net", "non_signaled_median_net",
    "signaled_positive_net_rate", "mean_weekly_net_spread", "median_weekly_net_spread",
    "positive_weekly_net_spread_rate", "cohorts_with_net_spread",
}
QUARTILE_KEYS = {
    "quartile", "cohort_count", "eligible_observations", "signaled_count",
    "non_signaled_count", "signaled_mean_gross", "non_signaled_mean_gross",
    "mean_weekly_gross_spread", "primary_mean_weekly_net_spread",
}


def fmean_or_none(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def median_or_none(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def round_or_none(value: float | None, digits: int = 12) -> float | None:
    return round(value, digits) if value is not None else None


def positive_rate(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(value > 0 for value in values) / len(values)


def fetch_daily(client: TornsyClient, symbol: str, attempts: int = 3):
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            obs = client.get_stock(symbol, "d1", limit=FETCH_LIMIT)
            return obs, parse_tornsy_rows(obs.payload, "d1")
        except Exception as exc:  # source boundary; preserve final error only
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise ResearchToolError(f"Tornsy fetch failed for {symbol}/d1: {last}")


def first_thursday_on_or_after(day: date) -> date:
    return day + timedelta(days=(hyp.ANCHOR_WEEKDAY - day.weekday()) % 7)


def candidate_anchors(rows_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[date]:
    timestamps: list[int] = []
    for rows in rows_by_symbol.values():
        for row in rows:
            ts = row.get("timestamp")
            if isinstance(ts, (int, float)):
                timestamps.append(int(ts))
    if not timestamps:
        raise ResearchToolError("No daily timestamps available for HYP-001 feasibility audit.")
    first_day = datetime.fromtimestamp(min(timestamps), tz=timezone.utc).date()
    anchor = first_thursday_on_or_after(first_day)
    last_anchor = DISCOVERY_OUTCOME_CUTOFF - timedelta(days=hyp.RETURN_HORIZON_DAYS)
    result: list[date] = []
    while anchor <= last_anchor:
        result.append(anchor)
        anchor += timedelta(days=7)
    return result


def build_observations(
    rows_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    cutoff_ts = hyp.anchor_timestamp(DISCOVERY_OUTCOME_CUTOFF)
    observations: list[dict[str, Any]] = []
    anchors = candidate_anchors(rows_by_symbol)
    for symbol, rows in rows_by_symbol.items():
        opens = hyp.daily_open_map(rows, cutoff_ts)
        for anchor in anchors:
            anchor_ts = hyp.anchor_timestamp(anchor)
            outcome_ts = anchor_ts + hyp.RETURN_HORIZON_DAYS * 86400
            if outcome_ts > cutoff_ts:
                continue
            classified = hyp.classify_stock(rows, anchor_ts)
            if not classified.get("eligible"):
                continue
            entry = classified.get("anchor_open")
            exit_price = opens.get(outcome_ts)
            if not isinstance(entry, (int, float)) or not isinstance(exit_price, (int, float)):
                continue
            if entry <= 0 or exit_price <= 0:
                continue
            forward = float(exit_price) / float(entry) - 1.0
            if not math.isfinite(forward):
                continue
            observations.append({
                "symbol": symbol,
                "anchor": anchor.isoformat(),
                "condition_met": bool(classified.get("condition_met")),
                "entry": float(entry),
                "exit": float(exit_price),
                "gross_return": forward,
            })
    return observations


def ceiling_fee(gross_sale_value: Decimal) -> Decimal:
    if gross_sale_value <= 0:
        raise ValueError("gross sale value must be positive")
    return (gross_sale_value * FEE_RATE).quantize(Decimal("1"), rounding=ROUND_CEILING)


def modeled_net_return(
    entry: float,
    exit_price: float,
    *,
    notional: int,
    stress_bps: int,
) -> float | None:
    stress = Decimal(stress_bps) / Decimal(10_000)
    buy = Decimal(str(entry)) * (Decimal("1") + stress)
    sell = Decimal(str(exit_price)) * (Decimal("1") - stress)
    if buy <= 0 or sell <= 0:
        return None
    shares = int((Decimal(notional) / buy).to_integral_value(rounding=ROUND_FLOOR))
    if shares < 1:
        return None
    purchase = buy * Decimal(shares)
    sale_gross = sell * Decimal(shares)
    fee = ceiling_fee(sale_gross)
    net = (sale_gross - fee - purchase) / purchase
    value = float(net)
    return value if math.isfinite(value) else None


def group_by_anchor(observations: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        grouped[str(row["anchor"])].append(row)
    return dict(grouped)


def weekly_spreads(
    observations: Sequence[Mapping[str, Any]],
    value_key: str,
) -> list[float]:
    spreads: list[float] = []
    for rows in group_by_anchor(observations).values():
        signaled = [float(row[value_key]) for row in rows if row.get("condition_met") and row.get(value_key) is not None]
        nonsignaled = [float(row[value_key]) for row in rows if not row.get("condition_met") and row.get(value_key) is not None]
        if signaled and nonsignaled:
            spreads.append(statistics.fmean(signaled) - statistics.fmean(nonsignaled))
    return spreads


def gross_metrics(observations: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    signaled = [float(row["gross_return"]) for row in observations if row.get("condition_met")]
    nonsignaled = [float(row["gross_return"]) for row in observations if not row.get("condition_met")]
    obs = {
        "signaled_mean": round_or_none(fmean_or_none(signaled)),
        "signaled_median": round_or_none(median_or_none(signaled)),
        "non_signaled_mean": round_or_none(fmean_or_none(nonsignaled)),
        "non_signaled_median": round_or_none(median_or_none(nonsignaled)),
        "pooled_spread": round_or_none(
            (statistics.fmean(signaled) - statistics.fmean(nonsignaled)) if signaled and nonsignaled else None
        ),
        "signaled_positive_rate": round_or_none(positive_rate(signaled)),
    }
    spreads = weekly_spreads(observations, "gross_return")
    weekly = {
        "mean_weekly_spread": round_or_none(fmean_or_none(spreads)),
        "median_weekly_spread": round_or_none(median_or_none(spreads)),
        "positive_spread_rate": round_or_none(positive_rate(spreads)),
    }
    return obs, weekly


def scenario_metric(
    observations: Sequence[Mapping[str, Any]],
    *,
    notional: int,
    stress_bps: int,
) -> dict[str, Any]:
    enriched: list[dict[str, Any]] = []
    sig_unavailable = 0
    non_unavailable = 0
    for row in observations:
        net = modeled_net_return(
            float(row["entry"]), float(row["exit"]), notional=notional, stress_bps=stress_bps
        )
        if net is None:
            if row.get("condition_met"):
                sig_unavailable += 1
            else:
                non_unavailable += 1
            continue
        enriched.append({**row, "net_return": net})
    signaled = [float(row["net_return"]) for row in enriched if row.get("condition_met")]
    nonsignaled = [float(row["net_return"]) for row in enriched if not row.get("condition_met")]
    spreads = weekly_spreads(enriched, "net_return")
    return {
        "notional": notional,
        "stress_bps_per_leg": stress_bps,
        "signaled_available": len(signaled),
        "non_signaled_available": len(nonsignaled),
        "signaled_unavailable": sig_unavailable,
        "non_signaled_unavailable": non_unavailable,
        "signaled_mean_net": round_or_none(fmean_or_none(signaled)),
        "signaled_median_net": round_or_none(median_or_none(signaled)),
        "non_signaled_mean_net": round_or_none(fmean_or_none(nonsignaled)),
        "non_signaled_median_net": round_or_none(median_or_none(nonsignaled)),
        "signaled_positive_net_rate": round_or_none(positive_rate(signaled)),
        "mean_weekly_net_spread": round_or_none(fmean_or_none(spreads)),
        "median_weekly_net_spread": round_or_none(median_or_none(spreads)),
        "positive_weekly_net_spread_rate": round_or_none(positive_rate(spreads)),
        "cohorts_with_net_spread": len(spreads),
    }


def primary_enriched(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in observations:
        net = modeled_net_return(
            float(row["entry"]), float(row["exit"]),
            notional=PRIMARY_NOTIONAL, stress_bps=PRIMARY_STRESS_BPS,
        )
        result.append({**row, "primary_net_return": net})
    return result


def split_anchor_quartiles(observations: Sequence[Mapping[str, Any]]) -> list[set[str]]:
    anchors = sorted(group_by_anchor(observations))
    if not anchors:
        return [set(), set(), set(), set()]
    n = len(anchors)
    result: list[set[str]] = []
    for q in range(4):
        start = (q * n) // 4
        end = ((q + 1) * n) // 4
        result.append(set(anchors[start:end]))
    return result


def quartile_metrics(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    enriched = primary_enriched(observations)
    result: list[dict[str, Any]] = []
    for index, anchor_set in enumerate(split_anchor_quartiles(observations), start=1):
        rows = [row for row in enriched if row["anchor"] in anchor_set]
        signaled = [float(row["gross_return"]) for row in rows if row.get("condition_met")]
        nonsignaled = [float(row["gross_return"]) for row in rows if not row.get("condition_met")]
        gross_spreads = weekly_spreads(rows, "gross_return")
        net_spreads = weekly_spreads(rows, "primary_net_return")
        result.append({
            "quartile": index,
            "cohort_count": len(anchor_set),
            "eligible_observations": len(rows),
            "signaled_count": len(signaled),
            "non_signaled_count": len(nonsignaled),
            "signaled_mean_gross": round_or_none(fmean_or_none(signaled)),
            "non_signaled_mean_gross": round_or_none(fmean_or_none(nonsignaled)),
            "mean_weekly_gross_spread": round_or_none(fmean_or_none(gross_spreads)),
            "primary_mean_weekly_net_spread": round_or_none(fmean_or_none(net_spreads)),
        })
    return result


def annual_rows(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    enriched = primary_enriched(observations)
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        by_year[int(str(row["anchor"])[:4])].append(row)
    result: list[dict[str, Any]] = []
    for year in sorted(by_year):
        rows = by_year[year]
        signaled = [float(row["gross_return"]) for row in rows if row.get("condition_met")]
        nonsignaled = [float(row["gross_return"]) for row in rows if not row.get("condition_met")]
        result.append({
            "year": year,
            "cohort_count": len(group_by_anchor(rows)),
            "eligible_observations": len(rows),
            "signaled_count": len(signaled),
            "non_signaled_count": len(nonsignaled),
            "signaled_mean_gross": round_or_none(fmean_or_none(signaled)),
            "non_signaled_mean_gross": round_or_none(fmean_or_none(nonsignaled)),
            "mean_weekly_gross_spread": round_or_none(fmean_or_none(weekly_spreads(rows, "gross_return"))),
            "primary_mean_weekly_net_spread": round_or_none(
                fmean_or_none(weekly_spreads(rows, "primary_net_return"))
            ),
        })
    return result


def classify_feasibility(
    observations: Sequence[Mapping[str, Any]],
    primary: Mapping[str, Any],
    quartiles: Sequence[Mapping[str, Any]],
) -> tuple[str, list[str]]:
    signal_count = sum(bool(row.get("condition_met")) for row in observations)
    mean_sig = primary.get("signaled_mean_net")
    mean_spread = primary.get("mean_weekly_net_spread")
    positive_quartiles = sum(
        isinstance(row.get("primary_mean_weekly_net_spread"), (int, float))
        and row["primary_mean_weekly_net_spread"] > 0
        for row in quartiles
    )
    reasons = [
        f"signaled_observations={signal_count} (minimum {MIN_SIGNALLED_FOR_PLAUSIBILITY})",
        f"primary_signaled_mean_net={mean_sig}",
        f"primary_mean_weekly_net_spread={mean_spread} (target >= {MIN_PRIMARY_SPREAD})",
        f"positive_primary_quartiles={positive_quartiles}/4 (target >= 3)",
    ]
    if not isinstance(mean_sig, (int, float)) or not isinstance(mean_spread, (int, float)):
        return "MARGINAL_OR_UNSTABLE", reasons
    if mean_sig <= 0 or mean_spread <= 0:
        return "NOT_ECONOMICALLY_PLAUSIBLE", reasons
    if (
        signal_count >= MIN_SIGNALLED_FOR_PLAUSIBILITY
        and mean_spread >= MIN_PRIMARY_SPREAD
        and positive_quartiles >= 3
    ):
        return "ECONOMICALLY_PLAUSIBLE", reasons
    return "MARGINAL_OR_UNSTABLE", reasons


def build_summary(
    observations: Sequence[Mapping[str, Any]],
    *,
    source_fetches: int,
    source_errors: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gross_obs, gross_weekly = gross_metrics(observations)
    scenarios = [
        scenario_metric(observations, notional=notional, stress_bps=stress)
        for notional in POSITION_NOTIONALS
        for stress in STRESS_BPS
    ]
    primary = next(
        row for row in scenarios
        if row["notional"] == PRIMARY_NOTIONAL and row["stress_bps_per_leg"] == PRIMARY_STRESS_BPS
    )
    quartiles = quartile_metrics(observations)
    classification, reasons = classify_feasibility(observations, primary, quartiles)
    grouped = group_by_anchor(observations)
    summary = {
        "research_status": "DISCOVERY_SAMPLE_ECONOMIC_FEASIBILITY_NOT_CONFIRMATORY",
        "hypothesis_id": hyp.HYPOTHESIS_ID,
        "source": "audited_tornsy_d1",
        "generated_at_utc": iso_utc(),
        "discovery_outcome_cutoff_utc": f"{DISCOVERY_OUTCOME_CUTOFF.isoformat()}T00:00:00Z",
        "universe_size": 35,
        "source_fetches": source_fetches,
        "source_errors": source_errors,
        "eligible_observations": len(observations),
        "signaled_observations": sum(bool(row.get("condition_met")) for row in observations),
        "non_signaled_observations": sum(not bool(row.get("condition_met")) for row in observations),
        "cohorts_with_eligible_observations": len(grouped),
        "cohorts_with_cross_sectional_spread": len(weekly_spreads(observations, "gross_return")),
        "gross_observation_metrics": gross_obs,
        "gross_weekly_cross_sectional_metrics": gross_weekly,
        "scenario_metrics": scenarios,
        "chronological_quartiles": quartiles,
        "primary_scenario": {
            "notional": PRIMARY_NOTIONAL,
            "stress_bps_per_leg": PRIMARY_STRESS_BPS,
            "fee_rule": "ceil(0.001 * stressed_sale_gross)",
            "spread_unit": "equal_weight_mean_of_within_Thursday_cross_sectional_spreads",
        },
        "feasibility_classification": classification,
        "classification_reasons": reasons,
        "claim_boundary": (
            "Historical discovery-sample triage only. This result cannot confirm HYP-001, establish out-of-sample alpha, "
            "or authorize a trading recommendation."
        ),
        "execution_note": (
            "Full historical +1-minute fills are unavailable. Fixed adverse bps stress is used only for economic triage; "
            "future execution-aware validation must use current/+1-minute observations where available."
        ),
    }
    annual = annual_rows(observations)
    assert_safe_summary(summary)
    return summary, annual


def assert_safe_summary(summary: Mapping[str, Any]) -> None:
    if set(summary) != SUMMARY_KEYS:
        raise ResearchToolError("Unexpected economic-feasibility summary fields.")
    if summary.get("research_status") != "DISCOVERY_SAMPLE_ECONOMIC_FEASIBILITY_NOT_CONFIRMATORY":
        raise ResearchToolError("Economic-feasibility result must remain non-confirmatory.")
    if summary.get("hypothesis_id") != hyp.HYPOTHESIS_ID:
        raise ResearchToolError("Unexpected hypothesis ID.")
    if summary.get("universe_size") != 35:
        raise ResearchToolError("Unexpected universe size.")
    if set(summary.get("gross_observation_metrics", {})) != GROSS_OBS_KEYS:
        raise ResearchToolError("Unexpected gross observation schema.")
    if set(summary.get("gross_weekly_cross_sectional_metrics", {})) != GROSS_WEEKLY_KEYS:
        raise ResearchToolError("Unexpected weekly gross schema.")
    scenarios = summary.get("scenario_metrics")
    if not isinstance(scenarios, list) or len(scenarios) != len(POSITION_NOTIONALS) * len(STRESS_BPS):
        raise ResearchToolError("Unexpected scenario grid.")
    for row in scenarios:
        if not isinstance(row, Mapping) or set(row) != SCENARIO_KEYS:
            raise ResearchToolError("Unsafe scenario row.")
    quartiles = summary.get("chronological_quartiles")
    if not isinstance(quartiles, list) or len(quartiles) != 4:
        raise ResearchToolError("Expected four chronological quartiles.")
    for row in quartiles:
        if not isinstance(row, Mapping) or set(row) != QUARTILE_KEYS:
            raise ResearchToolError("Unsafe quartile row.")
    if summary.get("feasibility_classification") not in {
        "ECONOMICALLY_PLAUSIBLE", "MARGINAL_OR_UNSTABLE", "NOT_ECONOMICALLY_PLAUSIBLE"
    }:
        raise ResearchToolError("Unexpected feasibility classification.")
    if not isinstance(summary.get("classification_reasons"), list):
        raise ResearchToolError("Classification reasons must be a list.")


def write_annual(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = [
        "year", "cohort_count", "eligible_observations", "signaled_count", "non_signaled_count",
        "signaled_mean_gross", "non_signaled_mean_gross", "mean_weekly_gross_spread",
        "primary_mean_weekly_net_spread",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})


def run(args: argparse.Namespace) -> int:
    symbols = hyp.load_symbols(Path(args.manifest))
    client = TornsyClient()
    rows_by_symbol: dict[str, Sequence[Mapping[str, Any]]] = {}
    errors: list[str] = []
    fetches = 0
    for symbol in symbols:
        try:
            _, rows = fetch_daily(client, symbol)
            rows_by_symbol[symbol] = rows
            fetches += 1
        except ResearchToolError as exc:
            errors.append(f"{symbol}: {str(exc)[:160]}")
        time.sleep(args.request_delay)
    if errors:
        raise ResearchToolError(f"HYP-001 economic feasibility source incomplete: {len(errors)} errors; no evidence written")
    observations = build_observations(rows_by_symbol)
    if not observations:
        raise ResearchToolError("No eligible HYP-001 discovery observations were produced.")
    summary, annual = build_summary(observations, source_fetches=fetches, source_errors=0)
    output = Path(args.output)
    annual_path = Path(args.annual_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_annual(annual_path, annual)
    print(json.dumps({
        "classification": summary["feasibility_classification"],
        "eligible_observations": summary["eligible_observations"],
        "signaled_observations": summary["signaled_observations"],
        "primary": next(
            row for row in summary["scenario_metrics"]
            if row["notional"] == PRIMARY_NOTIONAL and row["stress_bps_per_leg"] == PRIMARY_STRESS_BPS
        ),
    }, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run HYP-001 historical economic feasibility audit")
    parser.add_argument("--manifest", default="research/external_driver_candidates.json")
    parser.add_argument("--output", default="research/output/hyp001_economic_feasibility/summary.json")
    parser.add_argument("--annual-output", default="research/output/hyp001_economic_feasibility/annual.csv")
    parser.add_argument("--request-delay", type=float, default=DEFAULT_REQUEST_DELAY)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.request_delay < 0:
            raise ResearchToolError("request delay cannot be negative")
        return run(args)
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
