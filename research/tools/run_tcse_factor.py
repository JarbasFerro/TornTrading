#!/usr/bin/env python3
"""Stage 0 TCSE market-factor analysis.

Measures whether the Torn City Stock Exchange index (TCSE) explains a common
component of tradable Torn stock returns. Public Tornsy data only; aggregate
outputs only; no trading signals or executable-profit claims.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from torn_research import ResearchToolError, TornsyClient, interval_seconds, parse_tornsy_rows

HORIZONS = {"1h": "h1", "24h": "d1"}
MIN_STOCKS_FOR_EQUAL_WEIGHT = 30


def load_tradable_symbols(manifest_path: Path) -> list[str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    stocks = payload.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 35:
        raise ResearchToolError("Expected exactly 35 tradable stocks in candidate manifest.")
    symbols = sorted({str(row.get("torn_symbol", "")).upper() for row in stocks if isinstance(row, dict)})
    if len(symbols) != 35 or "TCSE" in symbols:
        raise ResearchToolError("Canonical universe must contain 35 unique tradable symbols and exclude TCSE.")
    return symbols


def fetch_rows_with_retry(client: TornsyClient, symbol: str, interval: str, *, limit: int = 2000, attempts: int = 3) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            observation = client.get_stock(symbol, interval, limit=limit)
            return parse_tornsy_rows(observation.payload, interval)
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.0 + attempt)
    raise ResearchToolError(f"Tornsy fetch failed for {symbol}/{interval}: {last_error}")


def closed_prices(rows: Sequence[Mapping[str, Any]], interval: str, now_ts: int) -> dict[int, float]:
    step = interval_seconds(interval)
    if step is None:
        raise ResearchToolError(f"Unsupported interval: {interval}")
    current_boundary = (int(now_ts) // step) * step
    result: dict[int, float] = {}
    for row in rows:
        ts = row.get("timestamp")
        value = row.get("price") if interval == "m1" else row.get("close")
        if not isinstance(ts, (int, float)) or not isinstance(value, (int, float)):
            continue
        timestamp = int(ts)
        price = float(value)
        if timestamp >= current_boundary or not math.isfinite(price) or price <= 0:
            continue
        result[timestamp] = price
    return result


def one_period_returns(prices: Mapping[int, float], step_seconds: int) -> dict[int, float]:
    result: dict[int, float] = {}
    for ts, price in prices.items():
        prev = prices.get(ts - step_seconds)
        if prev is None or prev <= 0:
            continue
        value = price / prev - 1.0
        if math.isfinite(value):
            result[ts] = value
    return result


def simple_regression(x: Sequence[float], y: Sequence[float]) -> dict[str, float | None]:
    if len(x) != len(y) or len(x) < 3:
        return {"alpha": None, "beta": None, "r2": None, "pearson": None}
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    sxx = sum(v * v for v in dx)
    syy = sum(v * v for v in dy)
    if sxx == 0 or syy == 0:
        return {"alpha": None, "beta": None, "r2": None, "pearson": None}
    cov = sum(a * b for a, b in zip(dx, dy))
    beta = cov / sxx
    alpha = my - beta * mx
    pearson = cov / math.sqrt(sxx * syy)
    return {"alpha": alpha, "beta": beta, "r2": pearson * pearson, "pearson": pearson}


def residualize(stock: Mapping[int, float], factor: Mapping[int, float]) -> tuple[dict[int, float], dict[str, float | int | None]]:
    common = sorted(set(stock).intersection(factor))
    x = [factor[t] for t in common]
    y = [stock[t] for t in common]
    reg = simple_regression(x, y)
    if reg["alpha"] is None or reg["beta"] is None:
        return {}, {"count": len(common), **reg, "raw_stddev": None, "residual_stddev": None, "residual_variance_ratio": None}
    alpha = float(reg["alpha"])
    beta = float(reg["beta"])
    residuals = {t: stock[t] - (alpha + beta * factor[t]) for t in common}
    raw_std = statistics.stdev(y) if len(y) >= 2 else None
    res_values = list(residuals.values())
    residual_std = statistics.stdev(res_values) if len(res_values) >= 2 else None
    ratio = (residual_std * residual_std) / (raw_std * raw_std) if raw_std and residual_std is not None and raw_std > 0 else None
    return residuals, {
        "count": len(common), **reg,
        "raw_stddev": raw_std,
        "residual_stddev": residual_std,
        "residual_variance_ratio": ratio,
    }


def pearson_aligned(left: Mapping[int, float], right: Mapping[int, float]) -> tuple[int, float | None]:
    common = sorted(set(left).intersection(right))
    if len(common) < 3:
        return len(common), None
    reg = simple_regression([left[t] for t in common], [right[t] for t in common])
    return len(common), reg["pearson"]


def equal_weight_market(stock_returns: Mapping[str, Mapping[int, float]], min_stocks: int = MIN_STOCKS_FOR_EQUAL_WEIGHT) -> dict[int, float]:
    timestamps: set[int] = set()
    for series in stock_returns.values():
        timestamps.update(series)
    result: dict[int, float] = {}
    for ts in sorted(timestamps):
        values = [series[ts] for series in stock_returns.values() if ts in series]
        if len(values) >= min_stocks:
            result[ts] = statistics.fmean(values)
    return result


def chronological_quartiles(stock: Mapping[int, float], factor: Mapping[int, float]) -> list[dict[str, float | int | None]]:
    common = sorted(set(stock).intersection(factor))
    if len(common) < 80:
        return []
    rows: list[dict[str, float | int | None]] = []
    n = len(common)
    for q in range(4):
        start = round(q * n / 4)
        end = round((q + 1) * n / 4)
        ts = common[start:end]
        reg = simple_regression([factor[t] for t in ts], [stock[t] for t in ts])
        rows.append({"quartile": q + 1, "count": len(ts), **reg})
    return rows


def mean_pairwise_correlation(series_by_symbol: Mapping[str, Mapping[int, float]]) -> dict[str, float | int | None]:
    symbols = sorted(series_by_symbol)
    values: list[float] = []
    overlaps: list[int] = []
    for i, left in enumerate(symbols):
        for right in symbols[i + 1:]:
            n, corr = pearson_aligned(series_by_symbol[left], series_by_symbol[right])
            if corr is not None:
                values.append(corr)
                overlaps.append(n)
    return {
        "pair_count": len(values),
        "mean_pairwise_pearson": statistics.fmean(values) if values else None,
        "median_pairwise_pearson": statistics.median(values) if values else None,
        "mean_overlap_count": statistics.fmean(overlaps) if overlaps else None,
    }


def round_row(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key, value in list(out.items()):
        if isinstance(value, float):
            out[key] = round(value, 12) if math.isfinite(value) else None
    return out


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_guard(rows: Sequence[Mapping[str, Any]]) -> bool:
    forbidden = {"series", "returns", "prices", "timestamps", "observations", "raw_rows", "residuals"}
    return all(not isinstance(value, (list, dict)) and key.lower() not in forbidden for row in rows for key, value in row.items())


def run(args: argparse.Namespace) -> int:
    symbols = load_tradable_symbols(Path(args.manifest))
    now_ts = int(datetime.now(timezone.utc).timestamp())
    client = TornsyClient()
    factor_rows: list[dict[str, Any]] = []
    quartile_rows: list[dict[str, Any]] = []
    market_rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for horizon, interval in HORIZONS.items():
        step = interval_seconds(interval)
        if step is None:
            raise ResearchToolError(f"Missing interval size for {interval}")
        try:
            tcse_rows = fetch_rows_with_retry(client, "TCSE", interval)
            tcse = one_period_returns(closed_prices(tcse_rows, interval, now_ts), step)
        except ResearchToolError as exc:
            errors.append({"symbol": "TCSE", "horizon": horizon, "message": str(exc)[:300]})
            continue

        stock_returns: dict[str, dict[int, float]] = {}
        for symbol in symbols:
            try:
                rows = fetch_rows_with_retry(client, symbol, interval)
                stock_returns[symbol] = one_period_returns(closed_prices(rows, interval, now_ts), step)
            except ResearchToolError as exc:
                errors.append({"symbol": symbol, "horizon": horizon, "message": str(exc)[:300]})
            time.sleep(args.request_delay)

        equal_weight = equal_weight_market(stock_returns)
        ew_n, ew_corr = pearson_aligned(tcse, equal_weight)
        ew_reg = simple_regression(
            [tcse[t] for t in sorted(set(tcse).intersection(equal_weight))],
            [equal_weight[t] for t in sorted(set(tcse).intersection(equal_weight))],
        )
        market_rows.append(round_row({
            "horizon": horizon,
            "comparison": "TCSE_vs_equal_weight_35",
            "overlap_count": ew_n,
            "pearson": ew_corr,
            "r2": ew_reg["r2"],
            "beta": ew_reg["beta"],
        }))

        residuals_by_symbol: dict[str, dict[int, float]] = {}
        for symbol in symbols:
            series = stock_returns.get(symbol, {})
            residuals, stats = residualize(series, tcse)
            residuals_by_symbol[symbol] = residuals
            factor_rows.append(round_row({"horizon": horizon, "torn_symbol": symbol, **stats}))
            for row in chronological_quartiles(series, tcse):
                quartile_rows.append(round_row({"horizon": horizon, "torn_symbol": symbol, **row}))

        raw_corr = mean_pairwise_correlation(stock_returns)
        residual_corr = mean_pairwise_correlation(residuals_by_symbol)
        market_rows.append(round_row({"horizon": horizon, "comparison": "raw_pairwise_cross_stock", **raw_corr}))
        market_rows.append(round_row({"horizon": horizon, "comparison": "TCSE_residual_pairwise_cross_stock", **residual_corr}))

    all_rows = factor_rows + quartile_rows + market_rows
    if not aggregate_guard(all_rows):
        raise ResearchToolError("Aggregate-output guard failed.")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "tcse_factor_by_stock.csv", factor_rows)
    write_csv(output / "tcse_factor_quartiles.csv", quartile_rows)
    write_csv(output / "market_structure.csv", market_rows)
    write_csv(output / "errors.csv", errors)
    summary = {
        "research_status": "DESCRIPTIVE_FACTOR_ANALYSIS_ONLY",
        "tradable_stock_count": len(symbols),
        "factor": "TCSE",
        "horizons": list(HORIZONS),
        "factor_rows": len(factor_rows),
        "quartile_rows": len(quartile_rows),
        "market_structure_rows": len(market_rows),
        "error_count": len(errors),
        "interpretation": "Measures common-market structure only; no alpha or trading signal is validated.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not errors else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TCSE market-factor analysis.")
    parser.add_argument("--manifest", default="research/external_driver_candidates.json")
    parser.add_argument("--output", default="research/output/tcse_factor")
    parser.add_argument("--request-delay", type=float, default=0.25)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
