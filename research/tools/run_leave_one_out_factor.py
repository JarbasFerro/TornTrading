#!/usr/bin/env python3
"""Stage 0 leave-one-out equal-weight Torn market-factor analysis.

For each target stock, constructs a market factor from the other tradable stocks only.
This avoids self-inclusion when measuring common-factor explanatory power. Public
Tornsy data only; aggregate outputs only; no alpha or trading signal claims.
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
MIN_PEERS = 30


def load_symbols(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stocks = payload.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 35:
        raise ResearchToolError("Expected exactly 35 tradable stocks.")
    symbols = sorted({str(row.get("torn_symbol", "")).upper() for row in stocks if isinstance(row, dict)})
    if len(symbols) != 35 or "TCSE" in symbols:
        raise ResearchToolError("Canonical universe must contain 35 unique tradable stocks and exclude TCSE.")
    return symbols


def fetch_rows(client: TornsyClient, symbol: str, interval: str, attempts: int = 3) -> list[dict[str, Any]]:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return parse_tornsy_rows(client.get_stock(symbol, interval, limit=2000).payload, interval)
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1.0 + attempt)
    raise ResearchToolError(f"Tornsy fetch failed for {symbol}/{interval}: {last}")


def returns_from_rows(rows: Sequence[Mapping[str, Any]], interval: str, now_ts: int) -> dict[int, float]:
    step = interval_seconds(interval)
    if step is None:
        raise ResearchToolError(f"Unsupported interval: {interval}")
    boundary = (int(now_ts) // step) * step
    prices: dict[int, float] = {}
    for row in rows:
        ts = row.get("timestamp")
        value = row.get("price") if interval == "m1" else row.get("close")
        if not isinstance(ts, (int, float)) or not isinstance(value, (int, float)):
            continue
        t = int(ts)
        p = float(value)
        if t >= boundary or not math.isfinite(p) or p <= 0:
            continue
        prices[t] = p
    result: dict[int, float] = {}
    for t, p in prices.items():
        prev = prices.get(t - step)
        if prev is not None and prev > 0:
            r = p / prev - 1.0
            if math.isfinite(r):
                result[t] = r
    return result


def leave_one_out_factor(target: str, returns: Mapping[str, Mapping[int, float]], min_peers: int = MIN_PEERS) -> dict[int, float]:
    peers = [symbol for symbol in returns if symbol != target]
    timestamps: set[int] = set()
    for symbol in peers:
        timestamps.update(returns[symbol])
    factor: dict[int, float] = {}
    for ts in sorted(timestamps):
        values = [returns[s][ts] for s in peers if ts in returns[s]]
        if len(values) >= min_peers:
            factor[ts] = statistics.fmean(values)
    return factor


def regression(factor: Mapping[int, float], target: Mapping[int, float]) -> dict[str, float | int | None]:
    common = sorted(set(factor).intersection(target))
    if len(common) < 3:
        return {"count": len(common), "alpha": None, "beta": None, "pearson": None, "r2": None}
    x = [factor[t] for t in common]
    y = [target[t] for t in common]
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    sxx = sum(v * v for v in dx)
    syy = sum(v * v for v in dy)
    if sxx == 0 or syy == 0:
        return {"count": len(common), "alpha": None, "beta": None, "pearson": None, "r2": None}
    cov = sum(a * b for a, b in zip(dx, dy))
    beta = cov / sxx
    alpha = my - beta * mx
    corr = cov / math.sqrt(sxx * syy)
    return {"count": len(common), "alpha": alpha, "beta": beta, "pearson": corr, "r2": corr * corr}


def residualize(target: Mapping[int, float], factor: Mapping[int, float]) -> tuple[dict[int, float], dict[str, float | int | None]]:
    stats = regression(factor, target)
    common = sorted(set(target).intersection(factor))
    if stats["alpha"] is None or stats["beta"] is None:
        return {}, {**stats, "raw_stddev": None, "residual_stddev": None, "residual_variance_ratio": None}
    alpha = float(stats["alpha"])
    beta = float(stats["beta"])
    residuals = {t: target[t] - alpha - beta * factor[t] for t in common}
    raw = [target[t] for t in common]
    rv = list(residuals.values())
    raw_sd = statistics.stdev(raw) if len(raw) >= 2 else None
    res_sd = statistics.stdev(rv) if len(rv) >= 2 else None
    ratio = (res_sd / raw_sd) ** 2 if raw_sd and res_sd is not None and raw_sd > 0 else None
    return residuals, {**stats, "raw_stddev": raw_sd, "residual_stddev": res_sd, "residual_variance_ratio": ratio}


def chronological_quartiles(target: Mapping[int, float], factor: Mapping[int, float]) -> list[dict[str, float | int | None]]:
    common = sorted(set(target).intersection(factor))
    if len(common) < 80:
        return []
    rows = []
    n = len(common)
    for q in range(4):
        ts = common[round(q*n/4):round((q+1)*n/4)]
        rows.append({"quartile": q + 1, **regression({t: factor[t] for t in ts}, {t: target[t] for t in ts})})
    return rows


def pearson_aligned(left: Mapping[int, float], right: Mapping[int, float]) -> tuple[int, float | None]:
    stats = regression(left, right)
    return int(stats["count"]), stats["pearson"]


def pairwise_summary(series: Mapping[str, Mapping[int, float]]) -> dict[str, float | int | None]:
    symbols = sorted(series)
    corrs: list[float] = []
    for i, left in enumerate(symbols):
        for right in symbols[i+1:]:
            _, corr = pearson_aligned(series[left], series[right])
            if corr is not None:
                corrs.append(float(corr))
    return {
        "pair_count": len(corrs),
        "mean_pairwise_pearson": statistics.fmean(corrs) if corrs else None,
        "median_pairwise_pearson": statistics.median(corrs) if corrs else None,
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
                fields.append(key); seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def aggregate_guard(rows: Sequence[Mapping[str, Any]]) -> bool:
    forbidden = {"series", "returns", "prices", "timestamps", "observations", "raw_rows", "residuals"}
    return all(key.lower() not in forbidden and not isinstance(value, (list, dict)) for row in rows for key, value in row.items())


def run(args: argparse.Namespace) -> int:
    symbols = load_symbols(Path(args.manifest))
    now_ts = int(datetime.now(timezone.utc).timestamp())
    client = TornsyClient()
    factor_rows: list[dict[str, Any]] = []
    quartile_rows: list[dict[str, Any]] = []
    market_rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for horizon, interval in HORIZONS.items():
        stock_returns: dict[str, dict[int, float]] = {}
        for symbol in symbols:
            try:
                stock_returns[symbol] = returns_from_rows(fetch_rows(client, symbol, interval), interval, now_ts)
            except ResearchToolError as exc:
                errors.append({"symbol": symbol, "horizon": horizon, "message": str(exc)[:300]})
            time.sleep(args.request_delay)

        residuals: dict[str, dict[int, float]] = {}
        for symbol in symbols:
            target = stock_returns.get(symbol, {})
            loo = leave_one_out_factor(symbol, stock_returns)
            resid, stats = residualize(target, loo)
            residuals[symbol] = resid
            factor_rows.append(round_row({"horizon": horizon, "torn_symbol": symbol, "factor": "leave_one_out_equal_weight", **stats}))
            for row in chronological_quartiles(target, loo):
                quartile_rows.append(round_row({"horizon": horizon, "torn_symbol": symbol, **row}))

        market_rows.append(round_row({"horizon": horizon, "comparison": "raw_pairwise", **pairwise_summary(stock_returns)}))
        market_rows.append(round_row({"horizon": horizon, "comparison": "loo_residual_pairwise", **pairwise_summary(residuals)}))

    all_rows = factor_rows + quartile_rows + market_rows
    if not aggregate_guard(all_rows):
        raise ResearchToolError("Aggregate-output guard failed.")

    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "loo_factor_by_stock.csv", factor_rows)
    write_csv(output / "loo_factor_quartiles.csv", quartile_rows)
    write_csv(output / "market_structure.csv", market_rows)
    write_csv(output / "errors.csv", errors)
    summary = {
        "research_status": "DESCRIPTIVE_FACTOR_ANALYSIS_ONLY",
        "factor": "leave_one_out_equal_weight",
        "tradable_stock_count": len(symbols),
        "minimum_peer_count": MIN_PEERS,
        "horizons": list(HORIZONS),
        "factor_rows": len(factor_rows),
        "quartile_rows": len(quartile_rows),
        "market_structure_rows": len(market_rows),
        "error_count": len(errors),
        "self_inclusion": false if False else False,
        "interpretation": "Common-factor structure only; no prediction or alpha validation."
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not errors else 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run leave-one-out Torn market-factor analysis.")
    p.add_argument("--manifest", default="research/external_driver_candidates.json")
    p.add_argument("--output", default="research/output/leave_one_out_factor")
    p.add_argument("--request-delay", type=float, default=0.25)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
