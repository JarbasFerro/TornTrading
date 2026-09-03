#!/usr/bin/env python3
"""Probe Torn stock-log structure without persisting user log values.

The probe uses the official read-only Torn API. It persists only public stock-log
identifiers/titles plus matches against a preregistered set of generic candidate
field names and their primitive JSON type classes. It never writes log values,
log IDs, timestamps, titles, prices, fees, holdings, account totals, or unknown
field names from private user logs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from torn_research import ResearchToolError, TornApiClient, iso_utc

# Conservative pacing choice, not an asserted Torn API limit.
DEFAULT_INTER_REQUEST_DELAY_SECONDS = 0.7
USER_LOG_LIMIT = 100

# Frozen before observing the user's log schema. Only these generic names may be
# emitted from private log structures. Unknown keys are deliberately discarded.
CANDIDATE_FIELDS = frozenset({
    "stock",
    "stock_id",
    "stockid",
    "ticker",
    "acronym",
    "shares",
    "share",
    "amount",
    "quantity",
    "qty",
    "price",
    "share_price",
    "price_per_share",
    "fee",
    "fees",
    "total",
    "value",
    "gross",
    "gross_value",
    "proceeds",
    "net",
    "net_value",
    "profit",
    "loss",
    "cost",
    "cost_basis",
    "transaction_id",
})
ALLOWED_TYPES = frozenset({"null", "bool", "int", "float", "string", "object", "array", "other"})
ALLOWED_TOP_LEVEL = {
    "research_status",
    "source",
    "retrieved_at_utc",
    "stock_log_type_count",
    "user_log_access",
    "log_types",
    "interpretation",
}
ALLOWED_TYPE_KEYS = {
    "log_type_id",
    "public_name",
    "candidate_data_field_types",
    "candidate_params_field_types",
}
ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


def _extract_public_catalog(payload: Any, preferred_key: str) -> dict[int, str]:
    if not isinstance(payload, Mapping):
        raise ResearchToolError(f"Expected mapping response containing {preferred_key!r}.")
    candidate = payload.get(preferred_key, payload.get("data"))

    # Current API v2 shape: array of {id, title} objects.
    if isinstance(candidate, list):
        result: dict[int, str] = {}
        for row in candidate:
            if not isinstance(row, Mapping):
                continue
            raw_id = row.get("id")
            title = row.get("title", row.get("name"))
            try:
                item_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if isinstance(title, str) and title.strip():
                result[item_id] = title.strip()
        if result:
            return result

    # Legacy-compatible fallback used only to make the parser resilient to older
    # envelopes; current API v2 is array-based.
    if isinstance(candidate, Mapping):
        result = {}
        for key, value in candidate.items():
            try:
                item_id = int(key)
            except (TypeError, ValueError):
                continue
            if isinstance(value, str) and value.strip():
                result[item_id] = value.strip()
            elif isinstance(value, Mapping):
                title = value.get("title", value.get("name"))
                if isinstance(title, str) and title.strip():
                    result[item_id] = title.strip()
        if result:
            return result

    raise ResearchToolError(f"No usable public catalog found at {preferred_key!r}.")


def extract_logcategories(payload: Any) -> dict[int, str]:
    return _extract_public_catalog(payload, "logcategories")


def extract_logtypes(payload: Any) -> dict[int, str]:
    return _extract_public_catalog(payload, "logtypes")


def stock_category_ids(categories: Mapping[int, str]) -> list[int]:
    return sorted(category_id for category_id, title in categories.items() if "stock" in title.casefold())


def iter_log_entries(payload: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return
    candidate = payload.get("log", payload.get("logs"))
    if isinstance(candidate, list):
        for entry in candidate:
            if isinstance(entry, Mapping):
                yield entry
    elif isinstance(candidate, Mapping):
        # Legacy-compatible envelope fallback.
        for entry in candidate.values():
            if isinstance(entry, Mapping):
                yield entry


def log_type_id(entry: Mapping[str, Any]) -> int | None:
    details = entry.get("details")
    raw_id = details.get("id") if isinstance(details, Mapping) else entry.get("log")
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, list):
        return "array"
    return "other"


def accumulate_candidate_field_types(target: dict[str, set[str]], value: Any) -> None:
    if not isinstance(value, Mapping):
        return
    for key, field_value in value.items():
        if not isinstance(key, str):
            continue
        normalized = key.casefold()
        if normalized not in CANDIDATE_FIELDS:
            continue
        target.setdefault(normalized, set()).add(type_name(field_value))


def summarize_entries(
    declared_types: Mapping[int, str],
    payloads: Sequence[Any],
) -> list[dict[str, Any]]:
    state: dict[int, dict[str, Any]] = {
        log_id: {
            "log_type_id": log_id,
            "public_name": name,
            "candidate_data_field_types": {},
            "candidate_params_field_types": {},
        }
        for log_id, name in declared_types.items()
    }
    for payload in payloads:
        for entry in iter_log_entries(payload):
            entry_log_id = log_type_id(entry)
            if entry_log_id not in state:
                continue
            row = state[entry_log_id]
            accumulate_candidate_field_types(row["candidate_data_field_types"], entry.get("data"))
            accumulate_candidate_field_types(row["candidate_params_field_types"], entry.get("params"))

    rows: list[dict[str, Any]] = []
    for log_id in sorted(state):
        row = state[log_id]
        rows.append({
            "log_type_id": row["log_type_id"],
            "public_name": row["public_name"],
            "candidate_data_field_types": {
                key: sorted(types) for key, types in sorted(row["candidate_data_field_types"].items())
            },
            "candidate_params_field_types": {
                key: sorted(types) for key, types in sorted(row["candidate_params_field_types"].items())
            },
        })
    return rows


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != ALLOWED_TOP_LEVEL:
        raise ResearchToolError("Schema-probe output contains an unexpected top-level field.")
    if report.get("research_status") != "SCHEMA_OBSERVATION_ONLY":
        raise ResearchToolError("Unexpected research_status in schema report.")
    if report.get("source") != "official_torn_api_v2":
        raise ResearchToolError("Unexpected source in schema report.")
    retrieved = report.get("retrieved_at_utc")
    if not isinstance(retrieved, str) or not ISO_UTC_RE.match(retrieved):
        raise ResearchToolError("retrieved_at_utc must be a normalized UTC timestamp.")
    if report.get("user_log_access") not in {"available", "unavailable_or_failed"}:
        raise ResearchToolError("Unexpected user_log_access state.")
    if not isinstance(report.get("stock_log_type_count"), int) or report["stock_log_type_count"] < 0:
        raise ResearchToolError("stock_log_type_count must be a non-negative integer.")
    if not isinstance(report.get("interpretation"), str):
        raise ResearchToolError("interpretation must be a string.")

    rows = report.get("log_types")
    if not isinstance(rows, list):
        raise ResearchToolError("Schema-probe log_types must be a list.")
    if len(rows) != report["stock_log_type_count"]:
        raise ResearchToolError("stock_log_type_count does not match log_types length.")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != ALLOWED_TYPE_KEYS:
            raise ResearchToolError("Schema-probe output contains an unexpected per-type field.")
        if not isinstance(row.get("log_type_id"), int):
            raise ResearchToolError("Schema-probe log_type_id must be an integer.")
        if not isinstance(row.get("public_name"), str):
            raise ResearchToolError("Schema-probe public_name must be a string.")
        for field in ("candidate_data_field_types", "candidate_params_field_types"):
            mapping = row.get(field)
            if not isinstance(mapping, Mapping):
                raise ResearchToolError(f"{field} must be a mapping.")
            for key, classes in mapping.items():
                if key not in CANDIDATE_FIELDS:
                    raise ResearchToolError(f"Non-preregistered private field name attempted in {field}.")
                if not isinstance(classes, list) or not classes or not all(x in ALLOWED_TYPES for x in classes):
                    raise ResearchToolError(f"Unsafe type-class structure in {field}.")


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_report(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    if args.inter_request_delay < 0:
        raise ResearchToolError("--inter-request-delay must be non-negative.")

    client = TornApiClient(args.api_key)
    categories_observation = client.get("/torn/logcategories")
    categories = extract_logcategories(categories_observation.payload)
    category_ids = stock_category_ids(categories)
    if not category_ids:
        raise ResearchToolError("Official log-category catalog contained no stock-related category.")

    declared: dict[int, str] = {}
    for category_id in category_ids:
        observation = client.get(f"/torn/{category_id}/logtypes")
        declared.update(extract_logtypes(observation.payload))
    if not declared:
        raise ResearchToolError("Official stock log categories contained no log types.")

    payloads: list[Any] = []
    access = "available"
    try:
        for index, log_id in enumerate(sorted(declared)):
            observation = client.get("/user/log", {"log": str(log_id), "limit": USER_LOG_LIMIT})
            payloads.append(observation.payload)
            if args.inter_request_delay and index + 1 < len(declared):
                time.sleep(args.inter_request_delay)
    except ResearchToolError:
        # Do not preserve partial private-log observations when the probe is incomplete.
        payloads = []
        access = "unavailable_or_failed"

    rows = summarize_entries(declared, payloads)
    report = {
        "research_status": "SCHEMA_OBSERVATION_ONLY",
        "source": "official_torn_api_v2",
        "retrieved_at_utc": iso_utc(),
        "stock_log_type_count": len(rows),
        "user_log_access": access,
        "log_types": rows,
        "interpretation": (
            "Only preregistered generic candidate field names and primitive type classes are persisted. "
            "Unknown private-log keys and all private-log values are discarded; no execution mechanic is inferred by this probe alone."
        ),
    }
    write_report(Path(args.output), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if access == "available" else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe stock-log candidate fields without persisting user values.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="research/output/stock_log_schema/summary.json")
    parser.add_argument(
        "--inter-request-delay",
        type=float,
        default=DEFAULT_INTER_REQUEST_DELAY_SECONDS,
        help="Conservative delay between user-log requests; this is an operational pacing choice, not an API-limit claim.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
