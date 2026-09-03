#!/usr/bin/env python3
"""Audit the six latest post-protocol Torn Stock sell receipts, aggregate-only.

This is a post-action observational audit, not a confirmatory experiment. Private
trade fields are used transiently and are never persisted in the report.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from typing import Any, Mapping, Sequence

import analyze_stock_sell_fee_rounding as base
from torn_research import ResearchToolError, TornApiClient, iso_utc

PROTOCOL_MERGE_TS = 1788415072
PROTOCOL_MERGE_COMMIT = "94370c891cb6decb4eb4c21ebf2705527ddd9e33"
TARGET_COUNT = 6
API_LIMIT = 100
PRICE_LOWER_DELTA = Decimal("0.005")
PRICE_UPPER_DELTA = Decimal("0.01")
BOUNDARY_STEP = Decimal("1000")
HALF_DOLLAR = Decimal("0.50")

REPORT_KEYS = {
    "research_status",
    "source",
    "retrieved_at_utc",
    "protocol_merge_commit",
    "post_protocol_usable_logs_returned",
    "selected_latest_sales",
    "distinct_stock_count",
    "stable_second_window_counts",
    "two_decimal_price_count",
    "targeted_geometry_count",
    "distinct_boundary_count_within_geometry",
    "targeted_geometry_fee_support",
    "logged_price_ceiling_match_count",
    "model_results",
    "audit_conclusion",
    "preclick_plan_recorded",
    "confirmatory_eligible",
    "confirmatory_blocker",
    "privacy_note",
}
MODEL_RESULT_KEYS = {"model", "matches", "mismatches"}
STABLE_KEYS = {"inside_15_40", "outside_15_40"}
SUPPORT_KEYS = {"ceiling_k_plus_1", "competitor_k", "other"}
CONCLUSIONS = {
    "INSUFFICIENT_POST_PROTOCOL_SALES",
    "SIX_SALES_OBSERVED_NONE_TARGET_GEOMETRY",
    "POST_ACTION_GEOMETRY_SUPPORTS_CEILING",
    "POST_ACTION_GEOMETRY_SUPPORTS_COMPETITOR",
    "POST_ACTION_GEOMETRY_MIXED_OR_UNEXPECTED",
}


@dataclass(frozen=True)
class PrivateSale:
    observation: base.SaleObservation
    timestamp: int
    stock_id: int


def parse_private_sale(entry: Any) -> PrivateSale | None:
    observation = base.parse_sale_entry(entry)
    if observation is None or not isinstance(entry, Mapping):
        return None
    data = entry.get("data")
    if not isinstance(data, Mapping):
        return None
    try:
        timestamp = int(entry["timestamp"])
        stock_id = int(data["stock"])
    except (KeyError, TypeError, ValueError):
        return None
    if timestamp < PROTOCOL_MERGE_TS or stock_id <= 0:
        return None
    return PrivateSale(observation=observation, timestamp=timestamp, stock_id=stock_id)


def select_latest_six(payload: Any) -> tuple[list[PrivateSale], int]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("log"), list):
        raise ResearchToolError("Expected current Torn API v2 UserLogsResponse.log array.")
    parsed = [sale for entry in payload["log"] if (sale := parse_private_sale(entry)) is not None]
    parsed.sort(key=lambda sale: sale.timestamp, reverse=True)
    return parsed[:TARGET_COUNT], len(parsed)


def exact_two_decimal(price: Decimal) -> bool:
    return price.as_tuple().exponent == -2


def boundary_geometry(sale: PrivateSale) -> tuple[bool, int]:
    obs = sale.observation
    gross = obs.price * Decimal(obs.amount)
    k = int((gross / BOUNDARY_STEP).to_integral_value(rounding=ROUND_FLOOR))
    if not exact_two_decimal(obs.price) or k < 1:
        return False, k
    boundary = BOUNDARY_STEP * Decimal(k)
    low_price = max(Decimal("0"), obs.price - PRICE_LOWER_DELTA)
    high_price = obs.price + PRICE_UPPER_DELTA
    gross_low = low_price * Decimal(obs.amount)
    gross_high = high_price * Decimal(obs.amount)
    return gross_low > boundary and gross_high < boundary + HALF_DOLLAR, k


def logged_price_ceiling_fee(obs: base.SaleObservation) -> int:
    value = obs.price * Decimal(obs.amount) * base.FEE_RATE
    return int(value.quantize(Decimal("1"), rounding=ROUND_CEILING))


def model_results(sales: Sequence[PrivateSale]) -> list[dict[str, Any]]:
    observations = [sale.observation for sale in sales]
    rows: list[dict[str, Any]] = []
    for model in base.build_models():
        matches = sum(model.predict(obs) == obs.fee for obs in observations)
        rows.append({
            "model": model.name,
            "matches": matches,
            "mismatches": len(observations) - matches,
        })
    return rows


def build_report(sales: Sequence[PrivateSale], *, usable_returned: int, retrieved_at: str) -> dict[str, Any]:
    stable_inside = sum(15 <= sale.timestamp % 60 <= 40 for sale in sales)
    two_decimal = sum(exact_two_decimal(sale.observation.price) for sale in sales)

    geometry: list[tuple[PrivateSale, int]] = []
    for sale in sales:
        qualifies, k = boundary_geometry(sale)
        if qualifies:
            geometry.append((sale, k))

    ceiling_support = sum(sale.observation.fee == k + 1 for sale, k in geometry)
    competitor_support = sum(sale.observation.fee == k for sale, k in geometry)
    other_support = len(geometry) - ceiling_support - competitor_support

    if len(sales) < TARGET_COUNT:
        conclusion = "INSUFFICIENT_POST_PROTOCOL_SALES"
    elif not geometry:
        conclusion = "SIX_SALES_OBSERVED_NONE_TARGET_GEOMETRY"
    elif ceiling_support == len(geometry):
        conclusion = "POST_ACTION_GEOMETRY_SUPPORTS_CEILING"
    elif competitor_support == len(geometry):
        conclusion = "POST_ACTION_GEOMETRY_SUPPORTS_COMPETITOR"
    else:
        conclusion = "POST_ACTION_GEOMETRY_MIXED_OR_UNEXPECTED"

    report = {
        "research_status": "POST_ACTION_OBSERVATIONAL_AUDIT",
        "source": "official_torn_api_v2_user_log_5511",
        "retrieved_at_utc": retrieved_at,
        "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
        "post_protocol_usable_logs_returned": usable_returned,
        "selected_latest_sales": len(sales),
        "distinct_stock_count": len({sale.stock_id for sale in sales}),
        "stable_second_window_counts": {
            "inside_15_40": stable_inside,
            "outside_15_40": len(sales) - stable_inside,
        },
        "two_decimal_price_count": two_decimal,
        "targeted_geometry_count": len(geometry),
        "distinct_boundary_count_within_geometry": len({k for _, k in geometry}),
        "targeted_geometry_fee_support": {
            "ceiling_k_plus_1": ceiling_support,
            "competitor_k": competitor_support,
            "other": other_support,
        },
        "logged_price_ceiling_match_count": sum(
            logged_price_ceiling_fee(sale.observation) == sale.observation.fee for sale in sales
        ),
        "model_results": model_results(sales),
        "audit_conclusion": conclusion,
        "preclick_plan_recorded": False,
        "confirmatory_eligible": False,
        "confirmatory_blocker": (
            "The frozen P0-E5 protocol requires stock, price, planner-selected shares, K, predictions, and attempt number "
            "to be recorded before each human click. No such pre-click record exists for these six already-completed sales."
        ),
        "privacy_note": (
            "No event IDs, exact trade timestamps, stock IDs, share counts, prices, observed fees, profits/losses, gross "
            "values, per-trade K values, per-trade classifications, or raw API payloads are persisted."
        ),
    }
    assert_safe_report(report)
    return report


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != REPORT_KEYS:
        raise ResearchToolError("Unexpected post-action audit report fields.")
    if report.get("research_status") != "POST_ACTION_OBSERVATIONAL_AUDIT":
        raise ResearchToolError("Unexpected research status.")
    if report.get("source") != "official_torn_api_v2_user_log_5511":
        raise ResearchToolError("Unexpected source.")
    if report.get("protocol_merge_commit") != PROTOCOL_MERGE_COMMIT:
        raise ResearchToolError("Unexpected protocol merge commit.")
    for key in (
        "post_protocol_usable_logs_returned",
        "selected_latest_sales",
        "distinct_stock_count",
        "two_decimal_price_count",
        "targeted_geometry_count",
        "distinct_boundary_count_within_geometry",
        "logged_price_ceiling_match_count",
    ):
        if not isinstance(report.get(key), int) or report[key] < 0:
            raise ResearchToolError(f"{key} must be a non-negative integer.")
    selected = report["selected_latest_sales"]
    if selected > TARGET_COUNT:
        raise ResearchToolError("Selected more than the frozen six-sale target.")
    stable = report.get("stable_second_window_counts")
    if not isinstance(stable, Mapping) or set(stable) != STABLE_KEYS or sum(stable.values()) != selected:
        raise ResearchToolError("Invalid stable-second aggregate.")
    support = report.get("targeted_geometry_fee_support")
    if not isinstance(support, Mapping) or set(support) != SUPPORT_KEYS:
        raise ResearchToolError("Invalid geometry fee-support aggregate.")
    if sum(support.values()) != report["targeted_geometry_count"]:
        raise ResearchToolError("Geometry fee-support counts do not sum correctly.")
    if report.get("audit_conclusion") not in CONCLUSIONS:
        raise ResearchToolError("Unexpected audit conclusion.")
    if report.get("preclick_plan_recorded") is not False or report.get("confirmatory_eligible") is not False:
        raise ResearchToolError("Post-action audit must remain non-confirmatory.")
    if not isinstance(report.get("confirmatory_blocker"), str) or not isinstance(report.get("privacy_note"), str):
        raise ResearchToolError("Narrative fields must be strings.")

    models = report.get("model_results")
    expected_names = {model.name for model in base.build_models()}
    if not isinstance(models, list) or len(models) != len(expected_names):
        raise ResearchToolError("Model results must contain the frozen family.")
    seen: set[str] = set()
    for row in models:
        if not isinstance(row, Mapping) or set(row) != MODEL_RESULT_KEYS:
            raise ResearchToolError("Unsafe model result structure.")
        name = row.get("model")
        if name not in expected_names or name in seen:
            raise ResearchToolError("Unknown or duplicate model result.")
        seen.add(name)
        if not isinstance(row.get("matches"), int) or not isinstance(row.get("mismatches"), int):
            raise ResearchToolError("Model counts must be integers.")
        if row["matches"] + row["mismatches"] != selected:
            raise ResearchToolError("Model counts do not sum to selected sales.")


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_report(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    server_ts = base.resolve_server_timestamp(client)
    response = client.get(
        "/user/log",
        {
            "log": str(base.SELL_LOG_TYPE_ID),
            "from": PROTOCOL_MERGE_TS,
            "to": server_ts,
            "limit": API_LIMIT,
        },
    )
    selected, usable_returned = select_latest_six(response.payload)
    report = build_report(selected, usable_returned=usable_returned, retrieved_at=iso_utc())
    write_report(Path(args.output), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate audit of six latest post-protocol Torn Stock sell receipts.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="research/output/post_action_six_sale_audit/summary.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
