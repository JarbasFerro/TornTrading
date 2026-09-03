#!/usr/bin/env python3
"""Aggregate historical clues about Torn stock-sale execution timing.

Research-only diagnostic. Reads official Stock sell log timestamp/stock/price
transiently, compares the receipt price with exact previous/current/next Tornsy
minute prices, and persists aggregate coarse timing counts only.

No Torn game action is performed. This cannot close P0-E4 because historical
human click time and page-visible quote are unavailable.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from torn_research import ResearchToolError, TornApiClient, TornsyClient, extract_stock_rows, iso_utc, load_torn_api_key, parse_tornsy_rows

SELL_LOG_TYPE_ID = 5511
LOOKBACK_DAYS = 365
MAX_LOG_ROWS = 100
TORNSY_REQUEST_DELAY_SECONDS = 0.25
CENT = Decimal("0.01")

SECOND_BUCKETS = (
    ("S00_02", 0, 2),
    ("S03_09", 3, 9),
    ("S10_49", 10, 49),
    ("S50_59", 50, 59),
)
MATCH_PATTERNS = (
    "CURRENT_ONLY",
    "PREVIOUS_ONLY",
    "NEXT_ONLY",
    "PREVIOUS_CURRENT",
    "CURRENT_NEXT",
    "PREVIOUS_NEXT",
    "PREVIOUS_CURRENT_NEXT",
    "NONE",
)
REPORT_KEYS = {
    "research_status",
    "source",
    "retrieved_at_utc",
    "lookback_days",
    "official_sell_log_rows",
    "usable_sales",
    "rejected_sales",
    "unknown_stock_metadata",
    "tornsy_requests",
    "tornsy_errors",
    "source_incomplete_observations",
    "match_pattern_counts",
    "second_bins",
    "primary_early_boundary",
    "diagnostic_label",
    "interpretation",
    "privacy_note",
}
BIN_KEYS = {
    "bucket",
    "observations",
    "source_complete",
    "changed_boundary_observations",
    "changed_current_only",
    "changed_previous_only",
    "changed_other",
}
EARLY_KEYS = {"changed_boundary_observations", "current_only", "previous_only", "other"}


@dataclass(frozen=True)
class SaleEvent:
    timestamp: int
    stock_id: int
    logged_price: Decimal


@dataclass(frozen=True)
class ClassifiedEvent:
    bucket: str
    source_complete: bool
    match_pattern: str | None
    changed_boundary: bool


def decimal_price(value: Any) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError("missing price")
    try:
        price = Decimal(str(value).strip().replace("$", "").replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("invalid price") from exc
    if not price.is_finite() or price <= 0:
        raise ValueError("invalid price")
    return price.quantize(CENT)


def parse_sale(entry: Any) -> SaleEvent | None:
    if not isinstance(entry, Mapping):
        return None
    details = entry.get("details")
    data = entry.get("data")
    if not isinstance(details, Mapping) or not isinstance(data, Mapping):
        return None
    try:
        if int(details.get("id")) != SELL_LOG_TYPE_ID:
            return None
        timestamp = int(entry.get("timestamp"))
        stock_id = int(data.get("stock"))
        price = decimal_price(data.get("price"))
    except (TypeError, ValueError):
        return None
    if timestamp <= 0 or stock_id <= 0:
        return None
    return SaleEvent(timestamp=timestamp, stock_id=stock_id, logged_price=price)


def extract_sales(payload: Any) -> tuple[list[SaleEvent], int, int]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("log"), list):
        raise ResearchToolError("Expected current Torn API v2 UserLogsResponse.log array.")
    sales: list[SaleEvent] = []
    rejected = 0
    for entry in payload["log"]:
        parsed = parse_sale(entry)
        if parsed is None:
            rejected += 1
        else:
            sales.append(parsed)
    return sales, rejected, len(payload["log"])


def second_bucket(timestamp: int) -> str:
    second = int(timestamp) % 60
    for label, low, high in SECOND_BUCKETS:
        if low <= second <= high:
            return label
    raise AssertionError("unreachable second bucket")


def price_map(rows: Sequence[Mapping[str, Any]]) -> dict[int, Decimal]:
    result: dict[int, Decimal] = {}
    for row in rows:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            continue
        try:
            result[int(timestamp)] = decimal_price(row.get("price"))
        except ValueError:
            continue
    return result


def match_pattern(logged: Decimal, previous: Decimal, current: Decimal, next_price: Decimal) -> str:
    matches: list[str] = []
    if logged == previous:
        matches.append("PREVIOUS")
    if logged == current:
        matches.append("CURRENT")
    if logged == next_price:
        matches.append("NEXT")
    if not matches:
        return "NONE"
    key = "_".join(matches)
    mapping = {
        "PREVIOUS": "PREVIOUS_ONLY",
        "CURRENT": "CURRENT_ONLY",
        "NEXT": "NEXT_ONLY",
        "PREVIOUS_CURRENT": "PREVIOUS_CURRENT",
        "CURRENT_NEXT": "CURRENT_NEXT",
        "PREVIOUS_NEXT": "PREVIOUS_NEXT",
        "PREVIOUS_CURRENT_NEXT": "PREVIOUS_CURRENT_NEXT",
    }
    return mapping[key]


def classify_sale(sale: SaleEvent, minute_prices: Mapping[int, Decimal]) -> ClassifiedEvent:
    minute = (sale.timestamp // 60) * 60
    previous_ts = minute - 60
    current_ts = minute
    next_ts = minute + 60
    if not all(ts in minute_prices for ts in (previous_ts, current_ts, next_ts)):
        return ClassifiedEvent(
            bucket=second_bucket(sale.timestamp),
            source_complete=False,
            match_pattern=None,
            changed_boundary=False,
        )
    previous = minute_prices[previous_ts]
    current = minute_prices[current_ts]
    next_price = minute_prices[next_ts]
    return ClassifiedEvent(
        bucket=second_bucket(sale.timestamp),
        source_complete=True,
        match_pattern=match_pattern(sale.logged_price, previous, current, next_price),
        changed_boundary=previous != current,
    )


def empty_bin(label: str) -> dict[str, Any]:
    return {
        "bucket": label,
        "observations": 0,
        "source_complete": 0,
        "changed_boundary_observations": 0,
        "changed_current_only": 0,
        "changed_previous_only": 0,
        "changed_other": 0,
    }


def aggregate(events: Sequence[ClassifiedEvent], *, metadata: Mapping[str, int], retrieved_at: str) -> dict[str, Any]:
    pattern_counts = {name: 0 for name in MATCH_PATTERNS}
    bins = {label: empty_bin(label) for label, _, _ in SECOND_BUCKETS}
    source_incomplete = 0

    for event in events:
        row = bins[event.bucket]
        row["observations"] += 1
        if not event.source_complete:
            source_incomplete += 1
            continue
        row["source_complete"] += 1
        assert event.match_pattern is not None
        pattern_counts[event.match_pattern] += 1
        if event.changed_boundary:
            row["changed_boundary_observations"] += 1
            if event.match_pattern == "CURRENT_ONLY":
                row["changed_current_only"] += 1
            elif event.match_pattern == "PREVIOUS_ONLY":
                row["changed_previous_only"] += 1
            else:
                row["changed_other"] += 1

    early = bins["S00_02"]
    early_summary = {
        "changed_boundary_observations": early["changed_boundary_observations"],
        "current_only": early["changed_current_only"],
        "previous_only": early["changed_previous_only"],
        "other": early["changed_other"],
    }
    if early_summary["previous_only"] > 0:
        label = "PREVIOUS_MINUTE_RECEIPT_OBSERVED_IN_EARLY_POST_BOUNDARY_LOG_TIME"
        interpretation = (
            "At least one official sell receipt timestamped in the first three seconds of a changed minute matched "
            "the previous minute price only. This is a timing clue, not proof of the page-visible/click-time rule."
        )
    elif early_summary["changed_boundary_observations"] > 0 and early_summary["current_only"] == early_summary["changed_boundary_observations"]:
        label = "EARLY_CHANGED_BOUNDARY_RECEIPTS_ALL_MATCH_CURRENT_MINUTE"
        interpretation = (
            "All available first-three-second receipts at changed boundaries matched the current minute price. "
            "This is consistent with current-minute execution but is non-confirmatory without historical click time."
        )
    else:
        label = "NO_INFORMATIVE_EARLY_BOUNDARY_HISTORY"
        interpretation = (
            "The available historical sale receipts do not provide an unambiguous first-three-second changed-boundary clue. "
            "A controlled human boundary experiment remains necessary."
        )

    report = {
        "research_status": "DIAGNOSTIC_AGGREGATE_HISTORICAL_OBSERVATION",
        "source": "official_torn_user_log_5511_plus_reconciled_tornsy_m1",
        "retrieved_at_utc": retrieved_at,
        "lookback_days": LOOKBACK_DAYS,
        "official_sell_log_rows": metadata["official_sell_log_rows"],
        "usable_sales": metadata["usable_sales"],
        "rejected_sales": metadata["rejected_sales"],
        "unknown_stock_metadata": metadata["unknown_stock_metadata"],
        "tornsy_requests": metadata["tornsy_requests"],
        "tornsy_errors": metadata["tornsy_errors"],
        "source_incomplete_observations": source_incomplete,
        "match_pattern_counts": pattern_counts,
        "second_bins": [bins[label] for label, _, _ in SECOND_BUCKETS],
        "primary_early_boundary": early_summary,
        "diagnostic_label": label,
        "interpretation": interpretation,
        "privacy_note": (
            "Only aggregate coarse timing counts are persisted. No raw logs, event IDs/timestamps, exact seconds, "
            "stock identifiers, prices, amounts, fees, profits, or per-event classifications are written."
        ),
    }
    assert_safe_report(report)
    return report


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != REPORT_KEYS:
        raise ResearchToolError("Execution-timing report contains unexpected top-level fields.")
    if report.get("research_status") != "DIAGNOSTIC_AGGREGATE_HISTORICAL_OBSERVATION":
        raise ResearchToolError("Unexpected research status.")
    for key in (
        "lookback_days",
        "official_sell_log_rows",
        "usable_sales",
        "rejected_sales",
        "unknown_stock_metadata",
        "tornsy_requests",
        "tornsy_errors",
        "source_incomplete_observations",
    ):
        if not isinstance(report.get(key), int) or report[key] < 0:
            raise ResearchToolError(f"{key} must be a non-negative integer.")
    patterns = report.get("match_pattern_counts")
    if not isinstance(patterns, Mapping) or set(patterns) != set(MATCH_PATTERNS):
        raise ResearchToolError("Unexpected match-pattern schema.")
    if not all(isinstance(value, int) and value >= 0 for value in patterns.values()):
        raise ResearchToolError("Match-pattern counts must be non-negative integers.")
    rows = report.get("second_bins")
    if not isinstance(rows, list) or len(rows) != len(SECOND_BUCKETS):
        raise ResearchToolError("Unexpected second-bin structure.")
    expected_labels = [label for label, _, _ in SECOND_BUCKETS]
    for expected, row in zip(expected_labels, rows):
        if not isinstance(row, Mapping) or set(row) != BIN_KEYS or row.get("bucket") != expected:
            raise ResearchToolError("Unsafe second-bin row.")
        for key in BIN_KEYS - {"bucket"}:
            if not isinstance(row.get(key), int) or row[key] < 0:
                raise ResearchToolError("Second-bin counts must be non-negative integers.")
    early = report.get("primary_early_boundary")
    if not isinstance(early, Mapping) or set(early) != EARLY_KEYS:
        raise ResearchToolError("Unexpected early-boundary schema.")
    if not all(isinstance(value, int) and value >= 0 for value in early.values()):
        raise ResearchToolError("Early-boundary counts must be non-negative integers.")
    for key in ("source", "retrieved_at_utc", "diagnostic_label", "interpretation", "privacy_note"):
        if not isinstance(report.get(key), str) or not report[key]:
            raise ResearchToolError(f"{key} must be a non-empty string.")


def resolve_server_timestamp(client: TornApiClient) -> int:
    payload = client.get("/torn/timestamp").payload
    if not isinstance(payload, Mapping):
        raise ResearchToolError("Expected Torn timestamp response mapping.")
    raw = payload.get("timestamp")
    if raw is None and isinstance(payload.get("data"), Mapping):
        raw = payload["data"].get("timestamp")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ResearchToolError("No usable Torn server timestamp.") from None
    if value <= 0:
        raise ResearchToolError("Invalid Torn server timestamp.")
    return value


def stock_symbol_map(client: TornApiClient) -> dict[int, str]:
    payload = client.get("/torn/stocks", {"timestamp": int(time.time())}).payload
    result: dict[int, str] = {}
    for row in extract_stock_rows(payload):
        acronym = row.get("acronym")
        if isinstance(acronym, str) and acronym.isalpha():
            result[int(row["id"])] = acronym.upper()
    if not result:
        raise ResearchToolError("No stock ID/acronym mapping available.")
    return result


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    to_ts = resolve_server_timestamp(client)
    from_ts = to_ts - LOOKBACK_DAYS * 86400
    log_payload = client.get(
        "/user/log",
        {"log": str(SELL_LOG_TYPE_ID), "from": from_ts, "to": to_ts, "limit": MAX_LOG_ROWS},
    ).payload
    sales, rejected, raw_rows = extract_sales(log_payload)
    symbols = stock_symbol_map(client)
    tornsy = TornsyClient()

    classified: list[ClassifiedEvent] = []
    tornsy_requests = 0
    tornsy_errors = 0
    unknown_stock = 0
    cache: dict[tuple[str, int], dict[int, Decimal] | None] = {}

    for sale in sales:
        symbol = symbols.get(sale.stock_id)
        if symbol is None:
            unknown_stock += 1
            classified.append(ClassifiedEvent(second_bucket(sale.timestamp), False, None, False))
            continue
        minute = (sale.timestamp // 60) * 60
        cache_key = (symbol, minute)
        if cache_key not in cache:
            try:
                response = tornsy.get_stock(
                    symbol,
                    "m1",
                    from_ts=minute - 60,
                    to_ts=minute + 120,
                    limit=4,
                )
                tornsy_requests += 1
                cache[cache_key] = price_map(parse_tornsy_rows(response.payload, "m1"))
            except ResearchToolError:
                tornsy_requests += 1
                tornsy_errors += 1
                cache[cache_key] = None
            time.sleep(args.request_delay)
        prices = cache[cache_key]
        if prices is None:
            classified.append(ClassifiedEvent(second_bucket(sale.timestamp), False, None, False))
        else:
            classified.append(classify_sale(sale, prices))

    metadata = {
        "official_sell_log_rows": raw_rows,
        "usable_sales": len(sales),
        "rejected_sales": rejected,
        "unknown_stock_metadata": unknown_stock,
        "tornsy_requests": tornsy_requests,
        "tornsy_errors": tornsy_errors,
    }
    report = aggregate(classified, metadata=metadata, retrieved_at=iso_utc())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate historical Torn stock-sale execution-timing clues.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--request-delay", type=float, default=TORNSY_REQUEST_DELAY_SECONDS)
    parser.add_argument("--output", default="research/output/execution_timing_historical/summary.json")
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
