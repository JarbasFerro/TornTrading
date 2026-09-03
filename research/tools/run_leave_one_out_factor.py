#!/usr/bin/env python3
"""Describe common Torn-market structure with self-exclusion-safe equal-weight factors."""
from __future__ import annotations

import argparse, csv, json, math, statistics, sys, time
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
    symbols = sorted({str(x.get("torn_symbol", "")).upper() for x in stocks if isinstance(x, dict)})
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
                time.sleep(1 + attempt)
    raise ResearchToolError(f"Tornsy fetch failed for {symbol}/{interval}: {last}")


def returns_from_rows(rows: Sequence[Mapping[str, Any]], interval: str, now_ts: int) -> dict[int, float]:
    step = interval_seconds(interval)
    if step is None:
        raise ResearchToolError(f"Unsupported interval: {interval}")
    boundary = (now_ts // step) * step
    prices: dict[int, float] = {}
    for row in rows:
        ts, value = row.get("timestamp"), row.get("price") if interval == "m1" else row.get("close")
        if not isinstance(ts, (int, float)) or not isinstance(value, (int, float)):
            continue
        ts_i, price = int(ts), float(value)
        if ts_i < boundary and math.isfinite(price) and price > 0:
            prices[ts_i] = price
    result: dict[int, float] = {}
    for ts, price in prices.items():
        previous = prices.get(ts - step)
        if previous is not None and previous > 0:
            value = price / previous - 1
            if math.isfinite(value):
                result[ts] = value
    return result


def peer_factor(
    excluded: set[str],
    series: Mapping[str, Mapping[int, float]],
    min_peers: int = MIN_PEERS,
) -> dict[int, float]:
    peers = [symbol for symbol in series if symbol not in excluded]
    timestamps = set().union(*(set(series[symbol]) for symbol in peers)) if peers else set()
    result: dict[int, float] = {}
    for ts in sorted(timestamps):
        values = [series[symbol][ts] for symbol in peers if ts in series[symbol]]
        if len(values) >= min_peers:
            result[ts] = statistics.fmean(values)
    return result


def leave_one_out_factor(target: str, series: Mapping[str, Mapping[int, float]], min_peers: int = MIN_PEERS) -> dict[int, float]:
    return peer_factor({target}, series, min_peers=min_peers)


def regression(factor: Mapping[int, float], target: Mapping[int, float]) -> dict[str, float | int | None]:
    common = sorted(set(factor) & set(target))
    if len(common) < 3:
        return {"count": len(common), "alpha": None, "beta": None, "pearson": None, "r2": None}
    x, y = [factor[t] for t in common], [target[t] for t in common]
    mx, my = statistics.fmean(x), statistics.fmean(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    sxx, syy = sum(v*v for v in dx), sum(v*v for v in dy)
    if sxx == 0 or syy == 0:
        return {"count": len(common), "alpha": None, "beta": None, "pearson": None, "r2": None}
    covariance = sum(a*b for a, b in zip(dx, dy))
    beta = covariance / sxx
    corr = covariance / math.sqrt(sxx * syy)
    return {"count": len(common), "alpha": my - beta*mx, "beta": beta, "pearson": corr, "r2": corr*corr}


def residualize(target: Mapping[int, float], factor: Mapping[int, float]) -> tuple[dict[int, float], dict[str, float | int | None]]:
    stats = regression(factor, target)
    common = sorted(set(target) & set(factor))
    if stats["alpha"] is None or stats["beta"] is None:
        return {}, {**stats, "raw_stddev": None, "residual_stddev": None, "residual_variance_ratio": None}
    alpha, beta = float(stats["alpha"]), float(stats["beta"])
    residuals = {t: target[t] - alpha - beta*factor[t] for t in common}
    raw, res = [target[t] for t in common], list(residuals.values())
    raw_sd = statistics.stdev(raw) if len(raw) >= 2 else None
    res_sd = statistics.stdev(res) if len(res) >= 2 else None
    ratio = (res_sd/raw_sd)**2 if raw_sd and res_sd is not None and raw_sd > 0 else None
    return residuals, {**stats, "raw_stddev": raw_sd, "residual_stddev": res_sd, "residual_variance_ratio": ratio}


def chronological_quartiles(target: Mapping[int, float], factor: Mapping[int, float]) -> list[dict[str, float | int | None]]:
    common = sorted(set(target) & set(factor))
    if len(common) < 80:
        return []
    n, rows = len(common), []
    for q in range(4):
        ts = common[round(q*n/4):round((q+1)*n/4)]
        rows.append({"quartile": q+1, **regression({t: factor[t] for t in ts}, {t: target[t] for t in ts})})
    return rows


def pairwise_summary(series: Mapping[str, Mapping[int, float]]) -> dict[str, float | int | None]:
    symbols, corrs = sorted(series), []
    for i, left in enumerate(symbols):
        for right in symbols[i+1:]:
            corr = regression(series[left], series[right])["pearson"]
            if corr is not None:
                corrs.append(float(corr))
    return {"pair_count": len(corrs), "mean_pairwise_pearson": statistics.fmean(corrs) if corrs else None,
            "median_pairwise_pearson": statistics.median(corrs) if corrs else None}


def leave_two_out_pair_residual_correlation(
    left: str,
    right: str,
    series: Mapping[str, Mapping[int, float]],
    min_peers: int = MIN_PEERS,
) -> tuple[int, float | None]:
    """Residual correlation for one pair using a factor that excludes both members."""
    factor = peer_factor({left, right}, series, min_peers=min_peers)
    left_residuals, _ = residualize(series[left], factor)
    right_residuals, _ = residualize(series[right], factor)
    stats = regression(left_residuals, right_residuals)
    return int(stats["count"]), stats["pearson"]


def leave_two_out_residual_pairwise_summary(
    series: Mapping[str, Mapping[int, float]],
    min_peers: int = MIN_PEERS,
) -> dict[str, float | int | None]:
    """Aggregate pair dependence without either pair member entering its factor."""
    symbols, corrs = sorted(series), []
    for i, left in enumerate(symbols):
        for right in symbols[i+1:]:
            _, corr = leave_two_out_pair_residual_correlation(left, right, series, min_peers=min_peers)
            if corr is not None:
                corrs.append(float(corr))
    return {"pair_count": len(corrs), "mean_pairwise_pearson": statistics.fmean(corrs) if corrs else None,
            "median_pairwise_pearson": statistics.median(corrs) if corrs else None}


def rounded(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: (round(v, 12) if isinstance(v, float) and math.isfinite(v) else None if isinstance(v, float) else v) for k, v in row.items()}


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8"); return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def aggregate_guard(rows: Sequence[Mapping[str, Any]]) -> bool:
    forbidden = {"series", "returns", "prices", "timestamps", "observations", "raw_rows", "residuals"}
    return all(k.lower() not in forbidden and not isinstance(v, (list, dict)) for row in rows for k, v in row.items())


def run(args: argparse.Namespace) -> int:
    symbols, now_ts, client = load_symbols(Path(args.manifest)), int(datetime.now(timezone.utc).timestamp()), TornsyClient()
    factor_rows, quartile_rows, market_rows, errors = [], [], [], []
    for horizon, interval in HORIZONS.items():
        stock_returns: dict[str, dict[int, float]] = {}
        for symbol in symbols:
            try:
                stock_returns[symbol] = returns_from_rows(fetch_rows(client, symbol, interval), interval, now_ts)
            except ResearchToolError as exc:
                errors.append({"symbol": symbol, "horizon": horizon, "message": str(exc)[:300]})
            time.sleep(args.request_delay)
        for symbol in symbols:
            target = stock_returns.get(symbol, {})
            factor = leave_one_out_factor(symbol, stock_returns)
            _, stats = residualize(target, factor)
            factor_rows.append(rounded({"horizon": horizon, "torn_symbol": symbol, "factor": "leave_one_out_equal_weight", **stats}))
            quartile_rows.extend(rounded({"horizon": horizon, "torn_symbol": symbol, **row}) for row in chronological_quartiles(target, factor))
        market_rows.append(rounded({"horizon": horizon, "comparison": "raw_pairwise", **pairwise_summary(stock_returns)}))
        market_rows.append(rounded({"horizon": horizon, "comparison": "leave_two_out_residual_pairwise",
                                    **leave_two_out_residual_pairwise_summary(stock_returns)}))
    all_rows = factor_rows + quartile_rows + market_rows
    if not aggregate_guard(all_rows):
        raise ResearchToolError("Aggregate-output guard failed.")
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    write_csv(output/"loo_factor_by_stock.csv", factor_rows); write_csv(output/"loo_factor_quartiles.csv", quartile_rows)
    write_csv(output/"market_structure.csv", market_rows); write_csv(output/"errors.csv", errors)
    summary = {"research_status": "DESCRIPTIVE_FACTOR_ANALYSIS_ONLY", "factor": "leave_one_out_equal_weight",
               "pairwise_residual_factor": "leave_two_out_equal_weight", "tradable_stock_count": len(symbols),
               "minimum_peer_count": MIN_PEERS, "factor_rows": len(factor_rows), "quartile_rows": len(quartile_rows),
               "market_structure_rows": len(market_rows), "error_count": len(errors), "self_inclusion": False,
               "pairwise_mutual_inclusion": False,
               "interpretation": "Common-factor structure only; no prediction or alpha validation."}
    (output/"summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True)); return 0 if not errors else 3


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(); p.add_argument("--manifest", default="research/external_driver_candidates.json")
    p.add_argument("--output", default="research/output/leave_one_out_factor"); p.add_argument("--request-delay", type=float, default=0.25)
    try: return run(p.parse_args(argv))
    except (ResearchToolError, ValueError) as exc: print(f"error: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
