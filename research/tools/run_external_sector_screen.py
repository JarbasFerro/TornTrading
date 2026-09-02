#!/usr/bin/env python3
"""Run the first-stage sector/proxy-only external EOD screen.

This wrapper deliberately removes named-equity candidates from a temporary copy of
the frozen manifest, then delegates to the validated transient EOD screen. It does
not persist the temporary manifest or any external provider price series.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Sequence

import run_external_eod_screen as base
from torn_research import ResearchToolError


def sector_only_manifest(source: dict) -> dict:
    data = json.loads(json.dumps(source))
    for stock in data.get("stocks", []):
        stock["individual_equity_candidates"] = []
    return data


def sector_request_symbols(source: dict) -> list[str]:
    filtered = sector_only_manifest(source)
    return base.unique_external_symbols(filtered)


def run(args: argparse.Namespace) -> int:
    source_path = Path(args.manifest)
    source = base.load_manifest(source_path)
    filtered = sector_only_manifest(source)
    symbols = sector_request_symbols(source)
    if len(symbols) > 39:
        raise ResearchToolError(f"Sector-first request budget exceeded: {len(symbols)} symbols")
    if len(symbols) != 34:
        raise ResearchToolError(
            f"Frozen v1.0 sector universe changed unexpectedly: expected 34 symbols including controls, got {len(symbols)}"
        )

    with tempfile.TemporaryDirectory(prefix="torntrading-sector-screen-") as tmp:
        filtered_path = Path(tmp) / "sector_manifest.json"
        filtered_path.write_text(json.dumps(filtered), encoding="utf-8")
        delegated = argparse.Namespace(
            manifest=str(filtered_path),
            output=args.output,
            batch_index=0,
            batch_size=35,
            start_date=args.start_date,
        )
        return base.run(delegated)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the one-batch sector-first external EOD screen.")
    parser.add_argument("--manifest", default="research/external_driver_candidates.json")
    parser.add_argument("--output", default="research/output/external_sector_screen")
    parser.add_argument("--start-date", default=base.DEFAULT_START_DATE.isoformat())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
