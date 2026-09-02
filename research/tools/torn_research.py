#!/usr/bin/env python3
"""Research-only data collection and audit tooling for TornTrading.

No trading signals. No Torn game actions. Automatic Torn requests use API v2 only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

TORN_API_BASE = "https://api.torn.com/v2"
TORNSY_API_BASE = "https://tornsy.com/api"
USER_AGENT = "TornTrading-Research/0.1 (+https://github.com/JarbasFerro/TornTrading)"


class ResearchToolError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    value = value or utc_now()
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def safe_filename_timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json_immutable(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ResearchToolError(f"Refusing to overwrite existing raw file: {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@dataclass(frozen=True)
class HttpObservation:
    url: str
    request_started_at_utc: str
    response_received_at_utc: str
    elapsed_ms: int
    status: int
    payload: Any
    payload_sha256: str


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    sensitive = {"key", "apikey", "api_key", "token", "access_token"}
    items = [
        (key, "REDACTED" if key.lower() in sensitive else value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(items), parsed.fragment))


class JsonHttpClient:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> HttpObservation:
        request_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(url, headers=request_headers, method="GET")
        started_dt = utc_now()
        started_perf = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                body = ""
            raise ResearchToolError(f"HTTP {exc.code} from {redact_url(url)}: {body}") from None
        except urllib.error.URLError as exc:
            raise ResearchToolError(f"Network error requesting {redact_url(url)}: {exc.reason}") from None
        received_dt = utc_now()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResearchToolError(f"Non-JSON response from {redact_url(url)}: {exc}") from None
        return HttpObservation(
            url=redact_url(url),
            request_started_at_utc=iso_utc(started_dt),
            response_received_at_utc=iso_utc(received_dt),
            elapsed_ms=round((time.monotonic() - started_perf) * 1000),
            status=status,
            payload=payload,
            payload_sha256=sha256_json(payload),
        )


class TornApiClient:
    def __init__(self, api_key: str, http: JsonHttpClient | None = None) -> None:
        if not api_key.strip():
            raise ResearchToolError("TORN_API_KEY is required for official Torn API commands.")
        self._api_key = api_key.strip()
        self.http = http or JsonHttpClient()

    def get(self, path: str, query: Mapping[str, str | int] | None = None) -> HttpObservation:
        path = path if path.startswith("/") else "/" + path
        url = TORN_API_BASE + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        return self.http.get_json(url, headers={"Authorization": f"ApiKey {self._api_key}"})


class TornsyClient:
    INTERVALS = {"m1", "m5", "m15", "m30", "h1", "h2", "h4", "h6", "h12", "d1", "w1", "n1", "y1", "all"}

    def __init__(self, http: JsonHttpClient | None = None) -> None:
        self.http = http or JsonHttpClient()

    def get_stock(self, symbol: str, interval: str = "m1", *, from_ts: int | None = None, to_ts: int | None = None, limit: int = 2000) -> HttpObservation:
        symbol = normalize_symbol(symbol)
        if interval not in self.INTERVALS:
            raise ResearchToolError(f"Unsupported Tornsy interval: {interval}")
        if not 1 <= limit <= 2000:
            raise ResearchToolError("Tornsy limit must be between 1 and 2000.")
        query: dict[str, int | str] = {"interval": interval, "limit": limit}
        if from_ts is not None:
            query["from"] = int(from_ts)
        if to_ts is not None:
            query["to"] = int(to_ts)
        url = f"{TORNSY_API_BASE}/{urllib.parse.quote(symbol.lower())}?{urllib.parse.urlencode(query)}"
        return self.http.get_json(url)

    def get_watchlist(self) -> HttpObservation:
        return self.http.get_json(f"{TORNSY_API_BASE}/stocks")


def normalize_symbol(symbol: str) -> str:
    result = symbol.strip().upper()
    if not (3 <= len(result) <= 4 and result.isalpha()):
        raise ResearchToolError(f"Invalid Torn stock acronym: {symbol!r}")
    return result


def unwrap_list(payload: Any, preferred_key: str) -> list[Any]:
    if isinstance(payload, dict):
        if isinstance(payload.get(preferred_key), list):
            return payload[preferred_key]
        if isinstance(payload.get("data"), list):
            return payload["data"]
    if isinstance(payload, list):
        return payload
    raise ResearchToolError(f"Expected a list at '{preferred_key}' or 'data' in API response.")


def extract_stock_rows(payload: Any) -> list[dict[str, Any]]:
    rows = [row for row in unwrap_list(payload, "stocks") if isinstance(row, dict) and "id" in row]
    if not rows:
        raise ResearchToolError("No stock objects with an id found in /torn/stocks response.")
    return rows


def extract_history(payload: Any) -> list[dict[str, Any]]:
    """Extract chart history from documented and legacy-compatible envelopes."""
    if not isinstance(payload, dict):
        return []
    candidates: list[dict[str, Any]] = [payload]
    for key in ("stocks", "stock"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for candidate in candidates:
        chart = candidate.get("chart")
        if isinstance(chart, dict) and isinstance(chart.get("history"), list):
            return [x for x in chart["history"] if isinstance(x, dict)]
    return []


def timestamp_inventory(history: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    timestamps = sorted({int(row["timestamp"]) for row in history if isinstance(row.get("timestamp"), (int, float))})
    if not timestamps:
        return {"history_rows": len(history), "unique_timestamps": 0, "oldest_ts": None, "newest_ts": None, "span_days": None, "median_delta_s": None, "min_delta_s": None, "max_delta_s": None, "pct_60s_delta": None, "duplicates": len(history)}
    deltas = [b - a for a, b in zip(timestamps, timestamps[1:])]
    return {
        "history_rows": len(history), "unique_timestamps": len(timestamps), "oldest_ts": timestamps[0], "newest_ts": timestamps[-1],
        "span_days": round((timestamps[-1] - timestamps[0]) / 86400, 6),
        "median_delta_s": statistics.median(deltas) if deltas else None, "min_delta_s": min(deltas) if deltas else None,
        "max_delta_s": max(deltas) if deltas else None,
        "pct_60s_delta": round(sum(d == 60 for d in deltas) / len(deltas) * 100, 6) if deltas else None,
        "duplicates": len(history) - len(timestamps),
    }


def parse_tornsy_rows(payload: Any, interval: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in unwrap_list(payload, "data"):
        if not isinstance(raw, list) or not raw:
            continue
        try:
            timestamp = int(raw[0])
            if interval == "m1" and len(raw) >= 3:
                rows.append({"timestamp": timestamp, "price": float(raw[1]), "total_shares": int(raw[2]), "marketcap": int(raw[3]) if len(raw) > 3 and raw[3] is not None else None})
            elif interval != "m1" and len(raw) >= 6:
                rows.append({"timestamp": timestamp, "open": float(raw[1]), "high": float(raw[2]), "low": float(raw[3]), "close": float(raw[4]), "total_shares": int(raw[5]), "marketcap": int(raw[6]) if len(raw) > 6 and raw[6] is not None else None})
        except (TypeError, ValueError):
            continue
    return rows


def interval_seconds(interval: str) -> int | None:
    return {"m1": 60, "m5": 300, "m15": 900, "m30": 1800, "h1": 3600, "h2": 7200, "h4": 14400, "h6": 21600, "h12": 43200, "d1": 86400, "w1": 604800}.get(interval)


def audit_tornsy_rows(rows: Sequence[Mapping[str, Any]], interval: str) -> dict[str, Any]:
    timestamps = [int(row["timestamp"]) for row in rows]
    unique = sorted(set(timestamps))
    deltas = [b - a for a, b in zip(unique, unique[1:])]
    expected = interval_seconds(interval)
    gaps = [d for d in deltas if expected and d > expected]
    missing_slots = sum(max(0, d // expected - 1) for d in gaps if expected and d % expected == 0) if expected else None
    return {
        "rows": len(rows), "unique_timestamps": len(unique), "duplicates": len(rows) - len(unique),
        "oldest_ts": unique[0] if unique else None, "newest_ts": unique[-1] if unique else None,
        "span_days": round((unique[-1] - unique[0]) / 86400, 6) if len(unique) >= 2 else 0 if unique else None,
        "median_delta_s": statistics.median(deltas) if deltas else None, "min_delta_s": min(deltas) if deltas else None,
        "max_delta_s": max(deltas) if deltas else None, "expected_delta_s": expected,
        "gap_count": len(gaps) if expected else None, "missing_slots_if_regular": missing_slots,
    }


def reconcile_live_payloads(official_payload: Any, tornsy_payload: Any) -> dict[str, Any]:
    official_rows = extract_stock_rows(official_payload)
    tornsy_rows = unwrap_list(tornsy_payload, "data")
    tornsy_by_symbol = {str(row.get("stock", "")).upper(): row for row in tornsy_rows if isinstance(row, dict) and row.get("stock")}
    comparison = []
    for stock in official_rows:
        symbol = str(stock.get("acronym", "")).upper()
        market = stock.get("market") if isinstance(stock.get("market"), dict) else {}
        peer = tornsy_by_symbol.get(symbol)
        official_price = float(market["price"]) if market.get("price") is not None else None
        official_shares = int(market["shares"]) if market.get("shares") is not None else None
        tornsy_price = float(peer["price"]) if peer and peer.get("price") is not None else None
        tornsy_shares = int(peer["total_shares"]) if peer and peer.get("total_shares") is not None else None
        comparison.append({
            "stock_id": stock.get("id"), "acronym": symbol, "official_price": official_price, "tornsy_price": tornsy_price,
            "price_abs_diff": abs(official_price - tornsy_price) if official_price is not None and tornsy_price is not None else None,
            "price_equal_numeric": official_price == tornsy_price if official_price is not None and tornsy_price is not None else None,
            "official_shares": official_shares, "tornsy_total_shares": tornsy_shares,
            "shares_diff": official_shares - tornsy_shares if official_shares is not None and tornsy_shares is not None else None,
            "tornsy_present": peer is not None,
        })
    return {"tornsy_timestamp": tornsy_payload.get("timestamp") if isinstance(tornsy_payload, dict) else None, "official_stock_count": len(official_rows), "tornsy_stock_count": len(tornsy_by_symbol), "rows": comparison}


def observation_record(observation: HttpObservation) -> dict[str, Any]:
    return {"source_url": observation.url, "request_started_at_utc": observation.request_started_at_utc, "response_received_at_utc": observation.response_received_at_utc, "elapsed_ms": observation.elapsed_ms, "http_status": observation.status, "payload_sha256": observation.payload_sha256, "payload": observation.payload}


def command_snapshot(args: argparse.Namespace) -> int:
    client = TornApiClient(load_torn_api_key())
    run_id = safe_filename_timestamp()
    run_dir = Path(args.output) / "torn_api_v2" / "snapshots" / run_id
    server_time = client.get("/torn/timestamp")
    stocks = client.get("/torn/stocks")
    write_json_immutable(run_dir / "torn_timestamp.json", observation_record(server_time))
    write_json_immutable(run_dir / "torn_stocks.json", observation_record(stocks))
    write_json_immutable(run_dir / "manifest.json", {"command": "snapshot", "run_id": run_id, "created_at_utc": iso_utc(), "notes": "Retrieval time is not assumed to be market-effective price time."})
    print(run_dir)
    return 0


def command_official_history(args: argparse.Namespace) -> int:
    client = TornApiClient(load_torn_api_key())
    run_id = safe_filename_timestamp()
    run_dir = Path(args.output) / "torn_api_v2" / "official_history" / run_id
    stocks_observation = client.get("/torn/stocks")
    stocks = extract_stock_rows(stocks_observation.payload)
    write_json_immutable(run_dir / "all_stocks.json", observation_record(stocks_observation))
    inventory_rows: list[dict[str, Any]] = []
    for index, stock in enumerate(stocks):
        stock_id = int(stock["id"])
        acronym = str(stock.get("acronym") or stock_id).upper()
        observation = client.get(f"/torn/{stock_id}/stocks")
        inventory_rows.append({"stock_id": stock_id, "acronym": acronym, **timestamp_inventory(extract_history(observation.payload)), "payload_sha256": observation.payload_sha256})
        write_json_immutable(run_dir / f"{stock_id:02d}_{acronym}.json", observation_record(observation))
        if args.delay > 0 and index + 1 < len(stocks):
            time.sleep(args.delay)
    fields = ["stock_id", "acronym", "history_rows", "unique_timestamps", "oldest_ts", "newest_ts", "span_days", "median_delta_s", "min_delta_s", "max_delta_s", "pct_60s_delta", "duplicates", "payload_sha256"]
    write_csv(run_dir / "inventory.csv", fields, inventory_rows)
    write_json_immutable(run_dir / "inventory.json", inventory_rows)
    print(run_dir)
    return 0


def command_tornsy_audit(args: argparse.Namespace) -> int:
    observation = TornsyClient().get_stock(args.symbol, args.interval, from_ts=args.from_ts, to_ts=args.to_ts, limit=args.limit)
    symbol = normalize_symbol(args.symbol)
    report = {"source": "tornsy", "symbol": symbol, "interval": args.interval, "parameters": {"from": args.from_ts, "to": args.to_ts, "limit": args.limit}, "retrieval": {"request_started_at_utc": observation.request_started_at_utc, "response_received_at_utc": observation.response_received_at_utc, "payload_sha256": observation.payload_sha256}, "audit": audit_tornsy_rows(parse_tornsy_rows(observation.payload, args.interval), args.interval)}
    run_dir = Path(args.output) / "tornsy" / "audit" / symbol / args.interval / safe_filename_timestamp()
    write_json_immutable(run_dir / "raw.json", observation_record(observation))
    write_json_immutable(run_dir / "audit.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def command_reconcile_live(args: argparse.Namespace) -> int:
    torn = TornApiClient(load_torn_api_key())
    run_id = safe_filename_timestamp()
    run_dir = Path(args.output) / "reconciliation" / "live" / run_id
    server_time = torn.get("/torn/timestamp")
    official = torn.get("/torn/stocks")
    if args.wait_seconds > 0:
        time.sleep(args.wait_seconds)
    archive = TornsyClient().get_watchlist()
    report = {
        "command": "reconcile-live", "run_id": run_id, "created_at_utc": iso_utc(),
        "official_retrieval": {"request_started_at_utc": official.request_started_at_utc, "response_received_at_utc": official.response_received_at_utc, "payload_sha256": official.payload_sha256},
        "tornsy_retrieval": {"request_started_at_utc": archive.request_started_at_utc, "response_received_at_utc": archive.response_received_at_utc, "payload_sha256": archive.payload_sha256},
        "comparison": reconcile_live_payloads(official.payload, archive.payload),
        "interpretation_warning": "A mismatch is evidence to investigate, not automatically an error: timestamp semantics are still under research.",
    }
    write_json_immutable(run_dir / "torn_timestamp.json", observation_record(server_time))
    write_json_immutable(run_dir / "official_stocks.json", observation_record(official))
    write_json_immutable(run_dir / "tornsy_watchlist.json", observation_record(archive))
    write_json_immutable(run_dir / "comparison.json", report)
    print(run_dir)
    return 0


def command_tornsy_watchlist(args: argparse.Namespace) -> int:
    observation = TornsyClient().get_watchlist()
    run_dir = Path(args.output) / "tornsy" / "watchlist" / safe_filename_timestamp()
    write_json_immutable(run_dir / "raw.json", observation_record(observation))
    print(run_dir)
    return 0


def load_torn_api_key() -> str:
    key = os.environ.get("TORN_API_KEY", "").strip()
    if not key:
        raise ResearchToolError("Set TORN_API_KEY in the environment. API keys are intentionally not accepted on the command line.")
    return key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="torn-research", description="Research-only Torn stock collector/auditor. No trade actions or signals.")
    parser.add_argument("--output", default="data/raw", help="Root for immutable research outputs (default: data/raw).")
    subs = parser.add_subparsers(dest="command", required=True)
    snapshot = subs.add_parser("snapshot", help="Capture Torn server timestamp and current stocks.")
    snapshot.set_defaults(func=command_snapshot)
    history = subs.add_parser("official-history", help="Inventory official chart history for every stock.")
    history.add_argument("--delay", type=float, default=0.25)
    history.set_defaults(func=command_official_history)
    tornsy = subs.add_parser("tornsy-audit", help="Retrieve and audit one Tornsy historical window.")
    tornsy.add_argument("symbol")
    tornsy.add_argument("--interval", default="m1", choices=sorted(TornsyClient.INTERVALS))
    tornsy.add_argument("--from-ts", type=int, default=None)
    tornsy.add_argument("--to-ts", type=int, default=None)
    tornsy.add_argument("--limit", type=int, default=2000)
    tornsy.set_defaults(func=command_tornsy_audit)
    reconcile = subs.add_parser("reconcile-live", help="Capture official and Tornsy live data and compare them.")
    reconcile.add_argument("--wait-seconds", type=float, default=0.0)
    reconcile.set_defaults(func=command_reconcile_live)
    watchlist = subs.add_parser("tornsy-watchlist", help="Capture Tornsy current watchlist.")
    watchlist.set_defaults(func=command_tornsy_watchlist)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ResearchToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
