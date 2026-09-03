#!/usr/bin/env python3
"""Plan robust human-only stock fee-rounding confirmation trials.

Given a two-decimal Torn stock price, find share counts whose entire conservative
hidden execution-price interval keeps gross sale value strictly between an exact
$1,000 boundary and $0.50 above it.

For every returned candidate:
- ceil(0.1% * unrounded true gross) is invariant and equals K+1;
- floor / nearest fee rounding predicts K;
- floor / half-up / half-even gross rounding followed by fee ceiling predicts K.

The tool is a pure calculator: no API calls and no Torn game actions.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Sequence

PRICE_LOWER_DELTA = Decimal("0.005")
PRICE_UPPER_DELTA = Decimal("0.01")
GROSS_ROUNDING_HALF_THRESHOLD = Decimal("0.50")
BOUNDARY_STEP = Decimal("1000")
DEFAULT_MAX_SHARES = 100000
DEFAULT_MAX_GROSS = Decimal("10000")
DEFAULT_LIMIT = 20


class PlannerError(ValueError):
    pass


@dataclass(frozen=True)
class TrialCandidate:
    shares: int
    boundary_multiplier: int
    boundary_gross: str
    displayed_gross: str
    conservative_gross_low: str
    conservative_gross_high: str
    lower_margin: str
    upper_margin: str
    reference_unrounded_total_ceiling_fee: int
    competing_rounded_gross_or_non_ceiling_fee: int


def parse_price(value: str) -> Decimal:
    try:
        price = Decimal(value.strip().replace("$", "").replace(",", ""))
    except (InvalidOperation, AttributeError) as exc:
        raise PlannerError("price must be a finite positive decimal") from exc
    if not price.is_finite() or price <= 0:
        raise PlannerError("price must be a finite positive decimal")
    # The diagnostic established that current Stock sell log prices are represented
    # to cents. The targeted confirmation is frozen to that observed representation.
    if price.as_tuple().exponent != -2:
        raise PlannerError("price must contain exactly two decimal places")
    return price


def money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def is_robust_candidate(price: Decimal, shares: int) -> TrialCandidate | None:
    if shares <= 0:
        return None
    displayed_gross = price * Decimal(shares)
    k = int((displayed_gross / BOUNDARY_STEP).to_integral_value(rounding=ROUND_FLOOR))
    if k < 1:
        return None
    boundary = BOUNDARY_STEP * Decimal(k)

    low_price = max(Decimal("0"), price - PRICE_LOWER_DELTA)
    high_price = price + PRICE_UPPER_DELTA
    gross_low = low_price * Decimal(shares)
    gross_high = high_price * Decimal(shares)

    # Strict inequalities are intentional. They avoid tie conventions at both the
    # $1,000 fee boundary and the $0.50 integer-gross rounding threshold.
    if not gross_low > boundary:
        return None
    if not gross_high < boundary + GROSS_ROUNDING_HALF_THRESHOLD:
        return None

    reference_fee = k + 1
    competing_fee = k
    return TrialCandidate(
        shares=shares,
        boundary_multiplier=k,
        boundary_gross=money(boundary),
        displayed_gross=money(displayed_gross),
        conservative_gross_low=money(gross_low),
        conservative_gross_high=money(gross_high),
        lower_margin=money(gross_low - boundary),
        upper_margin=money(boundary + GROSS_ROUNDING_HALF_THRESHOLD - gross_high),
        reference_unrounded_total_ceiling_fee=reference_fee,
        competing_rounded_gross_or_non_ceiling_fee=competing_fee,
    )


def find_candidates(
    price: Decimal,
    *,
    max_shares: int = DEFAULT_MAX_SHARES,
    max_gross: Decimal = DEFAULT_MAX_GROSS,
    limit: int = DEFAULT_LIMIT,
) -> list[TrialCandidate]:
    if max_shares < 1:
        raise PlannerError("max_shares must be positive")
    if max_gross <= 0:
        raise PlannerError("max_gross must be positive")
    if limit < 1:
        raise PlannerError("limit must be positive")

    candidates: list[TrialCandidate] = []
    for shares in range(1, max_shares + 1):
        displayed_gross = price * Decimal(shares)
        if displayed_gross > max_gross:
            break
        candidate = is_robust_candidate(price, shares)
        if candidate is not None:
            candidates.append(candidate)

    # Lowest capital first; then prefer candidates with larger worst-side safety
    # margin. Decimal reconstruction is exact from our formatted cents here because
    # displayed gross is two-decimal price times integer shares.
    candidates.sort(
        key=lambda row: (
            Decimal(row.displayed_gross),
            -min(Decimal(row.lower_margin), Decimal(row.upper_margin)),
            row.shares,
        )
    )
    return candidates[:limit]


def build_report(price: Decimal, candidates: Sequence[TrialCandidate], *, max_gross: Decimal) -> dict:
    return {
        "research_status": "TRIAL_PLANNER_ONLY",
        "price": format(price, "f"),
        "conservative_true_price_interval": {
            "low": format(max(Decimal("0"), price - PRICE_LOWER_DELTA), "f"),
            "high": format(price + PRICE_UPPER_DELTA, "f"),
        },
        "max_gross": money(max_gross),
        "candidate_count": len(candidates),
        "candidates": [asdict(candidate) for candidate in candidates],
        "interpretation": (
            "Each candidate is a pure calculation. A human must execute any Torn transaction. "
            "Returned trials robustly separate unrounded-total fee ceiling from the remaining "
            "rounded-gross/floor/nearest alternatives under the preregistered hidden-price interval."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan robust human-only Torn stock fee-rounding trials.")
    parser.add_argument("--price", required=True, help="Current Torn stock price with exactly two decimal places.")
    parser.add_argument("--max-shares", type=int, default=DEFAULT_MAX_SHARES)
    parser.add_argument("--max-gross", default=str(DEFAULT_MAX_GROSS))
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        price = parse_price(args.price)
        try:
            max_gross = Decimal(str(args.max_gross))
        except InvalidOperation as exc:
            raise PlannerError("max_gross must be a positive decimal") from exc
        candidates = find_candidates(
            price,
            max_shares=args.max_shares,
            max_gross=max_gross,
            limit=args.limit,
        )
        print(json.dumps(build_report(price, candidates, max_gross=max_gross), indent=2, sort_keys=True))
        return 0
    except PlannerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
