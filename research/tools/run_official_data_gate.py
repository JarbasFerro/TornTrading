#!/usr/bin/env python3
"""Run the credentialed Stage 0 official-data gate.

Research-only. Reads a Torn API key from TORN_API_KEY, performs API v2 reads,
preserves redacted evidence, and compares official chart history with Tornsy.
No trading signals or game actions are produced.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
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
    parse_tornsy_rows,
    reconcile_live_payloads,
    safe_filename_timestamp,
    timestamp_inventory,
    write_csv,
    write_json_immutable,
)

INTERVAL_BY_SECONDS = {
    60: "m1",
    300: "m5",
    900: "m15",
    1800: "m30",
    3600: "h1",
    7200: "h2",
    14400: "h4",
    21600: "h6",
    43200: "h12",
    86400: "d1",
    604800: "w1",
}


def fresh_query() -> dict[str, int]:
    """Make an official Torn request unique to bypass service cache."""
    return {"timestamp": int(time.time())}


def official_price(row: Mapping[str, Any]) -> float | None:
    for key in ("price", "close", "value"):
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def choose_tornsy_interval(inventory: Mapping[str, Any]) -> str | None:
    value = inventory.get("median_delta_s")
    if not isinstance(value, (int, float)):
        return None
    return INTERVAL_BY_SECONDS.get(int(round(float(value))))


def tornsy_overlap_window(inventory: Mapping[str, Any], limit: int) -> tuple[int, int] | None:
    """Return Tornsy [from, to) bounds covering the official history window.

    Tornsy documents `from` as inclusive and `to` as exclusive, so the end bound
    is one observed interval beyond the newest official timestamp.
    """
    oldest = inventory.get("oldest_ts")
    newest = inventory.get("newest_ts")
    delta = inventory.get("median_delta_s")
    if not all(isinstance(v, (int, float)) for v in (oldest, newest, delta)):
        return None
    step = int(round(float(delta)))
    start = max(int(oldest), int(newest) - step * (limit - 1))
    return start, int(newest) + step


def tornsy_price(row: Mapping[str, Any], interval: str) -> float | None:
    key = "price" if interval == "m1" else "close"
    value = row.get(key)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def compare_at_offset(
    official_rows: Sequence[Mapping[str, Any]],
    archive_rows: Sequence[Mapping[str, Any]],
    *,
    interval: str,
    offset_seconds: int,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    archive_by_ts = {
        int(row["timestamp"]): row
        for row in archive_rows
        if isinstance(row.get("timestamp"), (int, float))
    }
    diffs: list[float] = []
    equal = 0
    comparable = 0
    for row in official_rows:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            continue
        peer = archive_by_ts.get(int(timestamp) + offset_seconds)
        if peer is None:
            continue
        left = official_price(row)
        right = tornsy_price(peer, interval)
        if left is None or right is None:
            continue
        comparable += 1
        diff = abs(left - right)
        diffs.append(diff)
        if diff <= tolerance:
            equal += 1
    return {
        "offset_seconds": offset_seconds,
        "comparable_pairs": comparable,
        "numeric_equal_pairs": equal,
        "numeric_equal_pct": round(equal / comparable * 100, 6) if comparable else None,
        "mean_abs_price_diff": statistics.fmean(diffs) if diffs else None,
        "max_abs_price_diff": max(diffs) if diffs else None,
    }


def choose_best_offset(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    usable = [row for row in rows if int(row.get("comparable_pairs") or 0) > 0]
    if not usable:
        return None

    def score(row: Mapping[str, Any]) -> tuple[float, int, float, int]:
        equal_pct = float(row.get("numeric_equal_pct") or 0.0)
        pairs = int(row.get("comparable_pairs") or 0)
        raw_diff = row.get("mean_abs_price_diff")
        mean_diff = float(raw_diff) if raw_diff is not None else float("inf")
        offset = abs(int(row.get("offset_seconds") or 0))
        return (equal_pct, pairs, -mean_diff, -offset)

    return max(usable, key=score)


def build_aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    compared = [row for row in rows if row.get("best_offset_seconds") is not None]
    unresolved = [row for row in rows if row.get("best_offset_seconds") is None]
    exact_zero = [
        row
        for row in compared
        if row.get("best_offset_seconds") == 0 and row.get("best_numeric_equal_pct") == 100.0
    ]
    return {
        "stocks_total": len(rows),
        "stocks_with_comparable_history": len(compared),
        "stocks_without_comparable_history": len(unresolved),
        "stocks_exact_at_zero_offset": len(exact_zero),
        "observed_official_intervals": sorted(
            {str(row["tornsy_interval"]) for row in rows if row.get("tornsy_interval")}
        ),
    }


def run(args: argparse.Namespace) -> int:
    torn = TornApiClient(load_torn_api_key())
    tornsy = TornsyClient()
    run_id = safe_filename_timestamp()
    run_dir = Path(args.output) / "official_data_gate" / run_id

    server_time = torn.get("/torn/timestamp", query=fresh_query())
    all_stocks = torn.get("/torn/stocks", query=fresh_query())
    stocks = extract_stock_rows(all_stocks.payload)
    write_json_immutable(run_dir / "raw" / "official_timestamp.json", observation_record(server_time))
    write_json_immutable(run_dir / "raw" / "official_stocks_initial.json", observation_record(all_stocks))

    comparison_rows: list[dict[str, Any]] = []
    for index, stock in enumerate(stocks):
        stock_id = int(stock["id"])
        symbol = str(stock.get("acronym") or stock_id).upper()
        official = torn.get(f"/torn/{stock_id}/stocks", query=fresh_query())
        history = extract_history(official.payload)
        inventory = timestamp_inventory(history)
        write_json_immutable(
            run_dir / "raw" / "official_history" / f"{stock_id:02d}_{symbol}.json",
            observation_record(official),
        )

        interval = choose_tornsy_interval(inventory)
        row: dict[str, Any] = {
            "stock_id": stock_id,
            "symbol": symbol,
            **inventory,
            "tornsy_interval": interval,
            "archive_rows": None,
            "best_offset_seconds": None,
            "best_comparable_pairs": None,
            "best_numeric_equal_pct": None,
            "best_mean_abs_price_diff": None,
            "all_offsets": [],
            "status": "unresolved",
        }

        bounds = tornsy_overlap_window(inventory, args.limit)
        if interval and history and bounds is not None:
            delta = int(round(float(inventory["median_delta_s"])))
            from_ts, to_ts = bounds
            archive = tornsy.get_stock(
                symbol,
                interval,
                from_ts=from_ts,
                to_ts=to_ts,
                limit=args.limit,
            )
            archive_rows = parse_tornsy_rows(archive.payload, interval)
            write_json_immutable(
                run_dir / "raw" / "tornsy_overlap" / f"{symbol}_{interval}.json",
                observation_record(archive),
            )
            offsets = [-2 * delta, -delta, 0, delta, 2 * delta]
            offset_rows = [
                compare_at_offset(history, archive_rows, interval=interval, offset_seconds=offset)
                for offset in offsets
            ]
            best = choose_best_offset(offset_rows)
            row["archive_rows"] = len(archive_rows)
            row["all_offsets"] = offset_rows
            if best is not None:
                row["best_offset_seconds"] = best["offset_seconds"]
                row["best_comparable_pairs"] = best["comparable_pairs"]
                row["best_numeric_equal_pct"] = best["numeric_equal_pct"]
                row["best_mean_abs_price_diff"] = best["mean_abs_price_diff"]
                row["status"] = "compared"
        elif not history:
            row["status"] = "no_official_history"
        else:
            row["status"] = "unsupported_official_cadence"

        comparison_rows.append(row)
        if args.delay > 0 and index + 1 < len(stocks):
            time.sleep(args.delay)

    # Capture live sources back-to-back with an explicit service-cache bypass.
    official_live = torn.get("/torn/stocks", query=fresh_query())
    live_archive = tornsy.get_watchlist()
    write_json_immutable(run_dir / "raw" / "official_stocks_live.json", observation_record(official_live))
    write_json_immutable(run_dir / "raw" / "tornsy_watchlist.json", observation_record(live_archive))
    live_comparison = reconcile_live_payloads(official_live.payload, live_archive.payload)

    inventory_fields = [
        "stock_id", "symbol", "history_rows", "unique_timestamps", "oldest_ts", "newest_ts",
        "span_days", "median_delta_s", "min_delta_s", "max_delta_s", "pct_60s_delta", "duplicates",
        "tornsy_interval", "archive_rows", "best_offset_seconds", "best_comparable_pairs",
        "best_numeric_equal_pct", "best_mean_abs_price_diff", "status",
    ]
    csv_rows = [{key: row.get(key) for key in inventory_fields} for row in comparison_rows]
    write_csv(run_dir / "history_inventory.csv", inventory_fields, csv_rows)
    write_json_immutable(run_dir / "history_comparison.json", comparison_rows)
    write_json_immutable(run_dir / "live_comparison.json", live_comparison)

    official_symbols = {str(row.get("acronym", "")).upper() for row in extract_stock_rows(official_live.payload)}
    tornsy_symbols = {
        str(row.get("stock", "")).upper()
        for row in (live_archive.payload.get("data", []) if isinstance(live_archive.payload, dict) else [])
        if isinstance(row, dict) and row.get("stock")
    }

    summary = {
        "created_at_utc": iso_utc(),
        "run_id": run_id,
        "aggregate": build_aggregate(comparison_rows),
        "live": {
            "official_stock_count": live_comparison.get("official_stock_count"),
            "tornsy_stock_count": live_comparison.get("tornsy_stock_count"),
            "tornsy_timestamp": live_comparison.get("tornsy_timestamp"),
            "exact_price_matches": sum(
                1 for row in live_comparison.get("rows", []) if row.get("price_equal_numeric") is True
            ),
            "tornsy_only_symbols": sorted(tornsy_symbols - official_symbols),
            "official_only_symbols": sorted(official_symbols - tornsy_symbols),
        },
        "cache_policy": "Official requests include a unique timestamp query parameter to bypass Torn service cache.",
        "interpretation": (
            "Evidence inventory only. Best timestamp offset is descriptive and must not be treated as a "
            "validated timing rule until repeated observations establish stability and execution semantics."
        ),
    }
    write_json_immutable(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"OUTPUT_DIR={run_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Stage 0 official Torn/Tornsy data reconciliation gate.")
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--delay", type=float, default=0.25)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.limit <= 2000:
        print("error: --limit must be 1..2000", file=sys.stderr)
        return 2
    if args.delay < 0:
        print("error: --delay must be non-negative", file=sys.stderr)
        return 2
    try:
        return run(args)
    except ResearchToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
