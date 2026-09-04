#!/usr/bin/env python3
"""Run the frozen TSB named-equity external EOD follow-up.

The sector evidence review promotes only TSB. This wrapper keeps the original
35-stock manifest shape required by the reviewed EOD engine, but clears every
sector/named candidate from non-promoted stocks. Raw external price rows remain
transient exactly as in run_external_eod_screen.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import run_external_eod_screen as base
from torn_research import ResearchToolError

PLAN_STATUS = "PREREGISTERED_NAMED_FOLLOWUP"
PROMOTED_TORN_SYMBOL = "TSB"
FROZEN_SECTOR_PROXIES = ("XLF", "KBE")
FROZEN_NAMED_CANDIDATES = ("HSBC", "JPM", "BAC", "C")
FROZEN_SHARED_CONTROLS = ("SPY", "ACWI", "QQQ", "IWM")
EXPECTED_REQUEST_SYMBOLS = frozenset(
    FROZEN_SHARED_CONTROLS + FROZEN_SECTOR_PROXIES + FROZEN_NAMED_CANDIDATES
)


def load_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("research_status") != PLAN_STATUS:
        raise ResearchToolError("Named follow-up plan has unexpected research status.")
    promoted = data.get("promoted_stocks")
    if not isinstance(promoted, list) or len(promoted) != 1:
        raise ResearchToolError("Named follow-up plan must promote exactly one Torn stock.")
    row = promoted[0]
    if not isinstance(row, Mapping) or str(row.get("torn_symbol", "")).upper() != PROMOTED_TORN_SYMBOL:
        raise ResearchToolError("Named follow-up plan must promote TSB only.")
    sectors = tuple(str(v).upper() for v in row.get("retained_sector_or_industry_proxies", []))
    named = tuple(str(v).upper() for v in row.get("named_equity_candidates", []))
    controls = tuple(str(v).upper() for v in data.get("shared_controls", []))
    if sectors != FROZEN_SECTOR_PROXIES:
        raise ResearchToolError("TSB sector-proxy set differs from the frozen follow-up.")
    if named != FROZEN_NAMED_CANDIDATES:
        raise ResearchToolError("TSB named-equity set differs from the frozen follow-up.")
    if controls != FROZEN_SHARED_CONTROLS:
        raise ResearchToolError("Shared-control set differs from the frozen follow-up.")
    return data


def named_followup_manifest(source: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    # Deep-copy through JSON so no caller-owned manifest object is mutated.
    data = json.loads(json.dumps(source))
    stocks = data.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 35:
        raise ResearchToolError("Source candidate manifest must retain exactly 35 Torn stocks.")

    promoted_rows = plan.get("promoted_stocks")
    if not isinstance(promoted_rows, list) or len(promoted_rows) != 1:
        raise ResearchToolError("Follow-up plan must contain exactly one promoted row.")

    found_tsb = False
    for stock in stocks:
        if not isinstance(stock, dict):
            raise ResearchToolError("Unexpected stock row in source candidate manifest.")
        torn_symbol = str(stock.get("torn_symbol", "")).upper()
        if torn_symbol == PROMOTED_TORN_SYMBOL:
            found_tsb = True
            source_sectors = tuple(str(v).upper() for v in stock.get("sector_or_industry_proxies", []) or [])
            source_named = tuple(str(v).upper() for v in stock.get("individual_equity_candidates", []) or [])
            if source_sectors != FROZEN_SECTOR_PROXIES:
                raise ResearchToolError("Frozen TSB sector proxies no longer match source candidate universe.")
            if source_named != FROZEN_NAMED_CANDIDATES:
                raise ResearchToolError("Frozen TSB named candidates no longer match source candidate universe.")
            stock["sector_or_industry_proxies"] = list(FROZEN_SECTOR_PROXIES)
            stock["individual_equity_candidates"] = list(FROZEN_NAMED_CANDIDATES)
        else:
            stock["sector_or_industry_proxies"] = []
            stock["individual_equity_candidates"] = []

    if not found_tsb:
        raise ResearchToolError("TSB is missing from source candidate universe.")

    source_controls = tuple(
        str(row.get("symbol", "")).upper()
        for row in data.get("shared_controls", [])
        if isinstance(row, Mapping)
    )
    if source_controls != FROZEN_SHARED_CONTROLS:
        raise ResearchToolError("Source shared controls no longer match frozen follow-up.")
    return data


def named_request_symbols(source: Mapping[str, Any], plan: Mapping[str, Any]) -> list[str]:
    filtered = named_followup_manifest(source, plan)
    return base.unique_external_symbols(filtered)


def run(args: argparse.Namespace) -> int:
    source = base.load_manifest(Path(args.manifest))
    plan = load_plan(Path(args.plan))
    filtered = named_followup_manifest(source, plan)
    symbols = named_request_symbols(source, plan)
    if frozenset(symbols) != EXPECTED_REQUEST_SYMBOLS:
        raise ResearchToolError(
            "Frozen TSB named-follow-up request set changed unexpectedly: "
            f"expected {sorted(EXPECTED_REQUEST_SYMBOLS)}, got {sorted(symbols)}"
        )
    if len(symbols) != 10:
        raise ResearchToolError(f"Expected exactly 10 external symbols, got {len(symbols)}.")

    with tempfile.TemporaryDirectory(prefix="torntrading-tsb-named-followup-") as tmp:
        filtered_path = Path(tmp) / "named_followup_manifest.json"
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
    parser = argparse.ArgumentParser(description="Run the frozen TSB named-equity EOD follow-up.")
    parser.add_argument("--manifest", default="research/external_driver_candidates.json")
    parser.add_argument("--plan", default="research/external_named_followup_v1.json")
    parser.add_argument("--output", default="research/output/external_named_followup_v1")
    parser.add_argument("--start-date", default=base.DEFAULT_START_DATE.isoformat())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (ResearchToolError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
