#!/usr/bin/env python3
"""Immutable prospective evidence capture for preregistered HYP-001."""
from __future__ import annotations

import argparse, hashlib, json, math, statistics, sys, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from torn_research import ResearchToolError, TornsyClient, iso_utc, parse_tornsy_rows

HYPOTHESIS_ID = "HYP-001"
PROSPECTIVE_START = date(2026, 9, 10)
ANCHOR_WEEKDAY = 3  # Thursday, Monday=0
LOOKBACK_DAYS = 365
RETURN_HORIZON_DAYS = 7
PERCENTILE_Q = 0.10
MIN_TRAILING_RETURNS = 300
FETCH_LIMIT = 450
MAX_CAPTURE_DELAY_SECONDS = 3 * 3600


def load_symbols(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stocks = payload.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 35:
        raise ResearchToolError("HYP-001 requires the frozen 35-stock universe.")
    symbols = sorted({str(x.get("torn_symbol", "")).upper() for x in stocks if isinstance(x, dict)})
    if len(symbols) != 35 or "TCSE" in symbols:
        raise ResearchToolError("HYP-001 universe must contain 35 unique tradable stocks and exclude TCSE.")
    return symbols


def validate_anchor(anchor: date) -> None:
    if anchor < PROSPECTIVE_START:
        raise ResearchToolError(f"Prospective evidence may not start before {PROSPECTIVE_START.isoformat()}.")
    if anchor.weekday() != ANCHOR_WEEKDAY:
        raise ResearchToolError("HYP-001 anchor must be Thursday UTC.")


def anchor_datetime(anchor: date) -> datetime:
    return datetime(anchor.year, anchor.month, anchor.day, tzinfo=timezone.utc)


def validate_capture_window(anchor: date, now_utc: datetime) -> None:
    validate_anchor(anchor)
    if now_utc.tzinfo is None:
        raise ResearchToolError("Capture time must be timezone-aware.")
    now_utc = now_utc.astimezone(timezone.utc)
    anchor_dt = anchor_datetime(anchor)
    delay = (now_utc - anchor_dt).total_seconds()
    if delay < 0:
        raise ResearchToolError("Prospective cohort cannot be captured before its anchor.")
    if delay > MAX_CAPTURE_DELAY_SECONDS:
        raise ResearchToolError(
            f"Prospective capture window expired {int(delay)}s after anchor; maximum is {MAX_CAPTURE_DELAY_SECONDS}s. "
            "Missed cohorts are not backfilled."
        )


def anchor_timestamp(anchor: date) -> int:
    return int(anchor_datetime(anchor).timestamp())


def percentile(values: Sequence[float], q: float) -> float:
    if not values: raise ResearchToolError("Cannot calculate percentile of empty series.")
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1: return ordered[0]
    position = (len(ordered)-1)*q; lo, hi = math.floor(position), math.ceil(position)
    if lo == hi: return ordered[lo]
    weight = position-lo
    return ordered[lo]*(1-weight)+ordered[hi]*weight


def daily_open_map(rows: Sequence[Mapping[str, Any]], anchor_ts: int) -> dict[int, float]:
    result: dict[int, float] = {}
    for row in rows:
        ts, value = row.get("timestamp"), row.get("open")
        if not isinstance(ts, (int, float)) or not isinstance(value, (int, float)): continue
        t, p = int(ts), float(value)
        if t <= anchor_ts and t % 86400 == 0 and math.isfinite(p) and p > 0: result[t] = p
    return result


def completed_7d_returns(opens: Mapping[int, float], anchor_ts: int) -> dict[int, float]:
    span = RETURN_HORIZON_DAYS*86400; earliest = anchor_ts-LOOKBACK_DAYS*86400
    result: dict[int, float] = {}
    for end_ts, price in opens.items():
        if not earliest <= end_ts <= anchor_ts: continue
        start = opens.get(end_ts-span)
        if start is None or start <= 0: continue
        value = price/start-1
        if math.isfinite(value): result[end_ts] = value
    return result


def classify_stock(rows: Sequence[Mapping[str, Any]], anchor_ts: int) -> dict[str, Any]:
    opens = daily_open_map(rows, anchor_ts); prior_ts = anchor_ts-RETURN_HORIZON_DAYS*86400
    anchor_open, prior_open = opens.get(anchor_ts), opens.get(prior_ts)
    if anchor_open is None: return {"eligible": False, "reason": "missing_anchor_open"}
    base = {"anchor_open": round(anchor_open, 8)}
    if prior_open is None: return {**base, "eligible": False, "reason": "missing_exact_7d_start"}
    base["prior_7d_open"] = round(prior_open, 8)
    returns = completed_7d_returns(opens, anchor_ts)
    if anchor_ts not in returns: return {**base, "eligible": False, "reason": "missing_exact_7d_return"}
    trailing = [v for t, v in returns.items() if anchor_ts-LOOKBACK_DAYS*86400 <= t <= anchor_ts]
    if len(trailing) < MIN_TRAILING_RETURNS:
        return {**base, "eligible": False, "reason": "insufficient_trailing_returns", "trailing_return_count": len(trailing)}
    threshold, prior_return = percentile(trailing, PERCENTILE_Q), returns[anchor_ts]
    return {**base, "eligible": True, "reason": None, "prior_7d_return": round(prior_return, 12),
            "trailing_return_count": len(trailing), "trailing_p10": round(threshold, 12),
            "condition_met": bool(prior_return <= threshold)}


def sha256_file(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_stock(client: TornsyClient, symbol: str, attempts: int = 3):
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            observation = client.get_stock(symbol, "d1", limit=FETCH_LIMIT)
            return observation, parse_tornsy_rows(observation.payload, "d1")
        except Exception as exc:
            last = exc
            if attempt+1 < attempts: time.sleep(1+attempt)
    raise ResearchToolError(f"Tornsy fetch failed for {symbol}/d1: {last}")


def create_outcome(previous: Mapping[str, Any], current_records: Mapping[str, Mapping[str, Any]], current_anchor: str) -> dict[str, Any]:
    stocks: dict[str, Any] = {}; signaled: list[float] = []; nonsignaled: list[float] = []
    for symbol, prior in previous.get("stocks", {}).items():
        current = current_records.get(symbol, {})
        if not prior.get("eligible"):
            stocks[symbol] = {"eligible": False, "reason": "prior_cohort_ineligible"}; continue
        start, end = prior.get("anchor_open"), current.get("anchor_open")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start <= 0:
            stocks[symbol] = {"eligible": False, "reason": "missing_or_invalid_outcome_endpoint"}; continue
        forward = float(end)/float(start)-1; condition = bool(prior.get("condition_met"))
        stocks[symbol] = {"eligible": True, "condition_met": condition, "forward_7d_return": round(forward, 12)}
        (signaled if condition else nonsignaled).append(forward)
    sig_mean = statistics.fmean(signaled) if signaled else None
    non_mean = statistics.fmean(nonsignaled) if nonsignaled else None
    spread = sig_mean-non_mean if sig_mean is not None and non_mean is not None else None
    return {"hypothesis_id": HYPOTHESIS_ID, "record_type": "prospective_outcome",
            "cohort_anchor_utc": previous.get("anchor_utc"), "outcome_anchor_utc": current_anchor,
            "generated_at_utc": iso_utc(), "signaled_count": len(signaled), "non_signaled_count": len(nonsignaled),
            "signaled_mean_forward_7d_return": round(sig_mean,12) if sig_mean is not None else None,
            "non_signaled_mean_forward_7d_return": round(non_mean,12) if non_mean is not None else None,
            "weekly_cross_sectional_spread": round(spread,12) if spread is not None else None, "stocks": stocks}


def write_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists(): raise ResearchToolError(f"Prospective evidence already exists and will not be overwritten: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    anchor = date.fromisoformat(args.anchor_date)
    validate_capture_window(anchor, datetime.now(timezone.utc))
    anchor_ts = anchor_timestamp(anchor)
    root = Path(args.output_root); cohort_path = root/"cohorts"/f"{anchor.isoformat()}.json"
    if cohort_path.exists():
        print(json.dumps({"status":"already_captured","cohort":str(cohort_path)},indent=2)); return 0
    manifest, hypothesis = Path(args.manifest), Path(args.hypothesis_registry)
    symbols = load_symbols(manifest); client = TornsyClient(); records: dict[str, Any] = {}; source_audit: dict[str, Any] = {}
    source_errors: list[dict[str,str]] = []
    for symbol in symbols:
        try:
            obs, rows = fetch_stock(client, symbol); records[symbol] = classify_stock(rows, anchor_ts)
            source_audit[symbol] = {"request_started_at_utc":obs.request_started_at_utc,
                "response_received_at_utc":obs.response_received_at_utc,"payload_sha256":obs.payload_sha256,"parsed_rows":len(rows)}
        except ResearchToolError as exc: source_errors.append({"symbol":symbol,"message":str(exc)[:300]})
        time.sleep(args.request_delay)
    if source_errors: raise ResearchToolError(f"Cohort capture incomplete: {len(source_errors)} source errors; no evidence written")
    endpoint_failures = [s for s,r in records.items() if r.get("reason") in {"missing_anchor_open","missing_exact_7d_start","missing_exact_7d_return"}]
    if endpoint_failures: raise ResearchToolError(f"Cohort endpoint quality failure for {len(endpoint_failures)} stocks; no evidence written")
    capture_completed_at = datetime.now(timezone.utc)
    validate_capture_window(anchor, capture_completed_at)
    cohort = {"hypothesis_id":HYPOTHESIS_ID,"record_type":"prospective_cohort","anchor_utc":f"{anchor.isoformat()}T00:00:00Z",
        "generated_at_utc":iso_utc(capture_completed_at),"hypothesis_registry_sha256":sha256_file(hypothesis),"manifest_sha256":sha256_file(manifest),
        "collector_sha256":sha256_file(Path(__file__)),"capture_window_seconds":MAX_CAPTURE_DELAY_SECONDS,
        "price_convention":"Tornsy d1 fixed open at Thursday 00:00 UTC","lookback_days":LOOKBACK_DAYS,
        "return_horizon_days":RETURN_HORIZON_DAYS,"threshold_percentile":PERCENTILE_Q,"minimum_trailing_returns":MIN_TRAILING_RETURNS,
        "eligible_count":sum(bool(r.get("eligible")) for r in records.values()),
        "condition_met_count":sum(bool(r.get("eligible") and r.get("condition_met")) for r in records.values()),
        "stocks":records,"source_audit":source_audit,"research_only":True,"trading_recommendation":False}
    previous_anchor = anchor-timedelta(days=7); previous_path = root/"cohorts"/f"{previous_anchor.isoformat()}.json"
    pending: tuple[Path,dict[str,Any]]|None = None
    if previous_path.exists():
        outcome_path = root/"outcomes"/f"{previous_anchor.isoformat()}.json"
        if not outcome_path.exists():
            previous = json.loads(previous_path.read_text(encoding="utf-8"))
            pending = (outcome_path, create_outcome(previous, records, f"{anchor.isoformat()}T00:00:00Z"))
    write_immutable(cohort_path, cohort)
    if pending: write_immutable(*pending)
    print(json.dumps({"status":"captured","anchor":anchor.isoformat(),"cohort_path":str(cohort_path),
        "outcome_created":str(pending[0]) if pending else None,"eligible_count":cohort["eligible_count"],
        "condition_met_count":cohort["condition_met_count"]},indent=2)); return 0


def main(argv: Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--anchor-date",required=True); p.add_argument("--manifest",default="research/external_driver_candidates.json")
    p.add_argument("--hypothesis-registry",default="research/registry/hypotheses.yaml"); p.add_argument("--output-root",default="research/prospective/HYP-001")
    p.add_argument("--request-delay",type=float,default=.25)
    try: return run(p.parse_args(argv))
    except (ResearchToolError,ValueError) as exc: print(f"error: {exc}",file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
