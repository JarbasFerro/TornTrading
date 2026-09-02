#!/usr/bin/env python3
"""Stage 0 external-driver EOD screening.

External provider price rows are processed in memory only and are never written to
persistent storage. Output contains non-reconstructable aggregate statistics only.
No trading signals or executable-profit claims are produced.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import urllib.parse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from torn_research import JsonHttpClient, ResearchToolError, TornsyClient, parse_tornsy_rows, write_csv

TIINGO_API_BASE = "https://api.tiingo.com/tiingo/daily"
DEFAULT_START_DATE = date(2021, 4, 6)
BROAD_CONTROLS = ("SPY", "ACWI", "QQQ", "IWM")
PRIMARY_CONTROL = "SPY"
PRICE_VARIANTS = ("adjusted", "raw")
DATE_OFFSETS = (-1, 0, 1)


def load_tiingo_token() -> str:
    token = os.environ.get("TIINGO_TOKEN", "").strip()
    if not token:
        raise ResearchToolError("TIINGO_TOKEN is required for the external EOD screen.")
    return token


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("research_status") != "HYPOTHESIS_CANDIDATE_UNIVERSE":
        raise ResearchToolError("External candidate manifest is not marked as hypothesis-only.")
    stocks = data.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 35:
        raise ResearchToolError("External candidate manifest must contain exactly 35 Torn stocks.")
    return data


def unique_external_symbols(manifest: Mapping[str, Any]) -> list[str]:
    symbols: set[str] = set()
    for control in manifest.get("shared_controls", []):
        if isinstance(control, Mapping) and control.get("symbol"):
            symbols.add(str(control["symbol"]).upper())
    for stock in manifest.get("stocks", []):
        if not isinstance(stock, Mapping):
            continue
        for key in ("sector_or_industry_proxies", "individual_equity_candidates"):
            for symbol in stock.get(key, []) or []:
                symbols.add(str(symbol).upper())
    return sorted(symbols)


def relevant_torn_roles(manifest: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
    roles: dict[str, list[dict[str, str]]] = defaultdict(list)
    for stock in manifest.get("stocks", []):
        torn_symbol = str(stock["torn_symbol"]).upper()
        for symbol in stock.get("sector_or_industry_proxies", []) or []:
            roles[str(symbol).upper()].append({"torn_symbol": torn_symbol, "candidate_role": "sector_proxy"})
        for symbol in stock.get("individual_equity_candidates", []) or []:
            roles[str(symbol).upper()].append({"torn_symbol": torn_symbol, "candidate_role": "named_equity"})
    for control in BROAD_CONTROLS:
        for stock in manifest.get("stocks", []):
            roles[control].append({"torn_symbol": str(stock["torn_symbol"]).upper(), "candidate_role": "broad_control"})
    return roles


def batch_symbols(manifest: Mapping[str, Any], batch_index: int, batch_size: int) -> tuple[list[str], int]:
    if batch_index < 0:
        raise ResearchToolError("batch_index must be non-negative")
    if not 1 <= batch_size <= 35:
        raise ResearchToolError("batch_size must be between 1 and 35")
    all_symbols = [s for s in unique_external_symbols(manifest) if s not in BROAD_CONTROLS]
    batch_count = max(1, math.ceil(len(all_symbols) / batch_size))
    if batch_index >= batch_count:
        raise ResearchToolError(f"batch_index {batch_index} out of range; batch_count={batch_count}")
    selected = all_symbols[batch_index * batch_size : (batch_index + 1) * batch_size]
    return sorted(set(BROAD_CONTROLS).union(selected)), batch_count


class TiingoEodClient:
    def __init__(self, token: str, http: JsonHttpClient | None = None) -> None:
        if not token.strip():
            raise ResearchToolError("Tiingo token must not be blank.")
        self._token = token.strip()
        self.http = http or JsonHttpClient(timeout_seconds=30.0)

    def get_prices(self, symbol: str, start: date, end: date) -> list[dict[str, Any]]:
        symbol = symbol.strip().upper()
        if not symbol or not all(ch.isalnum() or ch in ".-" for ch in symbol):
            raise ResearchToolError(f"Invalid external symbol: {symbol!r}")
        query = urllib.parse.urlencode({"startDate": start.isoformat(), "endDate": end.isoformat(), "format": "json"})
        url = f"{TIINGO_API_BASE}/{urllib.parse.quote(symbol)}/prices?{query}"
        observation = self.http.get_json(url, headers={"Authorization": f"Token {self._token}"})
        payload = observation.payload
        if not isinstance(payload, list):
            raise ResearchToolError(f"Unexpected Tiingo EOD response shape for {symbol}")
        # Return only to caller memory. Caller must never persist these rows.
        return [row for row in payload if isinstance(row, dict)]


def parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def external_return_series(rows: Sequence[Mapping[str, Any]], variant: str) -> dict[date, float]:
    if variant not in PRICE_VARIANTS:
        raise ResearchToolError(f"Unknown price variant: {variant}")
    key = "adjClose" if variant == "adjusted" else "close"
    points: list[tuple[date, float]] = []
    for row in rows:
        day = parse_iso_date(row.get("date"))
        value = row.get(key)
        if day is None or not isinstance(value, (int, float)):
            continue
        price = float(value)
        if not math.isfinite(price) or price <= 0:
            continue
        points.append((day, price))
    points.sort(key=lambda item: item[0])
    result: dict[date, float] = {}
    for (prev_day, prev_price), (day, price) in zip(points, points[1:]):
        if day == prev_day or prev_price <= 0:
            continue
        result[day] = price / prev_price - 1.0
    return result


def torn_daily_return_series(rows: Sequence[Mapping[str, Any]], *, today_utc: date) -> dict[date, float]:
    # Tornsy d1 timestamps are candle starts. Exclude the currently forming UTC-day candle.
    points: list[tuple[date, float]] = []
    for row in rows:
        ts = row.get("timestamp")
        close = row.get("close")
        if not isinstance(ts, (int, float)) or not isinstance(close, (int, float)):
            continue
        day = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
        if day >= today_utc:
            continue
        price = float(close)
        if math.isfinite(price) and price > 0:
            points.append((day, price))
    points.sort(key=lambda item: item[0])
    result: dict[date, float] = {}
    for (prev_day, prev_price), (day, price) in zip(points, points[1:]):
        if day == prev_day or prev_price <= 0:
            continue
        result[day] = price / prev_price - 1.0
    return result


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / denom


def average_ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    return pearson(average_ranks(xs), average_ranks(ys))


def simple_regression(xs: Sequence[float], ys: Sequence[float]) -> dict[str, float | None]:
    if len(xs) != len(ys) or len(xs) < 3:
        return {"alpha": None, "beta": None, "r2": None}
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return {"alpha": None, "beta": None, "r2": None}
    beta = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    alpha = my - beta * mx
    fitted = [alpha + beta * x for x in xs]
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((y - f) ** 2 for y, f in zip(ys, fitted))
    r2 = 1.0 - sse / sst if sst > 0 else None
    return {"alpha": alpha, "beta": beta, "r2": r2}


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    n = len(vector)
    augmented = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) < 1e-15:
            return None
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        div = augmented[col][col]
        augmented[col] = [v / div for v in augmented[col]]
        for r in range(n):
            if r == col:
                continue
            factor = augmented[r][col]
            augmented[r] = [a - factor * b for a, b in zip(augmented[r], augmented[col])]
    return [augmented[i][-1] for i in range(n)]


def multiple_r2(y: Sequence[float], predictors: Sequence[Sequence[float]]) -> float | None:
    n = len(y)
    if n < 4 or any(len(col) != n for col in predictors):
        return None
    columns = [[1.0] * n] + [list(col) for col in predictors]
    p = len(columns)
    xtx = [[sum(columns[i][k] * columns[j][k] for k in range(n)) for j in range(p)] for i in range(p)]
    xty = [sum(columns[i][k] * y[k] for k in range(n)) for i in range(p)]
    coeffs = solve_linear_system(xtx, xty)
    if coeffs is None:
        return None
    fitted = [sum(coeffs[j] * columns[j][k] for j in range(p)) for k in range(n)]
    my = statistics.fmean(y)
    sst = sum((value - my) ** 2 for value in y)
    if sst == 0:
        return None
    sse = sum((value - pred) ** 2 for value, pred in zip(y, fitted))
    return 1.0 - sse / sst


def align_pair(torn: Mapping[date, float], external: Mapping[date, float], offset_days: int) -> tuple[list[date], list[float], list[float]]:
    dates: list[date] = []
    ys: list[float] = []
    xs: list[float] = []
    for torn_day in sorted(torn):
        external_day = torn_day + timedelta(days=offset_days)
        if external_day in external:
            dates.append(torn_day)
            ys.append(float(torn[torn_day]))
            xs.append(float(external[external_day]))
    return dates, ys, xs


def align_triple(
    torn: Mapping[date, float],
    candidate: Mapping[date, float],
    control: Mapping[date, float],
    offset_days: int,
) -> tuple[list[date], list[float], list[float], list[float]]:
    dates: list[date] = []
    ys: list[float] = []
    xs: list[float] = []
    cs: list[float] = []
    for torn_day in sorted(torn):
        external_day = torn_day + timedelta(days=offset_days)
        if external_day in candidate and external_day in control:
            dates.append(torn_day)
            ys.append(float(torn[torn_day]))
            xs.append(float(candidate[external_day]))
            cs.append(float(control[external_day]))
    return dates, ys, xs, cs


def yearly_correlation_summary(dates: Sequence[date], xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any]:
    by_year: dict[int, tuple[list[float], list[float]]] = {}
    for day, x, y in zip(dates, xs, ys):
        bx, by = by_year.setdefault(day.year, ([], []))
        bx.append(x)
        by.append(y)
    values: list[float] = []
    eligible_years = 0
    for year in sorted(by_year):
        x_year, y_year = by_year[year]
        if len(x_year) < 30:
            continue
        corr = pearson(x_year, y_year)
        if corr is not None:
            eligible_years += 1
            values.append(corr)
    if not values:
        return {"eligible_years": 0, "median_yearly_pearson": None, "min_yearly_pearson": None, "max_yearly_pearson": None, "years_positive": 0, "years_negative": 0}
    return {
        "eligible_years": eligible_years,
        "median_yearly_pearson": statistics.median(values),
        "min_yearly_pearson": min(values),
        "max_yearly_pearson": max(values),
        "years_positive": sum(v > 0 for v in values),
        "years_negative": sum(v < 0 for v in values),
    }


def summarize_pair(
    torn_symbol: str,
    external_symbol: str,
    role: str,
    variant: str,
    offset_days: int,
    torn: Mapping[date, float],
    external: Mapping[date, float],
    control: Mapping[date, float] | None,
) -> dict[str, Any]:
    dates, ys, xs = align_pair(torn, external, offset_days)
    regression = simple_regression(xs, ys)
    result: dict[str, Any] = {
        "torn_symbol": torn_symbol,
        "external_symbol": external_symbol,
        "candidate_role": role,
        "price_variant": variant,
        "external_date_offset_days": offset_days,
        "overlap_count": len(dates),
        "overlap_start": dates[0].isoformat() if dates else None,
        "overlap_end": dates[-1].isoformat() if dates else None,
        "pearson": pearson(xs, ys),
        "spearman": spearman(xs, ys),
        "alpha": regression["alpha"],
        "beta": regression["beta"],
        "r2": regression["r2"],
        "primary_control": PRIMARY_CONTROL if control is not None and external_symbol != PRIMARY_CONTROL else None,
        "control_r2": None,
        "candidate_plus_control_r2": None,
        "incremental_r2_over_control": None,
        **yearly_correlation_summary(dates, xs, ys),
    }
    if control is not None and external_symbol != PRIMARY_CONTROL:
        triple_dates, y3, x3, c3 = align_triple(torn, external, control, offset_days)
        if len(triple_dates) >= 4:
            control_r2 = multiple_r2(y3, [c3])
            full_r2 = multiple_r2(y3, [c3, x3])
            result["control_r2"] = control_r2
            result["candidate_plus_control_r2"] = full_r2
            result["incremental_r2_over_control"] = (full_r2 - control_r2) if full_r2 is not None and control_r2 is not None else None
    return result


def round_metrics(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key, value in list(result.items()):
        if isinstance(value, float):
            result[key] = round(value, 10) if math.isfinite(value) else None
    return result


def output_is_non_reconstructable(rows: Sequence[Mapping[str, Any]]) -> bool:
    forbidden = {"prices", "price", "close", "adjclose", "returns", "series", "observations", "raw_rows"}
    for row in rows:
        for key, value in row.items():
            if key.lower() in forbidden:
                return False
            if isinstance(value, (list, dict)):
                return False
    return True


def run(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    symbols, batch_count = batch_symbols(manifest, args.batch_index, args.batch_size)
    roles = relevant_torn_roles(manifest)
    today_utc = datetime.now(timezone.utc).date()
    end_date = today_utc - timedelta(days=1)
    start_date = date.fromisoformat(args.start_date)
    if end_date <= start_date:
        raise ResearchToolError("External screen date range is empty.")

    # Torn history is public and may be retained, but this command intentionally keeps it in memory too.
    tornsy = TornsyClient()
    torn_returns: dict[str, dict[date, float]] = {}
    for stock in manifest["stocks"]:
        torn_symbol = str(stock["torn_symbol"]).upper()
        observation = tornsy.get_stock(torn_symbol, "d1", limit=2000)
        rows = parse_tornsy_rows(observation.payload, "d1")
        torn_returns[torn_symbol] = torn_daily_return_series(rows, today_utc=today_utc)

    tiingo = TiingoEodClient(load_tiingo_token())
    external_returns: dict[str, dict[str, dict[date, float]]] = {}
    errors: list[dict[str, str]] = []
    coverage: list[dict[str, Any]] = []
    for symbol in symbols:
        try:
            raw_rows = tiingo.get_prices(symbol, start_date, end_date)
            variants = {variant: external_return_series(raw_rows, variant) for variant in PRICE_VARIANTS}
            external_returns[symbol] = variants
            all_days = sorted({day for series in variants.values() for day in series})
            coverage.append({
                "external_symbol": symbol,
                "status": "ok",
                "return_observation_count": max((len(series) for series in variants.values()), default=0),
                "first_return_date": all_days[0].isoformat() if all_days else None,
                "last_return_date": all_days[-1].isoformat() if all_days else None,
            })
            # raw_rows goes out of scope at the next iteration; it is never written or logged.
        except ResearchToolError as exc:
            errors.append({"external_symbol": symbol, "error_class": type(exc).__name__, "message": str(exc)[:300]})
            coverage.append({"external_symbol": symbol, "status": "error", "return_observation_count": 0, "first_return_date": None, "last_return_date": None})

    results: list[dict[str, Any]] = []
    spy = external_returns.get(PRIMARY_CONTROL)
    for external_symbol in symbols:
        variants = external_returns.get(external_symbol)
        if not variants:
            continue
        for assignment in roles.get(external_symbol, []):
            torn_symbol = assignment["torn_symbol"]
            role = assignment["candidate_role"]
            torn = torn_returns.get(torn_symbol, {})
            for variant in PRICE_VARIANTS:
                candidate = variants.get(variant, {})
                control = spy.get(variant, {}) if spy else None
                for offset in DATE_OFFSETS:
                    results.append(round_metrics(summarize_pair(
                        torn_symbol,
                        external_symbol,
                        role,
                        variant,
                        offset,
                        torn,
                        candidate,
                        control,
                    )))

    if not output_is_non_reconstructable(results):
        raise ResearchToolError("Output schema failed non-reconstructability guard.")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_fields = [
        "torn_symbol", "external_symbol", "candidate_role", "price_variant", "external_date_offset_days",
        "overlap_count", "overlap_start", "overlap_end", "pearson", "spearman", "alpha", "beta", "r2",
        "primary_control", "control_r2", "candidate_plus_control_r2", "incremental_r2_over_control",
        "eligible_years", "median_yearly_pearson", "min_yearly_pearson", "max_yearly_pearson", "years_positive", "years_negative",
    ]
    write_csv(output_dir / "candidate_statistics.csv", result_fields, results)
    write_csv(output_dir / "external_coverage.csv", ["external_symbol", "status", "return_observation_count", "first_return_date", "last_return_date"], coverage)
    write_csv(output_dir / "errors.csv", ["external_symbol", "error_class", "message"], errors)
    summary = {
        "research_status": "DESCRIPTIVE_SCREEN_ONLY",
        "batch_index": args.batch_index,
        "batch_size": args.batch_size,
        "batch_count": batch_count,
        "external_symbols_requested": symbols,
        "external_symbols_succeeded": sum(row["status"] == "ok" for row in coverage),
        "external_symbols_failed": sum(row["status"] == "error" for row in coverage),
        "aggregate_result_rows": len(results),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "primary_price_variant": "adjusted",
        "sensitivity_price_variant": "raw",
        "date_offsets_tested": list(DATE_OFFSETS),
        "primary_control": PRIMARY_CONTROL,
        "raw_external_data_persisted": False,
        "interpretation": "Candidate reduction only. Date offsets are descriptive alignments, not causal lead/lag findings.",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run transient external EOD candidate screen.")
    parser.add_argument("--manifest", default="research/external_driver_candidates.json")
    parser.add_argument("--output", default="research/output/external_eod_screen")
    parser.add_argument("--batch-index", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=35)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE.isoformat())
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
