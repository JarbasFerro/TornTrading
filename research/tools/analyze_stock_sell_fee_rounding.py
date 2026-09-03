#!/usr/bin/env python3
"""Test preregistered Torn stock-sale fee-rounding models without publishing trades.

This research-only tool reads recent official Torn API v2 Stock sell logs (type
5511) transiently. It persists aggregate model-fit diagnostics only. Raw logs,
transaction IDs, event timestamps, stock IDs, share counts, prices, fees, profits,
and monetary summaries are never written to the evidence report.

No Torn game action is performed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from torn_research import ResearchToolError, TornApiClient, iso_utc

SELL_LOG_TYPE_ID = 5511
DEFAULT_LOOKBACK_DAYS = 365
MAX_LOG_ROWS = 100
FEE_RATE = Decimal("0.001")
MIN_DISCRIMINATING_OBSERVATIONS = 6
MIN_WINNER_PAIRWISE_SEPARATION = 6

ROUNDING = {
    "floor": ROUND_FLOOR,
    "ceiling": ROUND_CEILING,
    "half_up": ROUND_HALF_UP,
    "half_even": ROUND_HALF_EVEN,
}

# These are exact identities for non-negative gross values and therefore cannot
# be distinguished by any sale receipt. Keep the simpler total_value expression
# as the canonical representative rather than creating impossible uniqueness.
EXACT_REDUNDANT_GROSS_MODELS = {
    ("floor", "floor"),       # floor(floor(x) / 1000) == floor(x / 1000)
    ("ceiling", "ceiling"),   # ceil(ceil(x) / 1000) == ceil(x / 1000)
    ("floor", "half_up"),     # half-up threshold is an integer $500 boundary
}

REPORT_KEYS = {
    "research_status",
    "source",
    "retrieved_at_utc",
    "lookback_days",
    "sell_log_type_id",
    "api_row_cap",
    "usable_observations",
    "rejected_observations",
    "candidate_model_count",
    "discriminating_observations",
    "winner_minimum_pairwise_separation",
    "model_results",
    "prediction_equivalence_classes",
    "perfect_models",
    "decision_status",
    "acceptance_rule",
    "privacy_note",
}
MODEL_RESULT_KEYS = {"model", "matches", "mismatches", "match_rate"}
EQUIVALENCE_KEYS = {"models", "class_size"}
DECISION_STATES = {
    "UNIQUE_PERFECT_MODEL",
    "MULTIPLE_EQUIVALENT_PERFECT_MODELS",
    "MULTIPLE_NON_EQUIVALENT_PERFECT_MODELS",
    "NO_PERFECT_MODEL",
    "INSUFFICIENT_DISCRIMINATION",
    "INSUFFICIENT_WINNER_SEPARATION",
    "NO_USABLE_OBSERVATIONS",
}
ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


@dataclass(frozen=True)
class SaleObservation:
    amount: int
    price: Decimal
    fee: int


@dataclass(frozen=True)
class FeeModel:
    name: str
    predict: Callable[[SaleObservation], int]


def parse_decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("not a decimal")
    text = str(value).strip().replace(",", "").replace("$", "")
    if not text:
        raise ValueError("empty decimal")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def parse_sale_entry(entry: Any) -> SaleObservation | None:
    if not isinstance(entry, Mapping):
        return None
    details = entry.get("details")
    try:
        log_id = int(details.get("id")) if isinstance(details, Mapping) else None
    except (TypeError, ValueError):
        return None
    if log_id != SELL_LOG_TYPE_ID:
        return None
    data = entry.get("data")
    if not isinstance(data, Mapping):
        return None
    try:
        amount = int(data["amount"])
        price = parse_decimal(data["price"])
        fee = int(data["fees"])
    except (KeyError, TypeError, ValueError):
        return None
    if amount <= 0 or price <= 0 or fee < 0:
        return None
    return SaleObservation(amount=amount, price=price, fee=fee)


def extract_sales(payload: Any) -> tuple[list[SaleObservation], int]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("log"), list):
        raise ResearchToolError("Expected current Torn API v2 UserLogsResponse.log array.")
    sales: list[SaleObservation] = []
    rejected = 0
    for entry in payload["log"]:
        parsed = parse_sale_entry(entry)
        if parsed is None:
            rejected += 1
        else:
            sales.append(parsed)
    return sales, rejected


def round_integer(value: Decimal, mode: str) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUNDING[mode]))


def build_models() -> list[FeeModel]:
    """Return the frozen, behaviorally non-redundant candidate family.

    Families:
      A) total_value: price is per-share; fee is rounded once after price*amount*0.1%.
      B) gross_first: price*amount is first integer-rounded, then 0.1% fee is rounded.
      C) price_is_total: defensive semantic alternative where logged price is total sale value.
      D) per_share_fee_first: fee per share is rounded before multiplying by amount.

    Three gross-first formulas are excluded because they are exact identities of
    simpler total-value formulas for non-negative values. Sample-dependent
    equivalences are *not* collapsed: if history cannot distinguish them, the
    empirical gate remains open.

    The last two families are falsification controls. Official Torn documentation
    says the fee is 0.1% of total value sold, so they are not preferred absent
    evidence.
    """
    models: list[FeeModel] = []

    for fee_round in ROUNDING:
        name = f"total_value__fee_{fee_round}"
        models.append(FeeModel(
            name,
            lambda obs, fr=fee_round: round_integer(obs.price * Decimal(obs.amount) * FEE_RATE, fr),
        ))

    for gross_round in ROUNDING:
        for fee_round in ROUNDING:
            if (gross_round, fee_round) in EXACT_REDUNDANT_GROSS_MODELS:
                continue
            name = f"gross_{gross_round}__fee_{fee_round}"
            models.append(FeeModel(
                name,
                lambda obs, gr=gross_round, fr=fee_round: round_integer(
                    Decimal(round_integer(obs.price * Decimal(obs.amount), gr)) * FEE_RATE,
                    fr,
                ),
            ))

    for fee_round in ROUNDING:
        name = f"price_is_total__fee_{fee_round}"
        models.append(FeeModel(
            name,
            lambda obs, fr=fee_round: round_integer(obs.price * FEE_RATE, fr),
        ))

    for share_fee_round in ROUNDING:
        name = f"per_share_fee_{share_fee_round}__then_multiply"
        models.append(FeeModel(
            name,
            lambda obs, sr=share_fee_round: round_integer(obs.price * FEE_RATE, sr) * obs.amount,
        ))

    return sorted(models, key=lambda model: model.name)


def prediction_vectors(observations: Sequence[SaleObservation], models: Sequence[FeeModel]) -> dict[str, tuple[int, ...]]:
    return {model.name: tuple(model.predict(obs) for obs in observations) for model in models}


def discriminating_observation_count(vectors: Mapping[str, Sequence[int]]) -> int:
    if not vectors:
        return 0
    values = list(vectors.values())
    if not values:
        return 0
    width = len(values[0])
    return sum(len({vector[index] for vector in values}) > 1 for index in range(width))


def minimum_pairwise_separation(vectors: Mapping[str, Sequence[int]], winner: str) -> int | None:
    """Minimum number of observations separating winner from any competitor."""
    if winner not in vectors:
        raise ValueError("winner is not present in prediction vectors")
    winner_vector = vectors[winner]
    competitors = [name for name in vectors if name != winner]
    if not competitors:
        return None
    separations = [
        sum(a != b for a, b in zip(winner_vector, vectors[name]))
        for name in competitors
    ]
    return min(separations)


def equivalence_classes(vectors: Mapping[str, tuple[int, ...]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, ...], list[str]] = {}
    for model, vector in vectors.items():
        groups.setdefault(vector, []).append(model)
    rows = [
        {"models": sorted(names), "class_size": len(names)}
        for names in groups.values()
    ]
    rows.sort(key=lambda row: (row["models"][0], row["class_size"]))
    return rows


def analyze(observations: Sequence[SaleObservation], rejected: int, *, lookback_days: int, retrieved_at: str) -> dict[str, Any]:
    models = build_models()
    vectors = prediction_vectors(observations, models)
    observed_fees = tuple(obs.fee for obs in observations)

    result_rows: list[dict[str, Any]] = []
    perfect: list[str] = []
    for model in models:
        vector = vectors[model.name]
        matches = sum(predicted == observed for predicted, observed in zip(vector, observed_fees))
        mismatches = len(observations) - matches
        if observations and mismatches == 0:
            perfect.append(model.name)
        result_rows.append({
            "model": model.name,
            "matches": matches,
            "mismatches": mismatches,
            "match_rate": round(matches / len(observations), 6) if observations else None,
        })

    discrim = discriminating_observation_count(vectors)
    classes = equivalence_classes(vectors)
    class_by_model: dict[str, int] = {}
    for index, row in enumerate(classes):
        for model_name in row["models"]:
            class_by_model[model_name] = index

    winner_separation = minimum_pairwise_separation(vectors, perfect[0]) if len(perfect) == 1 else None

    if not observations:
        decision = "NO_USABLE_OBSERVATIONS"
    elif discrim < MIN_DISCRIMINATING_OBSERVATIONS:
        decision = "INSUFFICIENT_DISCRIMINATION"
    elif len(perfect) == 1 and (winner_separation or 0) < MIN_WINNER_PAIRWISE_SEPARATION:
        decision = "INSUFFICIENT_WINNER_SEPARATION"
    elif len(perfect) == 1:
        decision = "UNIQUE_PERFECT_MODEL"
    elif len(perfect) > 1 and len({class_by_model[name] for name in perfect}) == 1:
        decision = "MULTIPLE_EQUIVALENT_PERFECT_MODELS"
    elif len(perfect) > 1:
        decision = "MULTIPLE_NON_EQUIVALENT_PERFECT_MODELS"
    else:
        decision = "NO_PERFECT_MODEL"

    report = {
        "research_status": "AGGREGATE_HISTORICAL_OBSERVATION",
        "source": "official_torn_api_v2_user_log_5511",
        "retrieved_at_utc": retrieved_at,
        "lookback_days": lookback_days,
        "sell_log_type_id": SELL_LOG_TYPE_ID,
        "api_row_cap": MAX_LOG_ROWS,
        "usable_observations": len(observations),
        "rejected_observations": rejected,
        "candidate_model_count": len(models),
        "discriminating_observations": discrim,
        "winner_minimum_pairwise_separation": winner_separation,
        "model_results": result_rows,
        "prediction_equivalence_classes": classes,
        "perfect_models": sorted(perfect),
        "decision_status": decision,
        "acceptance_rule": (
            f"P0-E5 may be proposed for closure only when there are at least {MIN_DISCRIMINATING_OBSERVATIONS} "
            f"globally discriminating observations, exactly one perfect non-redundant candidate model, and that winner "
            f"differs from every competitor on at least {MIN_WINNER_PAIRWISE_SEPARATION} observations. Sample-dependent "
            "ties or weak nearest-competitor separation remain unresolved."
        ),
        "privacy_note": (
            "No raw logs, transaction IDs, event timestamps, stock IDs, share counts, prices, fees, profits, losses, "
            "monetary totals, or per-trade prediction vectors are persisted."
        ),
    }
    assert_safe_report(report)
    return report


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != REPORT_KEYS:
        raise ResearchToolError("Fee-rounding report contains an unexpected top-level field.")
    if report.get("research_status") != "AGGREGATE_HISTORICAL_OBSERVATION":
        raise ResearchToolError("Unexpected research_status.")
    if report.get("source") != "official_torn_api_v2_user_log_5511":
        raise ResearchToolError("Unexpected source.")
    retrieved = report.get("retrieved_at_utc")
    if not isinstance(retrieved, str) or not ISO_UTC_RE.match(retrieved):
        raise ResearchToolError("retrieved_at_utc must be normalized UTC.")
    for key in (
        "lookback_days",
        "sell_log_type_id",
        "api_row_cap",
        "usable_observations",
        "rejected_observations",
        "candidate_model_count",
        "discriminating_observations",
    ):
        if not isinstance(report.get(key), int) or report[key] < 0:
            raise ResearchToolError(f"{key} must be a non-negative integer.")
    winner_separation = report.get("winner_minimum_pairwise_separation")
    if winner_separation is not None and (not isinstance(winner_separation, int) or winner_separation < 0):
        raise ResearchToolError("winner_minimum_pairwise_separation must be null or a non-negative integer.")
    if report.get("sell_log_type_id") != SELL_LOG_TYPE_ID:
        raise ResearchToolError("Unexpected sell_log_type_id.")
    if report.get("api_row_cap") != MAX_LOG_ROWS:
        raise ResearchToolError("Unexpected api_row_cap.")
    if report.get("candidate_model_count") != len(build_models()):
        raise ResearchToolError("candidate_model_count does not match frozen family.")
    if report.get("decision_status") not in DECISION_STATES:
        raise ResearchToolError("Unexpected decision_status.")
    if not isinstance(report.get("acceptance_rule"), str) or not isinstance(report.get("privacy_note"), str):
        raise ResearchToolError("Narrative report fields must be strings.")

    model_names = {model.name for model in build_models()}
    results = report.get("model_results")
    if not isinstance(results, list) or len(results) != len(model_names):
        raise ResearchToolError("model_results must contain the entire frozen candidate family.")
    seen: set[str] = set()
    usable = report["usable_observations"]
    for row in results:
        if not isinstance(row, Mapping) or set(row) != MODEL_RESULT_KEYS:
            raise ResearchToolError("Unsafe model result structure.")
        name = row.get("model")
        if name not in model_names or name in seen:
            raise ResearchToolError("Unknown or duplicate model name.")
        seen.add(name)
        matches = row.get("matches")
        mismatches = row.get("mismatches")
        if not isinstance(matches, int) or not isinstance(mismatches, int) or matches < 0 or mismatches < 0:
            raise ResearchToolError("Model match counts must be non-negative integers.")
        if matches + mismatches != usable:
            raise ResearchToolError("Model match counts do not sum to usable observations.")
        rate = row.get("match_rate")
        if rate is not None and (not isinstance(rate, (int, float)) or not 0 <= rate <= 1):
            raise ResearchToolError("Invalid model match rate.")

    classes = report.get("prediction_equivalence_classes")
    if not isinstance(classes, list):
        raise ResearchToolError("prediction_equivalence_classes must be a list.")
    class_models: list[str] = []
    for row in classes:
        if not isinstance(row, Mapping) or set(row) != EQUIVALENCE_KEYS:
            raise ResearchToolError("Unsafe equivalence-class structure.")
        names = row.get("models")
        if not isinstance(names, list) or not names or not all(name in model_names for name in names):
            raise ResearchToolError("Invalid equivalence-class model list.")
        if row.get("class_size") != len(names):
            raise ResearchToolError("Incorrect equivalence class size.")
        class_models.extend(names)
    if sorted(class_models) != sorted(model_names):
        raise ResearchToolError("Equivalence classes must partition the frozen model family.")

    perfect = report.get("perfect_models")
    if not isinstance(perfect, list) or not all(name in model_names for name in perfect):
        raise ResearchToolError("Invalid perfect_models.")
    if len(perfect) == 1 and winner_separation is None:
        raise ResearchToolError("Unique perfect model requires a winner separation diagnostic.")
    if len(perfect) != 1 and winner_separation is not None:
        raise ResearchToolError("Winner separation must be null unless exactly one perfect model exists.")


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_report(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_server_timestamp(client: TornApiClient) -> int:
    observation = client.get("/torn/timestamp")
    payload = observation.payload
    if not isinstance(payload, Mapping):
        raise ResearchToolError("Expected mapping from /torn/timestamp.")
    raw = payload.get("timestamp")
    if raw is None and isinstance(payload.get("data"), Mapping):
        raw = payload["data"].get("timestamp")
    try:
        timestamp = int(raw)
    except (TypeError, ValueError):
        raise ResearchToolError("No usable official server timestamp returned.") from None
    if timestamp <= 0:
        raise ResearchToolError("Official server timestamp must be positive.")
    return timestamp


def run(args: argparse.Namespace) -> int:
    if not 1 <= args.lookback_days <= 3650:
        raise ResearchToolError("--lookback-days must be between 1 and 3650.")

    client = TornApiClient(args.api_key)
    to_ts = resolve_server_timestamp(client)
    from_ts = to_ts - args.lookback_days * 86400
    observation = client.get(
        "/user/log",
        {
            "log": str(SELL_LOG_TYPE_ID),
            "from": from_ts,
            "to": to_ts,
            "limit": MAX_LOG_ROWS,
        },
    )
    sales, rejected = extract_sales(observation.payload)
    report = analyze(
        sales,
        rejected,
        lookback_days=args.lookback_days,
        retrieved_at=iso_utc(),
    )
    write_report(Path(args.output), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate historical Torn stock-sale fee-rounding evidence.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--output", default="research/output/fee_rounding/summary.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
