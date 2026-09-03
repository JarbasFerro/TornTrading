#!/usr/bin/env python3
"""Snapshot current official Torn prices and plan discriminating fee trials.

Read-only research tooling. Produces public experiment plans only and performs no
Torn game action. Every proposed price must still match the Torn UI immediately
before a human manually executes a sale.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import analyze_stock_sell_fee_rounding as fee
import plan_stock_fee_rounding_trial as planner
from torn_research import ResearchToolError, TornApiClient, extract_stock_rows, iso_utc

MAX_GROSS = Decimal("5000")
MAX_SHARES = 1000
PER_STOCK_LIMIT = 100
PER_K_OUTPUT_LIMIT = 10
EXCLUDED_SYMBOLS = {"TCSE"}


@dataclass(frozen=True)
class PublicCandidate:
    stock_id: int
    stock_acronym: str
    stock_name: str
    planned_price: str
    shares: int
    boundary_multiplier: int
    displayed_gross: str
    conservative_gross_low: str
    conservative_gross_high: str
    lower_margin: str
    upper_margin: str
    worst_margin: str
    reference_fee: int
    competing_fee: int


def official_price(stock: Mapping[str, Any]) -> Decimal:
    market = stock.get("market")
    if not isinstance(market, Mapping) or market.get("price") is None:
        raise ValueError("stock has no market.price")
    try:
        raw = Decimal(str(market["price"]))
    except InvalidOperation as exc:
        raise ValueError("invalid market.price") from exc
    if not raw.is_finite() or raw <= 0:
        raise ValueError("invalid market.price")
    return raw.quantize(Decimal("0.01"))


def stock_identity(stock: Mapping[str, Any]) -> tuple[int, str, str]:
    try:
        stock_id = int(stock["id"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("stock has no usable id") from None
    symbol = str(stock.get("acronym", "")).strip().upper()
    name = str(stock.get("name", "")).strip()
    if stock_id <= 0 or not symbol or not name:
        raise ValueError("stock identity is incomplete")
    return stock_id, symbol, name


def public_candidate(stock: Mapping[str, Any], row: planner.TrialCandidate, price: Decimal) -> PublicCandidate:
    stock_id, symbol, name = stock_identity(stock)
    lower = Decimal(row.lower_margin)
    upper = Decimal(row.upper_margin)
    return PublicCandidate(
        stock_id=stock_id,
        stock_acronym=symbol,
        stock_name=name,
        planned_price=format(price, ".2f"),
        shares=row.shares,
        boundary_multiplier=row.boundary_multiplier,
        displayed_gross=row.displayed_gross,
        conservative_gross_low=row.conservative_gross_low,
        conservative_gross_high=row.conservative_gross_high,
        lower_margin=row.lower_margin,
        upper_margin=row.upper_margin,
        worst_margin=format(min(lower, upper), "f"),
        reference_fee=row.reference_unrounded_total_ceiling_fee,
        competing_fee=row.competing_rounded_gross_or_non_ceiling_fee,
    )


def build_candidates(stocks: Sequence[Mapping[str, Any]]) -> list[PublicCandidate]:
    best_by_stock_k: dict[tuple[int, int], PublicCandidate] = {}
    for stock in stocks:
        try:
            stock_id, symbol, _ = stock_identity(stock)
            if symbol in EXCLUDED_SYMBOLS:
                continue
            price = official_price(stock)
        except ValueError:
            continue
        rows = planner.find_candidates(
            price,
            max_shares=MAX_SHARES,
            max_gross=MAX_GROSS,
            limit=PER_STOCK_LIMIT,
        )
        for row in rows:
            candidate = public_candidate(stock, row, price)
            key = (stock_id, row.boundary_multiplier)
            previous = best_by_stock_k.get(key)
            if previous is None:
                best_by_stock_k[key] = candidate
                continue
            new_margin = Decimal(candidate.worst_margin)
            old_margin = Decimal(previous.worst_margin)
            if new_margin > old_margin or (
                new_margin == old_margin and Decimal(candidate.displayed_gross) < Decimal(previous.displayed_gross)
            ):
                best_by_stock_k[key] = candidate
    return list(best_by_stock_k.values())


def grouped_candidates(candidates: Sequence[PublicCandidate]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[int, list[PublicCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.boundary_multiplier, []).append(candidate)
    result: dict[str, list[dict[str, Any]]] = {}
    for k in sorted(groups):
        rows = sorted(
            groups[k],
            key=lambda c: (-Decimal(c.worst_margin), Decimal(c.displayed_gross), c.stock_acronym),
        )[:PER_K_OUTPUT_LIMIT]
        result[str(k)] = [asdict(row) for row in rows]
    return result


def choose_suggested_six(candidates: Sequence[PublicCandidate]) -> list[dict[str, Any]]:
    groups: dict[int, list[PublicCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.boundary_multiplier, []).append(candidate)
    for k in groups:
        groups[k].sort(key=lambda c: (-Decimal(c.worst_margin), Decimal(c.displayed_gross), c.stock_acronym))

    eligible_ks = [k for k in sorted(groups) if len({c.stock_id for c in groups[k]}) >= 2]
    if len(eligible_ks) < 3:
        return []

    # Lowest three available boundaries minimize capital. Choose two different
    # stocks per K and avoid reusing a stock across the six whenever possible.
    chosen: list[PublicCandidate] = []
    used_stocks: set[int] = set()
    for k in eligible_ks[:3]:
        picks: list[PublicCandidate] = []
        for candidate in groups[k]:
            if candidate.stock_id in used_stocks:
                continue
            picks.append(candidate)
            if len(picks) == 2:
                break
        if len(picks) < 2:
            for candidate in groups[k]:
                if candidate in picks:
                    continue
                picks.append(candidate)
                if len(picks) == 2:
                    break
        if len(picks) < 2:
            return []
        chosen.extend(picks)
        used_stocks.update(candidate.stock_id for candidate in picks)

    if len({candidate.boundary_multiplier for candidate in chosen}) < 3:
        return []
    if any(sum(other.stock_id == candidate.stock_id for other in chosen) > 3 for candidate in chosen):
        return []
    return [asdict(candidate) for candidate in chosen]


def build_report(stocks: Sequence[Mapping[str, Any]], *, server_timestamp: int, retrieved_at: str) -> dict[str, Any]:
    candidates = build_candidates(stocks)
    report = {
        "research_status": "LIVE_PUBLIC_EXPERIMENT_PLAN_SNAPSHOT",
        "source": "official_torn_api_v2_torn_stocks",
        "server_timestamp": server_timestamp,
        "retrieved_at_utc": retrieved_at,
        "tradable_stock_rows_considered": sum(
            1 for stock in stocks if str(stock.get("acronym", "")).strip().upper() not in EXCLUDED_SYMBOLS
        ),
        "candidate_stock_boundary_pairs": len(candidates),
        "max_displayed_gross": format(MAX_GROSS, ".2f"),
        "candidates_by_boundary": grouped_candidates(candidates),
        "suggested_six": choose_suggested_six(candidates),
        "validity_note": (
            "This snapshot is only a pre-click plan source. A candidate may be executed manually only if the Torn UI/current "
            "official price immediately before the click exactly equals planned_price and all controls in research/25_"
            "FEE_ROUNDING_TARGETED_CONFIRMATION.md are followed. If price changed, discard the stale candidate and replan."
        ),
        "compliance_note": "Read-only API collection and calculation only; no Torn buy/sell action is submitted.",
    }
    assert_safe_report(report)
    return report


def assert_candidate(row: Mapping[str, Any]) -> None:
    required = {
        "stock_id", "stock_acronym", "stock_name", "planned_price", "shares", "boundary_multiplier",
        "displayed_gross", "conservative_gross_low", "conservative_gross_high", "lower_margin", "upper_margin",
        "worst_margin", "reference_fee", "competing_fee",
    }
    if set(row) != required:
        raise ResearchToolError("Unexpected candidate plan fields.")
    price = planner.parse_price(str(row["planned_price"]))
    candidate = planner.is_robust_candidate(price, int(row["shares"]))
    if candidate is None:
        raise ResearchToolError("Persisted candidate does not satisfy frozen robust geometry.")
    if int(row["boundary_multiplier"]) != candidate.boundary_multiplier:
        raise ResearchToolError("Persisted candidate K differs from planner result.")
    if int(row["reference_fee"]) != candidate.reference_unrounded_total_ceiling_fee:
        raise ResearchToolError("Persisted reference fee differs from planner result.")
    if int(row["competing_fee"]) != candidate.competing_rounded_gross_or_non_ceiling_fee:
        raise ResearchToolError("Persisted competing fee differs from planner result.")


def assert_safe_report(report: Mapping[str, Any]) -> None:
    expected = {
        "research_status", "source", "server_timestamp", "retrieved_at_utc", "tradable_stock_rows_considered",
        "candidate_stock_boundary_pairs", "max_displayed_gross", "candidates_by_boundary", "suggested_six",
        "validity_note", "compliance_note",
    }
    if set(report) != expected:
        raise ResearchToolError("Unexpected live candidate snapshot fields.")
    if report.get("research_status") != "LIVE_PUBLIC_EXPERIMENT_PLAN_SNAPSHOT":
        raise ResearchToolError("Unexpected research status.")
    if report.get("source") != "official_torn_api_v2_torn_stocks":
        raise ResearchToolError("Unexpected source.")
    if not isinstance(report.get("server_timestamp"), int) or report["server_timestamp"] <= 0:
        raise ResearchToolError("Invalid server timestamp.")
    groups = report.get("candidates_by_boundary")
    if not isinstance(groups, Mapping):
        raise ResearchToolError("Candidate groups must be a mapping.")
    total = 0
    for key, rows in groups.items():
        try:
            k = int(key)
        except (TypeError, ValueError):
            raise ResearchToolError("Boundary group key must be an integer string.") from None
        if k < 1 or not isinstance(rows, list) or len(rows) > PER_K_OUTPUT_LIMIT:
            raise ResearchToolError("Invalid boundary candidate group.")
        for row in rows:
            if not isinstance(row, Mapping) or int(row.get("boundary_multiplier", -1)) != k:
                raise ResearchToolError("Candidate is in the wrong boundary group.")
            assert_candidate(row)
        total += len(rows)
    suggested = report.get("suggested_six")
    if not isinstance(suggested, list) or len(suggested) not in (0, 6):
        raise ResearchToolError("suggested_six must contain zero or six candidates.")
    for row in suggested:
        if not isinstance(row, Mapping):
            raise ResearchToolError("Invalid suggested candidate.")
        assert_candidate(row)
    if suggested:
        if len({row["boundary_multiplier"] for row in suggested}) < 3:
            raise ResearchToolError("Suggested set lacks three K boundaries.")
        if len({row["stock_id"] for row in suggested}) < 2:
            raise ResearchToolError("Suggested set lacks stock diversification.")
        for stock_id in {row["stock_id"] for row in suggested}:
            if sum(row["stock_id"] == stock_id for row in suggested) > 3:
                raise ResearchToolError("Suggested set exceeds per-stock cap.")
    if not isinstance(report.get("validity_note"), str) or not isinstance(report.get("compliance_note"), str):
        raise ResearchToolError("Narrative fields must be strings.")


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_report(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    server_timestamp = fee.resolve_server_timestamp(client)
    stock_response = client.get("/torn/stocks")
    stocks = extract_stock_rows(stock_response.payload)
    report = build_report(stocks, server_timestamp=server_timestamp, retrieved_at=iso_utc())
    write_report(Path(args.output), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Snapshot live public Torn stock prices and robust fee-trial plans.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="research/output/live_fee_trial_candidates/summary.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
