#!/usr/bin/env python3
"""Audit the already-executed HRG P0-E5b example against official Torn receipts.

Private transaction values are used transiently. The persisted report contains only
predeclared planned values and categorical/aggregate validity results.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import analyze_stock_sell_fee_rounding as fee_base
import plan_stock_fee_ceiling_family as broad
from torn_research import ResearchToolError, TornApiClient, extract_stock_rows, iso_utc

PROTOCOL_MERGE_TS = 1788465621
PROTOCOL_MERGE_COMMIT = "f5f6472151e670b9324e2f3f079294e9c96be940"
PLANNED_SYMBOL = "HRG"
PLANNED_PRICE = Decimal("272.67")
PLANNED_SHARES = 4
PLANNED_K = 1
PLANNED_CEILING_FEE = 2
PLANNED_NON_CEILING_FEE = 1
SELL_LOG_ID = 5511
BUY_LOG_ID = 5510

REPORT_KEYS = {
    "research_status", "source", "retrieved_at_utc", "protocol_merge_commit",
    "planned_symbol", "planned_price", "planned_shares", "planned_k",
    "planned_ceiling_fee", "planned_non_ceiling_fee", "matching_receipt_count",
    "latest_matching_receipt_selected", "symbol_matches", "amount_matches",
    "logged_price_matches", "geometry_revalidates", "event_second_in_15_40",
    "other_buy_sell_same_minute", "observed_fee_class", "trial_validity",
    "formal_confirmation_status", "protocol_deviation", "privacy_note",
}
FEE_CLASSES = {"CEILING_K_PLUS_1", "NON_CEILING_K", "OTHER", "NO_RECEIPT"}
VALIDITY = {"VALID", "INVALID_NO_RECEIPT", "INVALID_MULTIPLE_MATCHES", "INVALID_CONTROL_FAILURE"}


def _stock_id_for_symbol(stocks: Sequence[Mapping[str, Any]], symbol: str) -> int:
    matches = []
    for row in stocks:
        if str(row.get("acronym", "")).strip().upper() == symbol:
            try:
                matches.append(int(row["id"]))
            except (KeyError, TypeError, ValueError):
                pass
    if len(matches) != 1 or matches[0] <= 0:
        raise ResearchToolError(f"Could not resolve unique stock id for {symbol}")
    return matches[0]


def _private_sales(payload: Any) -> list[tuple[fee_base.SaleObservation, int, int]]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("log"), list):
        raise ResearchToolError("Expected UserLogsResponse.log array")
    rows = []
    for entry in payload["log"]:
        obs = fee_base.parse_sale_entry(entry)
        if obs is None or not isinstance(entry, Mapping):
            continue
        data = entry.get("data")
        if not isinstance(data, Mapping):
            continue
        try:
            ts = int(entry["timestamp"])
            stock_id = int(data["stock"])
        except (KeyError, TypeError, ValueError):
            continue
        if ts >= PROTOCOL_MERGE_TS:
            rows.append((obs, ts, stock_id))
    return rows


def _private_buys(payload: Any) -> list[tuple[int, int]]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("log"), list):
        raise ResearchToolError("Expected UserLogsResponse.log array")
    rows = []
    for entry in payload["log"]:
        if not isinstance(entry, Mapping):
            continue
        details = entry.get("details")
        data = entry.get("data")
        try:
            log_id = int(details.get("id")) if isinstance(details, Mapping) else None
            ts = int(entry["timestamp"])
            stock_id = int(data["stock"]) if isinstance(data, Mapping) else 0
        except (TypeError, ValueError, KeyError):
            continue
        if log_id == BUY_LOG_ID and ts >= PROTOCOL_MERGE_TS and stock_id > 0:
            rows.append((ts, stock_id))
    return rows


def build_report(*, stocks: Sequence[Mapping[str, Any]], sells_payload: Any, buys_payload: Any, retrieved_at: str) -> dict[str, Any]:
    planned = broad.is_broad_candidate(PLANNED_PRICE, PLANNED_SHARES)
    if planned is None or planned.boundary_multiplier != PLANNED_K:
        raise ResearchToolError("Frozen HRG example no longer revalidates through P0-E5b planner")
    if planned.ceiling_family_fee != PLANNED_CEILING_FEE or planned.non_ceiling_fee != PLANNED_NON_CEILING_FEE:
        raise ResearchToolError("Frozen HRG fee predictions differ from planner")

    hrg_id = _stock_id_for_symbol(stocks, PLANNED_SYMBOL)
    sales = _private_sales(sells_payload)
    matches = [row for row in sales if row[0].amount == PLANNED_SHARES and row[0].price == PLANNED_PRICE and row[2] == hrg_id]
    matches.sort(key=lambda row: row[1], reverse=True)

    selected = matches[0] if matches else None
    symbol_matches = amount_matches = logged_price_matches = geometry_ok = second_ok = False
    other_same_minute = 0
    fee_class = "NO_RECEIPT"

    if selected is not None:
        obs, ts, stock_id = selected
        symbol_matches = stock_id == hrg_id
        amount_matches = obs.amount == PLANNED_SHARES
        logged_price_matches = obs.price == PLANNED_PRICE
        candidate = broad.is_broad_candidate(obs.price, obs.amount)
        geometry_ok = candidate is not None and candidate.boundary_multiplier == PLANNED_K
        second_ok = 15 <= ts % 60 <= 40
        if obs.fee == PLANNED_CEILING_FEE:
            fee_class = "CEILING_K_PLUS_1"
        elif obs.fee == PLANNED_NON_CEILING_FEE:
            fee_class = "NON_CEILING_K"
        else:
            fee_class = "OTHER"

        minute = ts // 60
        other_sales = sum(1 for _, other_ts, _ in sales if other_ts // 60 == minute and other_ts != ts)
        buys = _private_buys(buys_payload)
        same_minute_buys = sum(1 for other_ts, _ in buys if other_ts // 60 == minute)
        other_same_minute = other_sales + same_minute_buys

    if not matches:
        validity = "INVALID_NO_RECEIPT"
    elif len(matches) > 1:
        validity = "INVALID_MULTIPLE_MATCHES"
    elif not all((symbol_matches, amount_matches, logged_price_matches, geometry_ok, second_ok)) or other_same_minute != 0:
        validity = "INVALID_CONTROL_FAILURE"
    else:
        validity = "VALID"

    report = {
        "research_status": "P0_E5B_POST_ACTION_TRIAL_AUDIT",
        "source": "official_torn_api_v2_user_log_5511_5510_and_torn_stocks",
        "retrieved_at_utc": retrieved_at,
        "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
        "planned_symbol": PLANNED_SYMBOL,
        "planned_price": "272.67",
        "planned_shares": PLANNED_SHARES,
        "planned_k": PLANNED_K,
        "planned_ceiling_fee": PLANNED_CEILING_FEE,
        "planned_non_ceiling_fee": PLANNED_NON_CEILING_FEE,
        "matching_receipt_count": len(matches),
        "latest_matching_receipt_selected": selected is not None,
        "symbol_matches": symbol_matches,
        "amount_matches": amount_matches,
        "logged_price_matches": logged_price_matches,
        "geometry_revalidates": geometry_ok,
        "event_second_in_15_40": second_ok,
        "other_buy_sell_same_minute": other_same_minute,
        "observed_fee_class": fee_class,
        "trial_validity": validity,
        "formal_confirmation_status": "SUPPORTING_NOT_FORMAL_COUNT",
        "protocol_deviation": (
            "The substantive stock/price/shares/K/predictions were written in chat before the receipt was read, but the attempt number was not explicitly recorded before execution; retain as supporting evidence rather than one of the frozen six formal trials."
        ),
        "privacy_note": (
            "No transaction IDs, exact timestamps, profits/losses, private stock IDs, raw payloads, or unplanned trade values are persisted."
        ),
    }
    assert_safe_report(report)
    return report


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != REPORT_KEYS:
        raise ResearchToolError("Unexpected audit report fields")
    if report.get("observed_fee_class") not in FEE_CLASSES:
        raise ResearchToolError("Unexpected fee class")
    if report.get("trial_validity") not in VALIDITY:
        raise ResearchToolError("Unexpected validity")
    if report.get("formal_confirmation_status") != "SUPPORTING_NOT_FORMAL_COUNT":
        raise ResearchToolError("This audit must not silently count as formal confirmation")
    if not isinstance(report.get("other_buy_sell_same_minute"), int) or report["other_buy_sell_same_minute"] < 0:
        raise ResearchToolError("Invalid same-minute action count")
    for key in ("matching_receipt_count", "planned_shares", "planned_k", "planned_ceiling_fee", "planned_non_ceiling_fee"):
        if not isinstance(report.get(key), int) or report[key] < 0:
            raise ResearchToolError(f"Invalid integer field: {key}")


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    ts_payload = client.get("/torn/timestamp").payload
    try:
        server_ts = int(ts_payload["timestamp"] if isinstance(ts_payload, Mapping) else ts_payload)
    except (KeyError, TypeError, ValueError):
        raise ResearchToolError("Could not parse Torn server timestamp") from None
    stocks = extract_stock_rows(client.get("/torn/stocks", query={"timestamp": server_ts}).payload)
    sells = client.get("/user/log", {"log": str(SELL_LOG_ID), "from": PROTOCOL_MERGE_TS, "limit": 100}).payload
    buys = client.get("/user/log", {"log": str(BUY_LOG_ID), "from": PROTOCOL_MERGE_TS, "limit": 100}).payload
    report = build_report(stocks=stocks, sells_payload=sells, buys_payload=buys, retrieved_at=iso_utc())
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Audit the already-executed HRG P0-E5b trial")
    p.add_argument("--api-key", required=True)
    p.add_argument("--output", default="research/output/p0_e5b_hrg_trial/summary.json")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
