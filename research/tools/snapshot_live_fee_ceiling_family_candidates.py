#!/usr/bin/env python3
"""Snapshot live official Torn prices and broad P0-E5b fee candidates.

Read-only research tooling. No Torn game action is submitted.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import plan_stock_fee_ceiling_family as broad
from torn_research import ResearchToolError, TornApiClient, extract_stock_rows, iso_utc

MAX_GROSS = Decimal("5000")
MAX_SHARES = 1000
PER_STOCK_LIMIT = 20
OUTPUT_LIMIT = 40
EXCLUDED_SYMBOLS = {"TCSE"}


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
    cents = raw.quantize(Decimal("0.01"))
    if raw != cents:
        raise ValueError("sub-cent official price is outside frozen protocol")
    return cents


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


def build_candidates(stocks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stock in stocks:
        try:
            stock_id, symbol, name = stock_identity(stock)
            if symbol in EXCLUDED_SYMBOLS:
                continue
            price = official_price(stock)
        except ValueError:
            continue
        candidates = broad.find_candidates(price, max_shares=MAX_SHARES, max_gross=MAX_GROSS, limit=PER_STOCK_LIMIT)
        for candidate in candidates:
            payload = asdict(candidate)
            payload.update({
                "stock_id": stock_id,
                "stock_acronym": symbol,
                "stock_name": name,
                "planned_price": format(price, ".2f"),
                "worst_margin": format(min(Decimal(candidate.lower_margin), Decimal(candidate.upper_margin)), "f"),
            })
            rows.append(payload)
    rows.sort(key=lambda row: (
        Decimal(row["displayed_gross"]),
        -Decimal(row["worst_margin"]),
        row["stock_acronym"],
        int(row["shares"]),
    ))
    return rows[:OUTPUT_LIMIT]


def validate_candidate(row: Mapping[str, Any]) -> None:
    price = broad.parse_price(str(row["planned_price"]))
    candidate = broad.is_broad_candidate(price, int(row["shares"]))
    if candidate is None:
        raise ResearchToolError("persisted P0-E5b candidate fails frozen broad geometry")
    if candidate.boundary_multiplier != int(row["boundary_multiplier"]):
        raise ResearchToolError("persisted P0-E5b K differs from frozen planner")
    if candidate.ceiling_family_fee != int(row["ceiling_family_fee"]):
        raise ResearchToolError("persisted P0-E5b ceiling prediction differs")
    if candidate.non_ceiling_fee != int(row["non_ceiling_fee"]):
        raise ResearchToolError("persisted P0-E5b competing prediction differs")


def build_report(stocks: Sequence[Mapping[str, Any]], *, server_timestamp: int, retrieved_at_utc: str) -> dict[str, Any]:
    candidates = build_candidates(stocks)
    for row in candidates:
        validate_candidate(row)
    return {
        "research_status": "LIVE_P0_E5B_CANDIDATE_SNAPSHOT",
        "source": "official_torn_api_v2_torn_stocks",
        "server_timestamp": int(server_timestamp),
        "retrieved_at_utc": retrieved_at_utc,
        "max_gross": format(MAX_GROSS, ".2f"),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "validity_note": "Every plan expires immediately if the Torn UI/current official price differs from planned_price before the human click.",
        "compliance_note": "Read-only API collection and calculation only; no Torn buy/sell action is submitted.",
    }


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    ts_obs = client.get("/torn/timestamp")
    payload = ts_obs.payload
    try:
        server_timestamp = int(payload["timestamp"] if isinstance(payload, Mapping) else payload)
    except (KeyError, TypeError, ValueError):
        raise ResearchToolError("Could not parse Torn server timestamp") from None
    stocks_obs = client.get("/torn/stocks", query={"timestamp": server_timestamp})
    report = build_report(extract_stock_rows(stocks_obs.payload), server_timestamp=server_timestamp, retrieved_at_utc=iso_utc())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Snapshot live P0-E5b fee candidates")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="research/output/live_fee_ceiling_family_candidates/summary.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
