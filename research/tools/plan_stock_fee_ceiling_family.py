#!/usr/bin/env python3
"""Plan broad P0-E5b human-only ceiling-family fee trials."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Sequence

import plan_stock_fee_rounding_trial as narrow

BOUNDARY_STEP = Decimal("1000")
LOWER_OFFSET = Decimal("1")
UPPER_OFFSET = Decimal("499")
DEFAULT_MAX_SHARES = 100000
DEFAULT_MAX_GROSS = Decimal("5000")
DEFAULT_LIMIT = 20


class PlannerError(ValueError):
    pass


@dataclass(frozen=True)
class BroadCandidate:
    shares: int
    boundary_multiplier: int
    displayed_gross: str
    conservative_gross_low: str
    conservative_gross_high: str
    lower_margin: str
    upper_margin: str
    ceiling_family_fee: int
    non_ceiling_fee: int


def parse_price(value: str) -> Decimal:
    try:
        return narrow.parse_price(value)
    except narrow.PlannerError as exc:
        raise PlannerError(str(exc)) from exc


def exact(value: Decimal) -> str:
    return format(value, "f")


def is_broad_candidate(price: Decimal, shares: int) -> BroadCandidate | None:
    if shares <= 0:
        return None
    displayed = price * Decimal(shares)
    k = int((displayed / BOUNDARY_STEP).to_integral_value(rounding=ROUND_FLOOR))
    if k < 1:
        return None
    boundary = BOUNDARY_STEP * Decimal(k)
    low = max(Decimal("0"), price - narrow.PRICE_LOWER_DELTA) * Decimal(shares)
    high = (price + narrow.PRICE_UPPER_DELTA) * Decimal(shares)
    low_threshold = boundary + LOWER_OFFSET
    high_threshold = boundary + UPPER_OFFSET
    if not low > low_threshold:
        return None
    if not high < high_threshold:
        return None
    return BroadCandidate(
        shares=shares,
        boundary_multiplier=k,
        displayed_gross=exact(displayed),
        conservative_gross_low=exact(low),
        conservative_gross_high=exact(high),
        lower_margin=exact(low - low_threshold),
        upper_margin=exact(high_threshold - high),
        ceiling_family_fee=k + 1,
        non_ceiling_fee=k,
    )


def find_candidates(price: Decimal, *, max_shares: int = DEFAULT_MAX_SHARES, max_gross: Decimal = DEFAULT_MAX_GROSS, limit: int = DEFAULT_LIMIT) -> list[BroadCandidate]:
    if max_shares < 1 or max_gross <= 0 or limit < 1:
        raise PlannerError("invalid planner limits")
    rows: list[BroadCandidate] = []
    for shares in range(1, max_shares + 1):
        if price * Decimal(shares) > max_gross:
            break
        candidate = is_broad_candidate(price, shares)
        if candidate is not None:
            rows.append(candidate)
    rows.sort(key=lambda r: (Decimal(r.displayed_gross), -min(Decimal(r.lower_margin), Decimal(r.upper_margin)), r.shares))
    return rows[:limit]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan broad P0-E5b Torn stock fee trials.")
    parser.add_argument("--price", required=True)
    parser.add_argument("--max-gross", default=str(DEFAULT_MAX_GROSS))
    parser.add_argument("--max-shares", type=int, default=DEFAULT_MAX_SHARES)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        price = parse_price(args.price)
        max_gross = Decimal(str(args.max_gross))
        rows = find_candidates(price, max_shares=args.max_shares, max_gross=max_gross, limit=args.limit)
        print(json.dumps({
            "research_status": "P0_E5B_BROAD_PLANNER_ONLY",
            "price": exact(price),
            "max_gross": exact(max_gross),
            "candidate_count": len(rows),
            "candidates": [asdict(row) for row in rows],
            "interpretation": "Human execution only. Broad candidates distinguish ceiling-like fee rounding from floor/nearest fee rounding; they do not identify exact gross preprocessing order.",
        }, indent=2, sort_keys=True))
        return 0
    except (PlannerError, narrow.PlannerError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
