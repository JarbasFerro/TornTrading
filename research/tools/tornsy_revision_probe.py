#!/usr/bin/env python3
"""Probe fixed closed Tornsy windows for retroactive historical revisions."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from torn_research import (
    ResearchToolError,
    TornsyClient,
    iso_utc,
    observation_record,
    parse_tornsy_rows,
    sha256_json,
    write_json_immutable,
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ResearchToolError(f"File not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ResearchToolError(f"Invalid JSON in {path}: {exc}") from None


def validate_config(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("windows"), list):
        raise ResearchToolError("Revision config must contain a windows array.")
    windows: list[dict[str, Any]] = []
    names: set[str] = set()
    for raw in payload["windows"]:
        if not isinstance(raw, dict):
            raise ResearchToolError("Each revision window must be an object.")
        name = str(raw.get("name", "")).strip()
        interval = str(raw.get("interval", "")).strip()
        from_ts = raw.get("from_ts")
        to_ts = raw.get("to_ts")
        if not name or name in names:
            raise ResearchToolError(f"Revision window name must be unique and non-empty: {name!r}")
        if interval not in TornsyClient.INTERVALS:
            raise ResearchToolError(f"Unsupported interval in revision window {name}: {interval}")
        if not isinstance(from_ts, int) or not isinstance(to_ts, int) or from_ts >= to_ts:
            raise ResearchToolError(f"Invalid timestamps in revision window {name}")
        names.add(name)
        windows.append({"name": name, "interval": interval, "from_ts": from_ts, "to_ts": to_ts})
    if not windows:
        raise ResearchToolError("At least one revision window is required.")
    return windows


def extract_symbols(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ResearchToolError("Tornsy watchlist response does not contain a data array.")
    symbols = sorted(
        {
            str(row.get("stock", "")).strip().upper()
            for row in payload["data"]
            if isinstance(row, dict) and row.get("stock")
        }
    )
    if not symbols:
        raise ResearchToolError("Tornsy watchlist contained no symbols.")
    return symbols


def semantic_rows(payload: Any, interval: str) -> list[dict[str, Any]]:
    rows = parse_tornsy_rows(payload, interval)
    return sorted(rows, key=lambda row: int(row["timestamp"]))


def fingerprint(payload: Any, interval: str) -> dict[str, Any]:
    rows = semantic_rows(payload, interval)
    return {
        "rows": len(rows),
        "oldest_ts": int(rows[0]["timestamp"]) if rows else None,
        "newest_ts": int(rows[-1]["timestamp"]) if rows else None,
        "semantic_sha256": sha256_json(rows),
    }


def build_baseline(entries: Sequence[Mapping[str, Any]], config_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "Tornsy",
        "config_sha256": config_sha256,
        "created_at_utc": iso_utc(),
        "entries": [
            {
                "symbol": row["symbol"],
                "window": row["window"],
                "interval": row["interval"],
                "from_ts": row["from_ts"],
                "to_ts": row["to_ts"],
                "rows": row["rows"],
                "oldest_ts": row["oldest_ts"],
                "newest_ts": row["newest_ts"],
                "semantic_sha256": row["semantic_sha256"],
            }
            for row in entries
        ],
    }


def compare_baseline(
    current: Sequence[Mapping[str, Any]], baseline: Mapping[str, Any], config_sha256: str
) -> dict[str, Any]:
    if baseline.get("config_sha256") != config_sha256:
        raise ResearchToolError("Baseline config hash does not match current revision-window config.")
    base_rows = baseline.get("entries")
    if not isinstance(base_rows, list):
        raise ResearchToolError("Baseline does not contain an entries array.")
    base_map = {
        (row.get("symbol"), row.get("window")): row
        for row in base_rows
        if isinstance(row, dict)
    }
    comparisons: list[dict[str, Any]] = []
    mismatches = 0
    for row in current:
        key = (row["symbol"], row["window"])
        prior = base_map.get(key)
        if prior is None:
            status = "missing_baseline"
        elif prior.get("semantic_sha256") != row.get("semantic_sha256"):
            status = "changed"
        elif prior.get("rows") != row.get("rows"):
            status = "changed"
        else:
            status = "unchanged"
        if status != "unchanged":
            mismatches += 1
        comparisons.append(
            {
                "symbol": row["symbol"],
                "window": row["window"],
                "status": status,
                "baseline_rows": prior.get("rows") if prior else None,
                "current_rows": row.get("rows"),
                "baseline_sha256": prior.get("semantic_sha256") if prior else None,
                "current_sha256": row.get("semantic_sha256"),
            }
        )
    current_keys = {(row["symbol"], row["window"]) for row in current}
    for key, prior in base_map.items():
        if key not in current_keys:
            mismatches += 1
            comparisons.append(
                {
                    "symbol": key[0],
                    "window": key[1],
                    "status": "missing_current",
                    "baseline_rows": prior.get("rows"),
                    "current_rows": None,
                    "baseline_sha256": prior.get("semantic_sha256"),
                    "current_sha256": None,
                }
            )
    return {"mismatches": mismatches, "comparisons": comparisons}


def run(args: argparse.Namespace) -> int:
    config_payload = load_json(Path(args.config))
    windows = validate_config(config_payload)
    config_sha = sha256_json(config_payload)
    client = TornsyClient()
    watchlist = client.get_watchlist()
    symbols = extract_symbols(watchlist.payload)

    run_dir = Path(args.output) / "tornsy" / "revision_probe" / args.run_id
    write_json_immutable(run_dir / "watchlist.json", observation_record(watchlist))

    entries: list[dict[str, Any]] = []
    total = len(symbols) * len(windows)
    completed = 0
    for symbol in symbols:
        for window in windows:
            completed += 1
            print(f"[{completed}/{total}] {symbol} {window['name']}", flush=True)
            observation = client.get_stock(
                symbol,
                window["interval"],
                from_ts=window["from_ts"],
                to_ts=window["to_ts"],
                limit=args.limit,
            )
            write_json_immutable(
                run_dir / "raw" / symbol / f"{window['name']}.json",
                observation_record(observation),
            )
            entries.append(
                {
                    "symbol": symbol,
                    "window": window["name"],
                    "interval": window["interval"],
                    "from_ts": window["from_ts"],
                    "to_ts": window["to_ts"],
                    **fingerprint(observation.payload, window["interval"]),
                    "payload_sha256": observation.payload_sha256,
                    "request_started_at_utc": observation.request_started_at_utc,
                    "response_received_at_utc": observation.response_received_at_utc,
                }
            )
            if args.delay > 0 and completed < total:
                time.sleep(args.delay)

    snapshot = {
        "schema_version": 1,
        "created_at_utc": iso_utc(),
        "config_sha256": config_sha,
        "symbol_count": len(symbols),
        "window_count": len(windows),
        "entries": entries,
    }
    write_json_immutable(run_dir / "snapshot.json", snapshot)
    write_json_immutable(run_dir / "candidate_baseline.json", build_baseline(entries, config_sha))

    if not args.baseline:
        print("BASELINE_STATUS=not_checked")
        print(f"OUTPUT_DIR={run_dir}")
        return 0

    result = compare_baseline(entries, load_json(Path(args.baseline)), config_sha)
    write_json_immutable(run_dir / "comparison.json", result)
    print(f"BASELINE_MISMATCHES={result['mismatches']}")
    print(f"OUTPUT_DIR={run_dir}")
    return 0 if result["mismatches"] == 0 else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe fixed closed Tornsy windows for historical revisions."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--run-id", default="manual")
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--delay", type=float, default=0.25)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.limit <= 2000 or args.delay < 0:
        return 2
    try:
        return run(args)
    except ResearchToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
