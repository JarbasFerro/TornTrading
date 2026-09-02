#!/usr/bin/env python3
"""Stage 0 Torn-only statistical anatomy.

Uses audited Tornsy historical endpoints to produce descriptive aggregate statistics
for the 35 current tradable Torn stocks. No strategy optimization, trading signals,
or executable-profit claims are produced.
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

HORIZONS: dict[str, tuple[str, int]] = {
    "1m": ("m1", 1),
    "5m": ("m5", 1),
    "1h": ("h1", 1),
    "6h": ("h6", 1),
    "24h": ("d1", 1),
    "7d": ("d1", 7),
    "30d": ("d1", 30),
}
FETCH_INTERVALS = ("m1", "m5", "h1", "h6", "d1")
ACF_LAGS = (1, 2, 3, 5, 10)
CORRELATION_HORIZONS = ("1h", "24h")


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


def closed_price_series(rows: Sequence[Mapping[str, Any]], interval: str, *, now_ts: int) -> list[tuple[int, float]]:
    seconds = interval_seconds(interval)
    if seconds is None:
        raise ResearchToolError(f"Unsupported interval for closed-series logic: {interval}")
    current_boundary = (int(now_ts) // seconds) * seconds
    points: dict[int, float] = {}
    for row in rows:
        ts = row.get("timestamp")
        value = row.get("price") if interval == "m1" else row.get("close")
        if not isinstance(ts, (int, float)) or not isinstance(value, (int, float)):
            continue
        timestamp = int(ts)
        price = float(value)
        if timestamp >= current_boundary:
            continue
        if math.isfinite(price) and price > 0:
            points[timestamp] = price
    return sorted(points.items())


def lagged_returns(series: Sequence[tuple[int, float]], lag: int, expected_step_seconds: int) -> list[tuple[int, float]]:
    """Return exact-horizon returns only; never bridge source gaps."""
    if lag < 1:
        raise ValueError("lag must be >= 1")
    if expected_step_seconds <= 0:
        raise ValueError("expected_step_seconds must be positive")
    expected_span = expected_step_seconds * lag
    result: list[tuple[int, float]] = []
    for i in range(lag, len(series)):
        ts, price = series[i]
        previous_ts, previous = series[i - lag]
        if ts - previous_ts != expected_span:
            continue
        if previous <= 0:
            continue
        value = price / previous - 1.0
        if math.isfinite(value):
            result.append((ts, value))
    return result


def percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def distribution_stats(values: Sequence[float]) -> dict[str, float | int | None]:
    n = len(values)
    if n == 0:
        return {
            "count": 0, "mean": None, "median": None, "stddev": None,
            "skewness": None, "excess_kurtosis": None,
            "min": None, "p01": None, "p05": None, "p25": None,
            "p75": None, "p95": None, "p99": None, "max": None,
            "positive_rate": None, "negative_rate": None, "zero_rate": None,
        }
    mean = statistics.fmean(values)
    median = statistics.median(values)
    stddev = statistics.stdev(values) if n >= 2 else 0.0
    if stddev > 0 and n >= 3:
        standardized = [(x - mean) / stddev for x in values]
        skewness = statistics.fmean(v ** 3 for v in standardized)
        excess_kurtosis = statistics.fmean(v ** 4 for v in standardized) - 3.0
    else:
        skewness = None
        excess_kurtosis = None
    return {
        "count": n,
        "mean": mean,
        "median": median,
        "stddev": stddev,
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
        "min": min(values),
        "p01": percentile(values, 0.01),
        "p05": percentile(values, 0.05),
        "p25": percentile(values, 0.25),
        "p75": percentile(values, 0.75),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
        "positive_rate": sum(v > 0 for v in values) / n,
        "negative_rate": sum(v < 0 for v in values) / n,
        "zero_rate": sum(v == 0 for v in values) / n,
    }


def autocorrelation(values: Sequence[float], lag: int) -> float | None:
    if lag < 1 or len(values) <= lag + 1:
        return None
    left = values[:-lag]
    right = values[lag:]
    mean_left = statistics.fmean(left)
    mean_right = statistics.fmean(right)
    dx = [x - mean_left for x in left]
    dy = [y - mean_right for y in right]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if denom == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / denom


def continuation_reversal_stats(values: Sequence[float]) -> dict[str, float | int | None]:
    if len(values) < 3:
        return {
            "transition_count": 0,
            "continuation_rate": None,
            "mean_next_after_positive": None,
            "mean_next_after_negative": None,
            "mean_next_after_bottom_decile": None,
            "mean_next_after_top_decile": None,
        }
    pairs = [(values[i - 1], values[i]) for i in range(1, len(values))]
    signed = [(a, b) for a, b in pairs if a != 0 and b != 0]
    continuation = sum((a > 0) == (b > 0) for a, b in signed) / len(signed) if signed else None
    after_positive = [b for a, b in pairs if a > 0]
    after_negative = [b for a, b in pairs if a < 0]
    p10 = percentile(values[:-1], 0.10)
    p90 = percentile(values[:-1], 0.90)
    bottom = [b for a, b in pairs if p10 is not None and a <= p10]
    top = [b for a, b in pairs if p90 is not None and a >= p90]
    return {
        "transition_count": len(pairs),
        "continuation_rate": continuation,
        "mean_next_after_positive": statistics.fmean(after_positive) if after_positive else None,
        "mean_next_after_negative": statistics.fmean(after_negative) if after_negative else None,
        "mean_next_after_bottom_decile": statistics.fmean(bottom) if bottom else None,
        "mean_next_after_top_decile": statistics.fmean(top) if top else None,
    }


def quartile_stability(values: Sequence[float]) -> list[dict[str, float | int | None]]:
    n = len(values)
    if n < 40:
        return []
    result: list[dict[str, float | int | None]] = []
    for index in range(4):
        start = round(index * n / 4)
        end = round((index + 1) * n / 4)
        chunk = list(values[start:end])
        result.append({
            "quartile": index + 1,
            "count": len(chunk),
            "mean": statistics.fmean(chunk) if chunk else None,
            "stddev": statistics.stdev(chunk) if len(chunk) >= 2 else None,
            "acf_lag1": autocorrelation(chunk, 1),
            "abs_acf_lag1": autocorrelation([abs(v) for v in chunk], 1),
            "positive_rate": sum(v > 0 for v in chunk) / len(chunk) if chunk else None,
        })
    return result


def pearson_aligned(left: Mapping[int, float], right: Mapping[int, float]) -> tuple[int, float | None]:
    common = sorted(set(left).intersection(right))
    if len(common) < 3:
        return len(common), None
    xs = [float(left[t]) for t in common]
    ys = [float(right[t]) for t in common]
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if denom == 0:
        return len(common), None
    return len(common), sum(x * y for x, y in zip(dx, dy)) / denom


def round_row(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key, value in list(result.items()):
        if isinstance(value, float):
            result[key] = round(value, 12) if math.isfinite(value) else None
    return result


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


def output_schema_is_aggregate(rows: Sequence[Mapping[str, Any]]) -> bool:
    forbidden_keys = {"series", "returns", "prices", "raw_rows", "observations", "timestamps"}
    for row in rows:
        for key, value in row.items():
            if key.lower() in forbidden_keys:
                return False
            if isinstance(value, (list, dict)):
                return False
    return True


def run(args: argparse.Namespace) -> int:
    symbols = load_tradable_symbols(Path(args.manifest))
    now_ts = int(datetime.now(timezone.utc).timestamp())
    client = TornsyClient()

    fetched: dict[tuple[str, str], list[dict[str, Any]]] = {}
    fetch_audit: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for symbol in symbols:
        for interval in FETCH_INTERVALS:
            try:
                rows = fetch_rows_with_retry(client, symbol, interval, limit=2000)
                fetched[(symbol, interval)] = rows
                fetch_audit.append({"torn_symbol": symbol, "interval": interval, "status": "ok", "source_rows": len(rows)})
            except ResearchToolError as exc:
                failures.append({"torn_symbol": symbol, "interval": interval, "message": str(exc)[:300]})
                fetch_audit.append({"torn_symbol": symbol, "interval": interval, "status": "error", "source_rows": 0})
            time.sleep(args.request_delay)

    horizon_rows: list[dict[str, Any]] = []
    acf_rows: list[dict[str, Any]] = []
    continuation_rows: list[dict[str, Any]] = []
    stability_rows: list[dict[str, Any]] = []
    return_maps: dict[tuple[str, str], dict[int, float]] = {}

    for symbol in symbols:
        for horizon, (interval, lag) in HORIZONS.items():
            source_rows = fetched.get((symbol, interval), [])
            prices = closed_price_series(source_rows, interval, now_ts=now_ts)
            step = interval_seconds(interval)
            if step is None:
                raise ResearchToolError(f"Missing interval size for {interval}")
            returns = lagged_returns(prices, lag, step)
            values = [value for _, value in returns]
            return_maps[(symbol, horizon)] = {ts: value for ts, value in returns}
            horizon_rows.append(round_row({
                "torn_symbol": symbol,
                "horizon": horizon,
                "source_interval": interval,
                "lag_periods": lag,
                "expected_span_seconds": step * lag,
                "first_return_ts": returns[0][0] if returns else None,
                "last_return_ts": returns[-1][0] if returns else None,
                **distribution_stats(values),
            }))
            for acf_lag in ACF_LAGS:
                acf_rows.append(round_row({
                    "torn_symbol": symbol,
                    "horizon": horizon,
                    "acf_lag_periods": acf_lag,
                    "return_acf": autocorrelation(values, acf_lag),
                    "absolute_return_acf": autocorrelation([abs(v) for v in values], acf_lag),
                    "observation_count": len(values),
                }))
            continuation_rows.append(round_row({"torn_symbol": symbol, "horizon": horizon, **continuation_reversal_stats(values)}))
            for row in quartile_stability(values):
                stability_rows.append(round_row({"torn_symbol": symbol, "horizon": horizon, **row}))

    correlation_rows: list[dict[str, Any]] = []
    for horizon in CORRELATION_HORIZONS:
        for i, left_symbol in enumerate(symbols):
            for right_symbol in symbols[i + 1:]:
                count, corr = pearson_aligned(return_maps.get((left_symbol, horizon), {}), return_maps.get((right_symbol, horizon), {}))
                correlation_rows.append(round_row({
                    "horizon": horizon,
                    "left_symbol": left_symbol,
                    "right_symbol": right_symbol,
                    "overlap_count": count,
                    "pearson": corr,
                }))

    all_rows = horizon_rows + acf_rows + continuation_rows + stability_rows + correlation_rows + fetch_audit
    if not output_schema_is_aggregate(all_rows):
        raise ResearchToolError("Aggregate-output schema guard failed.")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "horizon_statistics.csv", horizon_rows)
    write_csv(output / "autocorrelation.csv", acf_rows)
    write_csv(output / "continuation_reversal.csv", continuation_rows)
    write_csv(output / "stability_quartiles.csv", stability_rows)
    write_csv(output / "pairwise_correlations.csv", correlation_rows)
    write_csv(output / "fetch_audit.csv", fetch_audit)
    write_csv(output / "errors.csv", failures)

    strongest_return_acf = sorted(
        (row for row in acf_rows if row.get("acf_lag_periods") == 1 and isinstance(row.get("return_acf"), float)),
        key=lambda row: abs(float(row["return_acf"])),
        reverse=True,
    )[:15]
    strongest_abs_acf = sorted(
        (row for row in acf_rows if row.get("acf_lag_periods") == 1 and isinstance(row.get("absolute_return_acf"), float)),
        key=lambda row: abs(float(row["absolute_return_acf"])),
        reverse=True,
    )[:15]
    strongest_pairs = sorted(
        (row for row in correlation_rows if isinstance(row.get("pearson"), float)),
        key=lambda row: abs(float(row["pearson"])),
        reverse=True,
    )[:20]
    summary = {
        "research_status": "DESCRIPTIVE_ONLY",
        "tradable_stock_count": len(symbols),
        "horizons": list(HORIZONS),
        "source_intervals": list(FETCH_INTERVALS),
        "source_requests_attempted": len(symbols) * len(FETCH_INTERVALS),
        "source_requests_failed": len(failures),
        "horizon_stat_rows": len(horizon_rows),
        "autocorrelation_rows": len(acf_rows),
        "continuation_reversal_rows": len(continuation_rows),
        "stability_rows": len(stability_rows),
        "pairwise_correlation_rows": len(correlation_rows),
        "forming_periods_excluded": True,
        "source_gaps_bridged": False,
        "raw_history_persisted": False,
        "strongest_lag1_return_acf": strongest_return_acf,
        "strongest_lag1_absolute_return_acf": strongest_abs_acf,
        "strongest_pairwise_correlations": strongest_pairs,
        "interpretation": "Descriptive anatomy only. Strong autocorrelation/correlation is a hypothesis seed, not validated alpha.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, list)}, indent=2, sort_keys=True))
    return 0 if not failures else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute descriptive Torn stock-market statistical anatomy.")
    parser.add_argument("--manifest", default="research/external_driver_candidates.json")
    parser.add_argument("--output", default="research/output/statistical_anatomy")
    parser.add_argument("--request-delay", type=float, default=0.25)
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
