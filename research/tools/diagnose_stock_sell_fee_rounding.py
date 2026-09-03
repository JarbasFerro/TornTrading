#!/usr/bin/env python3
"""Diagnose Torn stock-sale fee-rounding anomalies without publishing trades.

This second-stage instrument is explicitly diagnostic. It follows official Torn
API v2 pagination across a fixed recent window, reuses the already-frozen 25 fee
models, and emits only aggregate diagnostics. It does not revise the failed
confirmatory acceptance rule and does not perform Torn game actions.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

import analyze_stock_sell_fee_rounding as base
from torn_research import ResearchToolError, TornApiClient, iso_utc

LOOKBACK_DAYS = 365
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_ROWS = PAGE_SIZE * MAX_PAGES
REFERENCE_MODEL = "total_value__fee_ceiling"
ALLOWED_NEXT_QUERY_KEYS = {"log", "from", "to", "sort", "limit"}

REPORT_KEYS = {
    "research_status",
    "source",
    "retrieved_at_utc",
    "lookback_days",
    "page_size",
    "max_pages",
    "max_rows",
    "pages_fetched",
    "history_exhausted_within_cap",
    "usable_observations",
    "rejected_observations",
    "duplicate_event_ids_discarded",
    "candidate_model_count",
    "globally_discriminating_observations",
    "model_results",
    "prediction_equivalence_classes",
    "perfect_models",
    "winner_minimum_pairwise_separation",
    "reference_ceiling_diagnostic",
    "logged_price_decimal_place_counts",
    "diagnostic_conclusion",
    "privacy_note",
}
MODEL_RESULT_KEYS = {"model", "matches", "mismatches", "match_rate"}
EQUIVALENCE_KEYS = {"models", "class_size"}
REFERENCE_KEYS = {
    "model",
    "matches",
    "mismatches",
    "match_rate",
    "residual_direction_counts",
    "absolute_residual_bucket_counts",
    "chronological_quartiles",
    "mismatch_precision_interval_reconciliation",
}
QUARTILE_KEYS = {"quartile", "observations", "mismatches"}
DIRECTION_KEYS = {"negative", "zero", "positive"}
ABS_BUCKET_KEYS = {"one", "two_to_five", "six_plus"}
RECONCILIATION_KEYS = {"nearest_half_quantum", "downward_truncation_quantum", "either"}


@dataclass(frozen=True)
class DiagnosticSale:
    sale: base.SaleObservation
    timestamp: int
    event_id: str
    price_quantum: Decimal


def price_quantum(price: Decimal) -> Decimal:
    exponent = price.as_tuple().exponent
    return Decimal(1).scaleb(exponent) if exponent < 0 else Decimal(1)


def parse_diagnostic_sale(entry: Any) -> DiagnosticSale | None:
    sale = base.parse_sale_entry(entry)
    if sale is None or not isinstance(entry, Mapping):
        return None
    raw_id = entry.get("id")
    raw_timestamp = entry.get("timestamp")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    try:
        timestamp = int(raw_timestamp)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return DiagnosticSale(
        sale=sale,
        timestamp=timestamp,
        event_id=raw_id,
        price_quantum=price_quantum(sale.price),
    )


def next_page_params(payload: Any, *, window_start: int, window_end: int) -> dict[str, Any] | None:
    if not isinstance(payload, Mapping):
        raise ResearchToolError("Expected mapping response for pagination.")
    metadata = payload.get("_metadata")
    links = metadata.get("links") if isinstance(metadata, Mapping) else None
    next_link = links.get("next") if isinstance(links, Mapping) else None
    if next_link is None:
        return None
    if not isinstance(next_link, str) or not next_link:
        raise ResearchToolError("Unexpected non-string next pagination link.")

    parsed = urlparse(next_link)
    if parsed.scheme and parsed.scheme != "https":
        raise ResearchToolError("Refusing non-HTTPS pagination link.")
    if parsed.netloc and parsed.netloc != "api.torn.com":
        raise ResearchToolError("Refusing pagination link outside api.torn.com.")
    if not parsed.path.endswith("/user/log"):
        raise ResearchToolError("Unexpected pagination path for user logs.")

    raw = parse_qs(parsed.query, keep_blank_values=False)
    params: dict[str, Any] = {
        "log": str(base.SELL_LOG_TYPE_ID),
        "from": window_start,
        "to": window_end,
        "sort": "DESC",
        "limit": PAGE_SIZE,
    }
    for key in ALLOWED_NEXT_QUERY_KEYS:
        values = raw.get(key)
        if values:
            params[key] = values[-1]

    try:
        log_id = int(params["log"])
        from_ts = int(params["from"])
        to_ts = int(params["to"])
        limit = int(params["limit"])
    except (TypeError, ValueError):
        raise ResearchToolError("Pagination link contained invalid numeric parameters.") from None

    if log_id != base.SELL_LOG_TYPE_ID:
        raise ResearchToolError("Pagination link changed the frozen sell-log type.")
    if not window_start <= from_ts <= window_end:
        raise ResearchToolError("Pagination link moved `from` outside the frozen window.")
    if not window_start <= to_ts <= window_end:
        raise ResearchToolError("Pagination link moved `to` outside the frozen window.")
    if from_ts > to_ts:
        raise ResearchToolError("Pagination link has from > to.")
    if not 1 <= limit <= PAGE_SIZE:
        raise ResearchToolError("Pagination link exceeded the frozen page size.")
    if str(params.get("sort", "DESC")).upper() != "DESC":
        raise ResearchToolError("Pagination link changed frozen descending sort order.")

    return {
        "log": str(log_id),
        "from": from_ts,
        "to": to_ts,
        "sort": "DESC",
        "limit": limit,
    }


def collect_paginated_sales(client: TornApiClient, *, window_start: int, window_end: int) -> tuple[list[DiagnosticSale], int, int, bool, int]:
    params: dict[str, Any] | None = {
        "log": str(base.SELL_LOG_TYPE_ID),
        "from": window_start,
        "to": window_end,
        "sort": "DESC",
        "limit": PAGE_SIZE,
    }
    observations: list[DiagnosticSale] = []
    seen_event_ids: set[str] = set()
    rejected = 0
    duplicates = 0
    pages = 0
    exhausted = False

    while params is not None and pages < MAX_PAGES and len(observations) < MAX_ROWS:
        response = client.get("/user/log", params)
        payload = response.payload
        if not isinstance(payload, Mapping) or not isinstance(payload.get("log"), list):
            raise ResearchToolError("Expected current Torn API v2 UserLogsResponse.log array.")
        pages += 1

        new_unique = 0
        for entry in payload["log"]:
            parsed = parse_diagnostic_sale(entry)
            if parsed is None:
                rejected += 1
                continue
            if parsed.event_id in seen_event_ids:
                duplicates += 1
                continue
            seen_event_ids.add(parsed.event_id)
            observations.append(parsed)
            new_unique += 1
            if len(observations) >= MAX_ROWS:
                break

        next_params = next_page_params(payload, window_start=window_start, window_end=window_end)
        if next_params is None:
            exhausted = True
            break
        if not payload["log"] or new_unique == 0:
            raise ResearchToolError("Pagination failed to advance to new unique sell logs.")
        params = next_params

    return observations, rejected, duplicates, exhausted, pages


def model_diagnostics(observations: Sequence[DiagnosticSale]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], int, int | None]:
    sales = [obs.sale for obs in observations]
    models = base.build_models()
    vectors = base.prediction_vectors(sales, models)
    observed_fees = tuple(obs.fee for obs in sales)
    rows: list[dict[str, Any]] = []
    perfect: list[str] = []
    for model in models:
        vector = vectors[model.name]
        matches = sum(predicted == observed for predicted, observed in zip(vector, observed_fees))
        mismatches = len(sales) - matches
        if sales and mismatches == 0:
            perfect.append(model.name)
        rows.append({
            "model": model.name,
            "matches": matches,
            "mismatches": mismatches,
            "match_rate": round(matches / len(sales), 6) if sales else None,
        })
    discrim = base.discriminating_observation_count(vectors)
    classes = base.equivalence_classes(vectors)
    winner_sep = base.minimum_pairwise_separation(vectors, perfect[0]) if len(perfect) == 1 else None
    return rows, classes, sorted(perfect), discrim, winner_sep


def _ceil_fee_at(price: Decimal, amount: int) -> int:
    return base.round_integer(price * Decimal(amount) * base.FEE_RATE, "ceiling")


def precision_interval_reconciles(obs: DiagnosticSale, mode: str) -> bool:
    p = obs.sale.price
    q = obs.price_quantum
    if mode == "nearest_half_quantum":
        low = max(Decimal(0), p - q / Decimal(2))
        high = p + q / Decimal(2)
    elif mode == "downward_truncation_quantum":
        low = p
        high = p + q
    else:
        raise ValueError("unknown precision interval mode")
    minimum = _ceil_fee_at(low, obs.sale.amount)
    maximum = _ceil_fee_at(high, obs.sale.amount)
    return minimum <= obs.sale.fee <= maximum


def chronological_quartiles(observations: Sequence[DiagnosticSale], reference_predictions: Sequence[int]) -> list[dict[str, Any]]:
    paired = sorted(zip(observations, reference_predictions), key=lambda item: item[0].timestamp)
    counts = [0, 0, 0, 0]
    mismatches = [0, 0, 0, 0]
    n = len(paired)
    for index, (obs, prediction) in enumerate(paired):
        quartile = min(3, (index * 4) // max(1, n))
        counts[quartile] += 1
        if obs.sale.fee != prediction:
            mismatches[quartile] += 1
    labels = ["Q1_oldest", "Q2", "Q3", "Q4_newest"]
    return [
        {"quartile": labels[i], "observations": counts[i], "mismatches": mismatches[i]}
        for i in range(4)
    ]


def decimal_place_counts(observations: Sequence[DiagnosticSale]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for obs in observations:
        exponent = obs.sale.price.as_tuple().exponent
        places = max(0, -exponent)
        label = str(places) if places <= 8 else "9_plus"
        counts[label] = counts.get(label, 0) + 1
    def sort_key(row: tuple[str, int]) -> tuple[int, str]:
        label = row[0]
        return (9 if label == "9_plus" else int(label), label)
    return [
        {"decimal_places": label, "observations": count}
        for label, count in sorted(counts.items(), key=sort_key)
    ]


def reference_ceiling_diagnostic(observations: Sequence[DiagnosticSale]) -> dict[str, Any]:
    model_by_name = {model.name: model for model in base.build_models()}
    reference = model_by_name[REFERENCE_MODEL]
    predictions = [reference.predict(obs.sale) for obs in observations]
    residuals = [obs.sale.fee - prediction for obs, prediction in zip(observations, predictions)]
    matches = sum(residual == 0 for residual in residuals)
    mismatches = len(residuals) - matches

    directions = {
        "negative": sum(residual < 0 for residual in residuals),
        "zero": matches,
        "positive": sum(residual > 0 for residual in residuals),
    }
    abs_buckets = {
        "one": sum(abs(residual) == 1 for residual in residuals if residual != 0),
        "two_to_five": sum(2 <= abs(residual) <= 5 for residual in residuals),
        "six_plus": sum(abs(residual) >= 6 for residual in residuals),
    }

    mismatch_obs = [obs for obs, residual in zip(observations, residuals) if residual != 0]
    nearest = sum(precision_interval_reconciles(obs, "nearest_half_quantum") for obs in mismatch_obs)
    truncation = sum(precision_interval_reconciles(obs, "downward_truncation_quantum") for obs in mismatch_obs)
    either = sum(
        precision_interval_reconciles(obs, "nearest_half_quantum")
        or precision_interval_reconciles(obs, "downward_truncation_quantum")
        for obs in mismatch_obs
    )

    return {
        "model": REFERENCE_MODEL,
        "matches": matches,
        "mismatches": mismatches,
        "match_rate": round(matches / len(observations), 6) if observations else None,
        "residual_direction_counts": directions,
        "absolute_residual_bucket_counts": abs_buckets,
        "chronological_quartiles": chronological_quartiles(observations, predictions),
        "mismatch_precision_interval_reconciliation": {
            "nearest_half_quantum": nearest,
            "downward_truncation_quantum": truncation,
            "either": either,
        },
    }


def build_report(
    observations: Sequence[DiagnosticSale],
    *,
    rejected: int,
    duplicates: int,
    pages: int,
    exhausted: bool,
    retrieved_at: str,
) -> dict[str, Any]:
    model_results, classes, perfect, discrim, winner_sep = model_diagnostics(observations)
    reference = reference_ceiling_diagnostic(observations)

    if not observations:
        conclusion = "NO_USABLE_OBSERVATIONS"
    elif reference["mismatches"] == 0 and len(perfect) == 1:
        conclusion = "EXPANDED_HISTORY_HAS_UNIQUE_PERFECT_MODEL"
    elif reference["mismatches"] == 0:
        conclusion = "CEILING_REFERENCE_PERFECT_BUT_MODEL_ORDER_UNRESOLVED"
    elif reference["mismatch_precision_interval_reconciliation"]["either"] == reference["mismatches"]:
        conclusion = "ALL_CEILING_MISMATCHES_COMPATIBLE_WITH_LOGGED_PRICE_PRECISION_HYPOTHESES"
    else:
        conclusion = "CEILING_MISMATCHES_NOT_FULLY_EXPLAINED_BY_TESTED_PRICE_PRECISION_HYPOTHESES"

    report = {
        "research_status": "DIAGNOSTIC_AGGREGATE_HISTORICAL_OBSERVATION",
        "source": "official_torn_api_v2_user_log_5511_paginated",
        "retrieved_at_utc": retrieved_at,
        "lookback_days": LOOKBACK_DAYS,
        "page_size": PAGE_SIZE,
        "max_pages": MAX_PAGES,
        "max_rows": MAX_ROWS,
        "pages_fetched": pages,
        "history_exhausted_within_cap": exhausted,
        "usable_observations": len(observations),
        "rejected_observations": rejected,
        "duplicate_event_ids_discarded": duplicates,
        "candidate_model_count": len(base.build_models()),
        "globally_discriminating_observations": discrim,
        "model_results": model_results,
        "prediction_equivalence_classes": classes,
        "perfect_models": perfect,
        "winner_minimum_pairwise_separation": winner_sep,
        "reference_ceiling_diagnostic": reference,
        "logged_price_decimal_place_counts": decimal_place_counts(observations),
        "diagnostic_conclusion": conclusion,
        "privacy_note": (
            "No raw logs, event IDs, event timestamps, stock IDs, share counts, observed prices, observed fees, profits, "
            "losses, monetary totals, exact event dates, or per-trade predictions are persisted. Event IDs/timestamps "
            "are used transiently only for pagination integrity, deduplication, and coarse chronological quartiles."
        ),
    }
    assert_safe_report(report)
    return report


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != REPORT_KEYS:
        raise ResearchToolError("Diagnostic report contains an unexpected top-level field.")
    if report.get("research_status") != "DIAGNOSTIC_AGGREGATE_HISTORICAL_OBSERVATION":
        raise ResearchToolError("Unexpected diagnostic research status.")
    if report.get("source") != "official_torn_api_v2_user_log_5511_paginated":
        raise ResearchToolError("Unexpected diagnostic source.")
    for key, expected in (
        ("lookback_days", LOOKBACK_DAYS),
        ("page_size", PAGE_SIZE),
        ("max_pages", MAX_PAGES),
        ("max_rows", MAX_ROWS),
        ("candidate_model_count", len(base.build_models())),
    ):
        if report.get(key) != expected:
            raise ResearchToolError(f"Unexpected frozen value for {key}.")
    for key in (
        "pages_fetched",
        "usable_observations",
        "rejected_observations",
        "duplicate_event_ids_discarded",
        "globally_discriminating_observations",
    ):
        if not isinstance(report.get(key), int) or report[key] < 0:
            raise ResearchToolError(f"{key} must be a non-negative integer.")
    if not isinstance(report.get("history_exhausted_within_cap"), bool):
        raise ResearchToolError("history_exhausted_within_cap must be boolean.")
    winner_sep = report.get("winner_minimum_pairwise_separation")
    if winner_sep is not None and (not isinstance(winner_sep, int) or winner_sep < 0):
        raise ResearchToolError("winner_minimum_pairwise_separation must be null or a non-negative integer.")

    model_names = {model.name for model in base.build_models()}
    results = report.get("model_results")
    if not isinstance(results, list) or len(results) != len(model_names):
        raise ResearchToolError("Diagnostic model_results must contain the frozen model family.")
    seen: set[str] = set()
    usable = report["usable_observations"]
    for row in results:
        if not isinstance(row, Mapping) or set(row) != MODEL_RESULT_KEYS:
            raise ResearchToolError("Unsafe diagnostic model result structure.")
        if row.get("model") not in model_names or row["model"] in seen:
            raise ResearchToolError("Unknown or duplicate diagnostic model.")
        seen.add(row["model"])
        if row.get("matches", -1) + row.get("mismatches", -1) != usable:
            raise ResearchToolError("Diagnostic match counts do not sum to usable observations.")

    classes = report.get("prediction_equivalence_classes")
    if not isinstance(classes, list):
        raise ResearchToolError("Diagnostic equivalence classes must be a list.")
    class_models: list[str] = []
    for row in classes:
        if not isinstance(row, Mapping) or set(row) != EQUIVALENCE_KEYS:
            raise ResearchToolError("Unsafe diagnostic equivalence structure.")
        names = row.get("models")
        if not isinstance(names, list) or not names or not all(name in model_names for name in names):
            raise ResearchToolError("Invalid diagnostic equivalence model list.")
        if row.get("class_size") != len(names):
            raise ResearchToolError("Incorrect diagnostic equivalence class size.")
        class_models.extend(names)
    if sorted(class_models) != sorted(model_names):
        raise ResearchToolError("Diagnostic equivalence classes must partition all models.")

    perfect = report.get("perfect_models")
    if not isinstance(perfect, list) or not all(name in model_names for name in perfect):
        raise ResearchToolError("Invalid diagnostic perfect_models.")

    reference = report.get("reference_ceiling_diagnostic")
    if not isinstance(reference, Mapping) or set(reference) != REFERENCE_KEYS:
        raise ResearchToolError("Unsafe reference ceiling diagnostic structure.")
    if reference.get("model") != REFERENCE_MODEL:
        raise ResearchToolError("Unexpected reference model.")
    if reference.get("matches", -1) + reference.get("mismatches", -1) != usable:
        raise ResearchToolError("Reference model counts do not sum to usable observations.")
    if not isinstance(reference.get("residual_direction_counts"), Mapping) or set(reference["residual_direction_counts"]) != DIRECTION_KEYS:
        raise ResearchToolError("Unsafe residual direction structure.")
    if sum(reference["residual_direction_counts"].values()) != usable:
        raise ResearchToolError("Residual direction counts do not sum to usable observations.")
    if not isinstance(reference.get("absolute_residual_bucket_counts"), Mapping) or set(reference["absolute_residual_bucket_counts"]) != ABS_BUCKET_KEYS:
        raise ResearchToolError("Unsafe absolute residual bucket structure.")
    if sum(reference["absolute_residual_bucket_counts"].values()) != reference["mismatches"]:
        raise ResearchToolError("Absolute residual buckets do not sum to reference mismatches.")
    quartiles = reference.get("chronological_quartiles")
    if not isinstance(quartiles, list) or len(quartiles) != 4:
        raise ResearchToolError("Expected four chronological quartiles.")
    if any(not isinstance(row, Mapping) or set(row) != QUARTILE_KEYS for row in quartiles):
        raise ResearchToolError("Unsafe chronological quartile structure.")
    if sum(row["observations"] for row in quartiles) != usable:
        raise ResearchToolError("Quartile observations do not sum to usable observations.")
    reconciliation = reference.get("mismatch_precision_interval_reconciliation")
    if not isinstance(reconciliation, Mapping) or set(reconciliation) != RECONCILIATION_KEYS:
        raise ResearchToolError("Unsafe precision reconciliation structure.")
    if any(not isinstance(value, int) or not 0 <= value <= reference["mismatches"] for value in reconciliation.values()):
        raise ResearchToolError("Invalid precision reconciliation count.")

    decimals = report.get("logged_price_decimal_place_counts")
    if not isinstance(decimals, list):
        raise ResearchToolError("logged_price_decimal_place_counts must be a list.")
    if sum(row.get("observations", -1) for row in decimals if isinstance(row, Mapping)) != usable:
        raise ResearchToolError("Decimal-place counts do not sum to usable observations.")
    for row in decimals:
        if not isinstance(row, Mapping) or set(row) != {"decimal_places", "observations"}:
            raise ResearchToolError("Unsafe decimal-place count structure.")
        if not isinstance(row["decimal_places"], str) or not isinstance(row["observations"], int) or row["observations"] < 0:
            raise ResearchToolError("Invalid decimal-place count row.")

    if not isinstance(report.get("diagnostic_conclusion"), str) or not isinstance(report.get("privacy_note"), str):
        raise ResearchToolError("Diagnostic narrative fields must be strings.")


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_report(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    window_end = base.resolve_server_timestamp(client)
    window_start = window_end - LOOKBACK_DAYS * 86400
    observations, rejected, duplicates, exhausted, pages = collect_paginated_sales(
        client,
        window_start=window_start,
        window_end=window_end,
    )
    report = build_report(
        observations,
        rejected=rejected,
        duplicates=duplicates,
        pages=pages,
        exhausted=exhausted,
        retrieved_at=iso_utc(),
    )
    write_report(Path(args.output), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose aggregate Torn stock-sale fee-rounding anomalies.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="research/output/fee_rounding_diagnostic/summary.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
