#!/usr/bin/env python3
"""Measure Torn/Tornsy stock publication timing around minute boundaries.

Research-only. API reads only. No Torn game actions or trading signals.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from torn_research import (
    ResearchToolError,
    TornApiClient,
    TornsyClient,
    extract_history,
    extract_stock_rows,
    iso_utc,
    load_torn_api_key,
    observation_record,
    safe_filename_timestamp,
    write_json_immutable,
)


def fresh_query() -> dict[str, int]:
    return {"timestamp": int(time.time())}


def epoch_from_iso(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def official_price_map(payload: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for stock in extract_stock_rows(payload):
        symbol = str(stock.get("acronym", "")).upper()
        market = stock.get("market") if isinstance(stock.get("market"), dict) else {}
        value = market.get("price")
        if symbol and isinstance(value, (int, float)) and math.isfinite(float(value)):
            result[symbol] = float(value)
    return result


def tornsy_price_map(payload: Any) -> dict[str, float]:
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    result: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("stock", "")).upper()
        value = row.get("price")
        if symbol and isinstance(value, (int, float, str)):
            try:
                result[symbol] = float(value)
            except (TypeError, ValueError):
                pass
    return result


def history_targets(history_payloads: Mapping[str, Any], boundary: int) -> dict[str, float]:
    targets: dict[str, float] = {}
    for symbol, payload in history_payloads.items():
        for row in extract_history(payload):
            if row.get("timestamp") == boundary and isinstance(row.get("price"), (int, float)):
                targets[symbol] = float(row["price"])
                break
    return targets


def exact_match_count(prices: Mapping[str, float], targets: Mapping[str, float], tolerance: float = 1e-9) -> int:
    return sum(
        1
        for symbol, target in targets.items()
        if symbol in prices and abs(float(prices[symbol]) - float(target)) <= tolerance
    )


def analyze_boundary(
    boundary: int,
    samples: Sequence[Mapping[str, Any]],
    history_payloads: Mapping[str, Any],
) -> dict[str, Any]:
    targets = history_targets(history_payloads, boundary)
    target_count = len(targets)
    official_candidates: list[dict[str, Any]] = []
    tornsy_candidates: list[dict[str, Any]] = []

    for sample in samples:
        if int(sample.get("boundary", -1)) != boundary:
            continue
        server_ts = sample.get("server_timestamp")
        official = sample.get("official_prices", {})
        tornsy = sample.get("tornsy_prices", {})
        official_matches = exact_match_count(official, targets)
        tornsy_matches = exact_match_count(tornsy, targets)
        official_candidates.append({
            "server_timestamp": server_ts,
            "response_received_at_utc": sample.get("official_response_received_at_utc"),
            "matches": official_matches,
        })
        tornsy_candidates.append({
            "tornsy_timestamp": sample.get("tornsy_timestamp"),
            "response_received_at_utc": sample.get("tornsy_response_received_at_utc"),
            "matches": tornsy_matches,
        })

    first_official_full = next(
        (
            row for row in official_candidates
            if isinstance(row.get("server_timestamp"), int)
            and row["server_timestamp"] >= boundary
            and target_count > 0
            and row["matches"] == target_count
        ),
        None,
    )
    first_tornsy_full = next(
        (
            row for row in tornsy_candidates
            if isinstance(row.get("tornsy_timestamp"), int)
            and row["tornsy_timestamp"] >= boundary
            and target_count > 0
            and row["matches"] == target_count
        ),
        None,
    )

    official_delay = None
    if first_official_full and first_official_full.get("response_received_at_utc"):
        official_delay = round(epoch_from_iso(str(first_official_full["response_received_at_utc"])) - boundary, 3)
    tornsy_delay = None
    if first_tornsy_full and first_tornsy_full.get("response_received_at_utc"):
        tornsy_delay = round(epoch_from_iso(str(first_tornsy_full["response_received_at_utc"])) - boundary, 3)

    return {
        "boundary_timestamp": boundary,
        "boundary_utc": datetime.fromtimestamp(boundary, timezone.utc).isoformat().replace("+00:00", "Z"),
        "history_target_stocks": target_count,
        "first_official_full_match": first_official_full,
        "official_full_match_delay_seconds": official_delay,
        "first_tornsy_full_match": first_tornsy_full,
        "tornsy_full_match_delay_seconds": tornsy_delay,
        "tornsy_minus_official_full_match_delay_seconds": (
            round(tornsy_delay - official_delay, 3)
            if tornsy_delay is not None and official_delay is not None
            else None
        ),
    }


def sleep_until(epoch: float) -> None:
    while True:
        remaining = epoch - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 0.25))


def choose_first_boundary(now: float, pre_seconds: float) -> int:
    candidate = (int(now) // 60 + 1) * 60
    if now > candidate - pre_seconds:
        candidate += 60
    return candidate


def run(args: argparse.Namespace) -> int:
    torn = TornApiClient(load_torn_api_key())
    tornsy = TornsyClient()
    run_id = safe_filename_timestamp()
    run_dir = Path(args.output) / "publication_boundary" / run_id

    initial_server = torn.get("/torn/timestamp", query=fresh_query())
    server_ts = int(initial_server.payload["timestamp"])
    local_now = time.time()
    server_offset = server_ts - local_now
    first_boundary = choose_first_boundary(local_now + server_offset, args.pre_seconds)

    boundaries = [first_boundary + 60 * i for i in range(args.boundaries)]
    samples: list[dict[str, Any]] = []

    for boundary in boundaries:
        local_boundary = boundary - server_offset
        start = local_boundary - args.pre_seconds
        end = local_boundary + args.post_seconds
        sleep_until(start)
        sample_index = 0
        next_sample = start
        while next_sample <= end + 1e-6:
            sleep_until(next_sample)
            server_obs = torn.get("/torn/timestamp", query=fresh_query())
            stocks_obs = torn.get("/torn/stocks", query=fresh_query())
            tornsy_obs = tornsy.get_watchlist()
            samples.append({
                "boundary": boundary,
                "sample_index": sample_index,
                "scheduled_local_epoch": next_sample,
                "server_timestamp": int(server_obs.payload["timestamp"]),
                "server_timestamp_observation": observation_record(server_obs),
                "official_response_received_at_utc": stocks_obs.response_received_at_utc,
                "official_observation": observation_record(stocks_obs),
                "official_prices": official_price_map(stocks_obs.payload),
                "tornsy_timestamp": (
                    int(tornsy_obs.payload["timestamp"])
                    if isinstance(tornsy_obs.payload, dict) and isinstance(tornsy_obs.payload.get("timestamp"), (int, float))
                    else None
                ),
                "tornsy_response_received_at_utc": tornsy_obs.response_received_at_utc,
                "tornsy_observation": observation_record(tornsy_obs),
                "tornsy_prices": tornsy_price_map(tornsy_obs.payload),
            })
            sample_index += 1
            next_sample = start + sample_index * args.interval_seconds

    # Fetch chart history after all observed boundaries. The 60-minute official
    # rolling window easily covers this short experiment.
    stock_list = torn.get("/torn/stocks", query=fresh_query())
    history_payloads: dict[str, Any] = {}
    history_observations: dict[str, Any] = {}
    for index, stock in enumerate(extract_stock_rows(stock_list.payload)):
        stock_id = int(stock["id"])
        symbol = str(stock.get("acronym", stock_id)).upper()
        obs = torn.get(f"/torn/{stock_id}/stocks", query=fresh_query())
        history_payloads[symbol] = obs.payload
        history_observations[symbol] = observation_record(obs)
        if args.history_delay > 0 and index + 1 < len(extract_stock_rows(stock_list.payload)):
            time.sleep(args.history_delay)

    boundary_results = [analyze_boundary(boundary, samples, history_payloads) for boundary in boundaries]
    valid_official = [x["official_full_match_delay_seconds"] for x in boundary_results if x["official_full_match_delay_seconds"] is not None]
    valid_tornsy = [x["tornsy_full_match_delay_seconds"] for x in boundary_results if x["tornsy_full_match_delay_seconds"] is not None]

    summary = {
        "run_id": run_id,
        "created_at_utc": iso_utc(),
        "parameters": {
            "boundaries": args.boundaries,
            "pre_seconds": args.pre_seconds,
            "post_seconds": args.post_seconds,
            "interval_seconds": args.interval_seconds,
            "history_delay": args.history_delay,
        },
        "initial_server_clock": observation_record(initial_server),
        "estimated_server_minus_runner_seconds": round(server_offset, 3),
        "boundary_results": boundary_results,
        "aggregate": {
            "boundaries_with_full_official_match": len(valid_official),
            "boundaries_with_full_tornsy_match": len(valid_tornsy),
            "official_full_match_delay_min_seconds": min(valid_official) if valid_official else None,
            "official_full_match_delay_max_seconds": max(valid_official) if valid_official else None,
            "tornsy_full_match_delay_min_seconds": min(valid_tornsy) if valid_tornsy else None,
            "tornsy_full_match_delay_max_seconds": max(valid_tornsy) if valid_tornsy else None,
        },
        "interpretation_warning": (
            "Observed availability bounds are limited by the sampling interval and network response latency. "
            "They describe API/Tornsy visibility, not Torn UI execution timing."
        ),
    }

    write_json_immutable(run_dir / "samples.json", samples)
    write_json_immutable(run_dir / "history_observations.json", history_observations)
    write_json_immutable(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"OUTPUT_DIR={run_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure cache-bypassed Torn/Tornsy publication timing.")
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--boundaries", type=int, default=3)
    parser.add_argument("--pre-seconds", type=float, default=6.0)
    parser.add_argument("--post-seconds", type=float, default=30.0)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--history-delay", type=float, default=0.25)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.boundaries <= 5:
        print("error: --boundaries must be 1..5", file=sys.stderr)
        return 2
    if args.pre_seconds < 0 or args.post_seconds <= 0 or args.interval_seconds < 2.0 or args.history_delay < 0:
        print("error: invalid timing parameters; interval must be >= 2 seconds", file=sys.stderr)
        return 2
    # Two official requests per sample at a 2-second minimum interval = at most
    # 60 Torn requests/minute during observation windows, below the documented 100/min limit.
    try:
        return run(args)
    except (ResearchToolError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
