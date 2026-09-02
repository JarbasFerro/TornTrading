#!/usr/bin/env python3
"""Run a bounded public Tornsy archive audit across all current stock symbols.

Research-only: no Torn API key, no Torn game requests, no trading logic.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from torn_research import (
    ResearchToolError,
    TornsyClient,
    audit_tornsy_rows,
    iso_utc,
    normalize_symbol,
    observation_record,
    parse_tornsy_rows,
    safe_filename_timestamp,
    write_json_immutable,
)

DEFAULT_INTERVALS = ("m1", "h1", "d1")


def extract_watchlist_symbols(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ResearchToolError("Tornsy watchlist response does not contain a data array.")
    symbols: list[str] = []
    for row in payload["data"]:
        if not isinstance(row, dict) or not row.get("stock"):
            continue
        symbol = normalize_symbol(str(row["stock"]))
        if symbol not in symbols:
            symbols.append(symbol)
    if not symbols:
        raise ResearchToolError("Tornsy watchlist contained no valid stock symbols.")
    return sorted(symbols)


def audit_row(symbol: str, interval: str, observation: Any) -> dict[str, Any]:
    rows = parse_tornsy_rows(observation.payload, interval)
    audit = audit_tornsy_rows(rows, interval)
    return {
        "symbol": symbol,
        "interval": interval,
        **audit,
        "request_started_at_utc": observation.request_started_at_utc,
        "response_received_at_utc": observation.response_received_at_utc,
        "elapsed_ms": observation.elapsed_ms,
        "payload_sha256": observation.payload_sha256,
        "error": None,
    }


def error_row(symbol: str, interval: str, message: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "interval": interval,
        "rows": None,
        "unique_timestamps": None,
        "duplicates": None,
        "oldest_ts": None,
        "newest_ts": None,
        "span_days": None,
        "median_delta_s": None,
        "min_delta_s": None,
        "max_delta_s": None,
        "expected_delta_s": None,
        "gap_count": None,
        "missing_slots_if_regular": None,
        "request_started_at_utc": None,
        "response_received_at_utc": None,
        "elapsed_ms": None,
        "payload_sha256": None,
        "error": message,
    }


def retry_get_stock(
    client: TornsyClient,
    symbol: str,
    interval: str,
    *,
    limit: int,
    attempts: int,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return client.get_stock(symbol, interval, limit=limit)
        except ResearchToolError as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
    assert last_error is not None
    raise last_error


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        raise ResearchToolError("Cannot write empty matrix summary.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: Sequence[Mapping[str, Any]], symbols: Sequence[str], intervals: Sequence[str]) -> dict[str, Any]:
    errors = [row for row in rows if row.get("error")]
    successful = [row for row in rows if not row.get("error")]
    by_interval: dict[str, dict[str, Any]] = {}
    for interval in intervals:
        group = [row for row in successful if row.get("interval") == interval]
        by_interval[interval] = {
            "successful_symbols": len(group),
            "error_symbols": len([row for row in errors if row.get("interval") == interval]),
            "min_rows": min((int(row["rows"]) for row in group if row.get("rows") is not None), default=None),
            "max_rows": max((int(row["rows"]) for row in group if row.get("rows") is not None), default=None),
            "max_gap_seconds": max((int(row["max_delta_s"]) for row in group if row.get("max_delta_s") is not None), default=None),
            "total_duplicates": sum(int(row["duplicates"] or 0) for row in group),
            "total_regular_missing_slots": sum(int(row["missing_slots_if_regular"] or 0) for row in group),
        }
    return {
        "created_at_utc": iso_utc(),
        "scope": {
            "symbol_count": len(symbols),
            "symbols": list(symbols),
            "intervals": list(intervals),
            "limit_per_request": 2000,
        },
        "requests_expected": len(symbols) * len(intervals),
        "requests_successful": len(successful),
        "requests_failed": len(errors),
        "by_interval": by_interval,
        "errors": [{"symbol": row.get("symbol"), "interval": row.get("interval"), "error": row.get("error")} for row in errors],
        "interpretation": "Bounded source-integrity inventory only. It does not establish canonical history, timestamp semantics, or predictive value.",
    }


def run(args: argparse.Namespace) -> int:
    intervals = tuple(args.intervals)
    client = TornsyClient()
    run_id = safe_filename_timestamp()
    run_dir = Path(args.output) / "tornsy" / "matrix" / run_id

    watchlist = client.get_watchlist()
    symbols = extract_watchlist_symbols(watchlist.payload)
    write_json_immutable(run_dir / "watchlist.json", observation_record(watchlist))

    rows: list[dict[str, Any]] = []
    total = len(symbols) * len(intervals)
    completed = 0

    for symbol in symbols:
        for interval in intervals:
            completed += 1
            print(f"[{completed}/{total}] {symbol} {interval}", flush=True)
            try:
                observation = retry_get_stock(
                    client,
                    symbol,
                    interval,
                    limit=args.limit,
                    attempts=args.attempts,
                )
                write_json_immutable(
                    run_dir / "raw" / symbol / f"{interval}.json",
                    observation_record(observation),
                )
                rows.append(audit_row(symbol, interval, observation))
            except ResearchToolError as exc:
                rows.append(error_row(symbol, interval, str(exc)))
            if args.delay > 0 and completed < total:
                time.sleep(args.delay)

    summary = build_summary(rows, symbols, intervals)
    summary["scope"]["limit_per_request"] = args.limit
    write_json_immutable(run_dir / "matrix.json", rows)
    write_json_immutable(run_dir / "summary.json", summary)
    write_csv(run_dir / "matrix.csv", rows)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"OUTPUT_DIR={run_dir}")
    return 0 if summary["requests_failed"] == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bounded Tornsy public archive audit across all current symbols.")
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--intervals", nargs="+", default=list(DEFAULT_INTERVALS), choices=sorted(TornsyClient.INTERVALS))
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between successful request attempts (default 0.5s).")
    parser.add_argument("--attempts", type=int, default=3)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.limit <= 2000:
        print("error: --limit must be 1..2000", file=sys.stderr)
        return 2
    if not 1 <= args.attempts <= 5:
        print("error: --attempts must be 1..5", file=sys.stderr)
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
